"""
BM25 keyword index for lexical search.
Complements semantic search with exact keyword matching.
"""
import pickle
import re
from pathlib import Path
from typing import List, Tuple, Optional
from rank_bm25 import BM25Okapi

from config import INDEX_DIR
from chunker import Chunk


def tokenize(text: str) -> List[str]:
    """
    Simple tokenization for BM25.
    Lowercases and splits on non-alphanumeric characters.
    """
    text = text.lower()
    tokens = re.findall(r'\b[a-z0-9]+\b', text)
    return tokens


class BM25Index:
    """BM25 index for keyword-based search."""
    
    def __init__(self):
        self.chunks: List[Chunk] = []
        self.tokenized_chunks: List[List[str]] = []
        self.bm25: Optional[BM25Okapi] = None
        self.doc_id_to_indices: dict = {}
    
    def add_chunks(self, chunks: List[Chunk]):
        """
        Add chunks to the BM25 index.
        
        Args:
            chunks: List of Chunk objects
        """
        start_idx = len(self.chunks)
        
        for i, chunk in enumerate(chunks):
            idx = start_idx + i
            
            # Track which indices belong to each doc
            if chunk.doc_id not in self.doc_id_to_indices:
                self.doc_id_to_indices[chunk.doc_id] = []
            self.doc_id_to_indices[chunk.doc_id].append(idx)
            
            # Tokenize chunk text
            tokens = tokenize(chunk.text)
            self.tokenized_chunks.append(tokens)
        
        self.chunks.extend(chunks)
        
        # Rebuild BM25 index
        self.bm25 = BM25Okapi(self.tokenized_chunks)
        
        print(f"  Added {len(chunks)} chunks to BM25 index (total: {len(self.chunks)})")
    
    def search(self, query: str, k: int = 10, 
               doc_id: Optional[str] = None) -> List[Tuple[Chunk, float]]:
        """
        Search for chunks matching the query.
        
        Args:
            query: Search query string
            k: Number of results to return
            doc_id: Optional - limit search to specific document
            
        Returns:
            List of (chunk, score) tuples
        """
        if self.bm25 is None or len(self.chunks) == 0:
            return []
        
        query_tokens = tokenize(query)
        scores = self.bm25.get_scores(query_tokens)
        
        # Get indices sorted by score
        sorted_indices = scores.argsort()[::-1]
        
        results = []
        for idx in sorted_indices:
            if scores[idx] <= 0:
                continue
            
            chunk = self.chunks[idx]
            
            # Filter by doc_id if specified
            if doc_id and chunk.doc_id != doc_id:
                continue
            
            results.append((chunk, float(scores[idx])))
            
            if len(results) >= k:
                break
        
        return results
    
    def save(self, name: str = "bm25_index"):
        """Save index to disk."""
        INDEX_DIR.mkdir(parents=True, exist_ok=True)
        
        metadata = {
            "chunks": [c.to_dict() for c in self.chunks],
            "tokenized_chunks": self.tokenized_chunks,
            "doc_id_to_indices": self.doc_id_to_indices
        }
        
        with open(INDEX_DIR / f"{name}.pkl", 'wb') as f:
            pickle.dump(metadata, f)
        
        print(f"  Saved BM25 index to {INDEX_DIR / name}")
    
    def load(self, name: str = "bm25_index") -> bool:
        """Load index from disk."""
        path = INDEX_DIR / f"{name}.pkl"
        
        if not path.exists():
            return False
        
        with open(path, 'rb') as f:
            metadata = pickle.load(f)
        
        self.chunks = [Chunk(**c) for c in metadata["chunks"]]
        self.tokenized_chunks = metadata["tokenized_chunks"]
        self.doc_id_to_indices = metadata["doc_id_to_indices"]
        
        # Rebuild BM25
        self.bm25 = BM25Okapi(self.tokenized_chunks)
        
        print(f"  Loaded BM25 index with {len(self.chunks)} chunks")
        return True


if __name__ == "__main__":
    # Test BM25 index
    index = BM25Index()
    
    chunks = [
        Chunk("doc1", 0, "Abraham Lincoln was the 16th president of the United States.", 0, 100),
        Chunk("doc1", 1, "The Civil War began in 1861 and ended in 1865.", 100, 200),
        Chunk("doc1", 2, "Fort Sumter was attacked on April 12, 1861.", 200, 300),
    ]
    
    index.add_chunks(chunks)
    
    # Test search
    results = index.search("Fort Sumter attack", k=2)
    for chunk, score in results:
        print(f"Score {score:.2f}: {chunk.text[:50]}...")

