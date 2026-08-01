#!/usr/bin/env python3
"""
Generate new ChEMBL text-to-SQL cases to expand benchmark from 95 to 200+ cases.

This script:
1. Queries ChEMBL database for good targets/assays/documents
2. Creates fixtures with proper structure
3. Generates SQL and executes to create ground truth
4. Properly escapes CSV to avoid ragged lines
"""

import json
import sqlite3
import subprocess
import os
from pathlib import Path
from typing import List, Dict, Any

# Configuration
DB_PATH = Path("/Users/ljubomir/ChEMBLdb-query/database/latest/chembl_36/chembl_36_sqlite/chembl_36.db")
FIXTURES_BASE = Path("/Users/ljubomir/ChEMBLdb-query/tests/fixtures")
CASES_FILE = Path("/Users/ljubomir/ChEMBLdb-query/tests/cases/web_scrape_hq_cases.json")

# Existing cases to avoid duplicates
with open(CASES_FILE) as f:
    EXISTING_IDS = {case["id"] for case in json.load(f)}

def get_unused_human_targets(limit: int = 30) -> List[Dict[str, Any]]:
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
    HAVING molecule_count >= 10
    ORDER BY molecule_count DESC
    LIMIT ?
    """

    cursor.execute(query, (limit * 3,))  # Get more than needed to filter duplicates
    results = []

    for row in cursor.fetchall():
        chembl_id, pref_name, assay_count, molecule_count = row

        # Skip if already used
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

def get_unused_assays(limit: int = 20) -> List[Dict[str, Any]]:
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
            "description": description[:100],  # Truncate long descriptions
            "molecule_count": molecule_count,
            "activity_count": activity_count,
            "case_id": case_id
        })

        if len(results) >= limit:
            break

    conn.close()
    return results

def get_unused_documents(limit: int = 20) -> List[Dict[str, Any]]:
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
            "title": title[:100] if title else "Unknown",
            "molecule_count": molecule_count,
            "case_id": case_id
        })

        if len(results) >= limit:
            break

    conn.close()
    return results

def create_target_case(target_info: Dict[str, Any], round_num: int) -> str:
    """Create a target IC50 case fixture."""
    case_id = target_info["case_id"]
    chembl_id = target_info["chembl_id"]
    pref_name = target_info["pref_name"]

    fixture_dir = FIXTURES_BASE / f"web_scrape{round_num}" / case_id
    fixture_dir.mkdir(parents=True, exist_ok=True)

    # Create SQL
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
ORDER BY molecule_chembl_id
"""

    benchmark_spec_uq = (
        f"Retrieve assay_chembl_id, target_type, tax_id, canonical_smiles, molecule_chembl_id, "
        f"standard_type, and pchembl_value for IC50 activities on human single protein target "
        f"{chembl_id} ({pref_name}) with pchembl_value not null and standard_relation '='."
    )
    uq_content = (
        f"Show IC50 activity rows with pChEMBL values for the human single-protein target "
        f"{chembl_id} ({pref_name}). Return assay ChEMBL ID, target type, tax_id, canonical "
        f"SMILES, molecule ChEMBL ID, standard type, and pChEMBL value.\n"
    )

    # Create metadata
    metadata_content = json.dumps({
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
    }, indent=2)

    # Create documentation
    documentation_content = f"""Target: {chembl_id} ({pref_name})

This is a human single protein target with IC50 activities.
Query retrieves all bioactivity data with pchembl_value.
"""

    # Write files
    (fixture_dir / "source.sql").write_text(sql_content)
    (fixture_dir / "sqlite.sql").write_text(sql_content)
    (fixture_dir / "uq.txt").write_text(uq_content)
    (fixture_dir / "benchmark_spec_uq.txt").write_text(benchmark_spec_uq)
    (fixture_dir / "metadata.json").write_text(metadata_content)
    (fixture_dir / "documentation.txt").write_text(documentation_content)

    return str(fixture_dir)

def create_assay_case(assay_info: Dict[str, Any], round_num: int) -> str:
    """Create an assay case fixture."""
    case_id = assay_info["case_id"]
    chembl_id = assay_info["chembl_id"]
    description = assay_info["description"]

    fixture_dir = FIXTURES_BASE / f"web_scrape{round_num}" / case_id
    fixture_dir.mkdir(parents=True, exist_ok=True)

    # Create SQL
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
        f"({description}) where standard_value is not null and standard_relation '='."
    )
    uq_content = (
        f"For assay {chembl_id}, list compounds with exact activity measurements. "
        f"Return canonical SMILES, molecule ChEMBL ID, standard type, standard relation, "
        f"standard value, and standard units.\n"
    )

    # Create metadata
    metadata_content = json.dumps({
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
    }, indent=2)

    # Create documentation
    documentation_content = f"""Assay: {chembl_id}

{description}
"""

    # Write files
    (fixture_dir / "source.sql").write_text(sql_content)
    (fixture_dir / "sqlite.sql").write_text(sql_content)
    (fixture_dir / "uq.txt").write_text(uq_content)
    (fixture_dir / "benchmark_spec_uq.txt").write_text(benchmark_spec_uq)
    (fixture_dir / "metadata.json").write_text(metadata_content)
    (fixture_dir / "documentation.txt").write_text(documentation_content)

    return str(fixture_dir)

