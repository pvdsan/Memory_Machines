# Event Extraction Pipeline

## Overview

This module implements an LLM-powered event extraction pipeline for historical documents related to Abraham Lincoln. The system uses **Google Gemini 2.5 Flash Lite** to identify and extract structured information about five key historical events from two types of document sources.

---

## Target Events

The pipeline extracts information about the following five pivotal moments in Lincoln's life:

| # | Event Name | Historical Date |
|---|------------|-----------------|
| 1 | Election Night 1860 | November 6, 1860 |
| 2 | Fort Sumter Decision | April 12-13, 1861 |
| 3 | Gettysburg Address | November 19, 1863 |
| 4 | Second Inaugural Address | March 4, 1865 |
| 5 | Ford's Theatre Assassination | April 14, 1865 |


---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           EVENT EXTRACTION PIPELINE                              │
└─────────────────────────────────────────────────────────────────────────────────┘

                              ┌──────────────────┐
                              │   main.py        │
                              │  (Orchestrator)  │
                              └────────┬─────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    │                                     │
                    ▼                                     ▼
        ┌───────────────────┐                 ┌───────────────────┐
        │   LoC Dataset     │                 │ Gutenberg Dataset │
        │ (5 Letters/Speeches)│               │    (5 Books)      │
        └─────────┬─────────┘                 └─────────┬─────────┘
                  │                                     │
                  │                                     │
                  ▼                                     ▼
        ┌───────────────────┐                 ┌───────────────────┐
        │ DIRECT EXTRACTION │                 │ BATCH EXTRACTION  │
        │ (prompt_direct.md)│                 │  (Two-Stage)      │
        │                   │                 │                   │
        │ • 1 API call/doc  │                 │ Stage 1:          │
        │ • All 5 events    │                 │ • Split into 30k  │
        │   extracted at    │                 │   token batches   │
        │   once            │                 │ • 1k token overlap│
        │                   │                 │ • prompt_batch.md │
        └─────────┬─────────┘                 │ • Extract all 5   │
                  │                           │   events per batch│
                  │                           │                   │
                  │                           │ Stage 2:          │
                  │                           │ • prompt_final.md │
                  │                           │ • 1 call per event│
                  │                           │ • Consolidate to  │
                  │                           │   structured JSON │
                  │                           └─────────┬─────────┘
                  │                                     │
                  ▼                                     ▼
        ┌───────────────────────────────────────────────────────────────┐
        │                    gemini_service.py                          │
        │                   (GeminiExtractor)                           │
        │                                                               │
        │  • API client initialization                                  │
        │  • Rate limiting (15s delay between calls)                    │
        │  • Retry logic with exponential backoff                       │
        │  • JSON response parsing                                      │
        └───────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
        ┌───────────────────────────────────────────────────────────────┐
        │                   Google Gemini API                           │
        │                (gemini-2.5-flash-lite)                        │
        │                                                               │
        │  Model Parameters:                                            │
        │  • Temperature: 0.2 (deterministic extraction)                │
        │  • Response MIME: application/json                            │
        └───────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
        ┌───────────────────────────────────────────────────────────────┐
        │                      OUTPUT FILES                             │
        │                                                               │
        │  output/                                                      │
        │  ├── intermediate/          (Markdown files for book batches) │
        │  │   └── {doc_id}_{event_slug}.md                             │
        │  └── final/                 (Structured JSON results)         │
        │      └── {doc_id}_{event_slug}.json                           │
        └───────────────────────────────────────────────────────────────┘
```

---

## Processing Strategy

### Direct Extraction (Letters/Speeches)

For short documents that fit within the context window:

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────────┐
│  Document   │ ──► │ prompt_direct.md │ ──► │  Gemini API      │
│  (Full Text)│     │ (All 5 events)   │     │  (1 API call)    │
└─────────────┘     └─────────────────┘     └────────┬─────────┘
                                                     │
                                                     ▼
                                            ┌──────────────────┐
                                            │  JSON Output     │
                                            │  (5 events)      │
                                            └──────────────────┘
```

**API Calls**: 1 call per document × 5 documents = **5 API calls**

### Batch Extraction (Books)

