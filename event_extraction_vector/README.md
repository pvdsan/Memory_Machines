# Hybrid Search Event Extraction Pipeline

## 1. Overview

This module implements a **Retrieval-Augmented Generation (RAG)** pipeline for extracting historical event information from Abraham Lincoln documents. It combines:

- **Semantic Search** (FAISS vector index)
- **Keyword Search** (BM25 lexical index)
- **LLM Extraction** (Gemini)

The hybrid approach ensures both conceptual relevance (semantic) and exact term matching (keyword) when retrieving relevant passages from lengthy historical books.

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    HYBRID SEARCH EVENT EXTRACTION PIPELINE                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                         DATA SOURCES                                   │ │
│  │  ┌─────────────────────┐         ┌─────────────────────┐               │ │
│  │  │ Gutenberg Books     │         │ LoC Letters/Speeches│               │ │
│  │  │ (Long documents)    │         │ (Short documents)   │               │ │
│  │  └──────────┬──────────┘         └──────────┬──────────┘               │ │
│  └─────────────┼───────────────────────────────┼──────────────────────────┘ │
│                │                               │                            │
│                ▼                               ▼                            │
│  ┌─────────────────────────────┐   ┌─────────────────────────────┐          │
│  │    HYBRID SEARCH PATH       │   │    DIRECT EXTRACTION PATH   │          │
│  │    (Books: ~100K+ words)    │   │    (Letters: <5K words)     │          │
│  └──────────────┬──────────────┘   └──────────────┬──────────────┘          │
│                 │                                 │                         │
│                 ▼                                 │                         │
│  ┌──────────────────────────────────────────┐    │                          │
│  │           CHUNKING LAYER                 │    │                          │
│  │  ┌────────────────────────────────────┐  │    │                          │
│  │  │ chunker.py                         │  │    │                          │
│  │  │ • 1000 tokens per chunk            │  │    │                          │
│  │  │ • 200 token overlap                │  │    │                          │
│  │  │ • Sentence boundary alignment      │  │    │                          │
│  │  └────────────────────────────────────┘  │    │                          │
│  └──────────────┬───────────────────────────┘    │                          │
│                 │                                 │                         │
│                 ▼                                 │                         │
│  ┌──────────────────────────────────────────┐    │                          │
│  │         DUAL INDEX CREATION              │    │                          │
│  │  ┌─────────────────┐ ┌─────────────────┐ │    │                          │
│  │  │ FAISS Index     │ │ BM25 Index      │ │    │                          │
│  │  │ (Semantic)      │ │ (Keyword)       │ │    │                          │
│  │  │                 │ │                 │ │    │                          │
│  │  │ embeddings.py   │ │ bm25_index.py   │ │    │                          │
│  │  │ faiss_index.py  │ │                 │ │    │                          │
│  │  └────────┬────────┘ └────────┬────────┘ │    │                          │
│  └───────────┼───────────────────┼──────────┘    │                          │
│              │                   │                │                         │
│              └─────────┬─────────┘                │                         │
│                        ▼                          │                         │
│  ┌──────────────────────────────────────────┐    │                          │
│  │          HYBRID SEARCH                   │    │                          │
│  │  ┌────────────────────────────────────┐  │    │                          │
│  │  │ hybrid_search.py                   │  │    │                          │
│  │  │                                    │  │    │                          │
│  │  │ Reciprocal Rank Fusion (RRF)       │  │    │                          │
│  │  │ Score = Σ 1/(k + rank)             │  │    │                          │
│  │  │                                    │  │    │                          │
│  │  │ Weights: 50% Semantic + 50% BM25   │  │    │                          │
│  │  └────────────────────────────────────┘  │    │                          │
│  └──────────────┬───────────────────────────┘    │                          │
│                 │                                 │                         │
│                 │    Top-K Chunks                 │                         │
│                 ▼                                 ▼                         │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                      LLM EXTRACTION LAYER                            │   │
│  │  ┌────────────────────────────────────────────────────────────────┐  │   │
│  │  │ extractor.py                                                   │  │   │
│  │  │                                                                │  │   │
│  │  │ Gemini 2.5 Flash Lite                                          │  │   │
│  │  │ • prompt_extract.md (for retrieved chunks)                     │  │   │
│  │  │ • prompt_direct.md (for full short documents)                  │  │   │
│  │  └────────────────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────┬───────────────────────────────────┘   │
│                                     │                                       │
│                                     ▼                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                           OUTPUT                                     │   │
│  │  output/final/{doc_id}_{event_slug}.json                             │   │
│  │  output/final/all_events.json (consolidated)                         │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└──────────────────────────────────────────────────────────────────────────────
```

---

## 3. Hybrid Search Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        HYBRID SEARCH DETAIL                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│    Query: "Election Night 1860 Abraham Lincoln"                         │
│                          │                                              │
│            ┌─────────────┴─────────────┐                                │
│            ▼                           ▼                                │
│   ┌─────────────────┐         ┌─────────────────┐                       │
│   │  SEMANTIC PATH  │         │  KEYWORD PATH   │                       │
│   ├─────────────────┤         ├─────────────────┤                       │
│   │                 │         │                 │                       │
│   │ Query → Embed   │         │ Query → Tokenize│                       │
│   │      ↓          │         │      ↓          │                       │
│   │ FAISS Search    │         │ BM25 Search     │                       │
│   │ (Cosine Sim)    │         │ (TF-IDF Variant)│                       │
│   │      ↓          │         │      ↓          │                       │
│   │ Top-15 Results  │         │ Top-15 Results  │                       │
│   │                 │         │                 │                       │
│   └────────┬────────┘         └────────┬────────┘                       │
│            │                           │                                │
│            │   Ranked Lists            │                                │
│            └─────────────┬─────────────┘                                │
│                          ▼                                              │
│            ┌─────────────────────────────┐                              │
│            │  RECIPROCAL RANK FUSION     │                              │
│            │                             │                              │
│            │  For each chunk:            │                              │
│            │  RRF = Σ 1/(60 + rank)      │                              │
│            │                             │                              │
│            │  Combined Score =           │                              │
│            │    0.5 × RRF_semantic +     │                              │
│            │    0.5 × RRF_keyword        │                              │
│            └──────────────┬──────────────┘                              │
│                           ▼                                             │
│            ┌─────────────────────────────┐                              │
│            │      TOP-5 CHUNKS           │                              │
│            │  (Sorted by combined score) │                              │
│            └─────────────────────────────┘                              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Document Processing Strategies

| Document Type | Source | Size | Processing Method |
|---------------|--------|------|-------------------|
| **Books** | Gutenberg | 100K+ words | Chunk → Index → Hybrid Search → Extract |
| **Letters** | LoC | <5K words | Direct LLM Extraction |
| **Speeches** | LoC | <5K words | Direct LLM Extraction |

**Rationale:**
- Long books cannot fit in LLM context windows → require chunking and retrieval
- Short documents fit entirely → direct extraction is more accurate

---

## 5. Component Details

### 5.1 Chunking (`chunker.py`)

**Technique:** Sliding window with intelligent boundaries

| Parameter | Value | Purpose |
|-----------|-------|---------|
| Chunk Size | 1000 tokens (~4000 chars) | Balance context vs. specificity |
| Overlap | 200 tokens (~800 chars) | Preserve cross-boundary information |
| Boundary | Paragraph/Sentence | Avoid mid-sentence splits |

```
Document: [====================================================]
                   ↓ Chunking
