"""
Configuration for hybrid vector event extraction pipeline.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from root .env file
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")

def load_api_key() -> str:
    """Load Gemini API key from environment variables"""
    return os.getenv('GEMINI_API_KEY', '')

# Target events to extract
EVENTS = [
    "Election Night 1860",
    "Fort Sumter Decision",
    "Gettysburg Address",
    "Second Inaugural Address",
    "Ford's Theatre Assassination"
]

# Paths
DATA_DIR = Path(__file__).parent.parent / "data_extraction" / "data"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_DIR = Path(__file__).parent / "output"
FINAL_DIR = OUTPUT_DIR / "final"
INDEX_DIR = OUTPUT_DIR / "indices"

# Chunking settings
CHUNK_SIZE_TOKENS = 1000
CHUNK_OVERLAP_TOKENS = 200
CHARS_PER_TOKEN = 4

# Retrieval settings
FAISS_TOP_K = 15      # Number of chunks to retrieve from FAISS (semantic search)
BM25_TOP_K = 15       # Number of chunks to retrieve from BM25 (keyword search)
TOP_K_CHUNKS = 5     # Final number of chunks after RRF fusion

# Query generation settings
USE_WEB_SEARCH = False  # Use Google Search grounding for query generation (set to False to disable)

# Gemini model settings
GEMINI_MODEL = "gemini-2.5-flash-lite"
GEMINI_EMBEDDING_MODEL = "models/text-embedding-004"
GEMINI_TEMPERATURE = 0.2

# Rate limiting
REQUEST_DELAY_SECONDS = 0.5  # Shorter delay for embedding calls (1500 RPM limit)
EXTRACTION_DELAY_SECONDS = 15  # Standard delay for extraction calls

