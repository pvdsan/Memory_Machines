"""
Gemini LLM service for event extraction.
Handles both direct extraction (small docs) and batch processing (books).

Two-prompt system:
- prompt_batch.md: Extract relevant text from each batch (books only)
- prompt_final.md: Create final JSON output (consolidate for books, direct for others)
"""
import json
import time
from pathlib import Path
from typing import Dict, List
from google import genai
from google.genai import types

from config import load_api_key, GEMINI_MODEL, GEMINI_TEMPERATURE, EVENTS, FINAL_DIR
from batch_processor import (
    split_into_batches, 
    estimate_tokens,
    init_intermediate_file,
    append_batch_extraction,
    get_consolidated_intermediate,
    clear_intermediate_files,
    list_intermediate_files,
    INTERMEDIATE_DIR
)

# Rate limiting settings (Free tier: 5 RPM, 250k TPM, 100 RPD)
# 5 RPM = 1 request per 12 seconds minimum, using 15s for safety margin
REQUEST_DELAY_SECONDS = 15  # Delay between requests to stay under 5 RPM
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 60  # Wait longer on rate limit errors

# Prompt paths
PROMPT_DIR = Path(__file__).parent / "prompts"
PROMPT_BATCH = PROMPT_DIR / "prompt_batch.md"    # For extracting excerpts from book batches
PROMPT_FINAL = PROMPT_DIR / "prompt_final.md"    # For consolidating excerpts into final JSON (per event)
PROMPT_DIRECT = PROMPT_DIR / "prompt_direct.md"  # For direct extraction from small docs (all events)


