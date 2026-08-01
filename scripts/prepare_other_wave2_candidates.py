#!/usr/bin/env python3
"""Prepare ~121 candidates for the 'other' family wave 2 expansion.

Queries the ChEMBL database for parameterizable candidates across 7 template types.
Validates each candidate produces 5-50000 rows.

Output: experiments/other_wave2_candidates_v4.9.json
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / 'database/latest/chembl_36/chembl_36_sqlite/chembl_36.db'
REGISTRY_PATH = REPO_ROOT / 'tests/cases/web_scrape_hq_cases.json'
OUTPUT_JSON = REPO_ROOT / 'experiments/other_wave2_candidates_v4.9.json'
OUTPUT_MD = REPO_ROOT / 'experiments/other_wave2_candidates_v4.9.md'

# Existing case IDs to exclude
EXISTING_IDS: set[str] = set()


def load_existing_ids() -> None:
    registry = json.loads(REGISTRY_PATH.read_text())
    for entry in registry:
        EXISTING_IDS.add(entry['id'])


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
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(sql)
        return len(cur.fetchall())
    except Exception:
        return 0
    finally:
        conn.close()


def exec_sql(sql: str) -> int:
    """Execute SQL and return row count. Returns -1 on error."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(sql)
        n = len(cur.fetchall())
        conn.close()
        return n
    except Exception:
        return -1


# ─── Template SQL generators ───

def sql_human_target_molecule_smiles(target_chembl_id: str) -> str:
    return f"""SELECT DISTINCT md.chembl_id AS compound_chembl_id, cs.canonical_smiles
FROM molecule_dictionary md
JOIN activities act ON act.molregno = md.molregno
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
JOIN compound_structures cs ON cs.molregno = md.molregno
WHERE a.assay_organism = 'Homo sapiens'
  AND td.chembl_id = '{target_chembl_id}'"""


def sql_target_activity_pubmed_doi(target_chembl_id: str) -> str:
    return f"""SELECT DISTINCT
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
  AND (d.pubmed_id IS NOT NULL OR d.doi IS NOT NULL)"""


def sql_approved_drugs_by_indication(efo_term: str) -> str:
    escaped = efo_term.replace("'", "''")
    return f"""SELECT DISTINCT
  md.chembl_id AS chembl_id,
  md.pref_name AS pref_name,
  cs.canonical_smiles AS canonical_smiles,
  di.efo_id AS indication_curie,
  di.efo_term AS indication_label,
  di.max_phase_for_ind AS max_phase_for_ind
FROM molecule_dictionary md
JOIN compound_structures cs ON md.molregno = cs.molregno
JOIN drug_indication di ON md.molregno = di.molregno
WHERE md.max_phase = 4
  AND di.efo_term = '{escaped}'
  AND di.efo_id IS NOT NULL"""


def sql_target_descriptions_by_organism(organism: str) -> str:
    escaped = organism.replace("'", "''")
    return f"""SELECT DISTINCT td.pref_name AS target_description
FROM activities act
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
WHERE a.assay_organism = '{escaped}'"""


def sql_approved_drugs_by_action_type(action_type: str) -> str:
    escaped = action_type.replace("'", "''")
    return f"""SELECT DISTINCT
  md.chembl_id AS chembl_id,
  md.pref_name AS pref_name,
  cs.canonical_smiles AS canonical_smiles,
  md.max_phase AS max_phase,
  dm.mechanism_of_action AS mechanism_of_action,
  dm.action_type AS action_type,
  td.chembl_id AS target_chembl_id,
  td.pref_name AS target_name
FROM molecule_dictionary md
JOIN compound_structures cs ON md.molregno = cs.molregno
JOIN drug_mechanism dm ON md.molregno = dm.molregno
LEFT JOIN target_dictionary td ON dm.tid = td.tid
WHERE md.max_phase = 4
  AND dm.action_type = '{escaped}'"""


def sql_drug_indications_by_phase(max_phase: int) -> str:
    return f"""SELECT md.chembl_id,
       md.pref_name,
       di.mesh_id,
       di.mesh_heading,
       di.efo_id AS indication_curie,
       di.efo_term AS indication_label,
       di.max_phase_for_ind
FROM molecule_dictionary md
JOIN drug_indication di ON md.molregno = di.molregno
WHERE md.max_phase = 4
  AND di.max_phase_for_ind = {max_phase}"""


def sql_count_activities_by_target_type() -> str:
    return """SELECT td.target_type, COUNT(DISTINCT act.activity_id) AS activity_count
FROM activities act
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
WHERE act.standard_type = 'IC50'
  AND act.standard_units = 'nM'
GROUP BY td.target_type
ORDER BY activity_count DESC"""


