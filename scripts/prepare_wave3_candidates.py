#!/usr/bin/env python3
"""
Prepare wave3 candidates for corpus expansion.
Focus: human_target_molecule_smiles, target_activity_with_pubmed_or_doi, document
Goal: ~200-250 new cases to bring total from 762 to ~1000
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import polars as pl

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "database/latest/chembl_36/chembl_36_sqlite/chembl_36.db"


def query_human_target_molecule_candidates(limit: int = 100) -> list[dict[str, Any]]:
    """Find human targets with good activity counts for molecule_smiles exports."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Find human SINGLE PROTEIN targets with decent activity counts
    # Exclude targets already used in wave2
    used_targets = {
        "CHEMBL1075138", "CHEMBL5391", "CHEMBL1741193", "CHEMBL1293258",
        "CHEMBL203", "CHEMBL1827", "CHEMBL1824", "CHEMBL240", "CHEMBL220",
        "CHEMBL1862", "CHEMBL1828", "CHEMBL1825", "CHEMBL189", "CHEMBL211",
        "CHEMBL279", "CHEMBL2207", "CHEMBL239", "CHEMBL244", "CHEMBL233",
        "CHEMBL5516", "CHEMBL1829", "CHEMBL5368", "CHEMBL228", "CHEMBL2117",
    }

    sql = """
    SELECT DISTINCT
        td.chembl_id AS target_chembl_id,
        td.pref_name AS target_name,
        COUNT(DISTINCT md.molregno) AS molecule_count
    FROM target_dictionary td
    JOIN assays a ON a.tid = td.tid
    JOIN activities act ON act.assay_id = a.assay_id
    JOIN molecule_dictionary md ON act.molregno = md.molregno
    JOIN compound_structures cs ON md.molregno = cs.molregno
    WHERE td.organism = 'Homo sapiens'
      AND td.target_type = 'SINGLE PROTEIN'
      AND a.assay_organism = 'Homo sapiens'
      AND cs.canonical_smiles IS NOT NULL
      AND td.chembl_id NOT IN ({})
    GROUP BY td.chembl_id, td.pref_name
    HAVING molecule_count BETWEEN 50 AND 20000
    ORDER BY molecule_count DESC
    LIMIT ?
    """.format(",".join(f"'{t}'" for t in used_targets))

    cur.execute(sql, [limit])
    results = []
    for row in cur.fetchall():
        target_chembl_id, target_name, molecule_count = row
        # Build case_id from target_name (clean special chars)
        name_clean = target_name.lower().replace("/", "_").replace(" ", "_").replace("(", "").replace(")", "").replace("'", "").replace("-", "_").replace("[", "").replace("]", "").replace(",", "_")[:50]
        case_id = f"human_{name_clean}_molecule_smiles"
        results.append({
            "case_id": case_id,
            "template": "human_target_molecule_smiles_export",
            "target_chembl_id": target_chembl_id,
            "target_name": target_name,
            "row_count": molecule_count,
            "sql": f"""SELECT DISTINCT md.chembl_id AS compound_chembl_id, cs.canonical_smiles
FROM molecule_dictionary md
JOIN activities act ON act.molregno = md.molregno
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN compound_structures cs ON cs.molregno = md.molregno
WHERE a.assay_organism = 'Homo sapiens'
  AND td.chembl_id = '{target_chembl_id}'""",
        })

    conn.close()
    return results


def query_target_ic50_pubmed_doi_candidates(limit: int = 80) -> list[dict[str, Any]]:
    """Find targets with good IC50 activity counts provenance."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Exclude targets already used in wave2
    used_targets = {
        "CHEMBL279", "CHEMBL203", "CHEMBL220", "CHEMBL1862", "CHEMBL233",
        "CHEMBL240", "CHEMBL1824", "CHEMBL189", "CHEMBL1825", "CHEMBL2207",
        "CHEMBL5516", "CHEMBL1829", "CHEMBL211", "CHEMBL228", "CHEMBL239",
        "CHEMBL2117", "CHEMBL244", "CHEMBL1827", "CHEMBL1828", "CHEMBL2364",
        "CHEMBL203", "CHEMBL220", "CHEMBL1862", "CHEMBL279",
    }

    sql = """
    SELECT DISTINCT
        td.chembl_id AS target_chembl_id,
        td.pref_name AS target_name,
        COUNT(DISTINCT act.activity_id) AS activity_count
    FROM target_dictionary td
    JOIN assays a ON a.tid = td.tid
    JOIN activities act ON act.assay_id = a.assay_id
    JOIN docs d ON act.doc_id = d.doc_id
    JOIN molecule_dictionary md ON act.molregno = md.molregno
    JOIN compound_structures cs ON md.molregno = cs.molregno
    WHERE td.organism = 'Homo sapiens'
      AND td.target_type = 'SINGLE PROTEIN'
      AND a.assay_organism = 'Homo sapiens'
      AND act.standard_type = 'IC50'
      AND act.standard_units = 'nM'
      AND cs.canonical_smiles IS NOT NULL
      AND (d.pubmed_id IS NOT NULL OR d.doi IS NOT NULL)
      AND td.chembl_id NOT IN ({})
    GROUP BY td.chembl_id, td.pref_name
    HAVING activity_count BETWEEN 100 AND 15000
    ORDER BY activity_count DESC
    LIMIT ?
    """.format(",".join(f"'{t}'" for t in used_targets))

    cur.execute(sql, [limit])
    results = []
    for row in cur.fetchall():
        target_chembl_id, target_name, activity_count = row
        name_clean = target_name.lower().replace("/", "_").replace(" ", "_").replace("(", "").replace(")", "").replace("'", "").replace("-", "_").replace("[", "").replace("]", "").replace(",", "_")[:50]
        case_id = f"target_ic50_with_pubmed_or_doi_{name_clean}"
        results.append({
            "case_id": case_id,
            "template": "target_activity_with_pubmed_or_doi",
            "target_chembl_id": target_chembl_id,
            "target_name": target_name,
            "row_count": activity_count,
            "sql": f"""SELECT DISTINCT
  md.chembl_id AS compound_chembl_id,
  cs.canonical_smiles AS canonical_smiles,
  cr.compound_key AS compound_key,
  COALESCE(CAST(d.pubmed_id AS TEXT), d.doi) AS pubmed_id_or_doi,
  a.description AS assay_description,
  act.standard_type AS standard_type,
  act.standard_relation AS standard_relation,
  act.standard_value AS standard_value,
  act.standard_units AS standard_units,
  act.activity_comment AS activity_comment,
  td.chembl_id AS target_chembl_id,
  td.pref_name AS target_name,
  td.organism AS target_organism
