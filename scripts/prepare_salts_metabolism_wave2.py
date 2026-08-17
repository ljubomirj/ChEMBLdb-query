#!/usr/bin/env python3
"""Generate salts and metabolism wave2 cases using grounded SQL + PB_SQL + PB_UP.

Salts:  parameterized by parent_chembl_id + target_chembl_id (from molecule_hierarchy).
Metabolism: parameterized by organism, pathway_key, or enzyme_name.

Output: experiments/{salts,metabolism}_wave2_candidates_v4.9.json
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / 'database/latest/chembl_36/chembl_36_sqlite/chembl_36.db'
REGISTRY_PATH = REPO_ROOT / 'cases/registries/archive/web_scrape_hq_cases.json'


def query_db(sql: str) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(sql)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        conn.close()


def count_rows(sql: str) -> int:
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(sql)
        n = len(cur.fetchall())
        conn.close()
        return n
    except Exception:
        return 0


def load_existing_ids() -> set[str]:
    registry = json.loads(REGISTRY_PATH.read_text())
    return {entry['id'] for entry in registry}


# ─── Salts SQL template ───

def salts_sql(parent_chembl_id: str, target_chembl_id: str) -> str:
    return f"""SELECT m.chembl_id AS compound_chembl_id,
       s.canonical_smiles,
       r.compound_key,
       COALESCE(CAST(d.pubmed_id AS TEXT), d.doi) AS pubmed_id_or_doi,
       a.description AS assay_description,
       act.standard_type,
       act.standard_relation,
       act.standard_value,
       act.standard_units,
       act.activity_comment,
       t.chembl_id AS target_chembl_id,
       t.pref_name AS target_name,
       t.organism AS target_organism
FROM molecule_dictionary m
LEFT JOIN compound_structures s ON s.molregno = m.molregno
JOIN compound_records r ON m.molregno = r.molregno
JOIN docs d ON r.doc_id = d.doc_id
JOIN activities act ON r.record_id = act.record_id
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary t ON a.tid = t.tid
WHERE t.chembl_id = '{target_chembl_id}'
  AND m.chembl_id IN (
    SELECT DISTINCT m1.chembl_id
    FROM molecule_dictionary m1
    JOIN molecule_hierarchy mh ON mh.molregno = m1.molregno
    JOIN molecule_dictionary m2 ON mh.parent_molregno = m2.molregno
    WHERE m2.chembl_id = '{parent_chembl_id}'
  )
  AND act.standard_type = 'IC50'
  AND act.standard_units = 'nM'"""


def gen_salts_candidates(limit: int = 80) -> list[dict]:
    existing = load_existing_ids()
    # Get all parent/target combos with enough IC50 salt activities
    rows = query_db("""SELECT md_parent.chembl_id AS parent_id,
       md_parent.pref_name AS parent_name,
       td.chembl_id AS target_id,
       td.pref_name AS target_name,
       COUNT(DISTINCT act.molregno) AS act_count
FROM molecule_dictionary md_parent
JOIN molecule_hierarchy mh ON mh.parent_molregno = md_parent.molregno
JOIN molecule_dictionary md_child ON mh.molregno = md_child.molregno
JOIN activities act ON md_child.molregno = act.molregno
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
WHERE act.standard_type = 'IC50'
  AND act.standard_units = 'nM'
  AND act.standard_value IS NOT NULL
  AND act.standard_relation = '='
GROUP BY md_parent.chembl_id, td.chembl_id
HAVING act_count >= 5
ORDER BY act_count DESC""")
    candidates = []
    for r in rows:
        pname = (r['parent_name'] or r['parent_id']).lower().replace(' ', '_').replace('-','_')[:30]
        tname = (r['target_name'] or r['target_id']).lower().replace(' ', '_').replace('-','_')[:30]
        slug = f"{pname}_{tname}_ic50_salts"
        cid = f"{slug}"
        if cid in existing:
            continue
        sql = salts_sql(r['parent_id'], r['target_id'])
        rc = count_rows(sql)
        if 5 <= rc <= 50000:
            candidates.append({
                'case_id': cid,
                'template': 'faq_parent_and_salts_activity_provenance',
                'parent_chembl_id': r['parent_id'],
                'parent_name': r['parent_name'],
                'target_chembl_id': r['target_id'],
                'target_name': r['target_name'],
                'row_count': rc,
                'sql': sql,
            })
        if len(candidates) >= limit:
            break
    return candidates


# ─── Metabolism SQL templates ───

def metabolism_by_organism_sql(organism: str) -> str:
    escaped = organism.replace("'", "''")
    return f"""SELECT cs.canonical_smiles,
       cr.compound_name AS substrate_compound_name,
       md.pref_name AS parent_compound_name,
       m.met_conversion,
       m.pathway_key,
       m.organism,
       m.enzyme_name
FROM metabolism m
JOIN compound_records cr ON m.substrate_record_id = cr.record_id
JOIN compound_structures cs ON cr.molregno = cs.molregno
LEFT JOIN molecule_hierarchy mh ON cr.molregno = mh.molregno
LEFT JOIN molecule_dictionary md ON mh.parent_molregno = md.molregno
WHERE m.organism = '{escaped}'
  AND cs.canonical_smiles IS NOT NULL
