#!/usr/bin/env python3
"""
Final promotion: create v4.5 with 200 cases total.
"""

import json
from pathlib import Path

BASE_DIR = Path("/Users/ljubomir/ChEMBLdb-query")

# Load v4.5 cases (150 cases)
v45_cases_file = BASE_DIR / "tests/cases/web_scrape_hq_cases_v4.5.json"
with open(v45_cases_file) as f:
    v45_cases = json.load(f)

# Load round 28 cases (50 cases)
round28_file = BASE_DIR / "scripts/new_cases_round_28.json"
with open(round28_file) as f:
    round28_cases = json.load(f)

print(f"v4.5 cases: {len(v45_cases)}")
print(f"Round 28 cases: {len(round28_cases)}")

# Get existing IDs
existing_ids = {case["id"] for case in v45_cases}

# Add round 28 cases
for case_info in round28_cases:
    case_id = case_info["case_id"]
    round_num = case_info["round"]

    if case_id in existing_ids:
        continue

    fixture_dir = BASE_DIR / "tests/fixtures" / f"web_scrape{round_num}" / case_id
    metadata_file = fixture_dir / "metadata.json"

    if not metadata_file.exists():
        print(f"  WARNING: No metadata for {case_id}")
        continue

    with open(metadata_file) as f:
        metadata = json.load(f)

    uq_file = fixture_dir / "uq.txt"
    uq_content = uq_file.read_text().strip()

    case_entry = {
        "id": case_id,
        "uq": uq_content,
        "source_url": metadata.get("source_url", ""),
        "source_sql_path": metadata.get("sql_path", ""),
        "sqlite_sql_path": metadata.get("sql_path", "").replace("source.sql", "sqlite.sql"),
        "result_csv_path": f"tests/fixtures/web_scrape{round_num}/{case_id}/result-last.csv",
        "log_path": f"tests/fixtures/web_scrape{round_num}/{case_id}/run-last.log",
        "db_path": "database/latest/chembl_36/chembl_36_sqlite/chembl_36.db",
        "size_class": "medium",
        "sort_keys": [],
        "normalize": {
            "lowercase_columns": True,
            "strip_values": True,
            "lowercase_values": []
        }
    }

    v45_cases.append(case_entry)
    print(f"  Added {case_id}")

print(f"\nTotal cases: {len(v45_cases)}")

# Save final cases file
final_cases_file = BASE_DIR / "tests/cases/web_scrape_hq_cases.json"
with open(final_cases_file, 'w') as f:
    json.dump(v45_cases, f, indent=2)

print(f"Saved to {final_cases_file}")

# Create v4.5 split
# Get original split distribution from v4.4_final
v44_file = BASE_DIR / "experiments/case_splits_v4.4_final.json"
with open(v44_file) as f:
    v44_split = json.load(f)

original_train_ids = {item["id"] for item in v44_split["splits"]["train"]}
original_val_ids = {item["id"] for item in v44_split["splits"]["val"]}
original_test_ids = {item["id"] for item in v44_split["splits"]["test"]}

# Build new splits
train_split = []
val_split = []
test_split = []

# Keep original distribution
for case in v45_cases:
    case_ref = {"corpus": "web_scrape_hq", "id": case["id"]}
    if case["id"] in original_train_ids:
        train_split.append(case_ref)
    elif case["id"] in original_val_ids:
        val_split.append(case_ref)
    elif case["id"] in original_test_ids:
        test_split.append(case_ref)
    else:
        # Distribute new cases: 70% train, 15% val, 15% test
        import random
        rand = random.random()
        if rand < 0.70:
            train_split.append(case_ref)
        elif rand < 0.85:
            val_split.append(case_ref)
        else:
            test_split.append(case_ref)

split_config = {
    "version": "v4.5",
    "description": f"Final expanded benchmark with {len(v45_cases)} cases (expanded from 95). Added {len(v45_cases) - 95} new cases covering diverse human targets, assays, and documents from ChEMBL 36.",
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
print(f"  Train: {len(train_split)} cases ({len(train_split)/len(v45_cases)*100:.1f}%)")
print(f"  Val: {len(val_split)} cases ({len(val_split)/len(v45_cases)*100:.1f}%)")
print(f"  Test: {len(test_split)} cases ({len(test_split)/len(v45_cases)*100:.1f}%)")

print("\n✅ v4.5 creation complete!")
print(f"   Expanded from 95 to {len(v45_cases)} cases ({len(v45_cases) - 95} new cases)")
