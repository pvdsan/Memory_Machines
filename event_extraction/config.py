"""
Configuration for event extraction pipeline.
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

# Target events to extract (only names, no extra context)
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
FINAL_DIR = OUTPUT_DIR / "final"  # Final JSON output

# Gemini model settings
GEMINI_MODEL = "gemini-2.5-flash-lite"  # Using Flash for speed, can upgrade to Pro for quality
GEMINI_TEMPERATURE = 0.2  # Low temperature for more deterministic extraction

