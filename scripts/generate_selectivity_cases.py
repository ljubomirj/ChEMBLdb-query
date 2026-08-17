#!/usr/bin/env python3
"""
Generate selectivity and diverse query cases to reach 225 total.
Creates rounds 23-27 with ~75 additional cases.
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

def get_kinase_selectivity_pairs(limit: int = 20) -> List[Dict[str, Any]]:
    """Find kinase pairs for selectivity queries."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = """
    SELECT DISTINCT
        t1.chembl_id as target1_id,
        t1.pref_name as target1_name,
        t2.chembl_id as target2_id,
        t2.pref_name as target2_name,
        COUNT(DISTINCT a1.molregno) as shared_molecules
    FROM target_dictionary t1
    JOIN target_dictionary t2 ON t1.chembl_id < t2.chembl_id
    JOIN assays ass1 ON t1.tid = ass1.tid
    JOIN activities a1 ON ass1.assay_id = a1.assay_id
    JOIN assays ass2 ON t2.tid = ass2.tid
    JOIN activities a2 ON ass2.assay_id = a2.assay_id AND a1.molregno = a2.molregno
    JOIN compound_structures cs ON a1.molregno = cs.molregno
    WHERE t1.target_type = 'SINGLE PROTEIN'
      AND t2.target_type = 'SINGLE PROTEIN'
      AND t1.tax_id = '9606'
      AND t2.tax_id = '9606'
      AND a1.standard_type = 'IC50'
      AND a2.standard_type = 'IC50'
      AND a1.pchembl_value IS NOT NULL
      AND a2.pchembl_value IS NOT NULL
      AND cs.canonical_smiles IS NOT NULL
    GROUP BY t1.chembl_id, t1.pref_name, t2.chembl_id, t2.pref_name
    HAVING shared_molecules >= 50
    ORDER BY shared_molecules DESC
    LIMIT ?
    """

    cursor.execute(query, (limit * 2,))
    results = []

    for row in cursor.fetchall():
        t1_id, t1_name, t2_id, t2_name, shared = row

        # Create a readable case ID
        t1_short = t1_id.lower().replace("chembl_", "")
        t2_short = t2_id.lower().replace("chembl_", "")
        case_id = f"selective_{t1_short}_over_{t2_short}_smiles_exact"

        if case_id in EXISTING_IDS:
            continue

        results.append({
            "target1_id": t1_id,
            "target1_name": t1_name,
            "target2_id": t2_id,
            "target2_name": t2_name,
            "shared_molecules": shared,
            "case_id": case_id
        })

        if len(results) >= limit:
            break

    conn.close()
    return results

def get_more_targets(limit: int = 30) -> List[Dict[str, Any]]:
    """Find more human targets not yet used."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = """
    SELECT DISTINCT
        td.chembl_id,
        td.pref_name,
        COUNT(DISTINCT act.molregno) as molecule_count
    FROM target_dictionary td
    JOIN activities act ON td.tid = act.tid
    JOIN compound_structures cs ON act.molregno = cs.molregno
    WHERE td.target_type = 'SINGLE PROTEIN'
      AND td.tax_id = '9606'
      AND act.standard_type = 'IC50'
      AND act.pchembl_value IS NOT NULL
      AND cs.canonical_smiles IS NOT NULL
    GROUP BY td.chembl_id, td.pref_name
    HAVING molecule_count >= 20
    ORDER BY molecule_count DESC
    LIMIT ?
    """

    cursor.execute(query, (limit * 3,))
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

def get_more_assays(limit: int = 25) -> List[Dict[str, Any]]:
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

    cursor.execute(query, (limit * 3,))
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

def create_selectivity_case(pair: Dict[str, Any], round_num: int) -> Tuple[str, str]:
    """Create a selectivity query case."""
    case_id = pair["case_id"]
    t1_id = pair["target1_id"]
    t2_id = pair["target2_id"]
    t1_name = pair["target1_name"]
    t2_name = pair["target2_name"]

    fixture_dir = FIXTURES_BASE / f"web_scrape{round_num}" / case_id
    fixture_dir.mkdir(parents=True, exist_ok=True)

    sql_content = f"""SELECT
    COMPOUND_STRUCTURES.canonical_smiles,
    MOLECULE_DICTIONARY.chembl_id,
    act1.pchembl_value AS pchembl_value_{t1_id.lower()},
    act2.pchembl_value AS pchembl_value_{t2_id.lower()}
