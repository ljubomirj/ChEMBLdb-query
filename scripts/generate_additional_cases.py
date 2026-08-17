#!/usr/bin/env python3
"""
Generate additional cases to reach 200+ total.
Simple approach: more targets and assays, skip expensive selectivity queries.
"""

import sqlite3
import csv
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Configuration
BASE_DIR = Path("/Users/ljubomir/ChEMBLdb-query")
DB_PATH = BASE_DIR / "database/latest/chembl_36/chembl_36_sqlite/chembl_36.db"
FIXTURES_BASE = BASE_DIR / "tests/fixtures"
CASES_FILE = BASE_DIR / "cases/registries/archive/web_scrape_hq_cases.json"

# Existing cases
with open(CASES_FILE) as f:
    EXISTING_IDS = {case["id"] for case in json.load(f)}

# Add newly created cases
with open(BASE_DIR / "scripts" / "new_cases_rounds_18_22.json") as f:
    for case in json.load(f):
        EXISTING_IDS.add(case["case_id"])

def get_targets_simple(limit: int = 60) -> List[Dict[str, Any]]:
    """Find more human targets not yet used."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = """
    SELECT DISTINCT
        td.chembl_id,
        td.pref_name,
        COUNT(DISTINCT act.molregno) as molecule_count
    FROM target_dictionary td
    JOIN assays a ON td.tid = a.tid
    JOIN activities act ON a.assay_id = act.assay_id
    JOIN compound_structures cs ON act.molregno = cs.molregno
    WHERE td.target_type = 'SINGLE PROTEIN'
      AND td.tax_id = '9606'
      AND act.standard_type = 'IC50'
      AND act.pchembl_value IS NOT NULL
      AND cs.canonical_smiles IS NOT NULL
    GROUP BY td.chembl_id, td.pref_name
    HAVING molecule_count >= 10
    ORDER BY molecule_count DESC
    LIMIT ?
    """

    cursor.execute(query, (limit * 2,))
    results = []

    for row in cursor.fetchall():
        chembl_id, pref_name, molecule_count = row
        case_id = f"chembl_downloader_target_{chembl_id.lower()}_ic50_human_pchembl"
        if case_id in EXISTING_IDS:
            continue
        results.append({
            "chembl_id": chembl_id,
            "pref_name": pref_name,
            "molecule_count": molecule_count,
            "case_id": case_id
        })
        if len(results) >= limit:
            break

    conn.close()
    return results

def get_assays_simple(limit: int = 40) -> List[Dict[str, Any]]:
    """Find more assays not yet used."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = """
    SELECT
        a.chembl_id,
        COUNT(DISTINCT act.molregno) as molecule_count,
        COUNT(*) as activity_count
    FROM assays a
    JOIN activities act ON a.assay_id = act.assay_id
    JOIN molecule_dictionary md ON act.molregno = md.molregno
    JOIN compound_structures cs ON md.molregno = cs.molregno
    WHERE act.standard_value IS NOT NULL
      AND act.standard_relation = '='
      AND cs.canonical_smiles IS NOT NULL
    GROUP BY a.chembl_id
    HAVING molecule_count >= 3
    ORDER BY activity_count DESC
    LIMIT ?
    """

    cursor.execute(query, (limit * 2,))
    results = []

    for row in cursor.fetchall():
        chembl_id, molecule_count, activity_count = row
        case_id = f"chembl_downloader_assay_{chembl_id.lower()}_exact"
        if case_id in EXISTING_IDS:
            continue
        results.append({
            "chembl_id": chembl_id,
            "molecule_count": molecule_count,
            "activity_count": activity_count,
            "case_id": case_id
        })
        if len(results) >= limit:
            break

    conn.close()
    return results

def execute_sql_to_csv(sql: str, csv_path: Path, db_path: Path) -> int:
    """Execute SQL and save results to CSV."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute(sql)
        if not cursor.description:
            return 0
        columns = [desc[0] for desc in cursor.description]

        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=columns, quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()
            for row in cursor:
                row_dict = {}
                for col in columns:
                    val = row[col]
                    row_dict[col] = "" if val is None else str(val)
                writer.writerow(row_dict)

        return len(list(cursor.execute(sql)))
    finally:
        conn.close()

def compress_csv(csv_path: Path) -> Path:
    """Compress CSV with zstd."""
    zst_path = csv_path.with_suffix(csv_path.suffix + ".zst")
    subprocess.run(["zstd", "-f", str(csv_path), "-o", str(zst_path)], check=True, capture_output=True)
    return zst_path

