# Data Extraction Pipeline for Abraham Lincoln Historical Documents

## 1. Overview

This module implements an automated data extraction and normalization pipeline for collecting Abraham Lincoln historical documents from two authoritative digital archives:

1. **Project Gutenberg** — Public domain books and biographies about Lincoln
2. **Library of Congress (LOC)** — Primary source documents (letters, speeches, manuscripts)

The pipeline follows a three-stage ETL (Extract, Transform, Load) architecture to produce a unified, clean dataset suitable for downstream NLP and historical analysis tasks.

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DATA EXTRACTION PIPELINE                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────┐         ┌─────────────────┐                        │
│  │ Project         │         │ Library of      │                        │
│  │ Gutenberg API   │         │ Congress API    │                        │
│  │ (Gutendex)      │         │ (JSON + HTML)   │                        │
│  └────────┬────────┘         └────────┬────────┘                        │
│           │                           │                                 │
│           ▼                           ▼                                 │
│  ┌─────────────────┐         ┌─────────────────┐                        │
│  │ gutenberg_      │         │ loc_            │     EXTRACTION         │
│  │ service.py      │         │ service.py      │     LAYER              │
│  └────────┬────────┘         └────────┬────────┘                        │
│           │                           │                                 │
│           ▼                           ▼                                 │
│  ┌─────────────────────────────────────────────┐                        │
│  │              data/raw/                       │                       │
│  │  ├── gutenberg/  (*.txt, _metadata.json)    │     RAW STORAGE        │
│  │  └── loc/        (*.txt, *.pdf, *.jpg)      │                        │
│  └─────────────────────┬───────────────────────┘                        │
│                        │                                                │
│                        ▼                                                │
│  ┌─────────────────────────────────────────────┐                        │
│  │           cleaning_service.py               │     TRANSFORMATION     │
│  │  • Encoding normalization (mojibake fix)    │     LAYER              │
│  │  • Metadata extraction (regex parsing)      │                        │
│  │  • Name normalization (Last, First → First Last)                     │
│  │  • Document type inference                  │                        │
│  └─────────────────────┬───────────────────────┘                        │
│                        │                                                │
│                        ▼                                                │
│  ┌─────────────────────────────────────────────┐                        │
│  │              data/processed/                 │                       │
│  │  ├── gutenberg_lincoln_dataset.json         │     PROCESSED          │
│  │  ├── loc_lincoln_dataset.json               │     OUTPUT             │
│  │  └── final.json (combined)                  │                        │
│  └─────────────────────────────────────────────┘                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Sources

### 3.1 Project Gutenberg

| Component | Description |
|-----------|-------------|
| **API** | Gutendex REST API (`gutendex.com/books`) |
| **Format** | Plain text (UTF-8) |
| **Content** | Full-length books and biographies about Abraham Lincoln |
| **Documents** | 5 books from various authors |

**Selected Works:**
- *Abraham Lincoln: a History — Volume 01* (ID: 6812)
- *The Life of Abraham Lincoln* (ID: 6811)
- *Abraham Lincoln, Volume II* (ID: 12801)
- *The Every-day Life of Abraham Lincoln* (ID: 14004)
- *Abraham Lincoln* by Lord Charnwood (ID: 18379)

### 3.2 Library of Congress

| Component | Description |
|-----------|-------------|
| **API** | LOC JSON API + HTML scraping for exhibits |
| **Formats** | PDF (manuscripts), TXT (transcriptions), JPG (images) |
| **Content** | Primary source documents: letters, speeches, addresses |
| **Documents** | 5 historical documents |

**Selected Documents:**
- Letter about Election Night 1860 (Lincoln to Truman Smith)
- Fort Sumter Decision report
- Gettysburg Address (Nicolay Copy)
- Second Inaugural Address
- Correspondence (March 1865)

---

## 4. Pipeline Stages

### 4.1 Extraction Layer

#### 4.1.1 Gutenberg Extraction

**Technique:** REST API consumption with format negotiation

