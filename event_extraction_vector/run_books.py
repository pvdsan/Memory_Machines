"""
Process only Gutenberg books (LoC already done).
"""
import json
from pathlib import Path

from config import PROCESSED_DIR, FINAL_DIR
from chunker import chunk_documents
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


def run_books():
    """Process only Gutenberg books."""
    print("=" * 60)
    print("PROCESSING GUTENBERG BOOKS (Hybrid Search)")
    print("=" * 60)
    
    # Load Gutenberg dataset
    gutenberg_path = PROCESSED_DIR / "gutenberg_lincoln_dataset.json"
    gutenberg_dataset = load_dataset(gutenberg_path)
    print(f"\nLoaded: {len(gutenberg_dataset)} books")
    
    # Initialize services
    print("\nInitializing services...")
    embedding_service = EmbeddingService()
    extractor = Extractor()
    
    # Try to load existing indices first
    print("\nChecking for existing indices...")
    faiss_index = FAISSIndex(dimension=embedding_service.dimension)
    bm25_index = BM25Index()
    
    faiss_loaded = faiss_index.load("gutenberg_faiss")
    bm25_loaded = bm25_index.load("gutenberg_bm25")
    
    if faiss_loaded and bm25_loaded:
        print("Loaded existing indices - skipping embedding creation!")
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
    
    # Create chunks
    print("\nChunking books...")
    all_chunks, chunks_by_doc = chunk_documents(books_data)
    print(f"Total chunks: {len(all_chunks)}")
    
    # Create embeddings
    print("\nCreating embeddings (this will take ~10-15 minutes)...")
    embeddings = embedding_service.embed_chunks(all_chunks)
    print(f"Created {len(embeddings)} embeddings")
    
        # Build indices
    print("\nBuilding indices...")
    faiss_index.add_chunks(all_chunks, embeddings)
    bm25_index.add_chunks(all_chunks)
    
        # Save indices for future runs
    faiss_index.save("gutenberg_faiss")
    bm25_index.save("gutenberg_bm25")
    
    # Create hybrid search
    hybrid_search = HybridSearch(faiss_index, bm25_index, embedding_service)
    
    # Extract from each book
    print("\n" + "=" * 60)
    print("EXTRACTING EVENTS")
    print("=" * 60)
    
    for i, doc in enumerate(gutenberg_dataset):
        doc_id = doc.get('id', f'gutenberg_{i}')
        doc_title = doc.get('title', 'Unknown')[:50]
        author = doc.get('from', 'Unknown Author')
        
        print(f"\n[{i+1}/{len(gutenberg_dataset)}] {doc_title}...")
        
        extractor.extract_from_book(
            hybrid_search=hybrid_search,
            doc_id=doc_id,
            doc_title=doc.get('title', 'Unknown'),
            author=author
        )
    
    # Summary
    print("\n" + "=" * 60)
    print("COMPLETE")
    print("=" * 60)
    
    if FINAL_DIR.exists():
        files = list(FINAL_DIR.glob("gutenberg_*.json"))
        print(f"Gutenberg files created: {len(files)}")
    
    # Consolidate all results into all_events.json
    consolidate_results()


if __name__ == "__main__":
    run_books()

