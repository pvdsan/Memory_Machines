"""
Batch processing utilities for handling large documents (books).
Splits documents into 30k token batches with 1k overlap.
Manages intermediate files for two-stage extraction.
"""
import json
import re
from pathlib import Path
from typing import List, Tuple, Dict

from config import OUTPUT_DIR, EVENTS

# Batch settings
MAX_TOKENS = 30000
OVERLAP_TOKENS = 1000
CHARS_PER_TOKEN = 4  # Rough estimate

# Intermediate files directory
INTERMEDIATE_DIR = OUTPUT_DIR / "intermediate"


def estimate_tokens(text: str) -> int:
    """Estimate token count from text (approximately 4 characters per token)."""
    return len(text) // CHARS_PER_TOKEN


def estimate_chars(tokens: int) -> int:
    """Convert token count to approximate character count."""
    return tokens * CHARS_PER_TOKEN


def split_into_batches(content: str, max_tokens: int = MAX_TOKENS, 
                       overlap_tokens: int = OVERLAP_TOKENS) -> List[Tuple[int, str]]:
    """
    Split text into overlapping batches of approximately max_tokens.
    
    Args:
        content: The full document text
        max_tokens: Maximum tokens per batch (default 15000)
        overlap_tokens: Overlap between batches (default 1000)
        
    Returns:
        List of tuples (batch_number, batch_content)
    """
    max_chars = estimate_chars(max_tokens)
    overlap_chars = estimate_chars(overlap_tokens)
    step_size = max_chars - overlap_chars
    
    batches = []
    start = 0
    batch_num = 1
    
    while start < len(content):
        end = start + max_chars
        
        # Try to break at a sentence or paragraph boundary
        if end < len(content):
            # Look for paragraph break first
            para_break = content.rfind('\n\n', start + step_size, end)
            if para_break > start + step_size // 2:
                end = para_break + 2
            else:
                # Look for sentence break
                sentence_break = content.rfind('. ', start + step_size, end)
                if sentence_break > start + step_size // 2:
                    end = sentence_break + 2
        
        batch_content = content[start:end].strip()
        if batch_content:
            batches.append((batch_num, batch_content))
            batch_num += 1
        
        # Move start position, accounting for overlap
        start = end - overlap_chars
        if start >= len(content) - overlap_chars:
            break
    
    return batches


def get_event_slug(event_name: str) -> str:
    """Convert event name to slug format."""
    safe_event = re.sub(r'[^\w\s-]', '', event_name.lower())
    safe_event = re.sub(r'[\s]+', '_', safe_event)
    return safe_event


def get_event_filename(doc_id: str, event_name: str) -> str:
    """Generate filename for intermediate results."""
    return f"{doc_id}_{get_event_slug(event_name)}.md"


def init_intermediate_file(doc_id: str, event_name: str, document_title: str, author: str):
    """Initialize an intermediate results file for a book/event pair."""
    INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)
    
    filename = get_event_filename(doc_id, event_name)
    filepath = INTERMEDIATE_DIR / filename
    
    # Create header in markdown format
    header = f"""# INTERMEDIATE EXTRACTION

# EVENT: {get_event_slug(event_name)}

# BOOK: {document_title}

# AUTHOR: {author}

"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(header)
    
    return filepath


def append_batch_extraction(doc_id: str, event_name: str, batch_num: int,
                            relevant_text: List[str], dates_mentioned: List[str] = None,
                            key_facts: List[str] = None):
    """
    Append extraction results from a batch to the intermediate file.
    Uses markdown format for readability.
    """
    filename = get_event_filename(doc_id, event_name)
    filepath = INTERMEDIATE_DIR / filename
    
    # Build chunk content
    lines = [f"\n## CHUNK {batch_num}\n"]
    
    # Add relevant excerpts
    for text in relevant_text:
        if text:
            lines.append(f"{text}\n\n")
    
    # Append to file
    with open(filepath, 'a', encoding='utf-8') as f:
        f.writelines(lines)


def get_consolidated_intermediate(doc_id: str, event_name: str) -> str:
    """
    Get consolidated intermediate content for an event.
    Reads the markdown file and returns its content for the final prompt.
    
    Returns:
        Content of the intermediate file
    """
    filename = get_event_filename(doc_id, event_name)
    filepath = INTERMEDIATE_DIR / filename
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        return "No information found."
    
    # Check if there's any chunk content (not just header)
    if "## CHUNK" not in content:
        return "No information found."
    
    # Add END marker and return
    return content + "\n# END"


def get_intermediate_data(doc_id: str, event_name: str) -> str:
    """Get raw intermediate content for an event."""
    return get_consolidated_intermediate(doc_id, event_name)


def clear_intermediate_files(doc_id: str = None):
    """Clear intermediate files, optionally for a specific document."""
    if not INTERMEDIATE_DIR.exists():
        return
    
    if doc_id:
        # Clear only files for this document
        for filepath in INTERMEDIATE_DIR.glob(f"{doc_id}_*.md"):
            filepath.unlink()
    else:
        # Clear all intermediate files
        for filepath in INTERMEDIATE_DIR.glob("*.md"):
            filepath.unlink()


def list_intermediate_files(doc_id: str = None) -> List[Path]:
    """List all intermediate files, optionally for a specific document."""
    if not INTERMEDIATE_DIR.exists():
        return []
    
    if doc_id:
        return list(INTERMEDIATE_DIR.glob(f"{doc_id}_*.md"))
    else:
        return list(INTERMEDIATE_DIR.glob("*.md"))


if __name__ == "__main__":
    # Test the batch splitting
    test_text = "A" * 100000  # 100k characters = ~25k tokens
    batches = split_into_batches(test_text)
    print(f"Split {len(test_text)} chars into {len(batches)} batches")
    for batch_num, content in batches:
        print(f"  Batch {batch_num}: {len(content)} chars (~{estimate_tokens(content)} tokens)")
