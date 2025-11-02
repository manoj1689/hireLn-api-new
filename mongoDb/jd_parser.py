import re
from textwrap import wrap
import numpy as np
from openai import OpenAI
import os
from dotenv import load_dotenv
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
load_dotenv()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# ------------------------------
MONGO_URI = os.getenv("MONGO_URI")  # should be your Atlas URI
if not MONGO_URI:
    raise ValueError("Please set MONGO_URI in your environment variables!")

# Use Server API v1 for Atlas
client = MongoClient(MONGO_URI, server_api=ServerApi('1'))

# Test connection
try:
    client.admin.command('ping')
    print("✅ Connected to MongoDB Atlas!")
except Exception as e:
    print("❌ Failed to connect to MongoDB Atlas:", e)
    raise e

db = client["hireln_db"]
resumes_collection = db["resumes"]
# ----------------- Cosine Similarity -----------------
def cosine_similarity(a, b):
    import numpy as np
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))

# ----------------- JD Categorization -----------------
import re
def categorize_jd(jd_text: str) -> dict:
    """
    Basic categorization of Job Description text.
    You can enhance this later using NLP keyword matching or regex.
    """
    jd_text_lower = jd_text.lower()
    categories = {
        "skills": "",
        "experience": "",
        "education": "",
        "responsibilities": "",
        "summary": ""
    }

    lines = jd_text.split("\n")
    current_category = "summary"

    for line in lines:
        line_strip = line.strip()
        if not line_strip:
            continue
        if "responsibilit" in line_strip.lower():
            current_category = "responsibilities"
        elif "skill" in line_strip.lower():
            current_category = "skills"
        elif "experience" in line_strip.lower():
            current_category = "experience"
        elif "education" in line_strip.lower():
            current_category = "education"
        categories[current_category] += " " + line_strip

    return categories


def get_jd_category_embeddings(jd_text: str, chunk_size: int = 1000, chunk_overlap: int = 200, model: str = "text-embedding-3-large"):
    """
    Split JD into categories and generate embeddings for each category.
    Adds chunk overlap to preserve context.
    Returns dict: category -> list of embeddings
    """
    cat_texts = categorize_jd(jd_text)
    cat_embeddings = {}

    for cat, text in cat_texts.items():
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = min(start + chunk_size, text_len)
            chunk = text[start:end]
            chunks.append(chunk)
            start += chunk_size - chunk_overlap  # move start, keeping overlap

        embeddings = []
        for chunk in chunks:
            response = openai_client.embeddings.create(model=model, input=chunk)
            emb_vector = response.data[0].embedding
            embeddings.append({
                "text": chunk,
                "embedding": emb_vector
            })
        cat_embeddings[cat] = embeddings
    
    return cat_embeddings


def process_jd(jd_text: str, semantic_threshold: float = 0.4):
    """
    Process the JD and compare against all resumes using category-wise embeddings.
    JD is categorized and embedded using get_jd_category_embeddings().
    Compares JD embeddings against resume chunk embeddings using cosine similarity.
    Returns all matched data per category and an overall semantic score per resume,
    including candidate name and email.
    """
    resumes = list(resumes_collection.find({}))
    if not resumes:
        return {"error": "No resumes found in MongoDB"}

    # 1️⃣ Generate category-wise JD embeddings
    jd_cat_emb = get_jd_category_embeddings(jd_text)
    results = []

    for resume in resumes:
        r_chunks = resume.get("chunks", [])
        resume_result = {
            "resume_id": str(resume.get("_id", "")),
            "filename": resume.get("filename", "Unnamed Resume"),
            "name": resume.get("name", "Unknown"),
            "email": resume.get("email", "Not Provided"),
            "categories": {},
            "overall_semantic_score": 0.0
        }

        matched_sims = []  # collect only similarity scores >= threshold

        # 2️⃣ Loop through each JD category
        for cat, jd_chunks in jd_cat_emb.items():
            cat_matches = []
            for jd_chunk in jd_chunks:
                jd_emb = np.array(jd_chunk["embedding"], dtype=float)
                for r_chunk in r_chunks:
                    r_emb = np.array(r_chunk["embedding"], dtype=float)
                    sim = cosine_similarity(jd_emb, r_emb)

                    # Only count meaningful matches
                    if sim >= semantic_threshold:
                        matched_sims.append(sim)
                        cat_matches.append({
                            "jd_text": jd_chunk["text"],
                            "resume_text": r_chunk["text"],
                            "similarity": round(sim, 4)
                        })

            # Save matches for this category
            resume_result["categories"][cat] = cat_matches

        # 3️⃣ Compute average similarity across matched scores only
        resume_result["overall_semantic_score"] = round(
            float(np.mean(matched_sims)) * 100, 2
        ) if matched_sims else 0.0

        results.append(resume_result)

    # 4️⃣ Return structured response
    return {
        "results": results,
        "summary": {
            "total_resumes": len(resumes),
            "semantic_threshold": semantic_threshold
        }
    }
