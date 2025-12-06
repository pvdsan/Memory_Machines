"""
Library of Congress Service - Download Abraham Lincoln documents from LOC.

This service:
- Automatically detects URL type (item/resource/exhibits) from URL
- Extracts document type from LOC API response
- Downloads PDFs and transcriptions

Usage:
    python loc_service.py

Output:
    data/raw/loc/*.pdf (original manuscripts)
    data/raw/loc/*.txt (transcriptions)
"""

import requests
import json
import time
import re
import html
from bs4 import BeautifulSoup

from config import LOC_URLS, RATE_LIMIT_DELAY, LOC_RAW_DIR


# =============================================================================
# URL Type Detection
# =============================================================================

def detect_url_type(url: str) -> str:
    """Automatically detect URL type from URL structure."""
    if '/item/' in url:
        return 'item'
    elif '/resource/' in url:
        return 'resource'
    elif '/exhibits/' in url:
        return 'exhibits'
    else:
        return 'unknown'


def extract_loc_id(url: str) -> str:
    """Extract LOC ID from URL."""
    url = url.rstrip('/')
    if '/item/' in url:
        return url.split('/item/')[-1].split('/')[0]
    elif '/resource/' in url:
        return url.split('/resource/')[-1].split('/')[0].replace('.', '_')
    elif '/exhibits/' in url:
        # Extract meaningful ID from exhibits URL
        parts = url.split('/')
        filename = parts[-1].replace('.html', '')
        return f"exhibits_{filename}"
    return "unknown"


# =============================================================================
# Fetch Functions
# =============================================================================

def fetch_json_api(url: str) -> dict:
    """Fetch data from LOC JSON API."""
    json_url = url.rstrip('/') + "/?fo=json"
    response = requests.get(json_url)
    response.raise_for_status()
    return response.json()


def fetch_exhibits_html(url: str) -> dict:
    """Fetch and parse HTML from /exhibits/ URLs (scraping)."""
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    content = ""
    title = ""
    
    title_elem = soup.find('h1') or soup.find('title')
    if title_elem:
        title = title_elem.get_text(strip=True)
    
    main_content = (
        soup.find('div', class_='content') or
        soup.find('div', id='content') or
        soup.find('article') or
        soup.find('main') or
        soup.find('body')
    )
    
    if main_content:
        paragraphs = main_content.find_all(['p', 'blockquote', 'pre'])
        content = "\n\n".join([
            p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)
        ])
    
    return {
        "title": title,
        "content": content,
        "url": url
    }


# =============================================================================
# Document Type Extraction
# =============================================================================

def extract_document_type(data: dict) -> str:
    """Extract document type from LOC API response."""
    item_data = data.get('item', {})
    
    # Check 'type' field
    doc_type = item_data.get('type', [])
    if isinstance(doc_type, list) and doc_type:
        return doc_type[0]
    elif isinstance(doc_type, str):
        return doc_type
    
    # Check 'original_format' field
    original_format = item_data.get('original_format', [])
    if isinstance(original_format, list) and original_format:
        return original_format[0]
    
    # Check 'genre' field
    genre = item_data.get('genre', [])
    if isinstance(genre, list) and genre:
        return genre[0]
    
    # Check title for clues
    title = item_data.get('title', '')
    title_lower = title.lower()
    if 'letter' in title_lower:
        return 'Letter'
    elif 'speech' in title_lower or 'address' in title_lower:
        return 'Speech'
    elif 'inaugural' in title_lower:
        return 'Speech'
    
    return 'Document'


# =============================================================================
# PDF/Image Download Functions
# =============================================================================

def find_pdf_url(data: dict) -> str | None:
    """Find PDF URL in LOC API response."""
    if 'resources' in data:
        for resource in data['resources']:
            if isinstance(resource, dict):
                if 'pdf' in resource:
                    return resource['pdf']
                if 'files' in resource:
                    for file_group in resource['files']:
                        if isinstance(file_group, list):
                            for file_info in file_group:
                                if isinstance(file_info, dict):
                                    url = file_info.get('url', '')
                                    if '.pdf' in url.lower():
                                        return url
    
    if 'resource' in data and isinstance(data['resource'], dict):
        if 'pdf' in data['resource']:
            return data['resource']['pdf']
    
    return None


