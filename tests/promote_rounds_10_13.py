#!/usr/bin/env python3
"""
Promote 26 cases from rounds 10-13 to web_scrape_hq.

Round 10: 6 target cases (JAK3, ACHE, PTGS2, MAPK14, NTRK1, ROCK2)
Round 11: 6 target cases (PIK3CD, TYK2, FGFR1, IGF1R, IRAK4, MAPK1)
Round 12: 7 assay cases (CHEMBL1267250, CHEMBL1614455, etc.)
Round 13: 7 document cases (CHEMBL1123558, CHEMBL1125325, etc.)
"""

import json
import shutil
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
FIXTURES_DIR = BASE_DIR / "tests" / "fixtures"
CASES_DIR = BASE_DIR / "tests" / "cases"

# All 26 cases to promote with their metadata
CASES_TO_PROMOTE = [
    # Round 10 - Target cases
    {
        "round": 10,
        "id": "chembl_downloader_target_jak3_ic50_human_pchembl",
        "target_chembl": "CHEMBL2148",
        "target_name": "JAK3 tyrosine kinase"
    },
    {
        "round": 10,
        "id": "chembl_downloader_target_ache_ic50_human_pchembl",
        "target_chembl": "CHEMBL220",
        "target_name": "acetylcholinesterase"
    },
    {
        "round": 10,
        "id": "chembl_downloader_target_ptgs2_ic50_human_pchembl",
        "target_chembl": "CHEMBL230",
        "target_name": "PTGS2"
    },
    {
        "round": 10,
        "id": "chembl_downloader_target_mapk14_ic50_human_pchembl",
        "target_chembl": "CHEMBL260",
        "target_name": "MAPK14"
    },
    {
        "round": 10,
        "id": "chembl_downloader_target_ntrk1_ic50_human_pchembl",
        "target_chembl": "CHEMBL2815",
        "target_name": "NTRK1"
    },
    {
        "round": 10,
        "id": "chembl_downloader_target_rock2_ic50_human_pchembl",
        "target_chembl": "CHEMBL2973",
        "target_name": "ROCK2"
    },
    # Round 11 - Target cases
    {
        "round": 11,
        "id": "chembl_downloader_target_pik3cd_ic50_human_pchembl",
        "target_chembl": "CHEMBL3130",
        "target_name": "PIK3CD"
    },
    {
        "round": 11,
        "id": "chembl_downloader_target_tyk2_ic50_human_pchembl",
        "target_chembl": "CHEMBL3553",
        "target_name": "TYK2"
    },
    {
        "round": 11,
        "id": "chembl_downloader_target_fgfr1_ic50_human_pchembl",
        "target_chembl": "CHEMBL3650",
        "target_name": "FGFR1"
    },
    {
        "round": 11,
        "id": "chembl_downloader_target_igf1r_ic50_human_pchembl",
        "target_chembl": "CHEMBL1862",
        "target_name": "IGF1R"
    },
    {
        "round": 11,
        "id": "chembl_downloader_target_irak4_ic50_human_pchembl",
        "target_chembl": "CHEMBL3778",
        "target_name": "IRAK4"
    },
    {
        "round": 11,
        "id": "chembl_downloader_target_mapk1_ic50_human_pchembl",
        "target_chembl": "CHEMBL4040",
        "target_name": "MAPK1"
    },
    # Round 12 - Assay cases
    {
        "round": 12,
        "id": "chembl_downloader_assay_chembl1267250_exact",
        "assay_chembl": "CHEMBL1267250"
    },
    {
        "round": 12,
        "id": "chembl_downloader_assay_chembl1614455_exact",
        "assay_chembl": "CHEMBL1614455"
    },
    {
        "round": 12,
        "id": "chembl_downloader_assay_chembl1794523_exact",
        "assay_chembl": "CHEMBL1794523"
    },
    {
        "round": 12,
        "id": "chembl_downloader_assay_chembl1964022_exact",
        "assay_chembl": "CHEMBL1964022"
    },
    {
        "round": 12,
        "id": "chembl_downloader_assay_chembl3705858_exact",
        "assay_chembl": "CHEMBL3705858"
    },
    {
        "round": 12,
        "id": "chembl_downloader_assay_chembl3705960_exact",
        "assay_chembl": "CHEMBL3705960"
    },
    {
        "round": 12,
        "id": "chembl_downloader_assay_chembl5732041_exact",
        "assay_chembl": "CHEMBL5732041"
    },
    # Round 13 - Document cases
    {
        "round": 13,
        "id": "chembl_downloader_document_molecules_chembl1123558",
        "doc_chembl": "CHEMBL1123558"
    },
    {
        "round": 13,
        "id": "chembl_downloader_document_molecules_chembl1125325",
        "doc_chembl": "CHEMBL1125325"
    },
    {
        "round": 13,
        "id": "chembl_downloader_document_molecules_chembl1126796",
        "doc_chembl": "CHEMBL1126796"
    },
    {
        "round": 13,
        "id": "chembl_downloader_document_molecules_chembl1131436",
        "doc_chembl": "CHEMBL1131436"
    },
    {
        "round": 13,
        "id": "chembl_downloader_document_molecules_chembl1133512",
        "doc_chembl": "CHEMBL1133512"
    },
    {
        "round": 13,
        "id": "chembl_downloader_document_molecules_chembl1134488",
        "doc_chembl": "CHEMBL1134488"
    },
    {
        "round": 13,
        "id": "chembl_downloader_document_molecules_chembl1134522",
        "doc_chembl": "CHEMBL1134522"
    },
]

