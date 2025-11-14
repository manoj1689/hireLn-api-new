import os
import re
from bson import ObjectId
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from openai import OpenAI
import numpy as np
from textwrap import wrap
from datetime import datetime
from dotenv import load_dotenv
from PyPDF2 import PdfReader
load_dotenv()

# MongoDB connection
# MongoDB Atlas setup
# ------------------------------
MONGO_URI = os.getenv("MONGO_URI")  # should be your Atlas URI
if not MONGO_URI:
    raise ValueError("Please set MONGO_URI in your environment variables!")

# Use Server API v1 for Atlas
client = MongoClient(MONGO_URI, server_api=ServerApi('1'))

db = client["hireln_db"]
resumes_collection = db["resumes"]

# OpenAI client
client_openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def read_resume(file_path: str) -> str:
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 100):
    """
    Split text into chunks of max chunk_size characters with overlap.
    """
    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - chunk_overlap  # move start, keeping overlap

    return chunks


def get_embedding(text: str, model: str = "text-embedding-3-large"):
    """
    Get embedding for a text chunk.
    """
    text = text.strip()
    if not text:
        return np.zeros(1).tolist()  # fallback for empty text
    response = client_openai.embeddings.create(model=model, input=text)
    return response.data[0].embedding


from datetime import datetime

def save_resume_with_embeddings(
    filename: str,
    resume_text: str,
    user_id: str,
    candidate_id: str
):
    """
    Save resume with embeddings, extracted name/email, userId, and candidateId into MongoDB.
    Prevents duplicate resume uploads for the same candidate and filename.
    """

    # 1️⃣ Check if resume with the same filename already exists for this candidate
    existing_resume = resumes_collection.find_one({
        "filename": filename,
        "candidateId": candidate_id
    })
    if existing_resume:
        raise ValueError(f"Resume '{filename}' already exists for this candidate.")

    # 2️⃣ Extract candidate info (optional)
    candidate_info = extract_name_email(resume_text)
    name = candidate_info.get("name")
    email = candidate_info.get("email")

    # 3️⃣ Chunk resume text for embeddings
    chunks = chunk_text(resume_text, chunk_size=500)

    # 4️⃣ Compute embeddings for each chunk
    chunk_data = []
    for chunk in chunks:
        emb = get_embedding(chunk)
        chunk_data.append({
            "text": chunk,
            "embedding": emb
        })

    # 5️⃣ Create MongoDB document
    resume_doc = {
        "filename": filename,
        "uploaded_at": datetime.utcnow(),
        "name": name,
        "email": email,
        "userId": user_id,
        "candidateId": candidate_id,
        "chunks": chunk_data
    }

    # 6️⃣ Insert into MongoDB
    result = resumes_collection.insert_one(resume_doc)

    print(f"✅ Saved '{filename}' for candidate {candidate_id} with {len(chunk_data)} chunks. Name: {name}, Email: {email}")
    return result.inserted_id


def get_resume_text_by_id(resume_id: str) -> dict:
    """
    Fetch a resume from MongoDB by resume_id and combine all chunk texts into a single string.
    Returns a dict with 'text' and 'filename'.
    """
    if not ObjectId.is_valid(resume_id):
        raise ValueError("Invalid resume_id")

    resume_doc = resumes_collection.find_one({"_id": ObjectId(resume_id)})
    if not resume_doc:
        raise ValueError(f"No resume found for resume_id: {resume_id}")

    chunks = resume_doc.get("chunks", [])
    combined_text = "\n".join(chunk.get("text", "") for chunk in chunks)
    filename = resume_doc.get("filename", "unknown.pdf")
    
    return {
        "text": combined_text,
        "filename": filename
    }

def extract_name_email(text: str):
    """
    Extracts candidate name and email from resume text.

    Args:
        text (str): The full text extracted from a resume.

    Returns:
        dict: { "name": str or None, "email": str or None }
    """

    # --- Extract email using regex ---
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    email_match = re.search(email_pattern, text)
    email = email_match.group(0) if email_match else None

    # --- Try to extract name from the top lines ---
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    possible_name = None

    if lines:
        # Check first 3 lines for name-like patterns
        for line in lines[:5]:
            # Heuristic: likely a name if it has 2 words, both starting with uppercase letters
            if re.match(r"^[A-Z][a-z]+\s[A-Z][a-z]+", line):
                possible_name = line
                break

    # Fallback if no name found
    if not possible_name and email:
        # Derive name from email username part
        username = email.split("@")[0]
        username = username.replace(".", " ").replace("_", " ")
        possible_name = username.title()

    return {
        "name": possible_name,
        "email": email
    }





def delete_resumes_by_candidate_id(candidate_id: str):
    """
    Delete all resume documents belonging to a given candidate from MongoDB.

    Args:
        candidate_id (str): The candidate ID whose resumes should be deleted.

    Returns:
        dict: A dictionary with deletion status and message.
    """
    # Validate candidate_id
    if not candidate_id:
        raise ValueError("candidate_id is required")

    # Delete all resumes linked to this candidate
    result = resumes_collection.delete_many({"candidateId": candidate_id})

    if result.deleted_count == 0:
        return {
            "status": "not_found",
            "message": f"No resumes found for candidateId: {candidate_id}"
        }

    print(f"🗑️ Successfully deleted {result.deleted_count} resumes for candidate {candidate_id}")
    return {
        "status": "success",
        "message": f"Deleted {result.deleted_count} resumes for candidate {candidate_id}."
    }
