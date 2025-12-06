"""
Main pipeline for hybrid vector event extraction.

Processing:
- Books (Gutenberg): Hybrid search (FAISS + BM25) -> Gemini extraction
- Letters/Speeches (LoC): Direct Gemini extraction
"""
import json
import time
from pathlib import Path
from datetime import datetime

from config import PROCESSED_DIR, FINAL_DIR, EVENTS, EXTRACTION_DELAY_SECONDS
from chunker import chunk_documents, Chunk
from embeddings import EmbeddingService
from faiss_index import FAISSIndex
from bm25_index import BM25Index
from hybrid_search import HybridSearch
from extractor import Extractor


def load_dataset(filepath: Path) -> list:
    """Load a JSON dataset file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def consolidate_results():
    """
    Consolidate all individual event extraction JSON files into a single all_events.json.
    """
    all_events = []
    
    if not FINAL_DIR.exists():
        print("No output directory found!")
        return
    
    json_files = sorted(FINAL_DIR.glob("*.json"))
    
    # Skip all_events.json if it already exists
    json_files = [f for f in json_files if f.name != "all_events.json"]
    
    for json_file in json_files:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            all_events.append(data)
    
    # Save consolidated file
    output_path = FINAL_DIR / "all_events.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_events, f, indent=2, ensure_ascii=False)
    
    print(f"\nConsolidated {len(all_events)} extractions into: {output_path}")


def run_extraction():
    """Run the full hybrid vector extraction pipeline."""
    print("=" * 60)
    print("HYBRID VECTOR EVENT EXTRACTION PIPELINE")
    print("=" * 60)
    
    print(f"\nTarget Events:")
    for event in EVENTS:
        print(f"  - {event}")
    
    print(f"\nProcessing Strategy:")
    print(f"  - Books: Hybrid Search (FAISS + BM25) -> Extraction")
    print(f"  - Letters/Speeches: Direct Extraction")
    print(f"  - Output: {FINAL_DIR}")
    
    # Load datasets
    print("\n[1/5] Loading datasets...")
    
    loc_path = PROCESSED_DIR / "loc_lincoln_dataset.json"
    gutenberg_path = PROCESSED_DIR / "gutenberg_lincoln_dataset.json"
    
    loc_dataset = load_dataset(loc_path)
    gutenberg_dataset = load_dataset(gutenberg_path)
    
    print(f"  - LoC: {len(loc_dataset)} documents (Direct extraction)")
    print(f"  - Gutenberg: {len(gutenberg_dataset)} books (Hybrid search)")
    
    # Initialize services
    print("\n[2/5] Initializing services...")
    embedding_service = EmbeddingService()
    extractor = Extractor()
    print(f"  - Embedding model: {embedding_service.model}")
    print(f"  - LLM model: {extractor.model}")
    
    # Process LoC dataset (direct extraction)
    print("\n[3/5] Processing LoC dataset (Letters/Speeches)...")
    print("-" * 40)
    
    loc_results = []
    for i, doc in enumerate(loc_dataset):
        doc_id = doc.get('id', f'loc_{i}')
        doc_title = doc.get('title', 'Unknown')[:50]
        doc_type = doc.get('document_type', 'Letter')
        author = doc.get('from', 'Abraham Lincoln')
        content = doc.get('content', '')
        
        print(f"\n[{i+1}/{len(loc_dataset)}] {doc_title}...")
        
        extractions = extractor.extract_from_letter(
            content=content,
            doc_id=doc_id,
            doc_title=doc.get('title', 'Unknown'),
            author=author,
            doc_type=doc_type
        )
        
        loc_results.append({
            "doc_id": doc_id,
            "doc_title": doc.get('title', 'Unknown'),
            "extractions": extractions
        })
        
        if i < len(loc_dataset) - 1:
            print(f"    Waiting {EXTRACTION_DELAY_SECONDS}s...")
            time.sleep(EXTRACTION_DELAY_SECONDS)
    
    # Process Gutenberg dataset (hybrid search)
    print("\n[4/5] Processing Gutenberg dataset (Books)...")
    print("-" * 40)
    
    # Try to load existing indices first
    print("\n  Checking for existing indices...")
    faiss_index = FAISSIndex(dimension=embedding_service.dimension)
    bm25_index = BM25Index()
    
    faiss_loaded = faiss_index.load("gutenberg_faiss")
    bm25_loaded = bm25_index.load("gutenberg_bm25")
    
    if faiss_loaded and bm25_loaded:
        print("  Loaded existing indices - skipping embedding creation!")
    else:
        # Prepare book data
        books_data = []
        for doc in gutenberg_dataset:
            doc_id = doc.get('id', 'unknown')
            books_data.append({
                'id': doc_id,
                'content': doc.get('content', ''),
                'title': doc.get('title', 'Unknown'),
                'author': doc.get('from', 'Unknown Author')
            })
        
        print("\n  Creating chunks...")
        all_chunks, chunks_by_doc = chunk_documents(books_data)
        
        print(f"\n  Total chunks: {len(all_chunks)}")
        
        # Create embeddings for all chunks
        print("\n  Creating embeddings (this may take a while)...")
        embeddings = embedding_service.embed_chunks(all_chunks)
        
        # Add to indices
        print("\n  Building indices...")
        faiss_index.add_chunks(all_chunks, embeddings)
        bm25_index.add_chunks(all_chunks)
        
        # Save indices for future runs
        faiss_index.save("gutenberg_faiss")
        bm25_index.save("gutenberg_bm25")
    
    # Create hybrid search
    hybrid_search = HybridSearch(faiss_index, bm25_index, embedding_service)
    
    # Extract from each book
    print("\n  Extracting events from books...")
    
    gutenberg_results = []
    for i, doc in enumerate(gutenberg_dataset):
        doc_id = doc.get('id', f'gutenberg_{i}')
        doc_title = doc.get('title', 'Unknown')[:50]
        author = doc.get('from', 'Unknown Author')
        
        print(f"\n  [{i+1}/{len(gutenberg_dataset)}] {doc_title}...")
        
        extractions = extractor.extract_from_book(
            hybrid_search=hybrid_search,
            doc_id=doc_id,
            doc_title=doc.get('title', 'Unknown'),
            author=author
        )
        
        gutenberg_results.append({
            "doc_id": doc_id,
            "doc_title": doc.get('title', 'Unknown'),
            "extractions": extractions
        })
    
    # Summary
    print("\n" + "=" * 60)
    print("[5/5] EXTRACTION COMPLETE")
    print("=" * 60)
    
    total_files = len(loc_dataset) * 5 + len(gutenberg_dataset) * 5
    print(f"\nOutput files: {total_files} document-event pairs")
    print(f"Location: {FINAL_DIR}")
    
    # Count files created
    if FINAL_DIR.exists():
        files = list(FINAL_DIR.glob("*.json"))
        print(f"Files created: {len(files)}")
    
    # Consolidate all results into all_events.json
    consolidate_results()
    
    print("\n[Done]")


if __name__ == "__main__":
    run_extraction()