1. **Metadata Retrieval**: Query Gutendex API with book IDs to fetch metadata (title, authors, available formats)
2. **Format Selection**: Prioritize UTF-8 plain text format; fallback to any `text/plain` format
3. **Content Download**: Retrieve full text content via direct URL
4. **Metadata Persistence**: Store book metadata separately for cleaning phase reference

#### 4.1.2 LOC Extraction

**Technique:** Hybrid API/scraping with automatic URL type detection

The LOC service handles three distinct URL patterns:

| URL Type | Pattern | Extraction Method |
|----------|---------|-------------------|
| `item` | `/item/{id}/` | JSON API |
| `resource` | `/resource/{id}/` | JSON API |
| `exhibits` | `/exhibits/...` | HTML scraping (BeautifulSoup) |

**Automatic Detection Algorithm:**
```
URL → Pattern Matching → Appropriate Handler
```

**Multi-format Download:**
- PDF manuscripts (original scans)
- Transcription files (when available via `fulltext_file` field)
- Image files (JPEG/TIFF fallback when PDF unavailable)

**Rate Limiting:** 3.5-second delay between requests (LOC limit: 20 req/min)

---

### 4.2 Transformation Layer

#### 4.2.1 Encoding Normalization

**Problem:** Historical texts often contain mojibake (encoding corruption) from multiple format conversions.

**Technique:** Character-level pattern replacement using a curated substitution table.

| Corrupted Pattern | Correct Character |
|-------------------|-------------------|
| `â€œ` | `"` (left double quote) |
| `â€™` | `'` (apostrophe) |
| `â€"` | `—` (em-dash) |
| `Ã©` | `é` |

**Additional Normalization:**
- Curly quotes → straight quotes
- Em/en dashes → standard hyphens
- Newlines/carriage returns → spaces
- Multiple spaces → single space

#### 4.2.2 Metadata Extraction from LOC Documents

**Technique:** Regex-based header parsing with pattern fallbacks

The cleaning service extracts structured metadata from unstructured text headers:

| Field | Detection Pattern |
|-------|-------------------|
| **Title** | `General Correspondence. YYYY-YYYY: {title}` |
| **Date** | `Day, Month DD, YYYY` or `[Month DD, YYYY]` |
| **From/To** | `{Person} to {Person}` sender-recipient pattern |
| **Place** | `City State Month` with state abbreviation matching |
| **Document Type** | Keyword inference (address/speech/letter/report) |

**Fallback Strategy:** When pattern matching fails, API metadata is used as secondary source.

#### 4.2.3 Name Normalization

**Problem:** Names appear in inconsistent formats across sources.

**Technique:** Algorithmic transformation with suffix/prefix handling

| Input Format | Output Format |
|--------------|---------------|
| `Lincoln, Abraham` | `Abraham Lincoln` |
| `Morse, John T., Jr.` | `John T. Morse Jr.` |
| `Charnwood, Godfrey Rathbone Benson, Baron` | `Baron Godfrey Rathbone Benson Charnwood` |
| `Hay, John, Nicolay, John G.` | `John Hay, John G. Nicolay` |

**Handled Elements:**
- Date removal (`1809-1865`)
- Parenthetical expansions (`(Francis Fisher)`)
- Titles/honorifics (`Baron`, `Sir`, `Lord`)
- Suffixes (`Jr.`, `Sr.`, `III`)

#### 4.2.4 Document Type Inference

**Technique:** Rule-based classification from content and metadata signals

```
IF title contains ["address", "speech", "inaugural"] → Speech
ELSE IF content starts with ["four score", "fellow countrymen"] → Speech  
ELSE IF has from AND to fields → Letter
ELSE IF title contains "report" → Report
ELSE → Document
```

---

### 4.3 Integration Layer

**Technique:** Schema-based dataset merging with source tagging

Both processed datasets are merged into `final.json` with source provenance:

```json
{
  "id": "gutenberg_6812",
  "source": "gutenberg",
  ...
}
```

---

## 5. Output Schema

