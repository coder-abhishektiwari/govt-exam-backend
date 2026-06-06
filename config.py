from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
PAPERS_DIR = BASE_DIR / "question_papers"
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = BASE_DIR / "pdf_cache"
INDEX_FILE = PAPERS_DIR / "index.json"
ANNOUNCEMENTS_FILE = DATA_DIR / "announcements.json"
BULLETINS_FILE = DATA_DIR / "bulletins.json"
ANALYTICS_FILE = DATA_DIR / "analytics.json"
MAX_CACHE_FILES = 100

PAPERS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)
