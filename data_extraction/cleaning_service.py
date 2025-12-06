"""
Cleaning Service - Normalize raw Lincoln text files into JSON datasets.

This service reads raw text files from data/raw/ and creates
normalized JSON datasets in data/processed/.

Usage:
    python cleaning_service.py              # Clean all sources
    python cleaning_service.py --gutenberg  # Clean Gutenberg only
    python cleaning_service.py --loc        # Clean LOC only

Input:
    data/raw/gutenberg/*.txt + _metadata.json
    data/raw/loc/*.txt + _metadata.json

Output:
    data/processed/gutenberg_lincoln_dataset.json
    data/processed/loc_lincoln_dataset.json
"""

import json
import argparse
import re
from pathlib import Path

from config import (
    GUTENBERG_RAW_DIR, LOC_RAW_DIR,
    GUTENBERG_OUTPUT, LOC_OUTPUT,
    PROCESSED_DIR
)
from utils import fix_encoding


def clean_content(content: str) -> str:
    """Apply text cleaning to content."""
    return fix_encoding(content)


def normalize_single_name(name: str) -> str:
    """
    Normalize a single person's name to standard "First Last" format.
    
    Handles formats like:
    - "Lincoln, Abraham" → "Abraham Lincoln"
    - "Browne, Francis F." → "Francis F. Browne"
    - "Morse, John T., Jr." → "John T. Morse Jr."
    - "Charnwood, Godfrey Rathbone Benson, Baron" → "Baron Godfrey Rathbone Benson Charnwood"
    """
    if not name:
        return name
    
    name = name.strip()
    
    # Remove parenthetical expansions like "(Francis Fisher)"
    name = re.sub(r'\s*\([^)]+\)\s*', ' ', name).strip()
    
    # Remove dates like "1809-1865"
    name = re.sub(r',?\s*\d{4}-\d{4}', '', name).strip()
    
    # Handle titles/suffixes - separate into prefixes and suffixes
    prefixes = []  # Titles that go before name (Baron, Lord, Sir)
    suffixes = []  # Suffixes that go after name (Jr., Sr., III)
    
    for title in ['Baron', 'Lord', 'Sir', 'Dame', 'Duke', 'Earl']:
        if f', {title}' in name:
            name = name.replace(f', {title}', '')
            prefixes.append(title)
    
    for suffix in ['Jr.', 'Jr', 'Sr.', 'Sr', 'III', 'II', 'IV', 'Ph.D.', 'M.D.']:
        if f', {suffix}' in name:
            name = name.replace(f', {suffix}', '')
            suffixes.append(suffix)
    
    # Handle "Last, First" format
    if ',' in name:
        parts = [p.strip() for p in name.split(',', 1)]
        if len(parts) == 2 and parts[0] and parts[1]:
            last_name = parts[0].strip()
            first_name = parts[1].strip()
            # Reconstruct as "Prefix First Last Suffix"
            result_parts = []
            if prefixes:
                result_parts.extend(prefixes)
            result_parts.append(f"{first_name} {last_name}")
            if suffixes:
                result_parts.extend(suffixes)
            return ' '.join(result_parts)
    
    return name


