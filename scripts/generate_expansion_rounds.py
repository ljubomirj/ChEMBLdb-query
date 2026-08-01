#!/usr/bin/env python3
"""
Generate new ChEMBL text-to-SQL cases to expand benchmark from 95 to 200+ cases.
Generates rounds 18-27 with ~55 new cases (target/assay/document queries).
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
CASES_FILE = BASE_DIR / "tests/cases/web_scrape_hq_cases.json"

# Existing cases to avoid duplicates
with open(CASES_FILE) as f:
    EXISTING_IDS = {case["id"] for case in json.load(f)}

def get_unused_human_targets(limit: int = 25) -> List[Dict[str, Any]]:
    """Find human single protein targets with good IC50 data not yet used."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = """
    SELECT DISTINCT
        td.chembl_id,
        td.pref_name,
        COUNT(DISTINCT a.assay_id) as assay_count,
        COUNT(DISTINCT act.molregno) as molecule_count
    FROM target_dictionary td
    JOIN assays a ON td.tid = a.tid
    JOIN activities act ON a.assay_id = act.assay_id
    JOIN compound_structures cs ON act.molregno = cs.molregno
    WHERE td.target_type = 'SINGLE PROTEIN'
      AND td.tax_id = '9606'
      AND act.standard_type = 'IC50'
      AND act.pchembl_value IS NOT NULL
      AND act.standard_relation = '='
      AND cs.canonical_smiles IS NOT NULL
    GROUP BY td.chembl_id, td.pref_name
    HAVING molecule_count >= 15
    ORDER BY molecule_count DESC
    LIMIT ?
    """

    cursor.execute(query, (limit * 3,))
    results = []

    for row in cursor.fetchall():
        chembl_id, pref_name, assay_count, molecule_count = row
        case_id = f"chembl_downloader_target_{chembl_id.lower()}_ic50_human_pchembl"
        if case_id in EXISTING_IDS:
            continue
        results.append({
            "chembl_id": chembl_id,
            "pref_name": pref_name,
            "assay_count": assay_count,
            "molecule_count": molecule_count,
            "case_id": case_id
        })
        if len(results) >= limit:
            break

    conn.close()
    return results

def get_unused_assays(limit: int = 15) -> List[Dict[str, Any]]:
    """Find assays with good activity data not yet used."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = """
    SELECT
        a.chembl_id,
        a.description,
        COUNT(DISTINCT act.molregno) as molecule_count,
        COUNT(*) as activity_count
    FROM assays a
    JOIN activities act ON a.assay_id = act.assay_id
    JOIN molecule_dictionary md ON act.molregno = md.molregno
    JOIN compound_structures cs ON md.molregno = cs.molregno
    WHERE act.standard_value IS NOT NULL
      AND act.standard_relation IS NOT NULL
      AND act.standard_relation = '='
      AND cs.canonical_smiles IS NOT NULL
    GROUP BY a.chembl_id, a.description
    HAVING molecule_count >= 5
    ORDER BY activity_count DESC
    LIMIT ?
    """

    cursor.execute(query, (limit * 3,))
    results = []

    for row in cursor.fetchall():
        chembl_id, description, molecule_count, activity_count = row
        case_id = f"chembl_downloader_assay_{chembl_id.lower()}_exact"
        if case_id in EXISTING_IDS:
            continue
        results.append({
            "chembl_id": chembl_id,
            "description": (description or "")[:100],
            "molecule_count": molecule_count,
            "activity_count": activity_count,
            "case_id": case_id
        })
        if len(results) >= limit:
            break

    conn.close()
    return results

def get_unused_documents(limit: int = 15) -> List[Dict[str, Any]]:
    """Find documents with multiple molecules not yet used."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = """
    SELECT
        d.chembl_id,
        d.title,
        COUNT(DISTINCT cr.molregno) as molecule_count
    FROM docs d
    JOIN compound_records cr ON d.doc_id = cr.doc_id
    JOIN molecule_dictionary md ON cr.molregno = md.molregno
    JOIN compound_structures cs ON md.molregno = cs.molregno
    WHERE cs.canonical_smiles IS NOT NULL
    GROUP BY d.chembl_id, d.title
    HAVING molecule_count BETWEEN 5 AND 100
    ORDER BY molecule_count DESC
    LIMIT ?
    """

    cursor.execute(query, (limit * 3,))
    results = []

    for row in cursor.fetchall():
        chembl_id, title, molecule_count = row
        case_id = f"chembl_downloader_document_molecules_{chembl_id.lower()}"
        if case_id in EXISTING_IDS:
            continue
        results.append({
            "chembl_id": chembl_id,
            "title": (title or "Unknown")[:100],
            "molecule_count": molecule_count,
            "case_id": case_id
        })
        if len(results) >= limit:
            break

    conn.close()
    return results

def execute_sql_to_csv(sql: str, csv_path: Path, db_path: Path) -> int:
    """Execute SQL and save results to CSV with proper quoting."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute(sql)

        if not cursor.description:
            return 0

        columns = [desc[0] for desc in cursor.description]

        # Use QUOTE_MINIMAL but quote all fields that need it (commas, quotes, newlines)
        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=columns, quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()

            for row in cursor:
                row_dict = {}
                for col in columns:
                    val = row[col]
                    # Convert to string and handle None
                    if val is None:
                        row_dict[col] = ""
                    else:
                        row_dict[col] = str(val)
                writer.writerow(row_dict)

        return len(list(cursor.execute(sql)))
    finally:
        conn.close()

