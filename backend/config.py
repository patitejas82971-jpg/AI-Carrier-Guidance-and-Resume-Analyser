import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    PROJECT_ROOT = BASE_DIR
    DATA_DIR = BASE_DIR / "backend" / "data"
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    MAX_UPLOAD_SIZE = 5 * 1024 * 1024
    ALLOWED_EXTENSIONS = {".pdf", ".docx"}
