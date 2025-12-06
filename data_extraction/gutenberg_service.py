"""
Gutenberg Service - Download Abraham Lincoln books from Project Gutenberg.

This service downloads RAW text files. Use cleaning_service.py to normalize.

Usage:
    python gutenberg_service.py

Output:
    data/raw/gutenberg/*.txt
"""

import requests
import json
from pathlib import Path

from config import GUTENBERG_BOOK_IDS, GUTENDEX_API_URL, GUTENBERG_RAW_DIR


def fetch_book_metadata(book_ids: list[int]) -> dict:
    """Fetch metadata for multiple books from Gutendex API."""
    ids_str = ','.join(map(str, book_ids))
    api_url = f"{GUTENDEX_API_URL}?ids={ids_str}"
    
    print(f"Fetching metadata from: {api_url}")
    response = requests.get(api_url)
    response.raise_for_status()
    
    return response.json()


def get_text_url(book: dict) -> str | None:
    """Get the plain text URL for a book, preferring UTF-8."""
    formats = book.get('formats', {})
    
    # Prefer UTF-8 plain text
    for fmt, url in formats.items():
        if 'text/plain' in fmt and 'utf-8' in fmt:
            return url
    
    # Fallback to any text/plain format
    for fmt, url in formats.items():
        if 'text/plain' in fmt:
            return url
    
    return None


def make_safe_filename(text: str, max_length: int = 50) -> str:
    """Create a safe filename from text."""
    safe = "".join(c for c in text if c.isalnum() or c in (' ', '-', '_')).strip()
    safe = safe.replace(' ', '_')
    return safe[:max_length]


def download_book(book: dict) -> tuple[str, str] | None:
    """
    Download a book's raw text content.
    
    Returns:
        Tuple of (filename, content) or None if failed.
    """
    book_id = book['id']
    title = book['title']
    
    text_url = get_text_url(book)
    if not text_url:
        print(f"  ⚠ No plain text format available")
        return None
    
    response = requests.get(text_url)
    if response.status_code != 200:
        print(f"  ⚠ Failed to download (status {response.status_code})")
        return None
    
    # Create filename
    safe_title = make_safe_filename(title)
    filename = f"{book_id}_{safe_title}.txt"
    
    return filename, response.text


def save_metadata(books: list[dict]):
    """Save book metadata to a JSON file for reference."""
    metadata = []
    for book in books:
        authors = ", ".join([a['name'] for a in book.get('authors', [])])
        metadata.append({
            "id": book['id'],
            "title": book['title'],
            "authors": authors,
            "reference": f"https://gutendex.com/books/{book['id']}/"
        })
    
    metadata_file = GUTENBERG_RAW_DIR / "_metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"   Saved metadata to: {metadata_file}")


def extract_gutenberg_data() -> list[str]:
    """
    Main extraction function.
    
    Downloads raw text files from Project Gutenberg.
    
    Returns:
        List of downloaded filenames.
    """
    print("=" * 70)
    print("Project Gutenberg - Download Raw Text Files")
    print("=" * 70)
    print(f"Books to download: {GUTENBERG_BOOK_IDS}")
    print()
    
    # Fetch metadata for all books
    data = fetch_book_metadata(GUTENBERG_BOOK_IDS)
    print(f"Found {data['count']} books in Gutendex API")
    print()
    
    # Ensure raw directory exists
    GUTENBERG_RAW_DIR.mkdir(parents=True, exist_ok=True)
    
    # Download each book
    downloaded_files = []
    
    for book in data['results']:
        book_id = book['id']
        title = book['title']
        
        print(f"📖 Downloading: {title[:60]}...")
        print(f"   ID: {book_id}")
        
        result = download_book(book)
        
        if result:
            filename, content = result
            filepath = GUTENBERG_RAW_DIR / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            downloaded_files.append(filename)
            print(f"   ✓ Saved: {filename} ({len(content):,} chars)")
        else:
            print(f"   ✗ Failed to download")
        
        print()
    
    # Save metadata for cleaning step
    save_metadata(data['results'])
    
    print("=" * 70)
    print(f"✓ Downloaded {len(downloaded_files)} raw text files")
    print(f"✓ Saved to: {GUTENBERG_RAW_DIR}")
    print("=" * 70)
    print("\n➡️  Run 'python cleaning_service.py' to normalize the data")
    
    return downloaded_files


if __name__ == "__main__":
    extract_gutenberg_data()