def create_target_case(target: Dict[str, Any], round_num: int) -> Tuple[str, str]:
    """Create a target IC50 case."""
    case_id = target["case_id"]
    chembl_id = target["chembl_id"]
    pref_name = target["pref_name"]

    fixture_dir = FIXTURES_BASE / f"web_scrape{round_num}" / case_id
    fixture_dir.mkdir(parents=True, exist_ok=True)

    sql_content = f"""SELECT
    ASSAYS.chembl_id              AS assay_chembl_id,
    TARGET_DICTIONARY.target_type,
    TARGET_DICTIONARY.tax_id,
    COMPOUND_STRUCTURES.canonical_smiles,
    MOLECULE_DICTIONARY.chembl_id AS molecule_chembl_id,
    ACTIVITIES.standard_type,
    ACTIVITIES.pchembl_value
FROM TARGET_DICTIONARY
     JOIN ASSAYS ON TARGET_DICTIONARY.tid = ASSAYS.tid
     JOIN ACTIVITIES ON ASSAYS.assay_id = ACTIVITIES.assay_id
     JOIN MOLECULE_DICTIONARY
        ON MOLECULE_DICTIONARY.molregno = ACTIVITIES.molregno
     JOIN COMPOUND_STRUCTURES
        ON MOLECULE_DICTIONARY.molregno = COMPOUND_STRUCTURES.molregno
WHERE TARGET_DICTIONARY.chembl_id = '{chembl_id}'
    AND ACTIVITIES.pchembl_value IS NOT NULL
    AND TARGET_DICTIONARY.target_type = 'SINGLE PROTEIN'
    AND ACTIVITIES.standard_relation = '='
    AND ACTIVITIES.standard_type = 'IC50'
    AND TARGET_DICTIONARY.tax_id = '9606'
ORDER BY molecule_chembl_id, assay_chembl_id
"""

    benchmark_spec_uq = (
        f"Retrieve assay_chembl_id, target_type, tax_id, canonical_smiles, molecule_chembl_id, "
        f"standard_type, and pchembl_value for IC50 activities on human single protein target "
        f"{chembl_id} ({pref_name}) with pchembl_value not null and standard_relation '='."
    )
    uq_content = (
        f"Show IC50 activity rows with pChEMBL values for the human single-protein target "
        f"{chembl_id} ({pref_name}). Return assay ChEMBL ID, target type, tax_id, canonical "
        f"SMILES, molecule ChEMBL ID, standard type, and pChEMBL value."
    )

    metadata_content = {
        "id": case_id,
        "source_title": f"chembl_downloader get_target_sql instantiated for {chembl_id}",
        "source_url": "https://github.com/cthoyt/chembl-downloader/blob/main/src/chembl_downloader/queries.py",
        "uq_origin": "explicit_from_function_comment_and_parameter",
        "uq_style": "realistic_uq",
        "uq_origin_kind": "templated_from_sql",
        "uq_path": f"tests/fixtures/web_scrape{round_num}/{case_id}/uq.txt",
        "benchmark_spec_uq_path": f"tests/fixtures/web_scrape{round_num}/{case_id}/benchmark_spec_uq.txt",
        "sql_path": f"tests/fixtures/web_scrape{round_num}/{case_id}/source.sql",
        "documentation_path": f"tests/fixtures/web_scrape{round_num}/{case_id}/documentation.txt"
    }

    documentation_content = f"Target: {chembl_id} ({pref_name})\n\nThis is a human single protein target with IC50 activities.\n"

    (fixture_dir / "source.sql").write_text(sql_content)
    (fixture_dir / "sqlite.sql").write_text(sql_content)
    (fixture_dir / "uq.txt").write_text(uq_content)
    (fixture_dir / "benchmark_spec_uq.txt").write_text(benchmark_spec_uq)
    (fixture_dir / "metadata.json").write_text(json.dumps(metadata_content, indent=2))
    (fixture_dir / "documentation.txt").write_text(documentation_content)

    return str(fixture_dir), case_id

