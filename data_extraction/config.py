"""
Configuration settings for Lincoln data extraction pipeline.
"""

from pathlib import Path

# =============================================================================
# Path Configuration
# =============================================================================
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

# Raw text directories (actual downloaded files)
GUTENBERG_RAW_DIR = RAW_DIR / "gutenberg"
LOC_RAW_DIR = RAW_DIR / "loc"

# Processed output paths (normalized JSON)
GUTENBERG_OUTPUT = PROCESSED_DIR / "gutenberg_lincoln_dataset.json"
LOC_OUTPUT = PROCESSED_DIR / "loc_lincoln_dataset.json"
COMBINED_OUTPUT = PROCESSED_DIR / "final.json"

# =============================================================================
# Gutenberg Configuration
# =============================================================================
GUTENBERG_BOOK_IDS = [6812, 6811, 12801, 14004, 18379]
GUTENDEX_API_URL = "https://gutendex.com/books"

# =============================================================================
# Library of Congress Configuration
# =============================================================================
# LOC API Rate Limit: 20 requests/minute = 3 seconds minimum between requests
# Using 3.5s to be safe and avoid 429 errors or 1-hour blocks
RATE_LIMIT_DELAY = 3.5  # seconds between requests

# The exact URLs required by the assignment
# url_type and document_type are extracted automatically by loc_service.py
LOC_URLS = [
    "https://www.loc.gov/item/mal0440500/",           # Letter about Election night 1860
    "https://www.loc.gov/resource/mal.0882800/",      # Fort Sumter Decision
    "https://www.loc.gov/exhibits/gettysburg-address/ext/trans-nicolay-copy.html",  # Gettysburg Address
    "https://www.loc.gov/resource/mal.4361300/",      # Second Inaugural Address
    "https://www.loc.gov/resource/mal.4361800/",      # Last Public Address (NOTE: returns wrong doc)
]

