#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / 'database/latest/chembl_36/chembl_36_sqlite/chembl_36.db'
ARCHIVE_CASES = REPO_ROOT / 'cases/registries/archive/web_scrape_hq_cases_archive_v4.7_1000.json'
OUT_JSON = REPO_ROOT / 'experiments/document_wave1_candidates_v4.8.json'
OUT_MD = REPO_ROOT / 'experiments/document_wave1_candidates_v4.8.md'


SQL = """
SELECT
    d.chembl_id AS document_chembl_id,
    d.title,
    d.journal,
    d.year,
    d.doc_type,
    COUNT(DISTINCT cr.molregno) AS molecule_count
FROM docs d
JOIN compound_records cr ON cr.doc_id = d.doc_id
JOIN compound_structures cs ON cs.molregno = cr.molregno
GROUP BY d.doc_id
HAVING COUNT(DISTINCT cr.molregno) >= ?
   AND COUNT(DISTINCT cr.molregno) <= ?
ORDER BY molecule_count DESC, d.chembl_id ASC
"""


def main() -> None:
    ap = argparse.ArgumentParser(description='Prepare grounded document wave-1 candidates.')
    ap.add_argument('--archive-cases', default=str(ARCHIVE_CASES))
    ap.add_argument('--min-molecules', type=int, default=20)
    ap.add_argument('--max-molecules', type=int, default=5000)
    ap.add_argument('--limit', type=int, default=120)
    ap.add_argument('--out-json', default=str(OUT_JSON))
    ap.add_argument('--out-md', default=str(OUT_MD))
    args = ap.parse_args()

    archive_cases = json.loads(Path(args.archive_cases).read_text())
    existing_docs = {
        item['id'].split('_')[-1].upper()
        for item in archive_cases
        if item['id'].startswith('chembl_downloader_document_molecules_')
    }

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(SQL, (args.min_molecules, args.max_molecules)).fetchall()
    finally:
        conn.close()

    candidates = []
    for row in rows:
        doc_id = str(row['document_chembl_id']).upper()
        if doc_id in existing_docs:
            continue
        case_id = f"chembl_downloader_document_molecules_{doc_id.lower()}"
        title = (row['title'] or '').strip()
        journal = (row['journal'] or '').strip()
        year = row['year']
        molecule_count = int(row['molecule_count'])
        candidates.append(
            {
                'case_id': case_id,
                'document_chembl_id': doc_id,
                'title': title,
                'journal': journal,
                'year': year,
                'doc_type': row['doc_type'],
                'molecule_count': molecule_count,
                'template_family': 'chembl_downloader_document_molecules_export',
                'generation_path': 'grounded_sql -> PB_SQL -> PB_UP',
            }
        )
        if len(candidates) >= args.limit:
            break

    payload = {
        'family': 'document',
        'template_family': 'chembl_downloader_document_molecules_export',
        'generation_path': 'grounded_sql -> PB_SQL -> PB_UP',
        'min_molecules': args.min_molecules,
        'max_molecules': args.max_molecules,
        'limit': args.limit,
        'n_candidates': len(candidates),
        'candidates': candidates,
    }
    Path(args.out_json).write_text(json.dumps(payload, indent=2) + '\n')

    lines = [
        '# Document Wave 1 Candidates v4.8',
        '',
        f"- Family: `document`",
        f"- Template family: `chembl_downloader_document_molecules_export`",
        f"- Candidate count: `{len(candidates)}`",
        f"- Molecule-count window: `{args.min_molecules}` to `{args.max_molecules}`",
        '',
        '## Top candidates',
        '',
    ]
    for item in candidates[:20]:
        title = item['title'] if item['title'] else '(untitled)'
        lines.append(
            f"- `{item['document_chembl_id']}` `{item['molecule_count']}` molecules :: {title[:140]}"
        )
    Path(args.out_md).write_text('\n'.join(lines) + '\n')

    print(
        json.dumps(
            {
                'out_json': str(Path(args.out_json).resolve()),
                'out_md': str(Path(args.out_md).resolve()),
                'n_candidates': len(candidates),
            }
        )
    )


if __name__ == '__main__':
    main()
