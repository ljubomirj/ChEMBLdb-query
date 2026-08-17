#!/usr/bin/env python3
"""
Quick generation of 50 more cases using simpler queries.
Targets only (fastest to execute).
"""

import sqlite3
import csv
import subprocess
import json
from pathlib import Path

BASE_DIR = Path("/Users/ljubomir/ChEMBLdb-query")
DB_PATH = BASE_DIR / "database/latest/chembl_36/chembl_36_sqlite/chembl_36.db"
FIXTURES_BASE = BASE_DIR / "tests/fixtures"

# Load existing case IDs
CASES_FILE = BASE_DIR / "cases/registries/archive/web_scrape_hq_cases_v4.5.json"
with open(CASES_FILE) as f:
    EXISTING_IDS = {case["id"] for case in json.load(f)}

def get_targets_fast(limit: int = 50):
    """Get 50 more targets quickly."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Simple query - just get targets with IC50 data
    query = """
    SELECT DISTINCT td.chembl_id, td.pref_name
    FROM target_dictionary td
    JOIN assays a ON td.tid = a.tid
    JOIN activities act ON a.assay_id = act.assay_id
    WHERE td.target_type = 'SINGLE PROTEIN'
      AND td.tax_id = '9606'
      AND act.standard_type = 'IC50'
      AND act.pchembl_value IS NOT NULL
    LIMIT ?
    """

    cursor.execute(query, (limit * 5,))
    results = []

    for row in cursor.fetchall():
        chembl_id, pref_name = row
        case_id = f"chembl_downloader_target_{chembl_id.lower()}_ic50_human_pchembl"
        if case_id not in EXISTING_IDS:
            results.append((chembl_id, pref_name, case_id))
        if len(results) >= limit:
            break

    conn.close()
    return results

def create_case(chembl_id, pref_name, case_id, round_num):
    """Create a single case."""
    fixture_dir = FIXTURES_BASE / f"web_scrape{round_num}" / case_id
    fixture_dir.mkdir(parents=True, exist_ok=True)

    sql = f"""SELECT
    ASSAYS.chembl_id AS assay_chembl_id,
    TARGET_DICTIONARY.target_type,
    TARGET_DICTIONARY.tax_id,
    COMPOUND_STRUCTURES.canonical_smiles,
    MOLECULE_DICTIONARY.chembl_id AS molecule_chembl_id,
    ACTIVITIES.standard_type,
    ACTIVITIES.pchembl_value
FROM TARGET_DICTIONARY
     JOIN ASSAYS ON TARGET_DICTIONARY.tid = ASSAYS.tid
     JOIN ACTIVITIES ON ASSAYS.assay_id = ACTIVITIES.assay_id
     JOIN MOLECULE_DICTIONARY ON MOLECULE_DICTIONARY.molregno = ACTIVITIES.molregno
     JOIN COMPOUND_STRUCTURES ON MOLECULE_DICTIONARY.molregno = COMPOUND_STRUCTURES.molregno
WHERE TARGET_DICTIONARY.chembl_id = '{chembl_id}'
    AND ACTIVITIES.pchembl_value IS NOT NULL
    AND TARGET_DICTIONARY.target_type = 'SINGLE PROTEIN'
    AND ACTIVITIES.standard_relation = '='
    AND ACTIVITIES.standard_type = 'IC50'
    AND TARGET_DICTIONARY.tax_id = '9606'
ORDER BY molecule_chembl_id, assay_chembl_id
LIMIT 1000
"""

    benchmark_spec_uq = (
        f"IC50 activities for human target {chembl_id} ({pref_name}). Require target_type = "
        f"'SINGLE PROTEIN', tax_id = '9606', standard_relation = '=', and pchembl_value not "
        f"null. Order rows by molecule_chembl_id, assay_chembl_id. Return only the first 1000 rows."
    )
    uq_content = (
        f"Show the first 1000 IC50 activity rows with pChEMBL values for the human single-protein "
        f"target {chembl_id} ({pref_name}). Return assay ChEMBL ID, target type, tax_id, "
        f"canonical SMILES, molecule ChEMBL ID, standard type, and pChEMBL value. "
        f"Order the rows by molecule ChEMBL ID and assay ChEMBL ID."
    )

    (fixture_dir / "source.sql").write_text(sql)
    (fixture_dir / "sqlite.sql").write_text(sql)
    (fixture_dir / "uq.txt").write_text(uq_content)
    (fixture_dir / "benchmark_spec_uq.txt").write_text(benchmark_spec_uq)

    metadata = {
        "id": case_id,
        "source_title": f"Target {chembl_id}",
        "source_url": "https://github.com/cthoyt/chembl-downloader",
        "uq_origin": "target_query",
        "uq_style": "realistic_uq",
        "uq_origin_kind": "templated_from_sql",
        "uq_path": f"tests/fixtures/web_scrape{round_num}/{case_id}/uq.txt",
        "benchmark_spec_uq_path": f"tests/fixtures/web_scrape{round_num}/{case_id}/benchmark_spec_uq.txt",
        "sql_path": f"tests/fixtures/web_scrape{round_num}/{case_id}/source.sql",
        "documentation_path": f"tests/fixtures/web_scrape{round_num}/{case_id}/documentation.txt"
    }
    (fixture_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))
    (fixture_dir / "documentation.txt").write_text(f"Target: {chembl_id}\n")

    return str(fixture_dir)

def materialize(fixture_dir):
    """Execute and create ground truth."""
    sql_path = Path(fixture_dir) / "sqlite.sql"
    csv_path = Path(fixture_dir) / "ground-truth.csv"

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(sql_path.read_text())

        if not cursor.description:
            conn.close()
            return False

        columns = [desc[0] for desc in cursor.description]
        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=columns, quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()
            for row in cursor:
                writer.writerow({c: (row[c] or "") for c in columns})

        conn.close()

        # Compress
        subprocess.run(["zstd", "-f", str(csv_path), "-o", str(csv_path.with_suffix(".csv.zst"))],
                      check=True, capture_output=True)
        return True
    except:
        return False

def main():
    print("Generating 50 more target cases...")

    targets = get_targets_fast(50)
    print(f"Found {len(targets)} targets")

    created = []
    round_num = 28

    for i, (chembl_id, pref_name, case_id) in enumerate(targets):
        fixture_dir = create_case(chembl_id, pref_name, case_id, round_num + (i // 25))
        print(f"[{i+1}/{len(targets)}] {case_id}", end=" ")

        if materialize(fixture_dir):
            print("✓")
            created.append({
                "case_id": case_id,
                "round": round_num + (i // 25),
                "type": "target"
            })
        else:
            print("✗")
            import shutil
            shutil.rmtree(fixture_dir, ignore_errors=True)

    print(f"\nCreated {len(created)} cases")

    # Save
    output = BASE_DIR / "scripts/new_cases_round_28.json"
    with open(output, 'w') as f:
        json.dump(created, f, indent=2)
    print(f"Saved to {output}")

if __name__ == "__main__":
    main()