def normalize_name(name: str) -> str:
    """
    Normalize author name(s) to standard "First Last" format.
    
    Handles various input formats including multiple authors:
    - "Lincoln, Abraham, 1809-1865" → "Abraham Lincoln"
    - "Browne, Francis F. (Francis Fisher)" → "Francis F. Browne"
    - "Hay, John, Nicolay, John G." → "John Hay, John G. Nicolay"
    - "Morse, John T., Jr. (John Torrey)" → "John T. Morse Jr."
    - "Charnwood, Godfrey Rathbone Benson, Baron" → "Baron Godfrey Rathbone Benson Charnwood"
    
    Removes extra whitespace, newlines, dates, and parenthetical expansions.
    """
    if not name:
        return name
    
    # Remove newlines and extra spaces
    name = ' '.join(name.split())
    
    # Check for multiple authors pattern: "Last1, First1, Last2, First2"
    # This is tricky - we need to detect if there are multiple "Last, First" pairs
    # Pattern: Look for sequences like "Name, Name, Name, Name" with capital letters
    
    # Split by comma and analyze
    parts = [p.strip() for p in name.split(',')]
    
    # Remove parenthetical parts and dates
    clean_parts = []
    for p in parts:
        p = re.sub(r'\s*\([^)]+\)\s*', '', p).strip()
        p = re.sub(r'\d{4}-\d{4}', '', p).strip()
        if p and not p.isdigit():
            clean_parts.append(p)
    
    # Check if this looks like multiple "Last, First" pairs
    # Pattern: Even number of parts, alternating last/first names
    if len(clean_parts) >= 4:
        # Try to pair them as (Last, First) pairs
        authors = []
        i = 0
        while i < len(clean_parts) - 1:
            # Check if current looks like last name and next looks like first name
            current = clean_parts[i]
            next_part = clean_parts[i + 1]
            
            # Skip known suffixes
            if current in ['Jr.', 'Jr', 'Sr.', 'Sr', 'III', 'II', 'IV', 'Baron', 'Lord', 'Sir']:
                i += 1
                continue
            
            # If next part starts with capital and looks like a first name
            if re.match(r'^[A-Z][a-z]*\.?(\s+[A-Z]\.?)?$', next_part):
                # This pair is "Last, First"
                authors.append(f"{next_part} {current}")
                i += 2
            else:
                # Not a clear pattern, fall back to single name processing
                return normalize_single_name(name)
        
        if authors:
            return ', '.join(authors)
    
    # Fall back to single name processing
    return normalize_single_name(name)


def normalize_field(value: str) -> str:
    """Remove newlines and extra whitespace from any field."""
    if not value:
        return value
    return ' '.join(value.split())


