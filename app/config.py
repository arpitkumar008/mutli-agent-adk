
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()  

BASE_DIR = Path(__file__).resolve().parent.parent
POLICY_DIR = BASE_DIR / "policies"
CHROMA_DIR = str(BASE_DIR / "chroma_db")
COLLECTION = "policies"

LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.5-flash-lite")
EMBED_MODEL = os.getenv("EMBED_MODEL", "gemini-embedding-001")
TOP_K = int(os.getenv("TOP_K", "5"))
MAX_CODE_CHARS = 20_000
APP_NAME = "policy_guard"