Chunk 1:  [===========]
Chunk 2:       [===========]      ← 200 token overlap
Chunk 3:            [===========]
```

### 5.2 Embedding Service (`embeddings.py`)

**Model:** `all-MiniLM-L6-v2` (sentence-transformers)

| Property | Value |
|----------|-------|
| Dimension | 384 |
| Type | Local (no API calls) |
| Speed | ~1000 embeddings/sec |

**Why Local Embeddings:**
- Fast batch processing (no rate limits)
- Free (no API costs)
- Consistent results

### 5.3 FAISS Index (`faiss_index.py`)

**Index Type:** `IndexFlatIP` (Inner Product)

| Feature | Implementation |
|---------|----------------|
| Similarity | Cosine (L2-normalized vectors) |
| Filtering | Document-level filtering supported |
| Persistence | Saves to `.faiss` + metadata `.pkl` |

### 5.4 BM25 Index (`bm25_index.py`)

**Algorithm:** BM25Okapi (rank_bm25 library)

| Feature | Implementation |
|---------|----------------|
| Tokenization | Lowercase + alphanumeric split |
| Scoring | TF-IDF variant with length normalization |
| Persistence | Saves to `.pkl` with tokenized corpus |

### 5.5 Hybrid Search (`hybrid_search.py`)

**Fusion Method:** Reciprocal Rank Fusion (RRF)

```
RRF_score(chunk) = Σ 1/(k + rank_i)