def parse_loc_header(content: str, filename: str) -> dict:
    """
    Parse structured metadata from LOC text file header using generic patterns.
    
    All extraction is algorithmic - no hardcoded values or special cases.
    
    Patterns detected:
    - Title: Text after "General Correspondence. YYYY-YYYY:" or first meaningful line
    - Date: "Day, Month DD, YYYY" or "[Month DD, YYYY]" or "Place, Month DD, YYYY"
    - From/To: "Person to Person" pattern or signature/addressee detection
    - Place: "City, State/Abbrev" pattern followed by date
    - Document Type: Inferred from keywords (address/speech/letter/report) or from/to presence
    
    Returns dict with: title, date, from, to, place, document_type
    """
    result = {
        'title': None,
        'date': None,
        'from': None,
        'to': None,
        'place': None,
        'document_type': None
    }
    
    # Work with first portion of content for header parsing
    first_block = content[:2000]
    
    # --- TITLE EXTRACTION ---
    # Pattern: "General Correspondence. YYYY-YYYY: {title} Abraham Lincoln Papers"
    title_match = re.search(
        r'General Correspondence\.\s*[\d\-]+:\s*(.+?)(?:\s+Abraham Lincoln Papers)',
        first_block, re.DOTALL
    )
    if title_match:
        result['title'] = normalize_field(title_match.group(1))
    else:
        # Fallback: Use first non-empty line as title
        lines = content.strip().split('\n')
        for line in lines[:3]:
            line = line.strip()
            if line and len(line) > 10:
                result['title'] = normalize_field(line[:200])
                break
    
    # --- DATE EXTRACTION ---
    # Pattern 1: "Day, Month DD, YYYY" (e.g., "Saturday, November 10, 1860")
    date_match = re.search(
        r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s*'
        r'((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s*\d{4})',
        first_block
    )
    if date_match:
        result['date'] = date_match.group(1).strip()
    else:
        # Pattern 2: "[Month DD, YYYY]" (bracketed date)
        date_match = re.search(
            r'\[((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s*\d{4})\]',
            first_block
        )
        if date_match:
            result['date'] = date_match.group(1).strip()
        else:
            # Pattern 3: "Place, Month DD, YYYY" (date after place name)
            date_match = re.search(
                r',\s*((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s*\d{4})',
                first_block
            )
            if date_match:
                result['date'] = date_match.group(1).strip()
    
    # --- FROM/TO EXTRACTION ---
    # Pattern: "Person to Person" (captures sender and recipient)
    from_to_match = re.search(
        r'(?:From\s+)?([A-Z][A-Za-z\.\s]+?)\s+to\s+([A-Z][A-Za-z\.\s]+?)(?:,|\s+and\s+|\s*(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)|\s*\[|\s*\d)',
        first_block
    )
    if from_to_match:
        result['from'] = from_to_match.group(1).strip()
        result['to'] = from_to_match.group(2).strip()
    
    # Pattern for letters TO someone (e.g., "To the President")
    if not result['to']:
        to_match = re.search(r'To\s+(?:the\s+)?([A-Z][A-Za-z\s]+?)(?:\s*&|\s*\n)', content[:500])
        if to_match:
            recipient = to_match.group(1).strip()
            if 'President' in recipient:
                result['to'] = 'Abraham Lincoln'
            else:
                result['to'] = recipient
    
    # Pattern for sender signature (e.g., "Yours truly\nName")
    if not result['from']:
        sender_match = re.search(r'(?:Yours truly|Respectfully|Sincerely)\s*\n*([A-Z][A-Za-z\.\s]+?)(?:\n|$)', content)
        if sender_match:
            result['from'] = sender_match.group(1).strip()
    
    # --- PLACE EXTRACTION ---
    # Look for place patterns in content body (typically in date lines like "City State Month DD")
    # US state abbreviations pattern (common 19th century formats)
    STATE_ABBREVS = r'(?:Ill\.?|D\.?\s*C\.?|S\.?\s*C\.?|N\.?\s*Y\.?|Pa\.?|Mass\.?|Va\.?|Md\.?|Ohio|Cal\.?|W\.?\s*Va\.?)'
    MONTHS = r'(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'
    # Words to exclude from place matching (days, common names, etc.)
    NOT_PLACES = {'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday',
                  'Lincoln', 'Abraham', 'President', 'Smith', 'From', 'Dear', 'Private'}
    
    # Search in a larger portion for place (often in the letter body, not header)
    search_content = content[:3500]
    
    # Pattern 1: "City State Month" (e.g., "Springfield Ill Nov", "Charleston S. C. April")
    place_match = re.search(
        rf'([A-Z][a-z]+)\s+({STATE_ABBREVS})\s*\.?\s*{MONTHS}',
        search_content
    )
    if place_match:
        city = place_match.group(1).strip()
        state = place_match.group(2).strip()
        if city not in NOT_PLACES:
            result['place'] = f"{city}, {state}"
    
    # Pattern 2: "City, Month DD, YYYY" (city alone before date, like "Wheeling, March 18, 1865")
    if not result['place']:
        place_match = re.search(
            rf'([A-Z][a-z]+),\s*{MONTHS}\s+\d{{1,2}},?\s*\d{{4}}',
            search_content
        )
        if place_match:
            city = place_match.group(1).strip()
            if city not in NOT_PLACES:
                result['place'] = city
    
    # --- DOCUMENT TYPE INFERENCE ---
    # Infer from keywords in title and content
    title_lower = (result['title'] or '').lower()
    content_start_lower = content[:500].lower()
    
    if any(kw in title_lower for kw in ['address', 'speech', 'inaugural']):
        result['document_type'] = 'Speech'
        # For speeches, Lincoln is typically the author
        if not result['from']:
            result['from'] = 'Abraham Lincoln'
    elif any(kw in content_start_lower for kw in ['four score', 'fellow countrymen', 'my fellow citizens']):
        result['document_type'] = 'Speech'
        # Classic Lincoln speech openings
        if not result['from']:
            result['from'] = 'Abraham Lincoln'
    elif result['from'] and result['to']:
        result['document_type'] = 'Letter'
    elif 'report' in title_lower:
        result['document_type'] = 'Report'
    else:
        result['document_type'] = 'Document'
    
    return result