def sql_molecules_by_phase_and_ro5() -> str:
    return """SELECT md.chembl_id, md.pref_name, cs.canonical_smiles,
       md.max_phase, md.ro5_passes
FROM molecule_dictionary md
JOIN compound_structures cs ON md.molregno = cs.molregno
WHERE md.max_phase = 4
  AND md.ro5_passes = 1
ORDER BY md.chembl_id"""


def sql_target_selectivity(target1_id: str, target1_name: str, target2_id: str, target2_name: str) -> str:
    return f"""SELECT DISTINCT md.chembl_id AS compound_chembl_id,
       cs.canonical_smiles,
       act1.standard_value AS ic50_target1_nM,
       act2.standard_value AS ic50_target2_nM
FROM activities act1
JOIN assays a1 ON act1.assay_id = a1.assay_id
JOIN target_dictionary td1 ON a1.tid = td1.tid
JOIN molecule_dictionary md ON act1.molregno = md.molregno
JOIN compound_structures cs ON md.molregno = cs.molregno
JOIN activities act2 ON act2.molregno = md.molregno
JOIN assays a2 ON act2.assay_id = a2.assay_id
JOIN target_dictionary td2 ON a2.tid = td2.tid
WHERE td1.chembl_id = '{target1_id}'
  AND td2.chembl_id = '{target2_id}'
  AND act1.standard_type = 'IC50' AND act1.standard_units = 'nM' AND act1.standard_relation = '='
  AND act2.standard_type = 'IC50' AND act2.standard_units = 'nM' AND act2.standard_relation = '='
  AND act1.standard_value IS NOT NULL AND act2.standard_value IS NOT NULL
  AND act1.standard_value < 1000 AND act2.standard_value > 10000"""


# ─── Candidate generators ───

def gen_human_target_molecule_smiles(limit: int = 30) -> list[dict]:
    """Find targets with good molecule/SMILES coverage, excluding existing."""
    existing_targets = {
        'CHEMBL284', 'CHEMBL203', 'CHEMBL2036', 'CHEMBL2780',
        'CHEMBL2354', 'CHEMBL2467', 'CHEMBL3880',
    }
    rows = query_db(f"""SELECT td.chembl_id, td.pref_name,
  COUNT(DISTINCT md.molregno) AS mol_count
FROM target_dictionary td
JOIN assays a ON a.tid = td.tid
JOIN activities act ON act.assay_id = a.assay_id
JOIN molecule_dictionary md ON act.molregno = md.molregno
JOIN compound_structures cs ON cs.molregno = md.molregno
WHERE td.organism = 'Homo sapiens'
  AND td.target_type = 'SINGLE PROTEIN'
  AND td.chembl_id NOT IN ({','.join(f"'{t}'" for t in existing_targets)})
GROUP BY td.chembl_id, td.pref_name
HAVING mol_count >= 20
ORDER BY mol_count DESC
LIMIT {limit}""")
    candidates = []
    for r in rows:
        cid = f"human_{r['pref_name'].lower().replace(' ', '_').replace('-', '_')[:40]}_molecule_smiles"
        if cid in EXISTING_IDS:
            continue
        sql = sql_human_target_molecule_smiles(r['chembl_id'])
        rc = count_rows(sql)
        if 5 <= rc <= 50000:
            candidates.append({
                'case_id': cid,
                'template': 'human_target_molecule_smiles_export',
                'target_chembl_id': r['chembl_id'],
                'target_name': r['pref_name'],
                'row_count': rc,
                'sql': sql,
            })
    return candidates


def gen_target_activity_pubmed_doi(limit: int = 25) -> list[dict]:
    existing_targets = {
        'CHEMBL284', 'CHEMBL203', 'CHEMBL1824', 'CHEMBL2971', 'CHEMBL1936',
    }
    rows = query_db(f"""SELECT td.chembl_id, td.pref_name,
  COUNT(DISTINCT act.activity_id) AS act_count
FROM target_dictionary td
JOIN assays a ON a.tid = td.tid
JOIN activities act ON act.assay_id = a.assay_id
JOIN docs d ON act.doc_id = d.doc_id
WHERE td.organism = 'Homo sapiens'
  AND td.target_type = 'SINGLE PROTEIN'
  AND act.standard_type = 'IC50'
  AND act.standard_units = 'nM'
  AND td.chembl_id NOT IN ({','.join(f"'{t}'" for t in existing_targets)})
  AND (d.pubmed_id IS NOT NULL OR d.doi IS NOT NULL)
GROUP BY td.chembl_id, td.pref_name
HAVING act_count >= 20
ORDER BY act_count DESC
LIMIT {limit}""")
    candidates = []
    for r in rows:
        name_slug = r['pref_name'].lower().replace(' ', '_').replace('-', '_')[:40]
        cid = f"target_ic50_with_pubmed_or_doi_{name_slug}"
        if cid in EXISTING_IDS:
            continue
        sql = sql_target_activity_pubmed_doi(r['chembl_id'])
        rc = count_rows(sql)
        if 5 <= rc <= 50000:
            candidates.append({
                'case_id': cid,
                'template': 'target_activity_with_pubmed_or_doi',
                'target_chembl_id': r['chembl_id'],
                'target_name': r['pref_name'],
                'row_count': rc,
                'sql': sql,
            })
    return candidates


