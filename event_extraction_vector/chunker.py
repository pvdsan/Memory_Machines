"""
Document chunking utilities for hybrid search.
Splits documents into overlapping chunks for embedding and indexing.
"""
from typing import List, Dict, Tuple
from dataclasses import dataclass

from config import CHUNK_SIZE_TOKENS, CHUNK_OVERLAP_TOKENS, CHARS_PER_TOKEN


@dataclass
class Chunk:
    """Represents a document chunk with metadata."""
    doc_id: str
    chunk_id: int
    text: str
    start_char: int
    end_char: int
    
    def to_dict(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "chunk_id": self.chunk_id,
            "text": self.text,
            "start_char": self.start_char,
            "end_char": self.end_char
        }


def estimate_tokens(text: str) -> int:
    """Estimate token count from text."""
    return len(text) // CHARS_PER_TOKEN


def estimate_chars(tokens: int) -> int:
    """Convert token count to character count."""
    return tokens * CHARS_PER_TOKEN


def chunk_document(content: str, doc_id: str) -> List[Chunk]:
    """
    Split a document into overlapping chunks.
    
    Args:
        content: Full document text
        doc_id: Document identifier
        
    Returns:
        List of Chunk objects
    """
    chunk_size_chars = estimate_chars(CHUNK_SIZE_TOKENS)
    overlap_chars = estimate_chars(CHUNK_OVERLAP_TOKENS)
    step_size = chunk_size_chars - overlap_chars
    
    chunks = []
    start = 0
    chunk_id = 0
    
    while start < len(content):
        end = start + chunk_size_chars
        
        # Try to break at paragraph or sentence boundary
        if end < len(content):
            # Look for paragraph break
            para_break = content.rfind('\n\n', start + step_size, end)
            if para_break > start + step_size // 2:
                end = para_break + 2
            else:
                # Look for sentence break
                sentence_break = content.rfind('. ', start + step_size, end)
                if sentence_break > start + step_size // 2:
                    end = sentence_break + 2
        
        chunk_text = content[start:end].strip()
        
        if chunk_text:
            chunks.append(Chunk(
                doc_id=doc_id,
                chunk_id=chunk_id,
                text=chunk_text,
                start_char=start,
                end_char=end
            ))
            chunk_id += 1
        
        # Move to next chunk with overlap
        start = end - overlap_chars
        if start >= len(content) - overlap_chars:
            break
    
    return chunks


def chunk_documents(documents: List[Dict]) -> Tuple[List[Chunk], Dict[str, List[Chunk]]]:
    """
    Chunk multiple documents.
    
    Args:
        documents: List of document dicts with 'id', 'content' fields
        
    Returns:
        Tuple of (all_chunks, chunks_by_doc)
    """
    all_chunks = []
    chunks_by_doc = {}
    
    for doc in documents:
        doc_id = doc.get('id', 'unknown')
        content = doc.get('content', '')
        
        doc_chunks = chunk_document(content, doc_id)
        all_chunks.extend(doc_chunks)
        chunks_by_doc[doc_id] = doc_chunks
        
        print(f"  {doc_id}: {len(doc_chunks)} chunks (~{estimate_tokens(content):,} tokens)")
    
    return all_chunks, chunks_by_doc


if __name__ == "__main__":
    # Test chunking
    test_text = "A" * 20000  # ~5000 tokens
    chunks = chunk_document(test_text, "test_doc")
    print(f"Split {len(test_text)} chars into {len(chunks)} chunks")
    for chunk in chunks:
        print(f"  Chunk {chunk.chunk_id}: {len(chunk.text)} chars")