def create_assay_case(assay: Dict[str, Any], round_num: int) -> Tuple[str, str]:
    """Create an assay case."""
    case_id = assay["case_id"]
    chembl_id = assay["chembl_id"]

    fixture_dir = FIXTURES_BASE / f"web_scrape{round_num}" / case_id
    fixture_dir.mkdir(parents=True, exist_ok=True)

    sql_content = f"""SELECT
    COMPOUND_STRUCTURES.canonical_smiles,
    MOLECULE_DICTIONARY.chembl_id,
    ACTIVITIES.STANDARD_TYPE,
    ACTIVITIES.STANDARD_RELATION,
    ACTIVITIES.STANDARD_VALUE,
    ACTIVITIES.STANDARD_UNITS
FROM MOLECULE_DICTIONARY
JOIN COMPOUND_STRUCTURES ON MOLECULE_DICTIONARY.molregno = COMPOUND_STRUCTURES.molregno
JOIN ACTIVITIES ON MOLECULE_DICTIONARY.molregno = ACTIVITIES.molregno
JOIN ASSAYS ON ACTIVITIES.ASSAY_ID = ASSAYS.ASSAY_ID
WHERE
    ASSAYS.chembl_id = '{chembl_id}'
    and ACTIVITIES.standard_value is not null
    and ACTIVITIES.standard_relation is not null
    and ACTIVITIES.standard_relation = '='
ORDER BY MOLECULE_DICTIONARY.chembl_id
"""

    benchmark_spec_uq = (
        f"Retrieve canonical_smiles, chembl_id, standard_type, standard_relation, "
        f"standard_value, and standard_units for activity rows in assay {chembl_id} "
        f"where standard_value is not null and standard_relation '='."
    )
    uq_content = (
        f"For assay {chembl_id}, list compounds with exact activity measurements. "
        f"Return canonical SMILES, molecule ChEMBL ID, standard type, standard relation, "
        f"standard value, and standard units."
    )

    metadata_content = {
        "id": case_id,
        "source_title": f"chembl_downloader get_assay_sql instantiated for {chembl_id}",
        "source_url": "https://github.com/cthoyt/chembl-downloader/blob/main/src/chembl_downloader/queries.py",
        "uq_origin": "explicit_from_function_comment_and_parameter",
        "uq_style": "realistic_uq",
        "uq_origin_kind": "templated_from_sql",
        "uq_path": f"tests/fixtures/web_scrape{round_num}/{case_id}/uq.txt",
        "benchmark_spec_uq_path": f"tests/fixtures/web_scrape{round_num}/{case_id}/benchmark_spec_uq.txt",
        "sql_path": f"tests/fixtures/web_scrape{round_num}/{case_id}/source.sql",
        "documentation_path": f"tests/fixtures/web_scrape{round_num}/{case_id}/documentation.txt"
    }

    documentation_content = f"Assay: {chembl_id}\n\n"

    (fixture_dir / "source.sql").write_text(sql_content)
    (fixture_dir / "sqlite.sql").write_text(sql_content)
    (fixture_dir / "uq.txt").write_text(uq_content)
    (fixture_dir / "benchmark_spec_uq.txt").write_text(benchmark_spec_uq)
    (fixture_dir / "metadata.json").write_text(json.dumps(metadata_content, indent=2))
    (fixture_dir / "documentation.txt").write_text(documentation_content)

    return str(fixture_dir), case_id

def materialize_case(fixture_dir: str, db_path: Path) -> bool:
    """Execute SQL and create ground truth CSV."""
    fixture_path = Path(fixture_dir)
    sql_path = fixture_path / "sqlite.sql"
    csv_path = fixture_path / "ground-truth.csv"

    if not sql_path.exists():
        return False

    try:
        sql = sql_path.read_text()
        row_count = execute_sql_to_csv(sql, csv_path, db_path)
        if row_count > 0:
            compress_csv(csv_path)
            return True
        return False
    except Exception as e:
        print(f"    ERROR: {e}")
        return False

def main():
    """Main generation workflow."""
    print("=" * 80)
    print("Expanding ChEMBL Benchmark: Adding 75 more cases (rounds 23-27)")
    print("=" * 80)

    print(f"\n📁 Database: {DB_PATH}")
    print(f"📋 Existing cases: {len(EXISTING_IDS)}")

    # Find new cases
    print("\n🔍 Finding new cases...")
    more_targets = get_targets_simple(60)
    more_assays = get_assays_simple(40)

    print(f"   ✓ {len(more_targets)} target IC50 cases")
    print(f"   ✓ {len(more_assays)} assay cases")
    print(f"   Total: {len(more_targets) + len(more_assays)} new cases")

    created_cases = []
    round_num = 23

    # Round 23-25: More targets
    print(f"\n🎯 Round {round_num}-25: Creating {len(more_targets)} target IC50 cases...")
    for i, target in enumerate(more_targets):
        fixture_dir, case_id = create_target_case(target, round_num + (i // 20))
        print(f"   [{i+1}/{len(more_targets)}] {case_id} ({target['molecule_count']} molecules)")

        if materialize_case(fixture_dir, DB_PATH):
            print(f"      ✓ Materialized")
            created_cases.append({"case_id": case_id, "round": round_num + (i // 20), "type": "target"})
        else:
            print(f"      ✗ Failed")
            import shutil
            shutil.rmtree(fixture_dir, ignore_errors=True)

    # Round 26-27: More assays
    round_num = 26
    print(f"\n🧪 Round {round_num}-27: Creating {len(more_assays)} assay cases...")
    for i, assay in enumerate(more_assays):
        fixture_dir, case_id = create_assay_case(assay, round_num + (i // 20))
        print(f"   [{i+1}/{len(more_assays)}] {case_id} ({assay['activity_count']} activities)")

        if materialize_case(fixture_dir, DB_PATH):
            print(f"      ✓ Materialized")
            created_cases.append({"case_id": case_id, "round": round_num + (i // 20), "type": "assay"})
        else:
            print(f"      ✗ Failed")
            import shutil
            shutil.rmtree(fixture_dir, ignore_errors=True)

    # Summary
    print("\n" + "=" * 80)
    print(f"✅ SUCCESS! Created {len(created_cases)} new cases")
    print(f"   Previous total: 150 cases")
    print(f"   New total: {150 + len(created_cases)} cases")
    print("=" * 80)

    # Save case list
    output_file = BASE_DIR / "scripts" / "new_cases_rounds_23_27.json"
    with open(output_file, 'w') as f:
        json.dump(created_cases, f, indent=2)
    print(f"\n📝 Case list saved to {output_file}")

if __name__ == "__main__":
    main()
