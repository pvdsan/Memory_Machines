"""
Lincoln Data Extraction Pipeline - Main Entry Point

Runs the complete data extraction and cleaning pipeline:
1. Fetch raw data from Project Gutenberg
2. Fetch raw data from Library of Congress
3. Clean and process all raw data
4. Combine into final.json

Usage:
    python main.py              # Run full pipeline
    python main.py --fetch      # Fetch only (no cleaning)
    python main.py --clean      # Clean only (skip fetching)
    python main.py --gutenberg  # Gutenberg only (fetch + clean)
    python main.py --loc        # LOC only (fetch + clean)
    python main.py --combine    # Combine datasets into final.json
"""

import argparse
import json

from gutenberg_service import extract_gutenberg_data
from loc_service import extract_loc_data
from cleaning_service import clean_gutenberg, clean_loc
from config import GUTENBERG_OUTPUT, LOC_OUTPUT, COMBINED_OUTPUT


def combine_datasets():
    """Combine Gutenberg and LOC datasets into final.json."""
    print("Combining datasets into final.json...")
    
    combined_data = []
    
    # Load Gutenberg data
    if GUTENBERG_OUTPUT.exists():
        with open(GUTENBERG_OUTPUT, 'r', encoding='utf-8') as f:
            gutenberg_data = json.load(f)
            combined_data.extend(gutenberg_data)
            print(f"  ✓ Loaded {len(gutenberg_data)} items from Gutenberg")
    else:
        print("  ⚠ Gutenberg dataset not found, skipping...")
    
    # Load LOC data
    if LOC_OUTPUT.exists():
        with open(LOC_OUTPUT, 'r', encoding='utf-8') as f:
            loc_data = json.load(f)
            combined_data.extend(loc_data)
            print(f"  ✓ Loaded {len(loc_data)} items from Library of Congress")
    else:
        print("  ⚠ LOC dataset not found, skipping...")
    
    # Add source field to distinguish data origin
    for item in combined_data:
        if item['id'].startswith('gutenberg_'):
            item['source'] = 'gutenberg'
        elif item['id'].startswith('loc_'):
            item['source'] = 'loc'
    
    # Save combined data
    COMBINED_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(COMBINED_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(combined_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Combined {len(combined_data)} total items into {COMBINED_OUTPUT}")
    return combined_data


def run_full_pipeline():
    """Run the complete pipeline: fetch all + clean all + combine."""
    print("=" * 70)
    print("LINCOLN DATA EXTRACTION PIPELINE")
    print("=" * 70)
    print()
    
    # Step 1: Fetch Gutenberg
    print("STEP 1/4: Fetching Project Gutenberg data...")
    extract_gutenberg_data()
    
    # Step 2: Fetch LOC
    print("\n" + "=" * 70)
    print("STEP 2/4: Fetching Library of Congress data...")
    extract_loc_data()
    
    # Step 3: Clean all
    print("\n" + "=" * 70)
    print("STEP 3/4: Cleaning all datasets...")
    clean_gutenberg()
    clean_loc()
    
    # Step 4: Combine datasets
    print("\n" + "=" * 70)
    print("STEP 4/4: Combining datasets...")
    combine_datasets()
    
    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE!")
    print("=" * 70)
    print("\nOutput files:")
    print("  → data/processed/gutenberg_lincoln_dataset.json")
    print("  → data/processed/loc_lincoln_dataset.json")
    print("  → data/processed/final.json")


def run_fetch_only():
    """Fetch all data without cleaning."""
    print("=" * 70)
    print("FETCHING DATA (no cleaning)")
    print("=" * 70)
    
    extract_gutenberg_data()
    print()
    extract_loc_data()
    
    print("\n✓ Fetch complete. Run 'python main.py --clean' to clean.")


def run_clean_only():
    """Clean existing raw data and combine."""
    print("=" * 70)
    print("CLEANING DATA")
    print("=" * 70)
    
    clean_gutenberg()
    clean_loc()
    
    print("\n" + "=" * 70)
    combine_datasets()


def run_combine_only():
    """Combine existing processed datasets into final.json."""
    print("=" * 70)
    print("COMBINING DATASETS")
    print("=" * 70)
    
    combine_datasets()


def run_gutenberg_only():
    """Fetch and clean Gutenberg data only."""
    print("=" * 70)
    print("GUTENBERG PIPELINE")
    print("=" * 70)
    
    extract_gutenberg_data()
    clean_gutenberg()


def run_loc_only():
    """Fetch and clean LOC data only."""
    print("=" * 70)
    print("LIBRARY OF CONGRESS PIPELINE")
    print("=" * 70)
    
    extract_loc_data()
    clean_loc()


def main():
    parser = argparse.ArgumentParser(
        description="Lincoln Data Extraction Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py              # Full pipeline (fetch + clean + combine)
  python main.py --fetch      # Fetch raw data only
  python main.py --clean      # Clean existing raw data + combine
  python main.py --combine    # Combine datasets into final.json
  python main.py --gutenberg  # Gutenberg only
  python main.py --loc        # Library of Congress only
        """
    )
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--fetch', action='store_true', help='Fetch only (no cleaning)')
    group.add_argument('--clean', action='store_true', help='Clean only (skip fetching)')
    group.add_argument('--combine', action='store_true', help='Combine datasets into final.json')
    group.add_argument('--gutenberg', action='store_true', help='Gutenberg only (fetch + clean)')
    group.add_argument('--loc', action='store_true', help='LOC only (fetch + clean)')
    
    args = parser.parse_args()
    
    if args.fetch:
        run_fetch_only()
    elif args.clean:
        run_clean_only()
    elif args.combine:
        run_combine_only()
    elif args.gutenberg:
        run_gutenberg_only()
    elif args.loc:
        run_loc_only()
    else:
        run_full_pipeline()


if __name__ == "__main__":
    main()