FROM MOLECULE_DICTIONARY
JOIN COMPOUND_STRUCTURES ON MOLECULE_DICTIONARY.molregno = COMPOUND_STRUCTURES.molregno
JOIN TARGET_DICTIONARY td1 ON td1.chembl_id = '{t1_id}'
JOIN ACTIVITIES act1 ON act1.molregno = MOLECULE_DICTIONARY.molregno AND act1.tid = td1.tid
JOIN TARGET_DICTIONARY td2 ON td2.chembl_id = '{t2_id}'
JOIN ACTIVITIES act2 ON act2.molregno = MOLECULE_DICTIONARY.molregno AND act2.tid = td2.tid
WHERE act1.standard_type = 'IC50'
  AND act2.standard_type = 'IC50'
  AND act1.pchembl_value IS NOT NULL
  AND act2.pchembl_value IS NOT NULL
  AND act1.pchembl_value > act2.pchembl_value
ORDER BY MOLECULE_DICTIONARY.chembl_id
"""

    uq_content = f"Retrieve canonical_smiles, chembl_id, and pchembl_values for molecules that are selective (more potent) for {t1_id} ({t1_name}) over {t2_id} ({t2_name})."

    metadata_content = {
        "id": case_id,
        "source_title": f"Selectivity query: {t1_id} over {t2_id}",
        "source_url": "https://github.com/cthoyt/chembl-downloader/blob/main/src/chembl_downloader/queries.py",
        "uq_origin": "selectivity_query",
        "uq_path": f"tests/fixtures/web_scrape{round_num}/{case_id}/uq.txt",
        "sql_path": f"tests/fixtures/web_scrape{round_num}/{case_id}/source.sql",
        "documentation_path": f"tests/fixtures/web_scrape{round_num}/{case_id}/documentation.txt"
    }

    documentation_content = f"Selectivity: {t1_id} ({t1_name}) over {t2_id} ({t2_name})\n\nFinds molecules more potent on target1 than target2 based on IC50 pchembl_value.\n"

    (fixture_dir / "source.sql").write_text(sql_content)
    (fixture_dir / "sqlite.sql").write_text(sql_content)
    (fixture_dir / "uq.txt").write_text(uq_content)
    (fixture_dir / "metadata.json").write_text(json.dumps(metadata_content, indent=2))
    (fixture_dir / "documentation.txt").write_text(documentation_content)

    return str(fixture_dir), case_id

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
    selectivity_pairs = get_kinase_selectivity_pairs(20)
    more_targets = get_more_targets(30)
    more_assays = get_more_assays(25)

    print(f"   ✓ {len(selectivity_pairs)} selectivity cases")
    print(f"   ✓ {len(more_targets)} target IC50 cases")
    print(f"   ✓ {len(more_assays)} assay cases")
    print(f"   Total: {len(selectivity_pairs) + len(more_targets) + len(more_assays)} new cases")

    created_cases = []
    round_num = 23

    # Round 23-24: Selectivity cases
    print(f"\n🎯 Round {round_num}-24: Creating {len(selectivity_pairs)} selectivity cases...")
    for i, pair in enumerate(selectivity_pairs):
        fixture_dir, case_id = create_selectivity_case(pair, round_num + (i // 10))
        print(f"   [{i+1}/{len(selectivity_pairs)}] {case_id}")

        if materialize_case(fixture_dir, DB_PATH):
            print(f"      ✓ Materialized")
            created_cases.append({"case_id": case_id, "round": round_num + (i // 10), "type": "selectivity"})
        else:
            print(f"      ✗ Failed")
            import shutil
            shutil.rmtree(fixture_dir, ignore_errors=True)

    # Round 25-26: More targets
    round_num = 25
    print(f"\n🎯 Round {round_num}-26: Creating {len(more_targets)} target IC50 cases...")
    for i, target in enumerate(more_targets):
        fixture_dir, case_id = create_target_case(target, round_num + (i // 15))
        print(f"   [{i+1}/{len(more_targets)}] {case_id} ({target['molecule_count']} molecules)")

        if materialize_case(fixture_dir, DB_PATH):
            print(f"      ✓ Materialized")
            created_cases.append({"case_id": case_id, "round": round_num + (i // 15), "type": "target"})
        else:
            print(f"      ✗ Failed")
            import shutil
            shutil.rmtree(fixture_dir, ignore_errors=True)

    # Round 27: More assays
    round_num = 27
    print(f"\n🧪 Round {round_num}: Creating {len(more_assays)} assay cases...")
    for i, assay in enumerate(more_assays):
        fixture_dir, case_id = create_assay_case(assay, round_num)
        print(f"   [{i+1}/{len(more_assays)}] {case_id} ({assay['activity_count']} activities)")

        if materialize_case(fixture_dir, DB_PATH):
            print(f"      ✓ Materialized")
            created_cases.append({"case_id": case_id, "round": round_num, "type": "assay"})
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