FROM activities act INDEXED BY fk_act_assay_id
JOIN molecule_dictionary md ON act.molregno = md.molregno
JOIN compound_structures cs ON md.molregno = cs.molregno
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN docs d ON act.doc_id = d.doc_id
LEFT JOIN compound_records cr ON act.record_id = cr.record_id
WHERE act.assay_id IN (
    SELECT a2.assay_id
    FROM assays a2
    JOIN target_dictionary td2 ON a2.tid = td2.tid
    WHERE td2.chembl_id = '{target_chembl_id}'
      AND td2.target_type = 'SINGLE PROTEIN'
      AND td2.organism = 'Homo sapiens'
)
  AND act.standard_type = 'IC50'
  AND act.standard_units = 'nM'
  AND td.chembl_id = '{target_chembl_id}'
  AND td.target_type = 'SINGLE PROTEIN'
  AND td.organism = 'Homo sapiens'
  AND cs.canonical_smiles IS NOT NULL
  AND (d.pubmed_id IS NOT NULL OR d.doi IS NOT NULL)""",
        })

    conn.close()
    return results


def query_document_candidates(limit: int = 120) -> list[dict[str, Any]]:
    """Find documents with good molecule counts."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    sql = """
    SELECT
        d.chembl_id AS doc_chembl_id,
        COUNT(DISTINCT md.molregno) AS molecule_count
    FROM docs d
    JOIN compound_records cr ON cr.doc_id = d.doc_id
    JOIN molecule_dictionary md ON cr.molregno = md.molregno
    WHERE d.doc_type = 'PUBLICATION'
      AND d.chembl_id IS NOT NULL
    GROUP BY d.chembl_id
    HAVING molecule_count BETWEEN 50 AND 5000
    ORDER BY molecule_count DESC
    LIMIT ?
    """

    cur.execute(sql, [limit])
    results = []
    for row in cur.fetchall():
        doc_chembl_id, molecule_count = row
        case_id = f"chembl_downloader_document_molecules_{doc_chembl_id.lower()}"
        results.append({
            "case_id": case_id,
            "template": "document_molecules_export",
            "doc_chembl_id": doc_chembl_id,
            "row_count": molecule_count,
            "sql": f"""SELECT
    md.chembl_id AS molecule_chembl_id,
    md.pref_name AS molecule_name,
    md.max_phase AS max_phase,
    md.molecule_type AS molecule_type,
    cs.canonical_smiles AS canonical_smiles
FROM docs d
JOIN compound_records cr ON cr.doc_id = d.doc_id
JOIN molecule_dictionary md ON cr.molregno = md.molregno
LEFT JOIN compound_structures cs ON md.molregno = cs.molregno
WHERE d.chembl_id = '{doc_chembl_id}'
ORDER BY md.chembl_id""",
        })

    conn.close()
    return results


def main() -> None:
    import json

    print("Preparing wave3 candidates...")

    # Query candidates from each family
    print("Querying human_target_molecule_smiles candidates...")
    human_mol = query_human_target_molecule_candidates(limit=50)

    print("Querying target_ic50_with_pubmed_or_doi candidates...")
    target_ic50 = query_target_ic50_pubmed_doi_candidates(limit=80)

    print("Querying document candidates...")
    documents = query_document_candidates(limit=120)

    all_candidates = human_mol + target_ic50 + documents

    output = {
        "total_candidates": len(all_candidates),
        "template_counts": {
            "human_target_molecule_smiles_export": len(human_mol),
            "target_activity_with_pubmed_or_doi": len(target_ic50),
            "document_molecules_export": len(documents),
        },
        "candidates": all_candidates,
    }

    output_path = Path(__file__).parent.parent / "experiments" / "wave3_candidates_v4.9.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nWrote {len(all_candidates)} candidates to {output_path}")
    print(f"  human_target_molecule_smiles_export: {len(human_mol)}")
    print(f"  target_activity_with_pubmed_or_doi: {len(target_ic50)}")
    print(f"  document_molecules_export: {len(documents)}")


if __name__ == "__main__":
    main()
