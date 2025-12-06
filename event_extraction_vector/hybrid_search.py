"""
Hybrid search combining FAISS (semantic) and BM25 (keyword) search.
Uses Reciprocal Rank Fusion (RRF) to combine results.
"""
import json
import numpy as np
from typing import List, Tuple, Optional, Dict
from collections import defaultdict
from google import genai

from config import TOP_K_CHUNKS, FAISS_TOP_K, BM25_TOP_K, USE_WEB_SEARCH, load_api_key, GEMINI_MODEL
from chunker import Chunk
from faiss_index import FAISSIndex
from bm25_index import BM25Index
from embeddings import EmbeddingService


class HybridSearch:
    """
    Combines FAISS vector search and BM25 keyword search.
    Uses Reciprocal Rank Fusion to merge results.
    """
    
    def __init__(self, faiss_index: FAISSIndex, bm25_index: BM25Index,
                 embedding_service: EmbeddingService):
        self.faiss_index = faiss_index
        self.bm25_index = bm25_index
        self.embedding_service = embedding_service
        
        # RRF parameter (typically 60)
        self.rrf_k = 60
        
        # Weight for combining semantic vs keyword (0.5 = equal weight)
        self.semantic_weight = 0.5
    
    def search(self, query: str, k: int = TOP_K_CHUNKS,
               doc_id: Optional[str] = None) -> List[Tuple[Chunk, float]]:
        """
        Perform hybrid search combining semantic and keyword results.
        
        Args:
            query: Search query
            k: Number of results to return
            doc_id: Optional - limit search to specific document
            
        Returns:
            List of (chunk, combined_score) tuples
        """
        # Get semantic results from FAISS
        query_embedding = self.embedding_service.embed_query(query)
        faiss_results = self.faiss_index.search(query_embedding, k=FAISS_TOP_K, doc_id=doc_id)
        
        # Get keyword results from BM25
        bm25_results = self.bm25_index.search(query, k=BM25_TOP_K, doc_id=doc_id)
        
        # Combine using RRF
        combined = self._reciprocal_rank_fusion(faiss_results, bm25_results)
        
        # Return top-k
        return combined[:k]
    
    def _reciprocal_rank_fusion(self, 
                                 faiss_results: List[Tuple[Chunk, float]],
                                 bm25_results: List[Tuple[Chunk, float]]) -> List[Tuple[Chunk, float]]:
        """
        Combine results using Reciprocal Rank Fusion.
        
        RRF score = sum(1 / (k + rank)) for each result list
        """
        # Track scores by chunk_id
        chunk_scores: Dict[str, float] = defaultdict(float)
        chunk_map: Dict[str, Chunk] = {}
        
        # Add FAISS scores
        for rank, (chunk, score) in enumerate(faiss_results):
            chunk_key = f"{chunk.doc_id}_{chunk.chunk_id}"
            rrf_score = self.semantic_weight * (1.0 / (self.rrf_k + rank + 1))
            chunk_scores[chunk_key] += rrf_score
            chunk_map[chunk_key] = chunk
        
        # Add BM25 scores
        for rank, (chunk, score) in enumerate(bm25_results):
            chunk_key = f"{chunk.doc_id}_{chunk.chunk_id}"
            rrf_score = (1 - self.semantic_weight) * (1.0 / (self.rrf_k + rank + 1))
            chunk_scores[chunk_key] += rrf_score
            chunk_map[chunk_key] = chunk
        
        # Sort by combined score
        sorted_results = sorted(chunk_scores.items(), key=lambda x: x[1], reverse=True)
        
        return [(chunk_map[key], score) for key, score in sorted_results]
    
    def search_for_event(self, event_name: str, doc_id: str, 
                         k: int = TOP_K_CHUNKS) -> List[Tuple[Chunk, float]]:
        """
        Search for chunks relevant to a specific event in a document.
        
        Args:
            event_name: Name of the historical event
            doc_id: Document to search within
            k: Number of chunks to retrieve
            
        Returns:
            List of (chunk, score) tuples
        """
        # Enhance query with event context
        query = f"{event_name} Abraham Lincoln historical event"
        
        return self.search(query, k=k, doc_id=doc_id)


def generate_queries_for_event(event_name: str, client: genai.Client) -> List[str]:
    """
    Use LLM to generate 5 diverse search phrases for an event.
    Optionally uses web search grounding based on config.
    
    Args:
        event_name: Name of the historical event
        client: Gemini client instance
        
    Returns:
        List of 5 search query strings
    """
    if USE_WEB_SEARCH:
        prompt = f"""Search the web for information about this historical event related to Abraham Lincoln, then generate exactly 5 diverse search queries that could be used to find relevant passages in historical documents:

Event: {event_name}

Requirements:
- Each query should be a short phrase (3-8 words)
- Queries should approach the event from different angles (people involved, location, date, significance, etc.)
- Do NOT include direct quotes or specific text that might appear in documents
- Keep queries general enough that a user without prior document knowledge would use them

Return ONLY a JSON array of 5 strings, no explanation:
["query 1", "query 2", "query 3", "query 4", "query 5"]"""
    else:
        prompt = f"""Generate exactly 5 diverse search queries to find information about this historical event in documents about Abraham Lincoln:

Event: {event_name}

Requirements:
- Each query should be a short phrase (3-8 words)
- Queries should approach the event from different angles (people involved, location, date, significance, etc.)
- Do NOT include direct quotes or specific text that might appear in documents
- Keep queries general enough that a user without prior document knowledge would use them

Return ONLY a JSON array of 5 strings, no explanation:
["query 1", "query 2", "query 3", "query 4", "query 5"]"""

    try:
        # Configure based on whether web search is enabled
        config = {"temperature": 0.7}
        if USE_WEB_SEARCH:
            config["tools"] = [{"google_search": {}}]
        else:
            config["response_mime_type"] = "application/json"
        
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=config
        )
        
        # Extract text and parse JSON from response
        response_text = response.text.strip()
        
        # Try to find JSON array in response
        import re
        json_match = re.search(r'\[.*?\]', response_text, re.DOTALL)
        if json_match:
            queries = json.loads(json_match.group())
        else:
            queries = json.loads(response_text)
        
        # Ensure we have exactly 5 queries
        if isinstance(queries, list) and len(queries) >= 5:
            return queries[:5]
        elif isinstance(queries, list) and len(queries) > 0:
            return queries
        else:
            # Fallback to just event name
            return [event_name]
    except Exception as e:
        print(f"    Error generating queries: {e}")
        return [event_name]


def create_event_queries() -> Dict[str, List[str]]:
    """
    Use LLM to generate diverse search queries for each event.
    This is fair because the LLM uses general knowledge, not document contents.
    """
    from config import EVENTS
    
    search_mode = "with web search" if USE_WEB_SEARCH else "without web search"
    print(f"  Generating search queries via LLM ({search_mode})...")
    
    api_key = load_api_key()
    client = genai.Client(api_key=api_key)
    
    queries = {}
    for event in EVENTS:
        print(f"    {event}...")
        queries[event] = generate_queries_for_event(event, client)
    
    return queries


if __name__ == "__main__":
    print("Hybrid search module loaded successfully")
    print("\nGenerating event queries via LLM:")
    event_queries = create_event_queries()
    for event, queries in event_queries.items():
        print(f"\n{event}:")
        for q in queries:
            print(f"  - {q}")