LIMIT 200"""


def metabolism_by_enzyme_sql(enzyme_name: str) -> str:
    escaped = enzyme_name.replace("'", "''")
    return f"""SELECT cs.canonical_smiles,
       cr.compound_name AS substrate_compound_name,
       md.pref_name AS parent_compound_name,
       m.met_conversion,
       m.pathway_key,
       m.organism,
       m.enzyme_name
FROM metabolism m
JOIN compound_records cr ON m.substrate_record_id = cr.record_id
JOIN compound_structures cs ON cr.molregno = cs.molregno
LEFT JOIN molecule_hierarchy mh ON cr.molregno = mh.molregno
LEFT JOIN molecule_dictionary md ON mh.parent_molregno = md.molregno
WHERE m.enzyme_name = '{escaped}'
  AND cs.canonical_smiles IS NOT NULL
LIMIT 200"""


def metabolism_first200_sql() -> str:
    return """SELECT cs.canonical_smiles,
       cr.compound_name AS substrate_compound_name,
       md.pref_name AS parent_compound_name,
       m.met_conversion,
       m.pathway_key,
       m.organism,
       m.enzyme_name
FROM metabolism m
JOIN compound_records cr ON m.substrate_record_id = cr.record_id
JOIN compound_structures cs ON cr.molregno = cs.molregno
LEFT JOIN molecule_hierarchy mh ON cr.molregno = mh.molregno
LEFT JOIN molecule_dictionary md ON mh.parent_molregno = md.molregno
WHERE cs.canonical_smiles IS NOT NULL
LIMIT 200"""


def gen_metabolism_candidates(limit: int = 50) -> list[dict]:
    existing = load_existing_ids()
    candidates = []

    # By organism (Homo sapiens, Rattus norvegicus, etc.)
    organisms = query_db("""SELECT organism, COUNT(*) as cnt
FROM metabolism GROUP BY organism
HAVING organism IS NOT NULL AND organism != ''
ORDER BY cnt DESC LIMIT 15""")
    for r in organisms:
        org = r['organism']
        slug = f"metabolism_{org.lower().replace(' ','_')[:30]}_first200"
        if slug in existing:
            continue
        sql = metabolism_by_organism_sql(org)
        rc = count_rows(sql)
        if 5 <= rc <= 50000:
            candidates.append({
                'case_id': slug,
                'template': 'metabolism_first_n_with_parent_name_enrichment',
                'description': f'First 200 metabolism records for organism={org}',
                'organism': org,
                'row_count': rc,
                'sql': sql,
            })

    # By enzyme (CYP3A4, CYP2C9, etc.)
    enzymes = query_db("""SELECT enzyme_name, COUNT(*) as cnt
FROM metabolism
WHERE enzyme_name IS NOT NULL AND enzyme_name != ''
GROUP BY enzyme_name
HAVING cnt >= 10
ORDER BY cnt DESC LIMIT 20""")
    for r in enzymes:
        enz = r['enzyme_name']
        slug = f"metabolism_enzyme_{enz.lower().replace(' ','_').replace('/','_')[:30]}_first200"
        if slug in existing:
            continue
        sql = metabolism_by_enzyme_sql(enz)
        rc = count_rows(sql)
        if 5 <= rc <= 50000:
            candidates.append({
                'case_id': slug,
                'template': 'metabolism_first_n_with_parent_name_enrichment',
                'description': f'First 200 metabolism records for enzyme={enz}',
                'enzyme_name': enz,
                'row_count': rc,
                'sql': sql,
            })

    return candidates[:limit]


def main() -> None:
    print("=== Salts Wave2 Candidates ===", flush=True)
    salts = gen_salts_candidates(limit=80)
    print(f"Found {len(salts)} salts candidates", flush=True)
    output = {'total_candidates': len(salts), 'candidates': salts}
    out_path = REPO_ROOT / 'experiments/salts_wave2_candidates_v4.9.json'
    out_path.write_text(json.dumps(output, indent=2) + '\n')
    # Report
    (REPO_ROOT / 'experiments/salts_wave2_candidates_v4.9.md').write_text(
        f"# Salts Wave2 Candidates\n\n- Total: {len(salts)}\n\n" +
        "\n".join(f"- `{c['case_id']}` rows={c['row_count']}" for c in salts) + "\n")

    print("\n=== Metabolism Wave2 Candidates ===", flush=True)
    metab = gen_metabolism_candidates(limit=50)
    print(f"Found {len(metab)} metabolism candidates", flush=True)
    output = {'total_candidates': len(metab), 'candidates': metab}
    out_path = REPO_ROOT / 'experiments/metabolism_wave2_candidates_v4.9.json'
    out_path.write_text(json.dumps(output, indent=2) + '\n')
    (REPO_ROOT / 'experiments/metabolism_wave2_candidates_v4.9.md').write_text(
        f"# Metabolism Wave2 Candidates\n\n- Total: {len(metab)}\n\n" +
        "\n".join(f"- `{c['case_id']}` rows={c['row_count']}" for c in metab) + "\n")


if __name__ == '__main__':
    main()