def find_image_urls(data: dict) -> list[str]:
    """Find all image URLs in LOC API response."""
    image_urls = []
    
    if 'resources' in data:
        for resource in data['resources']:
            if isinstance(resource, dict) and 'files' in resource:
                for file_group in resource['files']:
                    if isinstance(file_group, list):
                        for file_info in file_group:
                            if isinstance(file_info, dict):
                                url = file_info.get('url', '')
                                mimetype = file_info.get('mimetype', '')
                                if 'image' in mimetype or url.endswith(('.jpg', '.jpeg', '.tif', '.tiff')):
                                    image_urls.append(url)
    
    if 'resource' in data and isinstance(data['resource'], dict):
        if 'image' in data['resource']:
            image_urls.append(data['resource']['image'])
    
    return image_urls


def download_file(url: str, filepath: str) -> bool:
    """Download a file from URL."""
    try:
        print(f"      Downloading: {url[:70]}...")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return True
    except Exception as e:
        print(f"      Error downloading: {e}")
        return False


# =============================================================================
# Text Extraction
# =============================================================================

def extract_raw_xml_text(xml_text: str) -> str:
    """Extract plain text from XML/HTML content."""
    text = re.sub(r'<[^>]+>', ' ', xml_text)
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def fetch_fulltext(url: str) -> str | None:
    """Fetch fulltext transcription."""
    try:
        print(f"      Fetching transcription: {url[:60]}...")
        response = requests.get(url)
        response.raise_for_status()
        
        content = response.text
        if url.endswith('.xml') or '<' in content[:100]:
            content = extract_raw_xml_text(content)
        
        return content
    except Exception as e:
        print(f"      Error fetching transcription: {e}")
        return None


def find_fulltext_url(data: dict) -> str | None:
    """Find fulltext/transcription URL in LOC API response."""
    if 'resources' in data:
        for resource in data['resources']:
            if isinstance(resource, dict):
                if 'fulltext_file' in resource:
                    return resource['fulltext_file']
    
    if 'resource' in data and isinstance(data['resource'], dict):
        if 'fulltext_file' in data['resource']:
            return data['resource']['fulltext_file']
    
    return None


# =============================================================================
# Metadata Extraction
# =============================================================================

def extract_metadata(data: dict) -> dict:
    """Extract metadata from JSON API response."""
    item_data = data.get('item', {})
    
    title = item_data.get('title', 'Unknown')
    
    date = item_data.get('date', None)
    if isinstance(date, list):
        date = date[0] if date else None
    
    # Extract from/to from contributors or title
    contributors = item_data.get('contributor_names', [])
    from_person = None
    to_person = None
    
    # Check title for "from X to Y" pattern
    title_lower = title.lower() if title else ""
    if ' to ' in title_lower:
        parts = title.split(' to ')
        if len(parts) > 1:
            # First part might contain "from" info
            from_part = parts[0]
            to_person = parts[1].split(',')[0].strip()
            
            # Try to find author/from
            if 'Abraham Lincoln' in from_part:
                from_person = 'Abraham Lincoln'
            elif contributors:
                from_person = contributors[0]
    
    if not from_person and contributors:
        from_person = contributors[0]
    
    location = item_data.get('location', None)
    if isinstance(location, list):
        location = location[0] if location else None
    
    return {
        "title": title,
        "date": date,
        "from": from_person,
        "to": to_person,
        "place": location
    }


def make_safe_filename(text: str, max_length: int = 40) -> str:
    """Create a safe filename from text."""
    safe = "".join(c for c in text if c.isalnum() or c in (' ', '-', '_')).strip()
    safe = safe.replace(' ', '_')
    return safe[:max_length]


# =============================================================================
# Main Extraction
# =============================================================================