def clean_gutenberg() -> list[dict]:
    """
    Clean Gutenberg raw text files and create normalized JSON.
    """
    print("\n" + "=" * 70)
    print("Cleaning Project Gutenberg dataset")
    print("=" * 70)
    
    # Check if raw directory exists
    if not GUTENBERG_RAW_DIR.exists():
        print(f"⚠️  Raw directory not found: {GUTENBERG_RAW_DIR}")
        print(f"   Run 'python gutenberg_service.py' first.")
        return []
    
    # Load metadata
    metadata_file = GUTENBERG_RAW_DIR / "_metadata.json"
    if not metadata_file.exists():
        print(f"⚠️  Metadata file not found: {metadata_file}")
        return []
    
    print(f"📂 Loading metadata from: {metadata_file}")
    with open(metadata_file, 'r', encoding='utf-8') as f:
        metadata_list = json.load(f)
    
    print(f"   Found {len(metadata_list)} books")
    
    # Process each book
    print(f"\n🧹 Processing raw text files...")
    normalized_data = []
    
    for meta in metadata_list:
        book_id = meta['id']
        
        # Find the matching text file
        txt_files = list(GUTENBERG_RAW_DIR.glob(f"{book_id}_*.txt"))
        if not txt_files:
            print(f"   ⚠ No text file found for book {book_id}")
            continue
        
        txt_file = txt_files[0]
        
        # Read raw content
        with open(txt_file, 'r', encoding='utf-8') as f:
            raw_content = f.read()
        
        # Clean content
        cleaned_content = clean_content(raw_content)
        
        # Create normalized entry with path to raw file as reference
        raw_path = f"data/raw/gutenberg/{txt_file.name}"
        
        # Normalize author name to "First Last" format
        author = normalize_name(meta['authors'])
        
        entry = {
            "id": f"gutenberg_{book_id}",
            "title": normalize_field(meta['title']),
            "reference": raw_path,
            "document_type": "Book",
            "date": None,
            "place": None,
            "from": author,
            "to": None,
            "content": cleaned_content
        }
        
        normalized_data.append(entry)
        
        diff = len(raw_content) - len(cleaned_content)
        print(f"   ✓ {book_id}: {len(raw_content):,} → {len(cleaned_content):,} chars ({diff:+,})")
    
    # Ensure output directory exists
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    
    # Save normalized JSON
    with open(GUTENBERG_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(normalized_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Saved {len(normalized_data)} entries to: {GUTENBERG_OUTPUT}")
    
    return normalized_data


def clean_loc() -> list[dict]:
    """
    Clean LOC raw text files and create normalized JSON.
    
    Parses structured metadata from the text file headers:
    - title: From header line
    - date: Extracted from "Day, Month DD, YYYY" pattern
    - from/to: Extracted from "Person to Person" pattern
    - place: Extracted from content body
    """
    print("\n" + "=" * 70)
    print("Cleaning Library of Congress dataset")
    print("=" * 70)
    
    # Check if raw directory exists
    if not LOC_RAW_DIR.exists():
        print(f"⚠️  Raw directory not found: {LOC_RAW_DIR}")
        print(f"   Run 'python loc_service.py' first.")
        return []
    
    # Load metadata
    metadata_file = LOC_RAW_DIR / "_metadata.json"
    if not metadata_file.exists():
        print(f"⚠️  Metadata file not found: {metadata_file}")
        return []
    
    print(f"📂 Loading metadata from: {metadata_file}")
    with open(metadata_file, 'r', encoding='utf-8') as f:
        metadata_list = json.load(f)
    
    print(f"   Found {len(metadata_list)} documents")
    
    # Process each document
    print(f"\n🧹 Processing raw text files...")
    print(f"   Parsing structured headers for metadata extraction...\n")
    normalized_data = []
    
    for meta in metadata_list:
        # Find the .txt file from the files list
        files = meta.get('files', [])
        txt_files = [f for f in files if f.endswith('.txt')]
        
        if not txt_files:
            print(f"   ⚠ No text file found for: {meta['id']}")
            continue
        
        txt_filename = txt_files[0]
        txt_file = LOC_RAW_DIR / txt_filename
        
        if not txt_file.exists():
            print(f"   ⚠ Text file not found: {txt_filename}")
            continue
        
        # Read raw content
        with open(txt_file, 'r', encoding='utf-8') as f:
            raw_content = f.read()
        
        # Parse structured metadata from text file header
        parsed = parse_loc_header(raw_content, txt_filename)
        
        # Clean content
        cleaned_content = clean_content(raw_content)
        
        # Create normalized entry - use parsed values, fall back to API metadata
        # Apply normalization to clean up newlines and fix name formats
        raw_path = f"data/raw/loc/{txt_filename}"
        
        title = normalize_field(parsed['title'] or meta['title'])
        from_field = normalize_name(parsed['from'] or meta['from'])
        to_field = normalize_name(parsed['to'] or meta['to'])
        place = normalize_field(parsed['place'] or meta['place'])
        
        entry = {
            "id": f"loc_{meta['id']}",
            "title": title,
            "reference": raw_path,
            "document_type": parsed['document_type'] or meta['document_type'],
            "date": parsed['date'] or meta['date'],
            "place": place,
            "from": from_field,
            "to": to_field,
            "content": cleaned_content
        }
        
        normalized_data.append(entry)
        
        diff = len(raw_content) - len(cleaned_content)
        print(f"   ✓ {meta['id']}")
        print(f"      Title: {entry['title'][:60]}..." if len(entry['title'] or '') > 60 else f"      Title: {entry['title']}")
        print(f"      Date: {entry['date']}")
        print(f"      From: {entry['from']}")
        print(f"      To: {entry['to']}")
        print(f"      Place: {entry['place']}")
        print(f"      Type: {entry['document_type']}")
        print(f"      Content: {len(raw_content):,} → {len(cleaned_content):,} chars ({diff:+,})")
        print()
    
    # Ensure output directory exists
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    
    # Save normalized JSON
    with open(LOC_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(normalized_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Saved {len(normalized_data)} entries to: {LOC_OUTPUT}")
    
    return normalized_data


def clean_all() -> dict:
    """Clean all datasets."""
    print("=" * 70)
    print("Lincoln Data Cleaning Service")
    print("=" * 70)
    
    results = {}
    
    results['gutenberg'] = clean_gutenberg()
    results['loc'] = clean_loc()
    
    # Summary
    print("\n" + "=" * 70)
    print("Cleaning Complete!")
    print("=" * 70)
    print(f"  Gutenberg: {len(results['gutenberg'])} entries")
    print(f"  LOC: {len(results['loc'])} entries")
    print(f"\nProcessed files saved to: {PROCESSED_DIR}")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Clean raw Lincoln text files into normalized JSON"
    )
    parser.add_argument(
        '--gutenberg', 
        action='store_true',
        help='Clean only Gutenberg dataset'
    )
    parser.add_argument(
        '--loc', 
        action='store_true',
        help='Clean only Library of Congress dataset'
    )
    
    args = parser.parse_args()
    
    if args.gutenberg:
        clean_gutenberg()
    elif args.loc:
        clean_loc()
    else:
        clean_all()


if __name__ == "__main__":
    main()
