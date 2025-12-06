"""
Event extraction using Gemini LLM.
- Hybrid search results -> extraction for books
- Direct extraction for letters/speeches (LoC)
"""
import json
import time
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from google import genai

from config import (
    load_api_key, GEMINI_MODEL, GEMINI_TEMPERATURE, EVENTS,
    FINAL_DIR, EXTRACTION_DELAY_SECONDS, TOP_K_CHUNKS
)
from chunker import Chunk
from hybrid_search import HybridSearch


# Load prompts
PROMPT_DIR = Path(__file__).parent
PROMPT_EXTRACT = (PROMPT_DIR / "prompt_extract.md").read_text()
PROMPT_DIRECT = (PROMPT_DIR / "prompt_direct.md").read_text()


def get_event_slug(event_name: str) -> str:
    """Convert event name to filename-safe slug."""
    safe = re.sub(r'[^\w\s-]', '', event_name.lower())
    return re.sub(r'[\s]+', '_', safe)


def save_event_result(result: dict, doc_id: str, event_name: str, 
                      doc_title: str, doc_type: str):
    """Save extraction result for a single document-event pair."""
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    
    event_slug = get_event_slug(event_name)
    output_path = FINAL_DIR / f"{doc_id}_{event_slug}.json"
    
    result_with_meta = {
        "document_id": doc_id,
        "document_title": doc_title,
        "document_type": doc_type,
        **result
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result_with_meta, f, indent=2, ensure_ascii=False)


class Extractor:
    """Extracts event information using Gemini LLM."""
    
    def __init__(self):
        api_key = load_api_key()
        self.client = genai.Client(api_key=api_key)
        self.model = GEMINI_MODEL
    
    def _call_llm(self, prompt: str) -> dict:
        """Call Gemini and parse JSON response."""
        max_retries = 3
        retry_delay = 60
        
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config={
                        "temperature": GEMINI_TEMPERATURE,
                        "response_mime_type": "application/json"
                    }
                )
                
                result_text = response.text.strip()
                return json.loads(result_text)
                
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    wait_time = retry_delay * (2 ** attempt)
                    print(f"    Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"    Error: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
        
        return {"error": "Failed after retries"}
    
    def extract_from_chunks(self, chunks: List[Tuple[Chunk, float]], 
                            event_name: str, doc_title: str, author: str) -> dict:
        """
        Extract event information from retrieved chunks.
        
        Args:
            chunks: List of (chunk, score) tuples from hybrid search
            event_name: Event to extract
            doc_title: Document title
            author: Author name
            
        Returns:
            Extraction result dict
        """
        # Format chunks for prompt (limit each chunk to 2000 chars)
        chunk_texts = []
        for i, (chunk, score) in enumerate(chunks):
            text = chunk.text[:2000]  # Truncate long chunks
            chunk_texts.append(f"[Passage {i+1}]:\n{text}")
        
        retrieved_text = "\n\n".join(chunk_texts)
        
        prompt = PROMPT_EXTRACT.format(
            document_title=doc_title,
            author=author,
            event_name=event_name,
            retrieved_chunks=retrieved_text
        )
        
        return self._call_llm(prompt)
    
    def extract_direct(self, content: str, doc_title: str, author: str) -> dict:
        """
        Direct extraction for smaller documents (letters/speeches).
        
        Args:
            content: Full document content
            doc_title: Document title
            author: Author name
            
        Returns:
            Extraction result with all events
        """
        events_list = "\n".join(f"- {event}" for event in EVENTS)
        
        prompt = PROMPT_DIRECT.format(
            document_title=doc_title,
            author=author,
            events_list=events_list,
            document_content=content
        )
        
        return self._call_llm(prompt)
    
    def extract_from_book(self, hybrid_search: HybridSearch, doc_id: str,
                          doc_title: str, author: str) -> List[dict]:
        """
        Extract all events from a book using hybrid search.
        
        Args:
            hybrid_search: HybridSearch instance with indexed document
            doc_id: Document ID
            doc_title: Document title
            author: Author name
            
        Returns:
            List of extraction results (one per event)
        """
        results = []
        
        for event_name in EVENTS:
            print(f"    Searching for: {event_name}")
            
            try:
                # Retrieve relevant chunks
                chunks = hybrid_search.search_for_event(event_name, doc_id, k=TOP_K_CHUNKS)
                
                if not chunks:
                    print(f"      No relevant chunks found")
                    result = {
                        "event": event_name,
                        "author": author,
                        "claims": [],
                        "temporal_details": {"date": None, "time": None},
                        "tone": "Not mentioned"
                    }
                else:
                    print(f"      Found {len(chunks)} relevant chunks, extracting...")
                    result = self.extract_from_chunks(chunks, event_name, doc_title, author)
                    if "error" in result:
                        print(f"      Error in extraction, using empty result")
                        result = {
                            "event": event_name,
                            "author": author,
                            "claims": [],
                            "temporal_details": {"date": None, "time": None},
                            "tone": "Error in extraction"
                        }
                    time.sleep(EXTRACTION_DELAY_SECONDS)
            except Exception as e:
                print(f"      Exception: {e}")
                result = {
                    "event": event_name,
                    "author": author,
                    "claims": [],
                    "temporal_details": {"date": None, "time": None},
                    "tone": "Error"
                }
            
            # Save immediately
            save_event_result(result, doc_id, event_name, doc_title, "Book")
            results.append(result)
        
        return results
    
    def extract_from_letter(self, content: str, doc_id: str, 
                            doc_title: str, author: str, doc_type: str) -> List[dict]:
        """
        Extract all events from a letter/speech using direct extraction.
        
        Args:
            content: Document content
            doc_id: Document ID
            doc_title: Document title
            author: Author name
            doc_type: Document type (Letter/Speech)
            
        Returns:
            List of extraction results (one per event)
        """
        print(f"    Direct extraction...")
        
        result = self.extract_direct(content, doc_title, author)
        extractions = result.get("extractions", [])
        
        # Save each event separately
        for extraction in extractions:
            event_name = extraction.get("event", "unknown")
            save_event_result(extraction, doc_id, event_name, doc_title, doc_type)
        
        return extractions


if __name__ == "__main__":
    # Test extractor initialization
    extractor = Extractor()
    print(f"Extractor initialized with model: {extractor.model}")
    print(f"Events to extract: {EVENTS}")

