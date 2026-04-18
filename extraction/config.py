from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
JOURNALS_DIR = PROJECT_ROOT / "journals"
NEWSLETTERS_DIR = PROJECT_ROOT / "newsletters"
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "daylily.db"
MARKDOWN_DIR = DATA_DIR / "markdown"
JOURNALS_MD_DIR = MARKDOWN_DIR / "journals"
NEWSLETTERS_MD_DIR = MARKDOWN_DIR / "newsletters"
