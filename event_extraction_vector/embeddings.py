"""
Local embedding service using sentence-transformers.
Fast local embeddings without API calls.
"""
import numpy as np
from typing import List
from sentence_transformers import SentenceTransformer

from chunker import Chunk


class EmbeddingService:
    """Creates embeddings using local sentence-transformers model."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize with a local embedding model.
        
        Args:
            model_name: HuggingFace model name
                - "all-MiniLM-L6-v2": Fast, 384 dim (default)
                - "all-mpnet-base-v2": Better quality, 768 dim
        """
        print(f"  Loading embedding model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        self.model_name = model_name
        print(f"  Model loaded (dimension: {self.dimension})")
    
    def embed_text(self, text: str) -> np.ndarray:
        """
        Create embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Numpy array of embedding
        """
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.astype(np.float32)
    
    def embed_texts(self, texts: List[str], batch_size: int = 64) -> np.ndarray:
        """
        Create embeddings for multiple texts (batched, very fast).
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for encoding
            
        Returns:
            Numpy array of embeddings (N x dimension)
        """
        print(f"    Encoding {len(texts)} texts...")
        embeddings = self.model.encode(
            texts, 
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        return embeddings.astype(np.float32)
    
    def embed_chunks(self, chunks: List[Chunk]) -> np.ndarray:
        """
        Create embeddings for a list of chunks.
        
        Args:
            chunks: List of Chunk objects
            
        Returns:
            Numpy array of embeddings (N x dimension)
        """
        texts = [chunk.text for chunk in chunks]
        return self.embed_texts(texts)
    
    def embed_query(self, query: str) -> np.ndarray:
        """
        Create embedding for a search query.
        
        Args:
            query: Search query text
            
        Returns:
            Numpy array of embedding
        """
        return self.embed_text(query)


if __name__ == "__main__":
    # Test embedding
    service = EmbeddingService()
    test_texts = [
        "Abraham Lincoln was the 16th president.", 
        "The Civil War began in 1861.",
        "Fort Sumter was attacked on April 12, 1861."
    ]
    embeddings = service.embed_texts(test_texts)
    print(f"Created {len(embeddings)} embeddings with dimension {embeddings.shape[1]}")