def gen_approved_drugs_by_indication(limit: int = 20) -> list[dict]:
    rows = query_db(f"""SELECT di.efo_term, COUNT(DISTINCT md.molregno) AS drug_count
FROM drug_indication di
JOIN molecule_dictionary md ON di.molregno = md.molregno
WHERE md.max_phase = 4
  AND di.efo_term IS NOT NULL
GROUP BY di.efo_term
HAVING drug_count >= 3
ORDER BY drug_count DESC
LIMIT {limit}""")
    candidates = []
    for r in rows:
        slug = r['efo_term'].lower().replace(' ', '_').replace('-', '_')[:50]
        cid = f"approved_drugs_indication_{slug}"
        if cid in EXISTING_IDS:
            continue
        sql = sql_approved_drugs_by_indication(r['efo_term'])
        rc = count_rows(sql)
        if 5 <= rc <= 50000:
            candidates.append({
                'case_id': cid,
                'template': 'approved_drugs_with_indications_export',
                'efo_term': r['efo_term'],
                'drug_count': r['drug_count'],
                'row_count': rc,
                'sql': sql,
            })
    return candidates


def gen_target_descriptions_by_organism(limit: int = 15) -> list[dict]:
    rows = query_db(f"""SELECT a.assay_organism, COUNT(DISTINCT td.pref_name) AS target_count
FROM activities act
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
WHERE a.assay_organism IS NOT NULL
GROUP BY a.assay_organism
HAVING target_count >= 3
ORDER BY target_count DESC
LIMIT {limit}""")
    existing_organisms = {'Caenorhabditis elegans', 'Homo sapiens'}
    candidates = []
    for r in rows:
        org = r['assay_organism']
        if org in existing_organisms:
            continue
        slug = org.lower().replace(' ', '_')[:40]
        cid = f"target_descriptions_{slug}"
        if cid in EXISTING_IDS:
            continue
        sql = sql_target_descriptions_by_organism(org)
        rc = count_rows(sql)
        if 5 <= rc <= 50000:
            candidates.append({
                'case_id': cid,
                'template': 'target_description_list',
                'organism': org,
                'target_count': r['target_count'],
                'row_count': rc,
                'sql': sql,
            })
    return candidates


def gen_approved_drugs_by_action_type(limit: int = 15) -> list[dict]:
    rows = query_db(f"""SELECT dm.action_type, COUNT(DISTINCT md.molregno) AS drug_count
FROM drug_mechanism dm
JOIN molecule_dictionary md ON dm.molregno = md.molregno
WHERE md.max_phase = 4
  AND dm.action_type IS NOT NULL
GROUP BY dm.action_type
HAVING drug_count >= 3
ORDER BY drug_count DESC
LIMIT {limit}""")
    candidates = []
    for r in rows:
        slug = r['action_type'].lower().replace(' ', '_').replace('-', '_')[:40]
        cid = f"approved_drugs_mechanism_{slug}"
        if cid in EXISTING_IDS:
            continue
        sql = sql_approved_drugs_by_action_type(r['action_type'])
        rc = count_rows(sql)
        if 5 <= rc <= 50000:
            candidates.append({
                'case_id': cid,
                'template': 'approved_drugs_with_mechanisms_export',
                'action_type': r['action_type'],
                'drug_count': r['drug_count'],
                'row_count': rc,
                'sql': sql,
            })
    return candidates


def gen_drug_indications_by_phase(limit: int = 10) -> list[dict]:
    candidates = []
    for phase in range(4, 0, -1):
        sql = sql_drug_indications_by_phase(phase)
        rc = count_rows(sql)
        if 5 <= rc <= 50000:
            cid = f"drug_indications_max_phase_{phase}"
            if cid in EXISTING_IDS:
                continue
            candidates.append({
                'case_id': cid,
                'template': 'drug_indications_export',
                'max_phase': phase,
                'row_count': rc,
                'sql': sql,
            })
        if len(candidates) >= limit:
            break
    return candidates