def create_document_case(document_info: Dict[str, Any], round_num: int) -> str:
    """Create a document case fixture."""
    case_id = document_info["case_id"]
    chembl_id = document_info["chembl_id"]
    title = document_info["title"]

    fixture_dir = FIXTURES_BASE / f"web_scrape{round_num}" / case_id
    fixture_dir.mkdir(parents=True, exist_ok=True)

    # Create SQL
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

    # Create UQ
    uq_content = f"""Retrieve distinct chembl_id, compound_name, and canonical_smiles for molecules mentioned in document {chembl_id} ({title}).
"""

    # Create metadata
    metadata_content = json.dumps({
        "id": case_id,
        "source_title": f"chembl_downloader get_document_molecule_sql instantiated for {chembl_id}",
        "source_url": "https://github.com/cthoyt/chembl-downloader/blob/main/src/chembl_downloader/queries.py",
        "uq_origin": "explicit_from_function_comment_and_parameter",
        "uq_path": f"tests/fixtures/web_scrape{round_num}/{case_id}/uq.txt",
        "sql_path": f"tests/fixtures/web_scrape{round_num}/{case_id}/source.sql",
        "documentation_path": f"tests/fixtures/web_scrape{round_num}/{case_id}/documentation.txt"
    }, indent=2)

    # Create documentation
    documentation_content = f"""Document: {chembl_id}

{title}
"""

    # Write files
    (fixture_dir / "source.sql").write_text(sql_content)
    (fixture_dir / "sqlite.sql").write_text(sql_content)
    (fixture_dir / "uq.txt").write_text(uq_content)
    (fixture_dir / "metadata.json").write_text(metadata_content)
    (fixture_dir / "documentation.txt").write_text(documentation_content)

    return str(fixture_dir)

def execute_case(fixture_dir: str) -> bool:
    """Execute SQL and create ground truth CSV."""
    try:
        # Run the test script
        result = subprocess.run(
            ["uv", "run", "python", "-m", "tests.runners.execute_case", fixture_dir],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Error executing {fixture_dir}: {e}")
        return False

def main():
    """Main generation workflow."""
    print("🔍 Finding unused targets, assays, and documents...")

    # Start from web_scrape18
    base_round = 18

    # Generate new cases
    print(f"\n📊 Finding 25 new human target IC50 cases...")
    targets = get_unused_human_targets(25)
    print(f"   Found {len(targets)} targets")

    print(f"\n🧪 Finding 15 new assay cases...")
    assays = get_unused_assays(15)
    print(f"   Found {len(assays)} assays")

    print(f"\n📄 Finding 15 new document cases...")
    documents = get_unused_documents(15)
    print(f"   Found {len(documents)} documents")

    all_cases = [
        ("target", targets, create_target_case),
        ("assay", assays, create_assay_case),
        ("document", documents, create_document_case),
    ]

    round_num = base_round
    created_cases = []

    for case_type, case_list, creator_func in all_cases:
        print(f"\n🔨 Creating {len(case_list)} {case_type} cases...")
        for i, case_info in enumerate(case_list):
            fixture_dir = creator_func(case_info, round_num)
            print(f"   [{i+1}/{len(case_list)}] Created {case_info['case_id']}")

            # Execute to create ground truth
            print(f"      Executing SQL...")
            success = execute_case(fixture_dir)

            if success:
                print(f"      ✓ Success")
                created_cases.append(case_info['case_id'])
            else:
                print(f"      ✗ Failed (check logs)")
                # Clean up failed case
                import shutil
                shutil.rmtree(fixture_dir, ignore_errors=True)

        # Increment round for each type
        round_num += 1

    print(f"\n✅ Successfully created {len(created_cases)} new cases!")
    print(f"📁 Cases created in web_scrape{base_round}-web_scrape{round_num-1}")

    # Save list of created cases
    output_file = Path("/Users/ljubomir/ChEMBLdb-query/scripts/new_cases_list.txt")
    output_file.write_text("\n".join(created_cases))
    print(f"📝 Case IDs saved to {output_file}")

if __name__ == "__main__":
    main()
