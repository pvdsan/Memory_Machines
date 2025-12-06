"""
Shared utility functions for text cleaning and processing.
"""

import re
import html


def fix_encoding(text: str) -> str:
    """
    Fix common mojibake/encoding issues in text.
    
    Handles UTF-8 characters incorrectly decoded as Latin-1, curly quotes,
    em-dashes, and other special characters.
    """
    if not text:
        return text
    
    # Common UTF-8 mojibake patterns
    replacements = {
        # Curly quotes
        'â€œ': '"',   # opening double quote
        'â€': '"',    # closing double quote
        'â€˜': "'",   # opening single quote
        'â€™': "'",   # closing single quote / apostrophe
        # Dashes
        'â€"': '—',   # em-dash
        'â€"': '–',   # en-dash
        'â': '—',     # em-dash (partial)
        # Corrupted Unicode sequences (raw bytes)
        '\x80\x94': '',  # corrupted em-dash continuation
        '\x80\x9c': '',  # corrupted left quote continuation
        '\x80\x9d': '',  # corrupted right quote continuation
        '\x80\x99': '',  # corrupted apostrophe continuation
        # Other common issues
        'â€¦': '...',  # ellipsis
        'Ã©': 'é',
        'Ã¨': 'è',
        'Ã ': 'à',
        'Ã¢': 'â',
        'Ã®': 'î',
        'Ã´': 'ô',
        'Ã»': 'û',
        'Ã§': 'ç',
        'Ã': 'í',
    }
    
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    
    # Fix remaining â followed by special chars (common pattern)
    text = re.sub(r'â\s*"', '"', text)
    text = re.sub(r'"\s*â', '"', text)
    text = re.sub(r"â\s*'", "'", text)
    text = re.sub(r"'\s*â", "'", text)
    text = re.sub(r'\bâ(\w)', r'"\1', text)
    text = re.sub(r'(\w)â\b', r'\1"', text)
    text = re.sub(r'\sâ\s', ' — ', text)
    
    # Replace em-dashes and en-dashes with regular hyphens
    text = text.replace('—', '-')
    text = text.replace('–', '-')
    
    # Replace curly/smart quotes with straight quotes
    text = text.replace('"', '"')  # left double quote
    text = text.replace('"', '"')  # right double quote
    text = text.replace(''', "'")  # left single quote
                        
    text = text.replace(''', "'")  # right single quote / apostrophe
    
    # Remove stray quote marks surrounded by spaces (artifacts from encoding fixes)
    text = re.sub(r' " ', ' ', text)
    text = re.sub(r' "\s*$', '', text)  # trailing space-quote
    text = re.sub(r'^\s*" ', '', text)  # leading quote-space
    
    # Remove hyphen-dash patterns (em-dash artifacts)
    text = re.sub(r' - ', ' ', text)  # space-hyphen-space
    text = re.sub(r'-([^-\s]{1,200}?)-', r'\1', text)  # -text- used as quotes
    text = re.sub(r'\s-([A-Z])', r' \1', text)  # space-hyphen-capital (start of quote)
    text = re.sub(r'([a-z])-\s', r'\1 ', text)  # lowercase-hyphen-space (end of quote)
    text = re.sub(r'([.!?])-\s', r'\1 ', text)  # punctuation-hyphen-space
    # Em-dashes used without spaces (word-word patterns that aren't compound words)
    text = re.sub(r'([a-z])-([A-Z])', r'\1 \2', text)  # lowercase-Capital
    text = re.sub(r'([a-z])-([a-z]{2,})\b', r'\1 \2', text)  # word-word (not prefixes like re-)
    # Leading/trailing dashes on words (used as quotes in old texts)
    text = re.sub(r'\s-([a-zA-Z])', r' \1', text)  # space-dash-letter
    text = re.sub(r'([a-zA-Z])-\s', r'\1 ', text)  # letter-dash-space
    text = re.sub(r'\(-', '(', text)  # opening paren with dash
    text = re.sub(r'-\)', ')', text)  # closing paren with dash
    text = re.sub(r'\.-\)', '.)', text)  # period-dash-paren
    # Dashes before punctuation (artifacts)
    text = re.sub(r'-([;:,.!?])', r'\1', text)  # dash-punctuation
    text = re.sub(r"'s-;", "'s;", text)  # possessive-dash-semicolon
    
    # Remove newlines and carriage returns
    text = text.replace('\r\n', ' ')
    text = text.replace('\r', ' ')
    text = text.replace('\n', ' ')
    
    # Remove backslash escapes
    text = text.replace('\\"', '"')
    text = text.replace("\\'", "'")
    text = text.replace('\\', '')
    
    # Clean up any double spaces
    text = re.sub(r'  +', ' ', text)
    
    return text


def clean_xml_text(xml_text: str) -> str:
    """
    Extract plain text from XML/HTML content and fix encoding issues.
    """
    # Remove XML/HTML tags
    text = re.sub(r'<[^>]+>', ' ', xml_text)
    # Decode HTML entities
    text = html.unescape(text)
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Fix mojibake (encoding issues)
    text = fix_encoding(text)
    return text