def gen_other_grounded_sql(limit: int = 30) -> list[dict]:
    """Generate diverse SQL patterns that don't fit other templates."""
    candidates = []

    # 1. Count activities by target type (aggregation)
    sql = sql_count_activities_by_target_type()
    rc = count_rows(sql)
    if 5 <= rc <= 50000:
        cid = "count_ic50_activities_by_target_type"
        if cid not in EXISTING_IDS:
            candidates.append({
                'case_id': cid,
                'template': 'other_grounded_sql_family',
                'description': 'Count IC50 activities grouped by target_type',
                'row_count': rc,
                'sql': sql,
            })

    # 2. Approved drugs passing Lipinski RO5
    sql = sql_molecules_by_phase_and_ro5()
    rc = count_rows(sql)
    if 5 <= rc <= 50000:
        cid = "approved_drugs_lipinski_ro5_pass"
        if cid not in EXISTING_IDS:
            candidates.append({
                'case_id': cid,
                'template': 'other_grounded_sql_family',
                'description': 'Phase 4 drugs passing Lipinski rule of 5',
                'row_count': rc,
                'sql': sql,
            })

    # 3. Target selectivity queries (diverse target pairs)
    selectivity_pairs = [
        ('CHEMBL4026', 'PIK3CA', 'CHEMBL3045', 'mTOR'),
        ('CHEMBL211', 'CDK2', 'CHEMBL240', 'CDK1'),
        ('CHEMBL220', 'FGFR1', 'CHEMBL6030', 'FGFR2'),
        ('CHEMBL1943', 'VEGFR1', 'CHEMBL279', 'VEGFR2'),
        ('CHEMBL244', 'BCR-ABL', 'CHEMBL1867', 'SRC'),
    ]
    for t1_id, t1_name, t2_id, t2_name in selectivity_pairs:
        slug = f"{t1_name.lower()}_over_{t2_name.lower()}"
        cid = f"selective_{slug}_ic50_smiles"
        if cid in EXISTING_IDS:
            continue
        sql = sql_target_selectivity(t1_id, t1_name, t2_id, t2_name)
        rc = count_rows(sql)
        if 5 <= rc <= 50000:
            candidates.append({
                'case_id': cid,
                'template': 'other_grounded_sql_family',
                'description': f'{t1_name}-selective over {t2_name} IC50 compounds',
                'row_count': rc,
                'sql': sql,
            })

    # 4. Compound activity counts by organism
    sql = """SELECT td.organism, COUNT(DISTINCT act.activity_id) AS ic50_count
FROM activities act
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
WHERE act.standard_type = 'IC50' AND act.standard_units = 'nM'
GROUP BY td.organism
ORDER BY ic50_count DESC"""
    rc = count_rows(sql)
    if 5 <= rc <= 50000:
        cid = "ic50_activity_counts_by_organism"
        if cid not in EXISTING_IDS:
            candidates.append({
                'case_id': cid,
                'template': 'other_grounded_sql_family',
                'description': 'IC50 activity counts grouped by organism',
                'row_count': rc,
                'sql': sql,
            })

    # 5. Ki activity for specific target types
    for std_type in ['Ki', 'Kd', 'EC50']:
        sql = f"""SELECT DISTINCT md.chembl_id AS compound_chembl_id,
  cs.canonical_smiles, act.standard_type, act.standard_value, act.standard_units
FROM activities act
JOIN molecule_dictionary md ON act.molregno = md.molregno
JOIN compound_structures cs ON md.molregno = cs.molregno
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
WHERE td.organism = 'Homo sapiens'
  AND td.target_type = 'SINGLE PROTEIN'
  AND act.standard_type = '{std_type}'
  AND act.standard_units = 'nM'
  AND act.standard_value IS NOT NULL
  AND act.standard_value < 100
LIMIT 500"""
        rc = count_rows(sql)
        if 5 <= rc <= 50000:
            cid = f"human_sub100nm_{std_type.lower()}_first500"
            if cid not in EXISTING_IDS:
                candidates.append({
                    'case_id': cid,
                    'template': 'other_grounded_sql_family',
                    'description': f'Human single-protein sub-100nM {std_type} first 500',
                    'row_count': rc,
                    'sql': sql,
                })

    # 6. Multi-assay type export for a common target
    for target_id, target_name in [('CHEMBL1862', 'THR'), ('CHEMBL206', 'CES2'), ('CHEMBL221', 'MAOB')]:
        sql = f"""SELECT DISTINCT md.chembl_id, cs.canonical_smiles,
  act.standard_type, act.standard_value, act.standard_units
FROM activities act
JOIN molecule_dictionary md ON act.molregno = md.molregno
JOIN compound_structures cs ON md.molregno = cs.molregno
JOIN assays a ON act.assay_id = a.assay_id
JOIN target_dictionary td ON a.tid = td.tid
WHERE td.chembl_id = '{target_id}'
  AND act.standard_value IS NOT NULL
  AND act.standard_relation = '='
  AND cs.canonical_smiles IS NOT NULL
ORDER BY act.standard_value
LIMIT 500"""
        rc = count_rows(sql)
        if 5 <= rc <= 50000:
            slug = target_name.lower().replace(' ', '_')
            cid = f"target_{slug}_multi_type_activities_first500"
            if cid not in EXISTING_IDS:
                candidates.append({
                    'case_id': cid,
                    'template': 'other_grounded_sql_family',
                    'description': f'Multi-type activity export for {target_name} ({target_id})',
                    'row_count': rc,
                    'sql': sql,
                })

    # 7. Distinct molecule count by max_phase
    sql = """SELECT md.max_phase, COUNT(DISTINCT md.chembl_id) AS molecule_count
FROM molecule_dictionary md
GROUP BY md.max_phase
ORDER BY md.max_phase"""
    rc = count_rows(sql)
    if 5 <= rc <= 50000:
        cid = "molecule_counts_by_max_phase"
        if cid not in EXISTING_IDS:
            candidates.append({
                'case_id': cid,
                'template': 'other_grounded_sql_family',
                'description': 'Molecule counts grouped by max development phase',
                'row_count': rc,
                'sql': sql,
            })

    return candidates[:limit]


