#!/usr/bin/env python3
import csv, json, sqlite3, subprocess
from pathlib import Path

BASE_DIR = Path('/Users/ljubomir/ChEMBLdb-query')
DB_PATH = BASE_DIR / 'database/latest/chembl_36/chembl_36_sqlite/chembl_36.db'
MAIN_CASES = BASE_DIR / 'cases/registries/archive/web_scrape_hq_cases.json'
SNAPSHOT_CASES = BASE_DIR / 'cases/registries/archive/web_scrape_hq_cases_v4.6.json'
FIXTURES_BASE = BASE_DIR / 'tests/fixtures'
SUMMARY_PATH = BASE_DIR / 'experiments/v4.6_expansion_wave3_summary.json'
REPORT_PATH = BASE_DIR / 'experiments/v4.6_expansion_wave3_report.md'
TARGET_COUNT = 100
TARGET_ROWS_LIMIT = 1000
ROUND_BASE = 42

with open(MAIN_CASES) as f:
    cases = json.load(f)
existing_ids = {c['id'] for c in cases}

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute(
    """
    SELECT DISTINCT td.chembl_id, td.pref_name
    FROM target_dictionary td
    JOIN assays a ON td.tid = a.tid
    JOIN activities act ON a.assay_id = act.assay_id
    WHERE td.target_type = 'SINGLE PROTEIN'
      AND td.tax_id = '9606'
      AND act.standard_type = 'IC50'
      AND act.pchembl_value IS NOT NULL
    LIMIT ?
    """,
    (TARGET_COUNT * 18,),
)
rows = cur.fetchall()
conn.close()

candidates = []
for chembl_id, pref_name in rows:
    cid = f'chembl_downloader_target_{chembl_id.lower()}_ic50_human_pchembl'
    if cid in existing_ids:
        continue
    candidates.append((chembl_id, pref_name, cid))
    if len(candidates) >= TARGET_COUNT:
        break

print(f'target candidates: {len(candidates)}', flush=True)

def write_csv(sql: str, out_csv: Path) -> int:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor(); cur.execute(sql)
        cols = [d[0] for d in cur.description]
        n = 0
        with open(out_csv, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=cols, quoting=csv.QUOTE_MINIMAL)
            w.writeheader()
            for row in cur:
                n += 1
                w.writerow({c: '' if row[c] is None else str(row[c]) for c in cols})
        return n
    finally:
        conn.close()

new_entries = []
summary = {'previous_total': len(cases), 'targets': []}
for i, (chembl_id, pref_name, cid) in enumerate(candidates, 1):
    round_num = ROUND_BASE + ((i - 1) // 25)
    d = FIXTURES_BASE / f'web_scrape{round_num}' / cid
    d.mkdir(parents=True, exist_ok=True)
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
LIMIT {TARGET_ROWS_LIMIT}
"""
    uq = (
        f"Show the first {TARGET_ROWS_LIMIT} IC50 activity rows with pChEMBL values for the human single-protein target {chembl_id} ({pref_name}). "
        f"Return assay ChEMBL ID, target type, tax_id, canonical SMILES, molecule ChEMBL ID, standard type, and pChEMBL value. "
        f"Use only exact standard relation '=' rows with non-null pChEMBL values, and order the results by molecule ChEMBL ID and assay ChEMBL ID."
    )
    benchmark = (
        f"Retrieve the first {TARGET_ROWS_LIMIT} rows of assay_chembl_id, target_type, tax_id, canonical_smiles, molecule_chembl_id, standard_type, and pchembl_value for IC50 activities on human single protein target {chembl_id} ({pref_name}) with pchembl_value not null and standard_relation '='. Order rows by molecule_chembl_id, assay_chembl_id."
    )
    metadata = {
        'id': cid,
        'source_title': f'chembl_downloader target export for {chembl_id}',
        'source_url': 'https://github.com/cthoyt/chembl-downloader/blob/main/src/chembl_downloader/queries.py',
        'uq_origin': 'templated_from_sql',
        'uq_style': 'realistic_uq',
        'uq_origin_kind': 'templated_from_sql',
        'uq_path': f'tests/fixtures/web_scrape{round_num}/{cid}/uq.txt',
        'benchmark_spec_uq_path': f'tests/fixtures/web_scrape{round_num}/{cid}/benchmark_spec_uq.txt',
        'sql_path': f'tests/fixtures/web_scrape{round_num}/{cid}/source.sql',
        'documentation_path': f'tests/fixtures/web_scrape{round_num}/{cid}/documentation.txt',
    }
    (d / 'source.sql').write_text(sql)
    (d / 'sqlite.sql').write_text(sql)
    (d / 'uq.txt').write_text(uq + '\n')
    (d / 'benchmark_spec_uq.txt').write_text(benchmark + '\n')
    (d / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    (d / 'documentation.txt').write_text(f"Target: {chembl_id} ({pref_name})\n")
    row_count = write_csv(sql, d / 'ground-truth.csv')
    subprocess.run(['zstd', '-f', str(d / 'ground-truth.csv'), '-o', str(d / 'ground-truth.csv.zst')], check=True, capture_output=True)
    entry = {
        'id': cid,
        'uq': uq,
        'source_url': metadata['source_url'],
        'source_sql_path': metadata['sql_path'],
        'sqlite_sql_path': metadata['sql_path'].replace('source.sql', 'sqlite.sql'),
        'result_csv_path': f'tests/fixtures/web_scrape{round_num}/{cid}/result-last.csv',
        'log_path': f'tests/fixtures/web_scrape{round_num}/{cid}/run-last.log',
        'db_path': 'database/latest/chembl_36/chembl_36_sqlite/chembl_36.db',
        'size_class': 'medium',
        'sort_keys': ['molecule_chembl_id', 'assay_chembl_id', 'canonical_smiles', 'target_type', 'tax_id', 'standard_type', 'pchembl_value'],
        'column_rename_map': {
            'assay_chembl_id': 'assay_chembl_id',
            'chembl_id': 'molecule_chembl_id',
            'molecule_chembl_id': 'molecule_chembl_id',
            'canonical_smiles': 'canonical_smiles',
            'target_type': 'target_type',
            'tax_id': 'tax_id',
            'standard_type': 'standard_type',
            'pchembl_value': 'pchembl_value',
        },
        'normalize': {'lowercase_columns': True, 'strip_values': True, 'lowercase_values': []},
        'benchmark_spec_uq_path': str((d / 'benchmark_spec_uq.txt').resolve()),
        'uq_style': 'realistic_uq',
    }
    new_entries.append(entry)
    summary['targets'].append({'id': cid, 'rows': row_count, 'round': round_num})
    print(f'[{i}/{len(candidates)}] {cid} rows={row_count} round={round_num}', flush=True)

cases.extend(new_entries)
MAIN_CASES.write_text(json.dumps(cases, indent=2) + '\n')
SNAPSHOT_CASES.write_text(json.dumps(cases, indent=2) + '\n')
summary['new_target_cases'] = len(new_entries)
summary['new_cases'] = len(new_entries)
summary['new_total'] = len(cases)
SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + '\n')
REPORT_PATH.write_text(
    '# V4.6 Expansion Wave 3\n\n'
    f'- Previous total: {summary["previous_total"]}\n'
    f'- New target cases: {summary["new_target_cases"]}\n'
    f'- New total: {summary["new_total"]}\n\n'
    'Wave 3 continues the capped target_pchembl expansion to reach the 500-case milestone.\n'
)
print(json.dumps({'previous_total': summary['previous_total'], 'new_target_cases': summary['new_target_cases'], 'new_total': summary['new_total']}, indent=2))