def compress_csv(csv_path: Path) -> Path:
    """Compress CSV with zstd."""
    zst_path = csv_path.with_suffix(csv_path.suffix + ".zst")
    subprocess.run(["zstd", "-f", str(csv_path), "-o", str(zst_path)], check=True)
    return zst_path

def create_target_case(target_info: Dict[str, Any], round_num: int) -> Tuple[str, str]:
    """Create a target IC50 case fixture."""
    case_id = target_info["case_id"]
    chembl_id = target_info["chembl_id"]
    pref_name = target_info["pref_name"]

    fixture_dir = FIXTURES_BASE / f"web_scrape{round_num}" / case_id
    fixture_dir.mkdir(parents=True, exist_ok=True)

    # Create SQL with ORDER BY for deterministic results
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

    documentation_content = f"Target: {chembl_id} ({pref_name})\n\nThis is a human single protein target with IC50 activities.\nQuery retrieves all bioactivity data with pchembl_value.\n"

    # Write files
    (fixture_dir / "source.sql").write_text(sql_content)
    (fixture_dir / "sqlite.sql").write_text(sql_content)
    (fixture_dir / "uq.txt").write_text(uq_content)
    (fixture_dir / "benchmark_spec_uq.txt").write_text(benchmark_spec_uq)
    (fixture_dir / "metadata.json").write_text(json.dumps(metadata_content, indent=2))
    (fixture_dir / "documentation.txt").write_text(documentation_content)

    return str(fixture_dir), case_id

def create_assay_case(assay_info: Dict[str, Any], round_num: int) -> Tuple[str, str]:
    """Create an assay case fixture."""
    case_id = assay_info["case_id"]
    chembl_id = assay_info["chembl_id"]
    description = assay_info["description"]

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

    documentation_content = f"Assay: {chembl_id}\n\n{description}\n"

    (fixture_dir / "source.sql").write_text(sql_content)
    (fixture_dir / "sqlite.sql").write_text(sql_content)
    (fixture_dir / "uq.txt").write_text(uq_content)
    (fixture_dir / "benchmark_spec_uq.txt").write_text(benchmark_spec_uq)
    (fixture_dir / "metadata.json").write_text(json.dumps(metadata_content, indent=2))
    (fixture_dir / "documentation.txt").write_text(documentation_content)

    return str(fixture_dir), case_id

