#!/usr/bin/env python3
"""
Validate that all promoted cases have the required files.

This script checks that each promoted case has:
- source.sql
- sqlite.sql
- ground-truth.csv
"""

from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
FIXTURES_DIR = BASE_DIR / "tests" / "fixtures"
CASES_DIR = BASE_DIR / "tests" / "cases"

# New cases to validate
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

REQUIRED_FILES = ["source.sql", "sqlite.sql", "ground-truth.csv"]

def validate_case(case_id: str, round_num: int) -> bool:
    """Validate that a case has all required files."""
    case_dir = FIXTURES_DIR / f"web_scrape{round_num}" / case_id

    if not case_dir.exists():
        print(f"  ✗ {case_id}: directory does not exist")
        return False

    missing = []
    for filename in REQUIRED_FILES:
        filepath = case_dir / filename
        if not filepath.exists():
            missing.append(filename)

    if missing:
        print(f"  ✗ {case_id}: missing {', '.join(missing)}")
        return False

    # Check file sizes
    for filename in REQUIRED_FILES:
        filepath = case_dir / filename
        size = filepath.stat().st_size
        if size == 0 and filename == "ground-truth.csv":
            # Empty ground truth is OK (no results)
            pass
        elif size == 0:
            print(f"  ⚠ {case_id}: {filename} is empty")

    print(f"  ✓ {case_id}: all required files present")
    return True

def main():
    """Main validation function."""
    print("=" * 80)
    print("Validating promoted rounds 10-13 cases")
    print("=" * 80)

    success_count = 0
    for case_id, round_num in NEW_CASES:
        if validate_case(case_id, round_num):
            success_count += 1

    print(f"\n" + "=" * 80)
    print(f"Validation complete!")
    print(f"  - Validated: {success_count}/{len(NEW_CASES)} cases")
    print(f"  - Issues: {len(NEW_CASES) - success_count} cases")
    print("=" * 80)

if __name__ == "__main__":
    main()
