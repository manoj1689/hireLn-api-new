import os
import json
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials

# Load environment variables from a .env file
load_dotenv()

def init_firebase():
    """Initialize Firebase Admin SDK from .env JSON"""
    cred_json_str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")

    if not cred_json_str:
        raise ValueError("⚠️ Missing GOOGLE_APPLICATION_CREDENTIALS_JSON in .env file")

    cred_dict = json.loads(cred_json_str)

    if not firebase_admin._apps:
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)

        print("✅ Firebase Admin initialized successfully")