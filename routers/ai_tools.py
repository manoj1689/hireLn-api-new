import uuid
from fastapi import APIRouter, Depends, FastAPI, Form, HTTPException, Query, UploadFile, File, Header
from fastapi.middleware.cors import CORSMiddleware
import openai
from pydantic import BaseModel, Field, ValidationError
from typing import List, Dict, Any, Optional, Union
from mongoDb.jd_parser import process_jd
from mongoDb.resume_embeddings import get_resume_text_by_id, read_resume, save_resume_with_embeddings
from service.candidate_service import create_candidate_from_parsed_data
from utils.openai_client import create_openai_chat
from dotenv import load_dotenv
import json
import logging
import re
from requests import Session

# New imports for resume parsing

import base64
import fitz # PyMuPDF
import os
import tempfile
import requests
from pathlib import Path
from googleapiclient.discovery import build
from google.oauth2 import service_account
from fastapi import Depends
from database import get_db  # async session getter (assumed)
from prisma import Prisma 
from io import BytesIO
from models.schemas import (
    CandidateResponse,
    CandidateCreate,
    ErrorResponse,
    UserResponse,
    # New imports for resume parsing
    ParseResumesFromDriveResponse,
    ResumeParseResult
)
from auth.dependencies import get_current_user, get_user_or_interview_auth

router = APIRouter()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from a .env file
load_dotenv()

# Constants for resume parsing
# SERVER = "http://103.99.186.164:11434"
# MODEL = "qwen2.5vl:7b"

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# Load credentials from .env
creds_info = json.loads(os.getenv("GOOGLE_CREDENTIALS"))


openai_model = os.getenv("OPENAI_MODEL", "gpt-4")
openai_api_key = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key=openai_api_key)

# Initialize Google Drive service (global for efficiency)
try:
    credentials = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    drive_service = build("drive", "v3", credentials=credentials)
except Exception as e:
    logger.error(f"Failed to initialize Google Drive service: {e}")
    drive_service = None # Set to None if initialization fails, so endpoints can check

def clean_extracted_text(text: str) -> str:
    text = re.sub(r'\n{2,}', '\n\n', text).strip()
    return text