def main() -> None:
    load_existing_ids()

    all_candidates = []
    template_counts = {}

    generators = [
        ('human_target_molecule_smiles_export', gen_human_target_molecule_smiles, 30),
        ('target_activity_with_pubmed_or_doi', gen_target_activity_pubmed_doi, 25),
        ('approved_drugs_with_indications_export', gen_approved_drugs_by_indication, 20),
        ('target_description_list', gen_target_descriptions_by_organism, 15),
        ('approved_drugs_with_mechanisms_export', gen_approved_drugs_by_action_type, 15),
        ('drug_indications_export', gen_drug_indications_by_phase, 10),
        ('other_grounded_sql_family', gen_other_grounded_sql, 30),
    ]

    for template_name, gen_fn, limit in generators:
        print(f"Generating {template_name} candidates (limit={limit})...", flush=True)
        cands = gen_fn(limit=limit)
        print(f"  Found {len(cands)} valid candidates", flush=True)
        template_counts[template_name] = len(cands)
        for c in cands:
            c['template_name'] = template_name
        all_candidates.extend(cands)

    # Write output
    output = {
        'total_candidates': len(all_candidates),
        'template_counts': template_counts,
        'candidates': all_candidates,
    }
    OUTPUT_JSON.write_text(json.dumps(output, indent=2) + '\n')

    # Write report
    lines = [
        '# Other Family Wave 2 Candidates v4.9',
        '',
        f'- Total candidates: {len(all_candidates)}',
        '',
        '## Template breakdown',
        '',
        '| Template | Candidates |',
        '|----------|------------|',
    ]
    for t, c in sorted(template_counts.items(), key=lambda x: -x[1]):
        lines.append(f'| {t} | {c} |')
    lines.extend([
        '',
        '## Row count distribution',
        '',
        f'- Min: {min(c["row_count"] for c in all_candidates)}',
        f'- Max: {max(c["row_count"] for c in all_candidates)}',
        f'- Mean: {sum(c["row_count"] for c in all_candidates) / len(all_candidates):.0f}',
        '',
        '## Per-template summary',
        '',
    ])
    for t in [name for name, _, _ in generators]:
        t_cands = [c for c in all_candidates if c['template_name'] == t]
        if t_cands:
            lines.append(f'### {t} ({len(t_cands)} cases)')
            lines.append('')
            for c in t_cands[:5]:
                lines.append(f"- `{c['case_id']}` rows={c['row_count']}")
            if len(t_cands) > 5:
                lines.append(f"- ... and {len(t_cands) - 5} more")
            lines.append('')

    OUTPUT_MD.write_text('\n'.join(lines) + '\n')

    print(f"\nTotal candidates: {len(all_candidates)}")
    for t, c in sorted(template_counts.items(), key=lambda x: -x[1]):
        print(f"  {t}: {c}")
    print(f"Output: {OUTPUT_JSON}")
    print(f"Report: {OUTPUT_MD}")


if __name__ == '__main__':
    main()
