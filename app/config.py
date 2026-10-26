import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

MIN_SCORE = float(os.getenv("MIN_SCORE", "0.22"))

TOP_K = int(os.getenv("TOP_K", "5"))

CHUNK_SIZE = 800       
CHUNK_OVERLAP = 150   

DATA_PDFS_DIR = BASE_DIR / "data" / "pdfs"
REQUESTS_FILE = BASE_DIR / "app" / "requests_data.json"
