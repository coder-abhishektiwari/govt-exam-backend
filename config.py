from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
PAPERS_DIR = BASE_DIR / "question_papers"
CACHE_DIR = BASE_DIR / "pdf_cache"
INDEX_FILE = PAPERS_DIR / "index.json"
MAX_CACHE_FILES = 100

PAPERS_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)