All normalized documents conform to this unified schema:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier (`{source}_{original_id}`) |
| `title` | string | Human-readable document title |
| `reference` | string | Path to raw source file |
| `document_type` | enum | `Book`, `Letter`, `Speech`, `Document`, `Report` |
| `date` | string | Date as extracted from source |
| `place` | string | Geographic location (if identified) |
| `from` | string | Author/sender (normalized name) |
| `to` | string | Recipient (if applicable) |
| `content` | string | Full cleaned text content |
| `source` | string | Origin dataset (`gutenberg` or `loc`) |

---

## 6. Directory Structure

```
data_extraction/
├── main.py                 # Pipeline orchestrator (CLI interface)
├── config.py               # Centralized configuration (paths, URLs, IDs)
├── gutenberg_service.py    # Project Gutenberg extraction
├── loc_service.py          # Library of Congress extraction
├── cleaning_service.py     # Transformation and normalization
├── utils.py                # Shared utilities (encoding fixes)
├── generate_report.py      # Dataset statistics generator
│
└── data/
    ├── raw/
    │   ├── gutenberg/
    │   │   ├── _metadata.json
    │   │   └── {id}_{title}.txt
    │   └── loc/
    │       ├── _metadata.json
    │       ├── {id}_{title}.txt
    │       ├── {id}_{title}.pdf
    │       └── {id}_{title}.jpg
    │
    └── processed/
        ├── gutenberg_lincoln_dataset.json
        ├── loc_lincoln_dataset.json
        └── final.json
```

---

## 7. Key Design Decisions

### 7.1 Separation of Extraction and Cleaning

**Rationale:** Raw files are preserved separately to allow:
- Re-cleaning with different parameters without re-downloading
- Audit trail for data provenance
- Manual inspection of source quality

### 7.2 Metadata-Driven Processing

**Rationale:** Each raw directory contains `_metadata.json` which:
- Links downloaded files to their source URLs
- Preserves API-provided metadata
- Enables cleaning service to operate independently

### 7.3 Dual Metadata Strategy (LOC)

**Rationale:** LOC documents use both:
1. **API metadata** — Structured fields from JSON response
2. **Parsed headers** — Regex extraction from document text

This hybrid approach maximizes metadata coverage when API fields are incomplete.

### 7.4 Graceful Degradation

**Rationale:** The pipeline handles missing resources gracefully:
- No PDF available → download image instead
- No transcription → skip text file, note in metadata
- API error → log warning, continue with remaining documents

---

## 8. Challenges and Solutions

| Challenge | Solution |
|-----------|----------|
| **Rate limiting** | Configurable delay (3.5s) between LOC requests |
| **Inconsistent URL formats** | Automatic URL type detection via pattern matching |
| **Encoding corruption (mojibake)** | Comprehensive character substitution table |
| **Unstructured metadata** | Multi-pattern regex parsing with fallbacks |
| **Name format variations** | Algorithmic normalization handling prefixes/suffixes |
| **Missing transcriptions** | PDF/image download as alternative artifact |

---

## 9. Usage

```bash
# Full pipeline (extract + clean + combine)
python main.py

# Individual stages
python main.py --fetch       # Download only
python main.py --clean       # Clean only (requires prior fetch)
python main.py --combine     # Merge datasets only

# Source-specific
python main.py --gutenberg   # Gutenberg only
python main.py --loc         # LOC only

# Generate statistics report
python generate_report.py
```

---

## 10. Dependencies

- `requests` — HTTP client for API consumption
- `beautifulsoup4` — HTML parsing for exhibits pages
- `pathlib` — Cross-platform path handling
- `json` — Data serialization
- `re` — Regular expression pattern matching

---

## 11. Limitations and Future Work

1. **OCR Quality**: LOC transcriptions depend on LOC's OCR accuracy
2. **Incomplete Metadata**: Some documents lack date/place information
3. **Single Language**: Pipeline assumes English text
4. **Static Configuration**: Book/document IDs are hardcoded in config

**Potential Enhancements:**
- Dynamic search-based document discovery
- Multi-language encoding support
- OCR validation and correction
- Incremental updates (detect new documents)

---

*This pipeline was developed as part of the Memory Machines project for historical document analysis.*