def load_prompt(filepath: Path) -> str:
    """Load a prompt template from file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def get_event_slug(event_name: str) -> str:
    """Convert event name to filename-safe slug."""
    import re
    safe = re.sub(r'[^\w\s-]', '', event_name.lower())
    return re.sub(r'[\s]+', '_', safe)


def save_event_result(event_result: dict, doc_id: str, event_name: str, doc_title: str, doc_type: str):
    """Save extraction result for a single document-event pair."""
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    
    event_slug = get_event_slug(event_name)
    output_path = FINAL_DIR / f"{doc_id}_{event_slug}.json"
    
    # Add document metadata to the event result
    result_with_meta = {
        "document_id": doc_id,
        "document_title": doc_title,
        "document_type": doc_type,
        **event_result
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result_with_meta, f, indent=2, ensure_ascii=False)


def save_all_events_for_document(extractions: list, doc_id: str, doc_title: str, doc_type: str):
    """Save each event as a separate JSON file for a document."""
    for event_result in extractions:
        event_name = event_result.get("event", "unknown")
        save_event_result(event_result, doc_id, event_name, doc_title, doc_type)
    
    print(f"    Saved: {len(extractions)} event files for {doc_id}")


class GeminiExtractor:
    """Extracts event information from historical documents using Gemini."""
    
    def __init__(self):
        api_key = load_api_key()
        self.client = genai.Client(api_key=api_key)
        self.model = GEMINI_MODEL
        
        # Load all prompt templates
        self.prompt_batch = load_prompt(PROMPT_BATCH)
        self.prompt_final = load_prompt(PROMPT_FINAL)
        self.prompt_direct = load_prompt(PROMPT_DIRECT)
    
    def _build_batch_prompt(self, batch_content: str, document_title: str, 
                            author: str, batch_num: int, total_batches: int) -> str:
        """Build prompt for extracting ALL events from a batch."""
        events_list = "\n".join([f"- {event}" for event in EVENTS])
        return self.prompt_batch.format(
            document_title=document_title,
            author=author,
            batch_num=batch_num,
            total_batches=total_batches,
            events_list=events_list,
            batch_content=batch_content
        )
    
    def _build_final_prompt(self, source_content: str, document_title: str, 
                            author: str, event_name: str) -> str:
        """Build prompt for creating final JSON output for a single event (book consolidation)."""
        return self.prompt_final.format(
            document_title=document_title,
            author=author,
            event_name=event_name,
            source_content=source_content
        )
    
    def _build_direct_prompt(self, document_content: str, document_title: str, author: str) -> str:
        """Build prompt for direct extraction from small documents (all events at once)."""
        events_list = "\n".join([f"- {event}" for event in EVENTS])
        return self.prompt_direct.format(
            document_title=document_title,
            author=author,
            events_list=events_list,
            document_content=document_content
        )

    def _call_llm_json(self, prompt: str) -> dict:
        """Make LLM call expecting JSON response."""
        for attempt in range(MAX_RETRIES):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=GEMINI_TEMPERATURE,
                        response_mime_type="application/json"
                    )
                )
                
                # Parse the JSON response
                result = json.loads(response.text)
                return result
                
            except json.JSONDecodeError as e:
                print(f"    Failed to parse JSON: {e}")
                return {"error": str(e), "extractions": []}
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    if attempt < MAX_RETRIES - 1:
                        wait_time = RETRY_DELAY_SECONDS * (2 ** attempt)
                        print(f"    Rate limited, waiting {wait_time}s (retry {attempt + 2}/{MAX_RETRIES})...")
                        time.sleep(wait_time)
                        continue
                print(f"    Error: {e}")
                return {"error": str(e), "extractions": []}
        
        return {"error": "Max retries exceeded", "extractions": []}
    
    def _call_llm_text(self, prompt: str) -> str:
        """Make LLM call expecting plain text response."""
        for attempt in range(MAX_RETRIES):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=GEMINI_TEMPERATURE
                    )
                )
                return response.text.strip()
                
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    if attempt < MAX_RETRIES - 1:
                        wait_time = RETRY_DELAY_SECONDS * (2 ** attempt)
                        print(f"    Rate limited, waiting {wait_time}s (retry {attempt + 2}/{MAX_RETRIES})...")
                        time.sleep(wait_time)
                        continue
                print(f"    Error: {e}")
                return "ERROR"
        
        return "ERROR"

    def extract_events_direct(self, document_content: str, document_title: str, author: str) -> dict:
        """
        Extract events directly (for small documents like letters/speeches).
        Uses prompt_direct.md to extract all events in one LLM call.
        """
        prompt = self._build_direct_prompt(document_content, document_title, author)
        return self._call_llm_json(prompt)

    def extract_events_batched(self, document_content: str, document_title: str, 
                                author: str, doc_id: str) -> dict:
        """
        Extract events from a large document (book) using two-stage processing.
        
        Stage 1: For each batch, extract ALL 5 events at once → save to separate intermediate files
        Stage 2: For each event, use prompt_final.md to create final JSON from intermediate content
        """
        # Split into batches
        batches = split_into_batches(document_content)
        total_batches = len(batches)
        total_tokens = estimate_tokens(document_content)
        
        print(f"    Document has ~{total_tokens:,} tokens, split into {total_batches} batches")
        print(f"    Stage 1: {total_batches} batch calls (all events per batch)")
        print(f"    Stage 2: {len(EVENTS)} final calls (one per event)")
        
        # Clear any existing intermediate files for this doc
        clear_intermediate_files(doc_id)
        
        # Initialize intermediate files for all events
        for event_name in EVENTS:
            init_intermediate_file(doc_id, event_name, document_title, author)
        
        # STAGE 1: Extract all events from each batch
        print(f"\n    Stage 1: Extracting from {total_batches} batches...")
        for batch_num, batch_content in batches:
            print(f"      Batch {batch_num}/{total_batches}...", end=" ")
            
            prompt = self._build_batch_prompt(
                batch_content, document_title, author, batch_num, total_batches
            )
            result = self._call_llm_json(prompt)
            
            # Parse JSON response: {"Event Name": ["excerpt1", ...], ...}
            if "error" not in result:
                found_count = 0
                for event_name in EVENTS:
                    excerpts = result.get(event_name, [])
                    if excerpts:
                        append_batch_extraction(
                            doc_id=doc_id,
                            event_name=event_name,
                            batch_num=batch_num,
                            relevant_text=excerpts
                        )
                        found_count += 1
                print(f"{found_count} events found")
            else:
                print("error")
            
            # Delay between batches
            if batch_num < total_batches:
                time.sleep(REQUEST_DELAY_SECONDS)
        
        # STAGE 2: Create final JSON for each event
        print(f"\n    Stage 2: Creating final JSON for {len(EVENTS)} events...")
        extractions = []
        
        for event_name in EVENTS:
            print(f"      {event_name}...", end=" ")
            
            intermediate_content = get_consolidated_intermediate(doc_id, event_name)
            
            if not intermediate_content or intermediate_content == "No information found.":
                extractions.append({
                    "event": event_name,
                    "author": author,
                    "claims": [],
                    "temporal_details": {"date": None, "time": None},
                    "tone": "Not mentioned"
                })
                print("no data")
                continue
            
            # Use prompt_final to create structured output
            prompt = self._build_final_prompt(
                source_content=intermediate_content,
                document_title=document_title,
                author=author,
                event_name=event_name
            )
            result = self._call_llm_json(prompt)
            
            if "error" not in result and "event" in result:
                extractions.append(result)
                print(f"{len(result.get('claims', []))} claims")
            else:
                extractions.append({
                    "event": event_name,
                    "author": author,
                    "claims": [],
                    "temporal_details": {"date": None, "time": None},
                    "tone": "Not mentioned"
                })
                print("error")
            
            time.sleep(REQUEST_DELAY_SECONDS)
        
        return {
            "extractions": extractions,
            "document_id": doc_id,
            "document_title": document_title,
            "document_type": "Book",
            "batches_processed": total_batches
        }

    def extract_events(self, document_content: str, document_title: str, 
                       author: str, document_type: str = "Unknown", 
                       doc_id: str = "unknown") -> dict:
        """
        Extract event information from a document.
        Uses batch processing for books, direct extraction for other types.
        
        Args:
            document_content: The full text content of the document
            document_title: Title of the document
            author: Author or source of the document
            document_type: Type of document (Book, Letter, Speech, etc.)
            doc_id: Document identifier
            
        Returns:
            Dictionary containing extracted event information
        """
        if document_type == "Book":
            return self.extract_events_batched(
                document_content, document_title, author, doc_id
            )
        else:
            return self.extract_events_direct(
                document_content, document_title, author
            )

    def extract_events_from_dataset(self, dataset: list) -> list:
        """
        Extract events from all documents in a dataset.
        Saves each document result immediately to final folder.
        
        Args:
            dataset: List of document dictionaries with 'content', 'title', 'from', 'document_type' fields
            
        Returns:
            List of extraction results for each document
        """
        all_extractions = []
        
        for i, doc in enumerate(dataset):
            doc_type = doc.get('document_type', 'Unknown')
            doc_id = doc.get('id', f'doc_{i}')
            doc_title = doc.get('title', 'Unknown')[:55]
            
            print(f"\n[{i+1}/{len(dataset)}] {doc_title}...")
            print(f"    Type: {doc_type}")
            
            # Determine author
            author = doc.get('from', 'Unknown Author')
            if author == 'Unknown Author':
                author = doc_type
            
            result = self.extract_events(
                document_content=doc.get('content', ''),
                document_title=doc.get('title', 'Unknown'),
                author=author,
                document_type=doc_type,
                doc_id=doc_id
            )
            
            # Add document metadata
            result['document_id'] = doc_id
            result['document_title'] = doc.get('title', 'Unknown')
            result['document_type'] = doc_type
            
            # Save each event as separate JSON file immediately
            if 'extractions' in result:
                save_all_events_for_document(
                    result['extractions'], 
                    doc_id, 
                    doc.get('title', 'Unknown'),
                    doc_type
                )
            
            all_extractions.append(result)
            
            # Delay between documents
            if i < len(dataset) - 1:
                print(f"    Waiting {REQUEST_DELAY_SECONDS}s before next document...")
                time.sleep(REQUEST_DELAY_SECONDS)
            
        return all_extractions


if __name__ == "__main__":
    # Quick test
    extractor = GeminiExtractor()
    print("Gemini Extractor initialized successfully!")
    print(f"Model: {extractor.model}")
    print(f"Events to extract: {EVENTS}")
    print(f"\nPrompts loaded:")
    print(f"  - Batch (books): {PROMPT_BATCH}")
    print(f"  - Final (consolidate): {PROMPT_FINAL}")
    print(f"  - Direct (letters/speeches): {PROMPT_DIRECT}")
