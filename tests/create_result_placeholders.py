#!/usr/bin/env python3
"""
Create placeholder result-last.csv and run-last.log files for promoted cases.

These placeholders will be overwritten when the cases are actually executed.
"""

from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
FIXTURES_DIR = BASE_DIR / "tests" / "fixtures"

# New cases to create placeholders for
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

def create_placeholders(case_id: str, round_num: int):
    """Create placeholder files for a case."""
    case_dir = FIXTURES_DIR / f"web_scrape{round_num}" / case_id

    # Create placeholder result-last.csv
    result_path = case_dir / "result-last.csv"
    if not result_path.exists():
        result_path.write_text("# Placeholder - will be overwritten by actual LLM run\n")
        print(f"  Created {result_path.name}")

    # Create placeholder run-last.log
    log_path = case_dir / "run-last.log"
    if not log_path.exists():
        log_path.write_text("# Placeholder - will be overwritten by actual LLM run\n")
        print(f"  Created {log_path.name}")

def main():
    """Main function."""
    print("=" * 80)
    print("Creating placeholder result files for promoted cases")
    print("=" * 80)

    for case_id, round_num in NEW_CASES:
        print(f"\n{case_id} (round {round_num}):")
        create_placeholders(case_id, round_num)

    print(f"\n" + "=" * 80)
    print(f"Placeholder creation complete!")
    print(f"  - Created placeholders for {len(NEW_CASES)} cases")
    print("=" * 80)

if __name__ == "__main__":
    main()
