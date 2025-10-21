import os
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


def save_resume_with_embeddings(filename: str, resume_text: str):
    # Check if filename already exists
    existing_resume = resumes_collection.find_one({"filename": filename})
    if existing_resume:
        # Raise an exception so the route can handle and show a message
        raise ValueError(f"Resume '{filename}' already exists in the database.")

    # Chunk resume
    chunks = chunk_text(resume_text, chunk_size=500)

    # Compute embeddings for each chunk
    chunk_data = []
    for chunk in chunks:
        emb = get_embedding(chunk)
        chunk_data.append({"text": chunk, "embedding": emb})

    # Create MongoDB document
    resume_doc = {
        "filename": filename,
        "uploaded_at": datetime.utcnow(),
        "chunks": chunk_data
    }

    # Insert into MongoDB
    result = resumes_collection.insert_one(resume_doc)
    
    print(f"✅ Saved {filename} with {len(chunk_data)} chunks and embeddings.")
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