For large documents that exceed context limits:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          STAGE 1: BATCH EXTRACTION                      │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────┐     ┌─────────────────────────────────────────────┐
│  Document   │ ──► │  batch_processor.py                         │
│  (Book)     │     │  • Split into 30k token batches             │
│  ~100k-500k │     │  • 1k token overlap for context continuity  │
│  tokens     │     │  • Smart splitting at sentence/paragraph    │
└─────────────┘     └──────────────────┬──────────────────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    ▼                                     ▼
              ┌───────────┐                         ┌───────────┐
              │  Batch 1  │  ...                    │  Batch N  │
              └─────┬─────┘                         └─────┬─────┘
                    │                                     │
                    ▼                                     ▼
              ┌───────────────┐                     ┌───────────────┐
              │prompt_batch.md│                     │prompt_batch.md│
              │ Extract all 5 │                     │ Extract all 5 │
              │ events        │                     │ events        │
              └───────┬───────┘                     └───────┬───────┘
                      │                                     │
                      ▼                                     ▼
              ┌───────────────────────────────────────────────────┐
              │     Intermediate Files (Markdown)                 │
              │     • {doc_id}_election_night_1860.md             │
              │     • {doc_id}_fort_sumter_decision.md            │
              │     • {doc_id}_gettysburg_address.md              │
              │     • {doc_id}_second_inaugural_address.md        │
              │     • {doc_id}_fords_theatre_assassination.md     │
              └───────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                          STAGE 2: CONSOLIDATION                         │
└─────────────────────────────────────────────────────────────────────────┘

For each of the 5 events:
              ┌───────────────────┐     ┌─────────────────┐
              │ Intermediate .md  │ ──► │ prompt_final.md │
              │ (All batch data   │     │ (Consolidate &  │
              │  for one event)   │     │  Structure)     │
              └───────────────────┘     └────────┬────────┘
                                                 │
                                                 ▼
                                        ┌─────────────────┐
                                        │  Gemini API     │
                                        │  (1 call/event) │
                                        └────────┬────────┘
                                                 │
                                                 ▼
                                        ┌─────────────────┐
                                        │  Final JSON     │
                                        │  (Structured)   │
                                        └─────────────────┘
```

---

## API Call Analysis

### Rate Limiting Configuration

| Parameter | Value | Description |
|-----------|-------|-------------|
| Request Delay | 15 seconds | Delay between consecutive API calls |
| Max Retries | 3 | Retry attempts on rate limit errors |
| Retry Delay | 60 seconds | Base wait time (exponential backoff) |
| Free Tier Limit | 5 RPM | Requests per minute |
| Token Limit | 250k TPM | Tokens per minute |
| Daily Limit | 100 RPD | Requests per day |

### API Call Breakdown

#### LoC Dataset (Direct Extraction)
```
Documents: 5
API Calls per Document: 1
─────────────────────────
Total LoC API Calls: 5
```

#### Gutenberg Dataset (Batch Extraction)

Assuming average ~4 batches per book (based on typical book length of ~120k-150k characters):

```
Documents: 5 books

Stage 1 (Batch Extraction):
  Average batches per book: ~4
  API calls: 5 books × 4 batches = ~20 calls

Stage 2 (Consolidation):
  Events per book: 5
  API calls: 5 books × 5 events = 25 calls