def extract_loc_data() -> list[dict]:
    """
    Main extraction function.
    
    Downloads PDFs and transcriptions from Library of Congress.
    URL type and document type are extracted automatically.
    
    Returns:
        List of metadata for downloaded files.
    """
    print("=" * 70)
    print("Library of Congress - Download Raw Files")
    print("=" * 70)
    print(f"URLs to process: {len(LOC_URLS)}")
    print(f"Rate limit delay: {RATE_LIMIT_DELAY}s between requests")
    print()
    
    print("URLs:")
    for i, url in enumerate(LOC_URLS, 1):
        url_type = detect_url_type(url)
        print(f"  {i}. [{url_type}] {url[:60]}...")
    
    # Ensure raw directory exists
    LOC_RAW_DIR.mkdir(parents=True, exist_ok=True)
    
    # Process each URL
    metadata_list = []
    
    for i, url in enumerate(LOC_URLS):
        if i > 0:
            print(f"\n⏳ Waiting {RATE_LIMIT_DELAY}s (rate limiting)...")
            time.sleep(RATE_LIMIT_DELAY)
        
        url_type = detect_url_type(url)
        loc_id = extract_loc_id(url)
        
        print(f"\n📥 Fetching: {url}")
        print(f"   URL type: {url_type} (auto-detected)")
        print(f"   ID: {loc_id}")
        
        downloaded_files = []
        
        if url_type == 'exhibits':
            # Exhibits page - scrape HTML for transcription
            try:
                html_data = fetch_exhibits_html(url)
                
                # Save transcription
                safe_title = make_safe_filename(html_data['title'] or loc_id)
                txt_filename = f"{loc_id}_{safe_title}.txt"
                txt_filepath = LOC_RAW_DIR / txt_filename
                
                with open(txt_filepath, 'w', encoding='utf-8') as f:
                    f.write(html_data['content'])
                
                downloaded_files.append(txt_filename)
                print(f"   ✓ Saved transcription: {txt_filename}")
                
                metadata = {
                    "title": html_data['title'],
                    "date": None,  # Would need to extract from page
                    "from": None,
                    "to": None,
                    "place": None
                }
                document_type = "Speech"  # Exhibits are typically speeches/addresses
                
            except Exception as e:
                print(f"   ✗ Error: {e}")
                metadata = {"title": loc_id, "date": None, "from": None, "to": None, "place": None}
                document_type = "Document"
                
        else:
            # JSON API - get PDF and transcription
            try:
                data = fetch_json_api(url)
                print(f"   ✓ Got JSON response")
                
                # Extract document type from API response
                document_type = extract_document_type(data)
                print(f"   Document type: {document_type} (extracted from API)")
                
                metadata = extract_metadata(data)
                safe_title = make_safe_filename(metadata['title'] or loc_id)
                
                # Try to download PDF
                pdf_url = find_pdf_url(data)
                if pdf_url:
                    pdf_filename = f"{loc_id}_{safe_title}.pdf"
                    pdf_filepath = LOC_RAW_DIR / pdf_filename
                    
                    if download_file(pdf_url, str(pdf_filepath)):
                        downloaded_files.append(pdf_filename)
                        print(f"   ✓ Saved PDF: {pdf_filename}")
                else:
                    # Try to get images instead
                    image_urls = find_image_urls(data)
                    if image_urls:
                        print(f"   ℹ No PDF found, {len(image_urls)} images available")
                        for img_url in image_urls[:1]:
                            ext = '.jpg' if '.jpg' in img_url.lower() else '.tif'
                            img_filename = f"{loc_id}_{safe_title}{ext}"
                            img_filepath = LOC_RAW_DIR / img_filename
                            
                            if download_file(img_url, str(img_filepath)):
                                downloaded_files.append(img_filename)
                                print(f"   ✓ Saved image: {img_filename}")
                    else:
                        print(f"   ⚠ No PDF or images found")
                
                # Try to get transcription
                fulltext_url = find_fulltext_url(data)
                if fulltext_url:
                    transcription = fetch_fulltext(fulltext_url)
                    if transcription:
                        txt_filename = f"{loc_id}_{safe_title}.txt"
                        txt_filepath = LOC_RAW_DIR / txt_filename
                        
                        with open(txt_filepath, 'w', encoding='utf-8') as f:
                            f.write(transcription)
                        
                        downloaded_files.append(txt_filename)
                        print(f"   ✓ Saved transcription: {txt_filename} ({len(transcription):,} chars)")
                
            except Exception as e:
                print(f"   ✗ Error: {e}")
                metadata = {"title": loc_id, "date": None, "from": None, "to": None, "place": None}
                document_type = "Document"
        
        # Store metadata
        metadata_list.append({
            "id": loc_id,
            "files": downloaded_files,
            "url": url,
            "url_type": url_type,
            "title": metadata['title'],
            "document_type": document_type,
            "date": metadata['date'],
            "place": metadata['place'],
            "from": metadata['from'],
            "to": metadata['to']
        })
    
    # Save metadata
    metadata_file = LOC_RAW_DIR / "_metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata_list, f, indent=2, ensure_ascii=False)
    
    print(f"\n   Saved metadata to: {metadata_file}")
    
    # Summary
    print("\n" + "=" * 70)
    print("Download Summary:")
    total_files = sum(len(m['files']) for m in metadata_list)
    print(f"  Total files downloaded: {total_files}")
    for m in metadata_list:
        print(f"  • {m['id']} [{m['document_type']}]: {', '.join(m['files']) if m['files'] else 'No files'}")
    
    print("=" * 70)
    print(f"✓ Saved to: {LOC_RAW_DIR}")
    print("=" * 70)
    print("\n➡️  Run 'python cleaning_service.py' to normalize the data")
    
    return metadata_list


if __name__ == "__main__":
    extract_loc_data()
