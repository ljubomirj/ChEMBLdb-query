#!/usr/bin/env python3
"""
Materialize ground truth for promoted rounds 10-13 cases.

This script executes the sqlite.sql for each promoted case against the
ChEMBL SQLite database and saves the results to ground-truth.csv.
"""

import sqlite3
import csv
from pathlib import Path
import json

# Base paths
BASE_DIR = Path(__file__).parent.parent
FIXTURES_DIR = BASE_DIR / "tests" / "fixtures"
CASES_DIR = BASE_DIR / "tests" / "cases"

# Database path
DB_PATH = BASE_DIR / "database" / "latest" / "chembl_36" / "chembl_36_sqlite" / "chembl_36.db"

# New cases to materialize
NEW_CASES = [
    # Round 10
    ("chembl_downloader_target_jak3_ic50_human_pchembl", 10),
    ("chembl_downloader_target_ache_ic50_human_pchembl", 10),
    ("chembl_downloader_target_ptgs2_ic50_human_pchembl", 10),
    ("chembl_downloader_target_mapk14_ic50_human_pchembl", 10),
    ("chembl_downloader_target_ntrk1_ic50_human_pchembl", 10),
    ("chembl_downloader_target_rock2_ic50_human_pchembl", 10),
    # Round 11
    ("chembl_downloader_target_pik3cd_ic50_human_pchembl", 11),
    ("chembl_downloader_target_tyk2_ic50_human_pchembl", 11),
    ("chembl_downloader_target_fgfr1_ic50_human_pchembl", 11),
    ("chembl_downloader_target_igf1r_ic50_human_pchembl", 11),
    ("chembl_downloader_target_irak4_ic50_human_pchembl", 11),
    ("chembl_downloader_target_mapk1_ic50_human_pchembl", 11),
    # Round 12
    ("chembl_downloader_assay_chembl1267250_exact", 12),
    ("chembl_downloader_assay_chembl1614455_exact", 12),
    ("chembl_downloader_assay_chembl1794523_exact", 12),
    ("chembl_downloader_assay_chembl1964022_exact", 12),
    ("chembl_downloader_assay_chembl3705858_exact", 12),
    ("chembl_downloader_assay_chembl3705960_exact", 12),
    ("chembl_downloader_assay_chembl5732041_exact", 12),
    # Round 13
    ("chembl_downloader_document_molecules_chembl1123558", 13),
    ("chembl_downloader_document_molecules_chembl1125325", 13),
    ("chembl_downloader_document_molecules_chembl1126796", 13),
    ("chembl_downloader_document_molecules_chembl1131436", 13),
    ("chembl_downloader_document_molecules_chembl1133512", 13),
    ("chembl_downloader_document_molecules_chembl1134488", 13),
    ("chembl_downloader_document_molecules_chembl1134522", 13),
]

def execute_sql_to_csv(sql_path: Path, csv_path: Path, db_path: Path):
    """Execute SQL and save results to CSV."""
    # Read SQL
    sql = sql_path.read_text()

    # Connect to database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Access columns by name

    try:
        cursor = conn.cursor()
        cursor.execute(sql)

        # Get column names
        if cursor.description:
            columns = [desc[0] for desc in cursor.description]
        else:
            print(f"  WARNING: No results from {sql_path}")
            return

        # Write to CSV
        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()

            for row in cursor:
                writer.writerow(dict(row))

        row_count = cursor.rowcount if cursor.rowcount >= 0 else sum(1 for _ in cursor)
        print(f"  Materialized {csv_path.name} ({row_count} rows)")

    except Exception as e:
        print(f"  ERROR: Failed to materialize {sql_path.name}: {e}")
        raise
    finally:
        conn.close()

def materialize_case(case_id: str, round_num: int):
    """Materialize ground truth for a single case."""
    source_dir = FIXTURES_DIR / f"web_scrape{round_num}" / case_id

    sql_path = source_dir / "sqlite.sql"
    ground_truth_path = source_dir / "ground-truth.csv"

    if not sql_path.exists():
        print(f"  SKIP: {sql_path} does not exist")
        return

    # Execute SQL and save to CSV
    execute_sql_to_csv(sql_path, ground_truth_path, DB_PATH)

def main():
    """Main materialization function."""
    print("=" * 80)
    print("Materializing ground truth for rounds 10-13 promoted cases")
    print("=" * 80)

    if not DB_PATH.exists():
        print(f"\nERROR: Database not found at {DB_PATH}")
        print("Please ensure the ChEMBL SQLite database is available.")
        return

    print(f"\nDatabase: {DB_PATH}")
    print(f"Cases to materialize: {len(NEW_CASES)}\n")

    success_count = 0
    for case_id, round_num in NEW_CASES:
        print(f"Materializing {case_id} (round {round_num})...")
        try:
            materialize_case(case_id, round_num)
            success_count += 1
        except Exception as e:
            print(f"  FAILED: {e}")

    print(f"\n" + "=" * 80)
    print(f"Materialization complete!")
    print(f"  - Success: {success_count}/{len(NEW_CASES)} cases")
    print(f"  - Failed: {len(NEW_CASES) - success_count} cases")
    print("=" * 80)

if __name__ == "__main__":
    main()
