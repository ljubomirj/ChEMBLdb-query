#!/usr/bin/env python3
"""
Promote rounds 18-22 cases to web_scrape_hq corpus and create v4.5 case split.
"""

import json
from pathlib import Path
from typing import List, Dict, Any

# Configuration
BASE_DIR = Path("/Users/ljubomir/ChEMBLdb-query")
CASES_FILE = BASE_DIR / "tests/cases/web_scrape_hq_cases.json"
NEW_CASES_FILE = BASE_DIR / "scripts/new_cases_rounds_18_22.json"

# Load existing cases
with open(CASES_FILE) as f:
    existing_cases = json.load(f)

# Get existing case IDs
existing_ids = {case["id"] for case in existing_cases}

# Load new cases
with open(NEW_CASES_FILE) as f:
    new_cases_list = json.load(f)

print(f"Existing cases: {len(existing_cases)}")
print(f"New cases to promote: {len(new_cases_list)}")

# Get case details from fixtures
def get_case_metadata(case_id: str, round_num: int) -> Dict[str, Any]:
    """Get case metadata from fixture directory."""
    fixture_dir = BASE_DIR / "tests/fixtures" / f"web_scrape{round_num}" / case_id

    # Read metadata.json
    metadata_file = fixture_dir / "metadata.json"
    if not metadata_file.exists():
        return None

    with open(metadata_file) as f:
        metadata = json.load(f)

    # Read uq.txt
    uq_file = fixture_dir / "uq.txt"
    uq_content = uq_file.read_text().strip() if uq_file.exists() else ""

    # Create case entry
    case_entry = {
        "id": case_id,
        "uq": uq_content,
        "source_url": metadata.get("source_url", ""),
        "source_sql_path": metadata.get("sql_path", ""),
        "sqlite_sql_path": metadata.get("sql_path", "").replace("source.sql", "sqlite.sql"),
        "result_csv_path": f"tests/fixtures/web_scrape{round_num}/{case_id}/result-last.csv",
        "log_path": f"tests/fixtures/web_scrape{round_num}/{case_id}/run-last.log",
        "db_path": "database/latest/chembl_36/chembl_36_sqlite/chembl_36.db",
        "size_class": "medium" if "target" in case_id or "assay" in case_id else "small",
        "sort_keys": [],
        "normalize": {
            "lowercase_columns": True,
            "strip_values": True,
            "lowercase_values": []
        }
    }

    return case_entry

# Promote new cases
promoted_cases = []
for case_info in new_cases_list:
    case_id = case_info["case_id"]
    round_num = case_info["round"]

    if case_id in existing_ids:
        print(f"  Skipping {case_id} (already exists)")
        continue

    case_metadata = get_case_metadata(case_id, round_num)
    if case_metadata:
        promoted_cases.append(case_metadata)
        print(f"  Promoted {case_id}")
    else:
        print(f"  WARNING: Could not load metadata for {case_id}")

# Add to existing cases
all_cases = existing_cases + promoted_cases

print(f"\nTotal cases after promotion: {len(all_cases)}")

# Save updated cases file
output_file = BASE_DIR / "tests/cases/web_scrape_hq_cases_v4.5.json"
with open(output_file, 'w') as f:
    json.dump(all_cases, f, indent=2)

print(f"Saved to {output_file}")

# Create v4.5 split with train/val/test
# Distribute new cases across splits maintaining ratio
train_split = [c for c in all_cases if c["id"] in {ec["id"] for ec in existing_cases[:60]}]
val_split = [c for c in all_cases if c["id"] in {ec["id"] for ec in existing_cases[60:75]}]
test_split = [c for c in all_cases if c["id"] in {ec["id"] for ec in existing_cases[75:]}]

# Add new cases (distribute roughly 70% train, 15% val, 15% test)
for i, case in enumerate(promoted_cases):
    case_ref = {"corpus": "web_scrape_hq", "id": case["id"]}
    if i % 100 < 70:  # 70% to train
        train_split.append(case_ref)
    elif i % 100 < 85:  # 15% to val
        val_split.append(case_ref)
    else:  # 15% to test
        test_split.append(case_ref)

split_config = {
    "version": "v4.5",
    "description": f"Expanded benchmark from 95 to {len(all_cases)} cases. Added {len(promoted_cases)} new cases from rounds 18-22 covering more human targets, assays, and documents.",
    "splits": {
        "train": train_split,
        "val": val_split,
        "test": test_split
    }
}

split_file = BASE_DIR / "experiments/case_splits_v4.5.json"
with open(split_file, 'w') as f:
    json.dump(split_config, f, indent=2)

print(f"\nCreated {split_file}")
print(f"  Train: {len(train_split)} cases")
print(f"  Val: {len(val_split)} cases")
print(f"  Test: {len(test_split)} cases")

print("\n✅ Promotion complete!")
