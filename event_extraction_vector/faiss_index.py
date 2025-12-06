"""
FAISS vector index for semantic search.
Stores chunk embeddings for similarity search.
"""
import pickle
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional
import faiss

from config import INDEX_DIR
from chunker import Chunk


class FAISSIndex:
    """FAISS index for vector similarity search."""
    
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)  # Inner product (cosine similarity with normalized vectors)
        self.chunks: List[Chunk] = []
        self.doc_id_to_indices: dict = {}  # doc_id -> list of indices
    
    def add_chunks(self, chunks: List[Chunk], embeddings: np.ndarray):
        """
        Add chunks and their embeddings to the index.
        
        Args:
            chunks: List of Chunk objects
            embeddings: Numpy array of embeddings (N x dimension)
        """
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        
        start_idx = len(self.chunks)
        
        for i, chunk in enumerate(chunks):
            idx = start_idx + i
            
            # Track which indices belong to each doc
            if chunk.doc_id not in self.doc_id_to_indices:
                self.doc_id_to_indices[chunk.doc_id] = []
            self.doc_id_to_indices[chunk.doc_id].append(idx)
        
        self.chunks.extend(chunks)
        self.index.add(embeddings)
        
        print(f"  Added {len(chunks)} chunks to FAISS index (total: {len(self.chunks)})")
    
    def search(self, query_embedding: np.ndarray, k: int = 10, 
               doc_id: Optional[str] = None) -> List[Tuple[Chunk, float]]:
        """
        Search for similar chunks.
        
        Args:
            query_embedding: Query embedding vector
            k: Number of results to return
            doc_id: Optional - limit search to specific document
            
        Returns:
            List of (chunk, score) tuples
        """
        # Normalize query
        query = query_embedding.reshape(1, -1).astype(np.float32)
        faiss.normalize_L2(query)
        
        # Search more than k if filtering by doc_id
        search_k = k * 3 if doc_id else k
        
        scores, indices = self.index.search(query, min(search_k, len(self.chunks)))
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.chunks):
                continue
            
            chunk = self.chunks[idx]
            
            # Filter by doc_id if specified
            if doc_id and chunk.doc_id != doc_id:
                continue
            
            results.append((chunk, float(score)))
            
            if len(results) >= k:
                break
        
        return results
    
    def save(self, name: str = "faiss_index"):
        """Save index to disk."""
        INDEX_DIR.mkdir(parents=True, exist_ok=True)
        
        # Save FAISS index
        faiss.write_index(self.index, str(INDEX_DIR / f"{name}.faiss"))
        
        # Save metadata
        metadata = {
            "chunks": [c.to_dict() for c in self.chunks],
            "doc_id_to_indices": self.doc_id_to_indices,
            "dimension": self.dimension
        }
        with open(INDEX_DIR / f"{name}_meta.pkl", 'wb') as f:
            pickle.dump(metadata, f)
        
        print(f"  Saved FAISS index to {INDEX_DIR / name}")
    
    def load(self, name: str = "faiss_index") -> bool:
        """Load index from disk."""
        faiss_path = INDEX_DIR / f"{name}.faiss"
        meta_path = INDEX_DIR / f"{name}_meta.pkl"
        
        if not faiss_path.exists() or not meta_path.exists():
            return False
        
        self.index = faiss.read_index(str(faiss_path))
        
        with open(meta_path, 'rb') as f:
            metadata = pickle.load(f)
        
        self.chunks = [Chunk(**c) for c in metadata["chunks"]]
        self.doc_id_to_indices = metadata["doc_id_to_indices"]
        self.dimension = metadata["dimension"]
        
        print(f"  Loaded FAISS index with {len(self.chunks)} chunks")
        return True


if __name__ == "__main__":
    # Test FAISS index
    index = FAISSIndex(dimension=768)
    
    # Create dummy chunks and embeddings
    chunks = [
        Chunk("doc1", 0, "Test chunk 1", 0, 100),
        Chunk("doc1", 1, "Test chunk 2", 100, 200),
    ]
    embeddings = np.random.randn(2, 768).astype(np.float32)
    
    index.add_chunks(chunks, embeddings)
    
    # Test search
    query = np.random.randn(768).astype(np.float32)
    results = index.search(query, k=2)
    print(f"Found {len(results)} results")

