# Memory Machines: Historical Document Analysis Pipeline

A multi-stage NLP pipeline for extracting and evaluating historical events from Abraham Lincoln documents using LLMs and hybrid search techniques.

---

## 📍 Quick Navigation for Evaluators

| Looking for... | Go to |
|----------------|-------|
| **Scraped Data** (raw & processed documents) | [`data_extraction/data/`](data_extraction/data/) |
| **Final Combined Dataset** | [`data_extraction/data/processed/final.json`](data_extraction/data/processed/final.json) |
| **Extracted Events** (structured JSON) | [`event_extraction/output/final/`](event_extraction/output/final/) |
| **All Events Combined** | [`event_extraction/output/final/event_extractions.json`](event_extraction/output/final/event_extractions.json) |
| **Evaluation Notebooks** | [`llm_as_judge/`](llm_as_judge/) |
| **Evaluation Results & Figures** | [`llm_as_judge/output/`](llm_as_judge/output/) |

---

## 🎯 Project Overview

This project implements an end-to-end pipeline for historical document analysis:

1. **Data Collection** — Automated extraction from Project Gutenberg and Library of Congress
2. **Event Extraction** — LLM-powered identification of key historical events
3. **Evaluation** — LLM-as-Judge assessment of extraction quality

### Target Events

| # | Event | Date |
|---|-------|------|
| 1 | Election Night 1860 | November 6, 1860 |
| 2 | Fort Sumter Decision | April 12-13, 1861 |
| 3 | Gettysburg Address | November 19, 1863 |
| 4 | Second Inaugural Address | March 4, 1865 |
| 5 | Ford's Theatre Assassination | April 14, 1865 |

---

## 📁 Project Structure

```
Memory_Machines/
├── data_extraction/          # Stage 1: Data Collection
│   ├── main.py               # Pipeline orchestrator
│   ├── gutenberg_service.py  # Project Gutenberg API client
│   ├── loc_service.py        # Library of Congress API client
│   ├── cleaning_service.py   # Text normalization
│   └── data/                 # Raw and processed datasets
│
├── event_extraction/         # Stage 2: LLM Event Extraction
│   ├── main.py               # Batch extraction pipeline
│   ├── gemini_service.py     # Gemini API client
│   ├── batch_processor.py    # Document chunking
│   └── output/               # Extracted events (JSON)
│
├── event_extraction_vector/  # [OPTIONAL] Alternative RAG-based Extraction
│   ├── main.py               # Full pipeline
│   ├── chunker.py            # Document chunking
│   ├── embeddings.py         # Vector embedding service
│   ├── faiss_index.py        # Semantic search index
│   ├── bm25_index.py         # Keyword search index
│   ├── hybrid_search.py      # Reciprocal Rank Fusion
│   └── extractor.py          # LLM extraction layer
│
├── llm_as_judge/             # Stage 3: Evaluation
│   ├── 3Ba_Prompt_Robustness.ipynb   # Prompt strategy comparison
│   ├── 3Bb_Self_Consistency.ipynb    # Model consistency analysis
│   ├── 3Bc_Inter_Rater_Agreement.ipynb
│   └── output/               # Evaluation results and figures
│
└── README.md                 # This file
```

---

## 🔧 Installation

### Prerequisites

- Python 3.11+
- Google Gemini API key

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/Memory_Machines.git
cd Memory_Machines

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### API Keys

Create a `.env` file in the project root:

```bash
# .env
GEMINI_API_KEY=your-api-key-here
```

---

## 🚀 Usage

### Stage 1: Data Extraction

```bash
cd data_extraction

# Full pipeline (fetch + clean + combine)
python main.py

# Individual stages
python main.py --fetch       # Download only
python main.py --clean       # Clean existing data
python main.py --combine     # Merge datasets
```

### Stage 2: Event Extraction

```bash
cd event_extraction
python main.py
```

### Stage 2 (Alternative): Hybrid Search RAG Extraction

> **Note:** This is an optional alternative approach using RAG. Use **either** `event_extraction` or `event_extraction_vector`, not both.

```bash
cd event_extraction_vector

# Full pipeline
python main.py

# Books only (uses cached indices)
python run_books.py
```

### Stage 3: Evaluation

Open the Jupyter notebooks in `llm_as_judge/`:

1. `3Ba_Prompt_Robustness.ipynb` — Compare Zero-Shot, CoT, and Few-Shot strategies
2. `3Bb_Self_Consistency.ipynb` — Analyze model consistency across runs
3. `3Bc_Inter_Rater_Agreement.ipynb` — Compare LLM vs human judgments

---

## 📊 Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MEMORY MACHINES PIPELINE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐     │
│  │  DATA EXTRACTION │     │ EVENT EXTRACTION │     │   LLM-AS-JUDGE   │     │
│  │                  │     │                  │     │                  │     │
│  │ • Gutenberg API  │ ──► │ • LLM Extraction │ ──► │ • Prompt Studies │     │
│  │ • LOC API        │     │   (or RAG alt.)  │     │ • Consistency    │     │
│  │ • Text Cleaning  │     │                  │     │ • Agreement      │     │
│  └──────────────────┘     └──────────────────┘     └──────────────────┘     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📚 Data Sources

| Source | Type | Documents |
|--------|------|-----------|
| **Project Gutenberg** | Books/Biographies | 5 works about Lincoln |
| **Library of Congress** | Primary Sources | Letters, speeches, manuscripts |

---

## 🤖 Models Used

| Component | Model | Purpose |
|-----------|-------|---------|
| Event Extraction | Gemini 2.5 Flash Lite | Structured claim extraction |
| LLM Judge | Gemini 2.5 Flash Lite | Consistency evaluation |
| Embeddings (optional) | all-MiniLM-L6-v2 | Local semantic embeddings (RAG only) |

---

## 📈 Key Features

- **Two-Stage Extraction**: Batch processing for long documents, direct extraction for short ones
- **Multi-Prompt Evaluation**: Zero-Shot, Chain-of-Thought, and Few-Shot comparison
- **Reproducible Pipeline**: Saved intermediate outputs for debugging
- **Optional RAG Alternative**: Hybrid search (FAISS + BM25) available as alternative extraction method

---

## 📄 License

This project is for research and educational purposes.

---

## 📖 References

- [Google Gemini API](https://ai.google.dev/)
- [Library of Congress Lincoln Papers](https://www.loc.gov/collections/abraham-lincoln-papers/)
- [Project Gutenberg](https://www.gutenberg.org/)

---

*Part of the Memory Machines project for historical document analysis using modern NLP techniques.*

