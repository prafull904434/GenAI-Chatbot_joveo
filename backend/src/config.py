from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent.parent   # project root 
DATA_DIR = BASE_DIR / "data"
INDEX_DIR = BASE_DIR / "index"

CHUNKS_PATH = INDEX_DIR / "chunks.csv"
EMBEDDINGS_PATH = INDEX_DIR / "embeddings.npy"

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

GITLAB_HANDBOOK_SITEMAP = "https://handbook.gitlab.com/sitemap.xml"
GITLAB_DIRECTION_SITEMAP = "https://about.gitlab.com/sitemap.xml"



    

MAX_PAGES = int(os.getenv("MAX_PAGES", "120"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "700"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))
TOP_K = int(os.getenv("TOP_K", "5"))

# ensure valid chunk overlap ratio
if CHUNK_OVERLAP >= CHUNK_SIZE:
    CHUNK_OVERLAP = int(CHUNK_SIZE * 0.2)

# fix retrieval size for stability
TOP_K = max(3, min(TOP_K, 10))