def extract_text_with_pymupdf(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    return "\n".join(page.get_text() for page in doc)


# Utility: extract structured data from a PDF using Open AI
def extract_resume_data(text: str) -> CandidateCreate:
    prompt = (
        "You are a strict JSON generator for extracting structured candidate data from resumes.\n"
        "Extract ONLY the following fields from the given resume text.\n"
        "Your output MUST be a valid, strictly formatted JSON object with ALL specified fields.\n\n"
        "⚠️ RULES:\n"
        "- Always include **ALL** fields listed below.\n"
        "- If data is missing:\n"
        "  - Use an empty string (`\"\"`) for string fields\n"
        "  - Use an empty array (`[]`) for list fields\n"
        "  - Use an empty object (`{}`) for object fields\n"
        "- Do NOT include extra fields or explanations.\n"
        "- Ensure all nested structures follow the expected format strictly.\n\n"
        "### Required JSON Fields:\n"
        "{\n"
        '  "name": string,\n'
        '  "email": string,\n'
        '  "phone": string,\n'
        '  "address": array of strings,\n'
        '  "location": string,\n'
        '  "personalInfo": {\n'
        '    "dob": string,\n'
        '    "gender": string,\n'
        '    "maritalStatus": string,\n'
        '    "nationality": string\n'
        '  },\n'
        '  "summary": string,\n'
        '  "education": [\n'
        '    {\n'
        '      "degree": string,\n'
        '      "institution": string,\n'
        '      "location": string,\n'
        '      "start_date": string,\n'
        '      "end_date": string,\n'
        '      "grade": string\n'
        '    }\n'
        '  ],\n'
        '  "experience": [\n'
        '    {\n'
        '      "title": string,\n'
        '      "company": string,\n'
        '      "location": string,\n'
        '      "start_date": string,\n'
        '      "end_date": string,\n'
        '      "description": string\n'
        '    }\n'
        '  ],\n'
        '  "previousJobs": [\n'
        '    {\n'
        '      "title": string,\n'
        '      "company": string,\n'
        '      "location": string,\n'
        '      "start_date": string,\n'
        '      "end_date": string,\n'
        '      "description": array of strings\n'
        '    }\n'
        '  ],\n'
        '  "internships": array of strings,\n'
        '  "technicalSkills": array of strings,\n'
        '  "softSkills": array of strings,\n'
        '  "languages": [\n'
        '    {\n'
        '      "language": string,\n'
        '      "proficiency": string\n'
        '    }\n'
        '  ],\n'

        '  "certifications": [\n'
        '    {\n'
        '      "title": string,\n'
        '      "issuer": string,\n'
        '      "date": string\n'
        '    }\n'
        '  ],\n'
        '  "projects": [\n'
        '    {\n'
        '      "title": string,\n'
        '      "description": string,\n'
        '      "url": string\n'
        '    }\n'
        '  ],\n'
        '  "hobbies": array of strings,\n'
        '  "salaryExpectation": integer,\n'
        '  "department": string\n'
        '  "resume": string (optional)\n'
        '  "portfolio": string (optional)\n'
        '  "linkedin": string (optional)\n'
        '  "github": string (optional)\n'
        '}\n\n'
        "### Resume text:\n"
        f"{text}\n\n"
        "### Response:\n"
        "Return a valid JSON object only. No markdown. No explanations. No extra keys."
    )
    messages = [
        {"role": "user", "content": prompt}
    ]

    try:
        response = client.chat.completions.create(
            model=openai_model,
            messages=messages,
            temperature=0.2,
            max_tokens=2000
        )
        content = response.choices[0].message.content.strip()

        # Strip ```json ... ``` wrappers if present
        content = re.sub(r"^```(json)?|```$", "", content.strip(), flags=re.MULTILINE).strip()

        parsed_data = json.loads(content)
        # ✅ Ensure "isGuest" is explicitly False
        parsed_data["isGuest"] = False
        return CandidateCreate(**parsed_data)  # Validate via Pydantic
    except Exception as e:
        logger.error("OpenAI API call failed", exc_info=True)
        raise HTTPException(status_code=500, detail=f"OpenAI API failed: {str(e)}")

# --- process_resume_file function ---
async def process_resume_file(
    temp_path: Path,
    file_name: str,
    current_user: UserResponse,
    db: Prisma,
    resume_id: str = None  # require resume_id
):
    if not resume_id:
        raise ValueError(f"Missing resume_id for file '{file_name}'")

    try:
        # 1️⃣ Read PDF
        with open(temp_path, "rb") as f:
            pdf_bytes = f.read()

        # 2️⃣ Extract and clean text
        raw_text = extract_text_with_pymupdf(pdf_bytes)
        cleaned_text = clean_extracted_text(raw_text)

        # 3️⃣ Parse resume data
        parsed_data = extract_resume_data(cleaned_text)

        # 4️⃣ Create candidate record with resume_id
        success, message = await create_candidate_from_parsed_data(
            parsed_data,
            current_user,
            db,
            resume_id=resume_id,
            resume_name=file_name
            
        )

        logger.info(f"Processed {file_name}: success={success}, message={message}")
        return {"file": file_name, "success": success, "message": message, "resume_id": resume_id}

    except Exception as e:
        logger.warning(f"Failed to process {file_name}: {e}")
        return {"file": file_name, "success": False, "message": str(e), "resume_id": resume_id}


# --- create-candidate_resume_upload endpoint ---
@router.post("/create-candidate")
async def create_candidate(
    file: UploadFile = File(..., description="Upload a PDF resume to create candidate"),
    current_user: UserResponse = Depends(get_current_user),
    db: Prisma = Depends(get_db)
):
    """
    Upload a single resume, parse it, create a candidate record and return result
    """
    resume_id = str(uuid.uuid4())
    temp_path = None
    file_name = file.filename

    try:
        # ✅ Save uploaded PDF temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(await file.read())
            temp_path = Path(temp_file.name)

        # ✅ Read and clean resume text
        raw_text = read_resume(temp_path)
        cleaned_text = clean_extracted_text(raw_text)

        # ✅ Parse structured data from resume
        parsed_data = extract_resume_data(cleaned_text)

        # ✅ Save candidate to DB
        success, message, candidate_info = await create_candidate_from_parsed_data(
            parsed_data,
            current_user,
            db,
            resume_id=resume_id,
            resume_name=file_name
        )

        return {
            "status": success,
            "message": message,
            "candidate": candidate_info
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create candidate: {str(e)}")

    finally:
        # ✅ Cleanup temp file
        if temp_path and temp_path.exists():
            temp_path.unlink()

            
# --- parse_resumes_upload endpoint ---
@router.post("/parse-resumes-upload")
async def parse_resumes_upload(
    files: List[UploadFile] = File(..., description="List of PDF resume files to upload and parse."),
    current_user: UserResponse = Depends(get_current_user),
    db: Prisma = Depends(get_db)
):
    """
    Upload multiple resumes, save to MongoDB (get _id), process each file (embedding/chunking),
    and return summary with resume name and resume_id.
    """
    creation_summary = []

    for file in files:
        file_name = file.filename
        temp_path = None
        try:
            # 1️⃣ Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                temp_file.write(await file.read())
                temp_path = Path(temp_file.name)

            # 2️⃣ Read resume text
            text = read_resume(temp_path)
            

            # 3️⃣ Save resume to MongoDB and get inserted ID
            resume_id = save_resume_with_embeddings(file_name, text)

          

            # 5️⃣ Add summary entry (use result from process_resume_file)
            creation_summary.append({
                "resume_name": file_name,
                "resume_id": str(resume_id)
               
            })

        except Exception as e:
            creation_summary.append({
                "resume_name": file_name,
                "success": False,
                "message": str(e)
            })

        finally:
            # 6️⃣ Cleanup temp file
            if temp_path and temp_path.exists():
                temp_path.unlink(missing_ok=True)

    return {"summary": creation_summary}

@router.get("/match/{job_id}", response_model=Any)
async def get_matched_candidates(
    job_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user)
):
    """Get candidates matched to a specific job using JD embeddings"""
    db = get_db()

    job = await db.job.find_unique(where={"id": job_id, "userId": current_user.id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    jd_text = (
        f"Job Title: {job.title}\n"
        f"Skills: {', '.join(job.skills or [])}\n"
        f"Experience: {job.experience}\n"
        f"Education: {job.education}\n"
        f"Description: {job.description}\n"
    )

    # Call the JD processor for comparison
    match_results = process_jd(jd_text)

    # Optionally sort resumes by score
    sorted_resumes = sorted(
        match_results["results"],
        key=lambda x: x["overall_semantic_score"],
        reverse=True
    )

    # Limit the results
    top_resumes = sorted_resumes[skip : skip + limit]

    return top_resumes


@router.post("/process-resume/preview-candidate/{resume_id}")
async def preview_candidate_from_resume(
    resume_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Parse an existing resume and return candidate-like object without saving to DB.
    """
    try:
        # 1️⃣ Fetch resume text from MongoDB
        resume_data = get_resume_text_by_id(resume_id)
        if not resume_data:
            raise HTTPException(status_code=404, detail="Resume not found")

        resume_text = resume_data.get("text", "")
        resume_file_name = resume_data.get("filename", "unknown")

        # 2️⃣ Parse resume text
        parsed_data = extract_resume_data(resume_text)
        print("parsed data",parsed_data)
        # 3️⃣ Create candidate object (in memory)
        

        # 4️⃣ Return the candidate object
        return {
            "status": "success",
            "message": "Candidate preview generated successfully",
            "resume_id": resume_id,
            "filename": resume_file_name,
            "candidate_data": parsed_data,  # return as object/dict
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-resume/{resume_id}")
async def process_resume_by_id(
    resume_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: Prisma = Depends(get_db)
):
    try:
        resume_data = get_resume_text_by_id(resume_id)
        if not resume_data:
            raise HTTPException(status_code=404, detail="Resume not found")

        resume_text = resume_data.get("text", "")
        resume_file_name = resume_data.get("filename", "unknown")

        parsed_data = extract_resume_data(resume_text)

        success, message, candidate_info = await create_candidate_from_parsed_data(
            parsed_data,
            current_user,
            db,
            resume_id=resume_id,
            resume_name=resume_file_name
        )

        return {
            "status": success,
            "message": message,
            "candidate": candidate_info
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/parse_resumes_from_drive")
async def parse_resumes_from_drive(
    folder_id: str = Query(..., description="Google Drive folder ID containing the resumes."),
    limit: int = Query(4, gt=0, le=100),
    current_user: UserResponse = Depends(get_current_user),
    db: Prisma = Depends(get_db)
):
    if not drive_service:
        raise HTTPException(status_code=500, detail="Google Drive service not initialized.")

    results = []

    try:
        query = f"'{folder_id}' in parents and trashed = false and mimeType='application/pdf'"
        response = drive_service.files().list(q=query, fields="files(id, name)").execute()
        files = response.get("files", [])[:limit]

        for file in files:
            file_id = file["id"]
            file_name = file["name"]
            temp_path = Path(tempfile.gettempdir()) / file_name

            try:
                # Download file
                download_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
                headers = {"Authorization": f"Bearer {credentials.token}"}
                res = requests.get(download_url, headers=headers)

                if res.status_code != 200:
                    raise Exception(f"Failed to download {file_name} from Google Drive.")

                with open(temp_path, "wb") as f:
                    f.write(res.content)

                result = await process_resume_file(temp_path, file_name, current_user, db)
                results.append(result)

            except Exception as e:
                results.append({
                    "file": file_name,
                    "success": False,
                    "message": str(e)
                })
            finally:
                if temp_path.exists():
                    temp_path.unlink(missing_ok=True)

        return {"summary": results}

    except Exception as e:
        logger.exception("Error in parse_resumes_from_drive")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
   