where:
  k = 60 (smoothing constant)
  rank_i = position in each result list
```

**Weighting:**
- Semantic: 50%
- Keyword: 50%

### 5.6 Extractor (`extractor.py`)

**Model:** `gemini-2.5-flash-lite`

| Parameter | Value |
|-----------|-------|
| Temperature | 0.2 |
| Output | JSON (structured) |
| Retry | 3 attempts with exponential backoff |

---

## 6. Output Schema

```json
{
  "document_id": "gutenberg_6812",
  "document_title": "Abraham Lincoln: a History — Volume 01",
  "document_type": "Book",
  "event": "Election Night 1860",
  "author": "John Hay, John G. Nicolay",
  "claims": [
    "Lincoln received news of his victory in Springfield",
    "The election results came via telegraph"
  ],
  "temporal_details": {
    "date": "November 6, 1860",
    "time": "evening"
  },
  "tone": "Analytical"
}
```

---

## 7. Directory Structure

```
event_extraction_vector/
├── main.py              # Full pipeline orchestrator
├── run_books.py         # Gutenberg-only processing
├── config.py            # Configuration (paths, models, parameters)
├── chunker.py           # Document chunking
├── embeddings.py        # Vector embedding service
├── faiss_index.py       # FAISS semantic index
├── bm25_index.py        # BM25 keyword index
├── hybrid_search.py     # RRF fusion search
├── extractor.py         # LLM event extraction
├── prompt_extract.md    # Prompt for retrieved chunks
├── prompt_direct.md     # Prompt for direct extraction
├── ../.env              # API keys loaded from root (not committed)
│
└── output/
    ├── indices/
    │   ├── gutenberg_faiss.faiss
    │   ├── gutenberg_faiss_meta.pkl
    │   └── gutenberg_bm25.pkl
    │
    └── final/
        ├── {doc_id}_{event_slug}.json
        └── all_events.json
```

---

## 8. Why Hybrid Search?

| Search Type | Strengths | Weaknesses |
|-------------|-----------|------------|
| **Semantic (FAISS)** | Conceptual similarity, synonyms, paraphrases | May miss exact terms |
| **Keyword (BM25)** | Exact matching, names, dates | No semantic understanding |
| **Hybrid (RRF)** | Best of both worlds | Slightly more computation |

**Example:**
- Query: "Lincoln's election victory"
- Semantic finds: "triumph at the polls", "presidential win"
- BM25 finds: "election", "Lincoln", "victory"
- Hybrid: Ranks chunks appearing in both lists higher

---

## 9. Configuration

```python
# Chunking
CHUNK_SIZE_TOKENS = 1000
CHUNK_OVERLAP_TOKENS = 200

# Retrieval
FAISS_TOP_K = 15       # Candidates from semantic search
BM25_TOP_K = 15        # Candidates from keyword search
TOP_K_CHUNKS = 5       # Final chunks after fusion

# Models
GEMINI_MODEL = "gemini-2.5-flash-lite"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
```

---

## 10. Usage

```bash
# Full pipeline (LoC + Gutenberg)
python main.py

# Books only (uses cached indices if available)
python run_books.py
```

---

## 11. Dependencies

- `faiss-cpu` — Vector similarity search
- `rank-bm25` — BM25 keyword search
- `sentence-transformers` — Local embeddings
- `google-genai` — Gemini LLM client
- `numpy` — Numerical operations
- `pyyaml` — Configuration loading

---

## 12. Key Design Decisions

### 12.1 Local vs. API Embeddings

**Choice:** Local embeddings (sentence-transformers)

**Rationale:**
- ~2000 chunks per book × 5 books = 10,000+ embeddings
- API calls would be slow and costly
- Local processing: ~10 seconds vs. ~30 minutes (API)

### 12.2 Index Persistence

**Choice:** Save indices to disk after first run

**Rationale:**
- Embedding creation is the slowest step (~10 min)
- Subsequent runs load cached indices instantly
- Re-run extraction without re-embedding

### 12.3 Dual Processing Paths

**Choice:** Hybrid search for books, direct extraction for letters

**Rationale:**
- Books: Too long for context window → must retrieve
- Letters: Short enough for full context → better accuracy with complete document

---

*This module is part of the Memory Machines project for historical document analysis using RAG techniques.*