def create_document_case(document_info: Dict[str, Any], round_num: int) -> Tuple[str, str]:
    """Create a document case fixture."""
    case_id = document_info["case_id"]
    chembl_id = document_info["chembl_id"]
    title = document_info["title"]

    fixture_dir = FIXTURES_BASE / f"web_scrape{round_num}" / case_id
    fixture_dir.mkdir(parents=True, exist_ok=True)

    sql_content = f"""SELECT DISTINCT
    MOLECULE_DICTIONARY.chembl_id,
    COMPOUND_RECORDS.compound_name,
    COMPOUND_STRUCTURES.canonical_smiles
FROM DOCS
    JOIN COMPOUND_RECORDS ON COMPOUND_RECORDS.doc_id == DOCS.doc_id
    JOIN MOLECULE_DICTIONARY
        ON MOLECULE_DICTIONARY.molregno == COMPOUND_RECORDS.molregno
    JOIN COMPOUND_STRUCTURES
        ON COMPOUND_RECORDS.molregno == COMPOUND_STRUCTURES.molregno
WHERE DOCS.chembl_id = '{chembl_id}'
ORDER BY MOLECULE_DICTIONARY.chembl_id
"""

    uq_content = f"Retrieve distinct chembl_id, compound_name, and canonical_smiles for molecules mentioned in document {chembl_id}."

    metadata_content = {
        "id": case_id,
        "source_title": f"chembl_downloader get_document_molecule_sql instantiated for {chembl_id}",
        "source_url": "https://github.com/cthoyt/chembl-downloader/blob/main/src/chembl_downloader/queries.py",
        "uq_origin": "explicit_from_function_comment_and_parameter",
        "uq_path": f"tests/fixtures/web_scrape{round_num}/{case_id}/uq.txt",
        "sql_path": f"tests/fixtures/web_scrape{round_num}/{case_id}/source.sql",
        "documentation_path": f"tests/fixtures/web_scrape{round_num}/{case_id}/documentation.txt"
    }

    documentation_content = f"Document: {chembl_id}\n\n{title}\n"

    (fixture_dir / "source.sql").write_text(sql_content)
    (fixture_dir / "sqlite.sql").write_text(sql_content)
    (fixture_dir / "uq.txt").write_text(uq_content)
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
    print("Expanding ChEMBL Benchmark: 95 -> 200+ cases")
    print("=" * 80)

    if not DB_PATH.exists():
        print(f"\nERROR: Database not found at {DB_PATH}")
        return

    print(f"\n📁 Database: {DB_PATH}")
    print(f"📋 Existing cases: {len(EXISTING_IDS)}")

    # Find new cases
    print("\n🔍 Finding new cases...")
    targets = get_unused_human_targets(25)
    assays = get_unused_assays(15)
    documents = get_unused_documents(15)

    print(f"   ✓ {len(targets)} new target IC50 cases")
    print(f"   ✓ {len(assays)} new assay cases")
    print(f"   ✓ {len(documents)} new document cases")
    print(f"   Total: {len(targets) + len(assays) + len(documents)} new cases")

    # Organize by rounds
    round_num = 18
    created_cases = []

    # Round 18-19: Targets (25 cases)
    print(f"\n🎯 Round {round_num}-19: Creating {len(targets)} target IC50 cases...")
    for i, target in enumerate(targets):
        fixture_dir, case_id = create_target_case(target, round_num + (i // 15))
        print(f"   [{i+1}/{len(targets)}] {case_id} ({target['molecule_count']} molecules)")

        if materialize_case(fixture_dir, DB_PATH):
            print(f"      ✓ Materialized")
            created_cases.append({
                "case_id": case_id,
                "round": round_num + (i // 15),
                "type": "target"
            })
        else:
            print(f"      ✗ Failed")
            import shutil
            shutil.rmtree(fixture_dir, ignore_errors=True)

    # Round 20-21: Assays (15 cases)
    round_num = 20
    print(f"\n🧪 Round {round_num}: Creating {len(assays)} assay cases...")
    for i, assay in enumerate(assays):
        fixture_dir, case_id = create_assay_case(assay, round_num)
        print(f"   [{i+1}/{len(assays)}] {case_id} ({assay['activity_count']} activities)")

        if materialize_case(fixture_dir, DB_PATH):
            print(f"      ✓ Materialized")
            created_cases.append({
                "case_id": case_id,
                "round": round_num,
                "type": "assay"
            })
        else:
            print(f"      ✗ Failed")
            import shutil
            shutil.rmtree(fixture_dir, ignore_errors=True)

    # Round 21-22: Documents (15 cases)
    round_num = 21
    print(f"\n📄 Round {round_num}: Creating {len(documents)} document cases...")
    for i, doc in enumerate(documents):
        fixture_dir, case_id = create_document_case(doc, round_num + (i // 10))
        print(f"   [{i+1}/{len(documents)}] {case_id} ({doc['molecule_count']} molecules)")

        if materialize_case(fixture_dir, DB_PATH):
            print(f"      ✓ Materialized")
            created_cases.append({
                "case_id": case_id,
                "round": round_num + (i // 10),
                "type": "document"
            })
        else:
            print(f"      ✗ Failed")
            import shutil
            shutil.rmtree(fixture_dir, ignore_errors=True)

    # Summary
    print("\n" + "=" * 80)
    print(f"✅ SUCCESS! Created {len(created_cases)} new cases")
    print(f"   Previous total: 95 cases")
    print(f"   New total: {95 + len(created_cases)} cases")
    print("=" * 80)

    # Save case list
    output_file = BASE_DIR / "scripts" / "new_cases_rounds_18_22.json"
    with open(output_file, 'w') as f:
        json.dump(created_cases, f, indent=2)
    print(f"\n📝 Case list saved to {output_file}")

    # Print cases by round for promotion
    rounds = {}
    for case in created_cases:
        r = case['round']
        if r not in rounds:
            rounds[r] = []
        rounds[r].append(case['case_id'])

    print(f"\n📦 Cases by round:")
    for r in sorted(rounds.keys()):
        print(f"   Round {r}: {len(rounds[r])} cases")

if __name__ == "__main__":
    main()