─────────────────────────────────────────
Total Gutenberg API Calls: ~45 calls
```

### Total Pipeline API Calls

| Stage | Source | Calculation | API Calls |
|-------|--------|-------------|-----------|
| Direct | LoC | 5 docs × 1 call | 5 |
| Stage 1 | Gutenberg | 5 books × ~4 batches | ~20 |
| Stage 2 | Gutenberg | 5 books × 5 events | 25 |
| **Total** | | | **~50 calls** |

### Time Estimate

With 15-second delays between calls:
```
Total time ≈ 50 calls × 15 seconds = 750 seconds ≈ 12.5 minutes
```

*Note: Actual time may vary based on API response times and rate limit handling.*

---

## Output Schema

### Event Extraction JSON Structure

```json
{
  "document_id": "string",
  "document_title": "string",
  "document_type": "Book | Letter | Speech",
  "event": "Event Name",
  "author": "Author Name",
  "claims": [
    "Factual claim 1 extracted from text",
    "Factual claim 2 extracted from text"
  ],
  "temporal_details": {
    "date": "Date when event occurred (or null)",
    "time": "Time when event occurred (or null)"
  },
  "tone": "Sympathetic | Critical | Neutral | Admiring | Analytical | Not mentioned"
}
```

---

## Sample Outputs

### Example 1: Gettysburg Address (Book Source - Analytical)

**Source**: *Abraham Lincoln* by Lord Charnwood (Gutenberg)

```json
{
  "document_id": "gutenberg_18379",
  "document_title": "Abraham Lincoln",
  "document_type": "Book",
  "event": "Gettysburg Address",
  "author": "Baron Godfrey Rathbone Benson Charnwood",
  "claims": [
    "The Gettysburg Address was delivered on November 19, 1863, at the dedication of a National Cemetery on the battlefield of Gettysburg.",
    "Edward Everett was the main orator at the ceremony where Lincoln's speech was given.",
    "President Lincoln was asked to say a few words at the close of the ceremony.",
    "The Gettysburg Address begins with the phrase 'Four score and seven years ago our fathers brought forth on this continent a new nation, conceived in liberty and dedicated to the proposition that all men are created equal.'",
    "The speech discusses the ongoing Civil War as a test of whether a nation conceived in liberty and dedicated to equality can endure.",
    "The speech emphasizes that the soldiers who fought and died have consecrated the ground far beyond any words spoken.",
    "The Gettysburg Address concludes with the famous phrase 'government of the people, by the people, for the people, shall not perish from the earth.'",
    "The Gettysburg Address is considered a chief outstanding example of Lincoln's peculiar oratorical power, noted for its singular perfection of form."
  ],
  "temporal_details": {
    "date": "November 19, 1863",
    "time": null
  },
  "tone": "Analytical"
}
```

### Example 2: Gettysburg Address (Primary Source - Lincoln's Own Words)

**Source**: Nicolay Copy of Gettysburg Address (Library of Congress)

```json
{
  "document_id": "loc_exhibits_trans-nicolay-copy",
  "document_title": "Four score and seven years ago...",
  "document_type": "Speech",
  "event": "Gettysburg Address",
  "author": "Abraham Lincoln",
  "claims": [
    "Four score and seven years ago our fathers brought forth, upon this continent, a new nation, conceived in liberty, and dedicated to the proposition that 'all men are created equal.'",
    "Now we are engaged in a great civil war, testing whether that nation, or any nation so conceived, and so dedicated, can long endure.",
    "We are met on a great battle field of that war.",
    "The brave men, living and dead, who struggled here, have hallowed it, far above our poor power to add or detract.",
    "The world will little note, nor long remember what we say here; while it can never forget what they did here.",
    "that we here highly resolve these dead shall not have died in vain",
    "that the nation shall have a new birth of freedom",
    "and that government of the people by the people for the people, shall not perish from the earth."
  ],
  "temporal_details": {
    "date": "November 19, 1863",
    "time": "Not mentioned"
  },
  "tone": "Admiring"
}
```

### Example 3: Ford's Theatre Assassination

**Source**: *The Life of Abraham Lincoln* by Henry Ketcham (Gutenberg)

```json
{
  "document_id": "gutenberg_6811",
  "document_title": "The Life of Abraham Lincoln",
  "document_type": "Book",
  "event": "Ford's Theatre Assassination",
  "author": "Henry Ketcham",
  "claims": [
    "The assassination of Abraham Lincoln at Ford's Theatre was an awful tragedy.",
    "The assassination occurred in a box at the theatre.",
    "The victim was described as the central figure of the great and good men of the century.",
    "The assassin used a revolver, thrust near the back of the victim's head.",
    "The victim was a kind man who had 'never willingly planted a thorn in any man's bosom' and could not bear to witness suffering.",
    "The nation mourned Lincoln's death.",
    "Lincoln was murdered because a fanatic perceived him as the South's most cruel enemy, despite being its best friend in his heart."
  ],
  "temporal_details": {
    "date": "April 14, 1865",
    "time": null
  },
  "tone": "Sympathetic"
}
```

---

## File Structure

```
event_extraction/
├── main.py                    # Pipeline orchestrator
├── config.py                  # Configuration and constants
├── gemini_service.py          # LLM API service layer
├── batch_processor.py         # Document batching utilities
├── keys.yaml                  # API key configuration (not in repo)
│
├── prompt_direct.md           # Prompt for letters/speeches (all events)
├── prompt_batch.md            # Prompt for book batches (excerpt extraction)
├── prompt_final.md            # Prompt for consolidation (final JSON)
│
└── output/
    ├── intermediate/          # Markdown files from batch processing
    │   └── {doc_id}_{event}.md
    └── final/                 # Structured JSON output
        ├── event_extractions.json           # Combined results
        ├── loc_event_extractions.json       # LoC results only
        ├── gutenberg_event_extractions.json # Gutenberg results only
        └── {doc_id}_{event}.json            # Individual event files
