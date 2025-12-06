"""
Main pipeline for event extraction from Lincoln historical documents.
Uses Gemini LLM to extract information about 5 key events.

Processing strategy:
- Books (Gutenberg): Batch processing with 15k token batches, 1k overlap
- Letters/Speeches (LoC): Direct full-context extraction
"""
import json
from pathlib import Path
from datetime import datetime

from config import PROCESSED_DIR, OUTPUT_DIR, FINAL_DIR, EVENTS
from gemini_service import GeminiExtractor
from batch_processor import INTERMEDIATE_DIR


def load_dataset(filepath: Path) -> list:
    """Load a JSON dataset file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_results(results: dict, filename: str):
    """Save extraction results to final JSON folder."""
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    output_path = FINAL_DIR / filename
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"Results saved to: {output_path}")
    return output_path


def run_extraction():
    """Run the full event extraction pipeline."""
    print("=" * 60)
    print("EVENT EXTRACTION PIPELINE")
    print("=" * 60)
    print(f"\nTarget Events:")
    for event in EVENTS:
        print(f"  - {event}")
    
    print(f"\nProcessing Strategy:")
    print(f"  - Books: Two-stage (batch extraction → final JSON)")
    print(f"    - Stage 1: prompt_batch.md (30k tokens, 1k overlap)")
    print(f"    - Stage 2: prompt_final.md (consolidate to JSON)")
    print(f"  - Letters/Speeches: Direct (prompt_final.md)")
    print(f"  - Intermediate files: {INTERMEDIATE_DIR}")
    print(f"  - Final output: {FINAL_DIR}")
    print(f"\nRate Limits (Free Tier):")
    print(f"  - 5 requests/minute (15s delay between calls)")
    print(f"  - 250,000 tokens/minute")
    print(f"  - 100 requests/day")
    
    # Initialize extractor
    print("\n[1/4] Initializing Gemini extractor...")
    extractor = GeminiExtractor()
    
    # Load datasets
    print("\n[2/4] Loading datasets...")
    
    loc_path = PROCESSED_DIR / "loc_lincoln_dataset.json"
    gutenberg_path = PROCESSED_DIR / "gutenberg_lincoln_dataset.json"
    
    loc_dataset = load_dataset(loc_path)
    gutenberg_dataset = load_dataset(gutenberg_path)
    
    print(f"  - LoC dataset: {len(loc_dataset)} documents (Letters/Speeches - direct extraction)")
    print(f"  - Gutenberg dataset: {len(gutenberg_dataset)} documents (Books - batch processing)")
    
    # Process LoC dataset (Lincoln's own words)
    print("\n[3/4] Extracting events from LoC dataset (Lincoln's writings)...")
    print("-" * 40)
    loc_extractions = extractor.extract_events_from_dataset(loc_dataset)
    
    # Process Gutenberg dataset (other authors)
    print("\n[4/4] Extracting events from Gutenberg dataset (Other authors)...")
    print("-" * 40)
    gutenberg_extractions = extractor.extract_events_from_dataset(gutenberg_dataset)
    
    # Compile results
    timestamp = datetime.now().isoformat()
    
    results = {
        "metadata": {
            "extraction_timestamp": timestamp,
            "target_events": EVENTS,
            "model_used": extractor.model,
            "loc_documents_processed": len(loc_dataset),
            "gutenberg_documents_processed": len(gutenberg_dataset)
        },
        "loc_extractions": loc_extractions,
        "gutenberg_extractions": gutenberg_extractions
    }
    
    # Save results
    print("\n" + "=" * 60)
    print("SAVING RESULTS")
    print("=" * 60)
    
    save_results(results, "event_extractions.json")
    
    # Also save separate files for each source
    save_results({"metadata": results["metadata"], "extractions": loc_extractions}, 
                 "loc_event_extractions.json")
    save_results({"metadata": results["metadata"], "extractions": gutenberg_extractions}, 
                 "gutenberg_event_extractions.json")
    
    # Print summary
    print("\n" + "=" * 60)
    print("EXTRACTION SUMMARY")
    print("=" * 60)
    
    print("\nLoC Extractions (Direct - Letters/Speeches):")
    for ext in loc_extractions:
        doc_title = ext.get('document_title', 'Unknown')[:50]
        if 'extractions' in ext:
            events_found = sum(1 for e in ext['extractions'] if e.get('claims'))
            print(f"  - {doc_title}... -> {events_found} events with content")
        else:
            print(f"  - {doc_title}... -> Error in extraction")
    
    print("\nGutenberg Extractions (Batched - Books):")
    for ext in gutenberg_extractions:
        doc_title = ext.get('document_title', 'Unknown')[:50]
        if 'extractions' in ext:
            events_found = sum(1 for e in ext['extractions'] if e.get('claims'))
            total_claims = sum(len(e.get('claims', [])) for e in ext['extractions'])
            print(f"  - {doc_title}... -> {events_found} events, {total_claims} claims")
        else:
            print(f"  - {doc_title}... -> Error in extraction")
    
    # Show intermediate files created
    if INTERMEDIATE_DIR.exists():
        intermediate_files = list(INTERMEDIATE_DIR.glob("*.md"))
        print(f"\nIntermediate files: {len(intermediate_files)} files in {INTERMEDIATE_DIR}")
    
    print(f"Final output saved to: {FINAL_DIR}")
    
    print("\n✓ Extraction complete!")
    return results


if __name__ == "__main__":
    run_extraction()

