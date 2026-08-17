#!/usr/bin/env python3
import csv
import json
import sqlite3
import subprocess
from pathlib import Path
from typing import Any

BASE_DIR = Path('/Users/ljubomir/ChEMBLdb-query')
DB_PATH = BASE_DIR / 'database/latest/chembl_36/chembl_36_sqlite/chembl_36.db'
MAIN_CASES = BASE_DIR / 'cases/registries/archive/web_scrape_hq_cases.json'
SNAPSHOT_CASES = BASE_DIR / 'cases/registries/archive/web_scrape_hq_cases_v4.6.json'
FIXTURES_BASE = BASE_DIR / 'tests/fixtures'
SUMMARY_PATH = BASE_DIR / 'experiments/v4.6_expansion_wave1_summary.json'
REPORT_PATH = BASE_DIR / 'experiments/v4.6_expansion_wave1_report.md'
TARGET_COUNT = 80
DOC_COUNT = 40
TARGET_ROWS_LIMIT = 1000


def load_cases() -> list[dict[str, Any]]:
    return json.loads(MAIN_CASES.read_text())


def existing_ids(cases: list[dict[str, Any]]) -> set[str]:
    return {c['id'] for c in cases}


def run_rows(sql: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        conn.close()


def get_target_candidates(existing: set[str], limit: int) -> list[dict[str, Any]]:
    rows = run_rows(
        """
        SELECT td.chembl_id, td.pref_name, COUNT(DISTINCT act.molregno) AS molecule_count
        FROM target_dictionary td
        JOIN assays a ON td.tid = a.tid
        JOIN activities act ON a.assay_id = act.assay_id
        JOIN compound_structures cs ON act.molregno = cs.molregno
        WHERE td.target_type = 'SINGLE PROTEIN'
          AND td.tax_id = '9606'
          AND act.standard_type = 'IC50'
          AND act.standard_relation = '='
          AND act.pchembl_value IS NOT NULL
          AND cs.canonical_smiles IS NOT NULL
        GROUP BY td.chembl_id, td.pref_name
        HAVING molecule_count >= 10
        ORDER BY molecule_count DESC, td.chembl_id
        LIMIT 500
        """
    )
    out = []
    for chembl_id, pref_name, molecule_count in rows:
        cid = f'chembl_downloader_target_{chembl_id.lower()}_ic50_human_pchembl'
        if cid in existing:
            continue
        out.append({'id': cid, 'chembl_id': chembl_id, 'pref_name': pref_name, 'molecule_count': molecule_count})
        if len(out) >= limit:
            break
    return out


def get_document_candidates(existing: set[str], limit: int) -> list[dict[str, Any]]:
    rows = run_rows(
        """
        SELECT d.chembl_id, COALESCE(d.title, ''), COUNT(DISTINCT cr.molregno) AS molecule_count
        FROM docs d
        JOIN compound_records cr ON d.doc_id = cr.doc_id
        JOIN molecule_dictionary md ON cr.molregno = md.molregno
        JOIN compound_structures cs ON md.molregno = cs.molregno
        WHERE cs.canonical_smiles IS NOT NULL
        GROUP BY d.chembl_id, d.title
        HAVING molecule_count BETWEEN 5 AND 120
        ORDER BY molecule_count DESC, d.chembl_id
        LIMIT 250
        """
    )
    out = []
    for chembl_id, title, molecule_count in rows:
        cid = f'chembl_downloader_document_molecules_{chembl_id.lower()}'
        if cid in existing:
            continue
        out.append({'id': cid, 'chembl_id': chembl_id, 'title': title, 'molecule_count': molecule_count})
        if len(out) >= limit:
            break
    return out


def write_csv(sql: str, out_csv: Path) -> int:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(sql)
        if not cur.description:
            return 0
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


def compress(out_csv: Path) -> None:
    subprocess.run(['zstd', '-f', str(out_csv), '-o', str(out_csv.with_suffix('.csv.zst'))], check=True, capture_output=True)


def make_target(info: dict[str, Any], round_num: int) -> tuple[dict[str, Any], int]:
    cid = info['id']
    chembl_id = info['chembl_id']
    pref_name = info['pref_name']
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
        f"Retrieve the first {TARGET_ROWS_LIMIT} rows of assay_chembl_id, target_type, tax_id, canonical_smiles, molecule_chembl_id, standard_type, and pchembl_value "
        f"for IC50 activities on human single protein target {chembl_id} ({pref_name}) with pchembl_value not null and standard_relation '='. "
        f"Order rows by molecule_chembl_id, assay_chembl_id."
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
    n = write_csv(sql, d / 'ground-truth.csv')
    compress(d / 'ground-truth.csv')
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
    return entry, n


def make_document(info: dict[str, Any], round_num: int) -> tuple[dict[str, Any], int]:
    cid = info['id']
    chembl_id = info['chembl_id']
    title = info['title']
    d = FIXTURES_BASE / f'web_scrape{round_num}' / cid
    d.mkdir(parents=True, exist_ok=True)
    sql = f"""SELECT DISTINCT
    MOLECULE_DICTIONARY.chembl_id,
    COMPOUND_RECORDS.compound_name,
    COMPOUND_STRUCTURES.canonical_smiles
FROM DOCS
JOIN COMPOUND_RECORDS ON COMPOUND_RECORDS.doc_id = DOCS.doc_id
JOIN MOLECULE_DICTIONARY ON MOLECULE_DICTIONARY.molregno = COMPOUND_RECORDS.molregno
JOIN COMPOUND_STRUCTURES ON COMPOUND_RECORDS.molregno = COMPOUND_STRUCTURES.molregno
WHERE DOCS.chembl_id = '{chembl_id}'
ORDER BY MOLECULE_DICTIONARY.chembl_id, COMPOUND_RECORDS.compound_name, COMPOUND_STRUCTURES.canonical_smiles
"""
    uq = f"For document {chembl_id}, list the distinct molecules reported there. Return molecule ChEMBL ID, compound name, and canonical SMILES. Only include rows where canonical SMILES is available."
    benchmark = f"Retrieve distinct chembl_id, compound_name, and canonical_smiles for molecules mentioned in document {chembl_id}, including only rows with canonical_smiles present. Order rows by chembl_id, compound_name, canonical_smiles."
    metadata = {
        'id': cid,
        'source_title': f'chembl_downloader document molecule export for {chembl_id}',
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
    (d / 'documentation.txt').write_text(f"Document: {chembl_id}\n\n{title[:300]}\n")
    n = write_csv(sql, d / 'ground-truth.csv')
    compress(d / 'ground-truth.csv')
    entry = {
        'id': cid,
        'uq': uq,
        'source_url': metadata['source_url'],
        'source_sql_path': metadata['sql_path'],
        'sqlite_sql_path': metadata['sql_path'].replace('source.sql', 'sqlite.sql'),
        'result_csv_path': f'tests/fixtures/web_scrape{round_num}/{cid}/result-last.csv',
        'log_path': f'tests/fixtures/web_scrape{round_num}/{cid}/run-last.log',
        'db_path': 'database/latest/chembl_36/chembl_36_sqlite/chembl_36.db',
        'size_class': 'small',
        'sort_keys': ['chembl_id', 'compound_name', 'canonical_smiles'],
        'column_rename_map': {'chembl_id': 'chembl_id', 'compound_name': 'compound_name', 'canonical_smiles': 'canonical_smiles'},
        'normalize': {'lowercase_columns': True, 'strip_values': True, 'lowercase_values': []},
        'benchmark_spec_uq_path': str((d / 'benchmark_spec_uq.txt').resolve()),
        'uq_style': 'realistic_uq',
    }
    return entry, n


def main() -> None:
    cases = load_cases()
    used = existing_ids(cases)
    targets = get_target_candidates(used, TARGET_COUNT)
    docs = get_document_candidates(used, DOC_COUNT)
    print(f'target candidates: {len(targets)}')
    print(f'document candidates: {len(docs)}')
    new_entries = []
    summary = {'previous_total': len(cases), 'targets': [], 'documents': []}
    for i, info in enumerate(targets, 1):
        round_num = 30 + ((i - 1) // 20)
        entry, n = make_target(info, round_num)
        new_entries.append(entry)
        summary['targets'].append({'id': entry['id'], 'rows': n, 'round': round_num})
        print(f'[target {i}/{len(targets)}] {entry["id"]} rows={n} round={round_num}', flush=True)
    for i, info in enumerate(docs, 1):
        round_num = 34 + ((i - 1) // 10)
        entry, n = make_document(info, round_num)
        new_entries.append(entry)
        summary['documents'].append({'id': entry['id'], 'rows': n, 'round': round_num})
        print(f'[doc {i}/{len(docs)}] {entry["id"]} rows={n} round={round_num}', flush=True)
    cases.extend(new_entries)
    MAIN_CASES.write_text(json.dumps(cases, indent=2) + '\n')
    SNAPSHOT_CASES.write_text(json.dumps(cases, indent=2) + '\n')
    summary['new_target_cases'] = len(summary['targets'])
    summary['new_document_cases'] = len(summary['documents'])
    summary['new_cases'] = len(new_entries)
    summary['new_total'] = len(cases)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + '\n')
    REPORT_PATH.write_text(
        '# V4.6 Expansion Wave 1\n\n'
        f'- Previous total: {summary["previous_total"]}\n'
        f'- New target cases: {summary["new_target_cases"]}\n'
        f'- New document cases: {summary["new_document_cases"]}\n'
        f'- New total: {summary["new_total"]}\n\n'
        'This wave deliberately excludes bulk assay_exact expansion because the remaining baseline failures are concentrated in that family.\n'
    )
    print(json.dumps({k: summary[k] for k in ['previous_total','new_target_cases','new_document_cases','new_cases','new_total']}, indent=2))

if __name__ == '__main__':
    main()