```

---

## Prompts

### 1. Direct Extraction Prompt (`prompt_direct.md`)

Used for Letters and Speeches (LoC dataset). Extracts all 5 events in a single API call.

**Input Variables**:
- `{document_title}`: Title of the document
- `{author}`: Author name
- `{events_list}`: List of 5 target events
- `{document_content}`: Full document text

**Output**: JSON array with all 5 events

### 2. Batch Extraction Prompt (`prompt_batch.md`)

Used for Stage 1 processing of Books. Extracts relevant excerpts for all events from each batch.

**Input Variables**:
- `{document_title}`: Book title
- `{author}`: Book author
- `{batch_num}`: Current batch number
- `{total_batches}`: Total number of batches
- `{events_list}`: List of 5 target events
- `{batch_content}`: Text content of current batch

**Output**: JSON object mapping event names to extracted excerpts

### 3. Final Consolidation Prompt (`prompt_final.md`)

Used for Stage 2 processing of Books. Consolidates batch excerpts into structured claims for a single event.

**Input Variables**:
- `{document_title}`: Book title
- `{author}`: Book author
- `{event_name}`: Specific event being consolidated
- `{source_content}`: Combined excerpts from all batches

**Output**: Structured JSON with claims, temporal details, and tone

---

## Model Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Model | `gemini-2.5-flash-lite` | Fast, cost-effective for extraction tasks |
| Temperature | 0.2 | Low temperature for deterministic, factual extraction |
| Response Format | `application/json` | Enforces structured output |

---

## Key Design Decisions

### 1. Two-Stage Processing for Books
Long documents are split into batches to avoid context window limitations. The two-stage approach ensures:
- **Completeness**: Every part of the document is analyzed
- **Quality**: Final consolidation removes duplicates and structures output

### 2. Overlapping Batches
1,000 token overlap between batches prevents losing context at batch boundaries.

### 3. Event-Centric Intermediate Files
One intermediate file per event (not per batch) allows:
- Better organization of extracted content
- Easier debugging and manual inspection
- Efficient consolidation in Stage 2

### 4. Immediate Saving
Results are saved immediately after extraction to prevent data loss on pipeline failures.

### 5. Separate Output Files
Each document-event pair gets its own JSON file for:
- Easy downstream processing
- Parallel analysis
- Selective re-extraction if needed

---

## Running the Pipeline

```bash
# Navigate to the event_extraction directory
cd event_extraction

# Run the full extraction pipeline
python main.py
```

### Expected Output

```
============================================================
EVENT EXTRACTION PIPELINE
============================================================

Target Events:
  - Election Night 1860
  - Fort Sumter Decision
  - Gettysburg Address
  - Second Inaugural Address
  - Ford's Theatre Assassination

Processing Strategy:
  - Books: Two-stage (batch extraction → final JSON)
  - Letters/Speeches: Direct (prompt_final.md)

Rate Limits (Free Tier):
  - 5 requests/minute (15s delay between calls)
  - 250,000 tokens/minute
  - 100 requests/day

[1/4] Initializing Gemini extractor...
[2/4] Loading datasets...
[3/4] Extracting events from LoC dataset (Lincoln's writings)...
[4/4] Extracting events from Gutenberg dataset (Other authors)...

✓ Extraction complete!
```

---

## Dependencies

```
google-genai>=0.3.0
pyyaml>=6.0
```

---

## References

- **Google Gemini API**: https://ai.google.dev/
- **Library of Congress Lincoln Papers**: https://www.loc.gov/collections/abraham-lincoln-papers/
- **Project Gutenberg**: https://www.gutenberg.org/

---

## Author

Event Extraction Pipeline for the Memory Machines Project