def get_case_uq(case_id: str, round_num: int) -> str:
    """Read the UQ from the source fixture."""
    uq_path = FIXTURES_DIR / f"web_scrape{round_num}" / case_id / "uq.txt"
    return uq_path.read_text().strip()

def create_web_scrape_hq_entry(case_info: dict) -> dict:
    """Create a web_scrape_hq case entry."""
    case_id = case_info["id"]
    round_num = case_info["round"]

    # Read UQ from source
    uq = get_case_uq(case_id, round_num)

    # Determine base paths
    source_dir = FIXTURES_DIR / f"web_scrape{round_num}" / case_id

    # Base entry structure
    entry = {
        "id": case_id,
        "uq": uq,
        "source_url": "https://github.com/cthoyt/chembl-downloader/blob/main/src/chembl_downloader/queries.py",
        "source_sql_path": str(source_dir / "source.sql"),
        "sqlite_sql_path": str(source_dir / "sqlite.sql"),
        "result_csv_path": str(source_dir / "result-last.csv"),
        "log_path": str(source_dir / "run-last.log"),
        "db_path": "database/latest/chembl_36/chembl_36_sqlite/chembl_36.db",
    }

    # Add case-type-specific metadata
    if "target_chembl" in case_info:
        # Target case
        target_chembl = case_info["target_chembl"]
        target_name = case_info["target_name"]

        entry.update({
            "size_class": "medium",
            "sort_keys": [
                "assay_chembl_id",
                "molecule_chembl_id",
                "canonical_smiles",
                "standard_type",
                "pchembl_value"
            ],
            "float_cols": ["pchembl_value"],
            "normalize": {
                "lowercase_columns": True,
                "strip_values": True,
                "lowercase_values": []
            },
            "column_rename_map": {
                "assay_chembl_id": "assay_chembl_id",
                "chembl_id": "molecule_chembl_id",
                "molecule_chembl_id": "molecule_chembl_id",
                "canonical_smiles": "canonical_smiles",
                "target_type": "target_type",
                "tax_id": "tax_id",
                "standard_type": "standard_type",
                "pchembl_value": "pchembl_value"
            }
        })
    elif "assay_chembl" in case_info:
        # Assay case
        entry.update({
            "size_class": "small",
            "sort_keys": [
                "molecule_chembl_id",
                "canonical_smiles",
                "standard_type",
                "standard_relation",
                "standard_value",
                "standard_units"
            ],
            "float_cols": ["standard_value"],
            "normalize": {
                "lowercase_columns": True,
                "strip_values": True,
                "lowercase_values": []
            },
            "column_rename_map": {
                "chembl_id": "molecule_chembl_id",
                "molecule_chembl_id": "molecule_chembl_id",
                "canonical_smiles": "canonical_smiles",
                "standard_type": "standard_type",
                "standard_relation": "standard_relation",
                "standard_value": "standard_value",
                "standard_units": "standard_units"
            }
        })
    elif "doc_chembl" in case_info:
        # Document case
        entry.update({
            "size_class": "small",
            "sort_keys": [
                "chembl_id",
                "compound_name",
                "canonical_smiles"
            ],
            "normalize": {
                "lowercase_columns": True,
                "strip_values": True,
                "lowercase_values": []
            },
            "column_rename_map": {
                "chembl_id": "chembl_id",
                "compound_name": "compound_name",
                "canonical_smiles": "canonical_smiles"
            }
        })

    return entry

def create_sqlite_sql(case_id: str, round_num: int):
    """Create sqlite.sql by copying source.sql."""
    source_dir = FIXTURES_DIR / f"web_scrape{round_num}" / case_id
    source_sql = source_dir / "source.sql"
    sqlite_sql = source_dir / "sqlite.sql"

    # Copy source.sql to sqlite.sql (they're already SQLite-compatible)
    shutil.copy(source_sql, sqlite_sql)
    print(f"  Created {sqlite_sql}")

def promote_case(case_info: dict):
    """Promote a single case to web_scrape_hq."""
    case_id = case_info["id"]
    round_num = case_info["round"]

    print(f"\nPromoting {case_id} (round {round_num})...")

    # Create sqlite.sql
    create_sqlite_sql(case_id, round_num)

    # Create web_scrape_hq entry
    entry = create_web_scrape_hq_entry(case_info)

    return entry

def main():
    """Main promotion function."""
    print("=" * 80)
    print("Promoting 26 cases from rounds 10-13 to web_scrape_hq")
    print("=" * 80)

    # Load existing web_scrape_hq_cases.json
    hq_cases_path = CASES_DIR / "web_scrape_hq_cases.json"
    with open(hq_cases_path) as f:
        existing_cases = json.load(f)

    print(f"\nExisting web_scrape_hq cases: {len(existing_cases)}")

    # Promote all cases
    new_entries = []
    for case_info in CASES_TO_PROMOTE:
        entry = promote_case(case_info)
        new_entries.append(entry)

    # Combine existing and new cases
    all_cases = existing_cases + new_entries

    # Write updated web_scrape_hq_cases.json
    with open(hq_cases_path, 'w') as f:
        json.dump(all_cases, f, indent=2)

    print(f"\n" + "=" * 80)
    print(f"Promotion complete!")
    print(f"  - Promoted {len(new_entries)} cases")
    print(f"  - New web_scrape_hq total: {len(all_cases)} cases")
    print(f"  - Updated: {hq_cases_path}")
    print("=" * 80)

    # Print summary by round
    print("\nSummary by round:")
    for round_num in [10, 11, 12, 13]:
        round_cases = [c for c in new_entries if f"web_scrape{round_num}" in c["source_sql_path"]]
        print(f"  Round {round_num}: {len(round_cases)} cases")

if __name__ == "__main__":
    main()
