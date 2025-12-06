"""Generate statistics report for Lincoln datasets."""
import json
import os
from pathlib import Path

# Load both datasets
g = json.load(open('data/processed/gutenberg_lincoln_dataset.json', encoding='utf-8'))
l = json.load(open('data/processed/loc_lincoln_dataset.json', encoding='utf-8'))

print('='*70)
print('GUTENBERG DATASET STATISTICS')
print('='*70)
print(f'Total entries: {len(g)}')
total_chars = sum(len(e['content']) for e in g)
print(f'Total content characters: {total_chars:,}')
print(f'Average characters per book: {total_chars//len(g):,}')
print()
for e in g:
    print(f"  {e['id']}: {len(e['content']):,} chars")
    print(f"    Title: {e['title'][:60]}...")
    print(f"    Author: {e['from']}")
    print()

print('='*70)
print('LOC DATASET STATISTICS')
print('='*70)
print(f'Total entries: {len(l)}')
total_chars = sum(len(e['content']) for e in l)
print(f'Total content characters: {total_chars:,}')
print()
for e in l:
    print(f"  {e['id']}: {len(e['content']):,} chars")
    print(f"    Title: {(e['title'] or '')[:60]}...")
    print(f"    Type: {e['document_type']}")
    print(f"    Date: {e['date']}")
    print(f"    From: {e['from']} -> To: {e['to']}")
    print(f"    Place: {e['place']}")
    print()

# File sizes
print('='*70)
print('RAW FILE SIZES')
print('='*70)
for source in ['gutenberg', 'loc']:
    raw_dir = Path(f'data/raw/{source}')
    if raw_dir.exists():
        print(f'\n{source.upper()}:')
        for f in sorted(raw_dir.iterdir()):
            if f.is_file():
                size = f.stat().st_size
                print(f"  {f.name}: {size:,} bytes")

