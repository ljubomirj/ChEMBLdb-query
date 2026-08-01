#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / 'database/latest/chembl_36/chembl_36_sqlite/chembl_36.db'
CASES_PATH = REPO_ROOT / 'tests/cases/web_scrape_hq_cases.json'
OUT_JSON = REPO_ROOT / 'experiments/assay_exact_wave1_candidates_v4.8.json'
OUT_MD = REPO_ROOT / 'experiments/assay_exact_wave1_candidates_v4.8.md'


def main() -> None:
    ap = argparse.ArgumentParser(description='Prepare assay_exact wave-1 candidates from grounded SQL family patterns already in the repo.')
    ap.add_argument('--limit', type=int, default=120)
    args = ap.parse_args()

    existing = {case['id'] for case in json.loads(CASES_PATH.read_text())}
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        '''
        SELECT
            a.chembl_id,
            COALESCE(a.description, '') AS description,
            COUNT(*) AS activity_count,
            COUNT(DISTINCT act.molregno) AS molecule_count
        FROM assays a
        JOIN activities act ON a.assay_id = act.assay_id
        JOIN molecule_dictionary md ON act.molregno = md.molregno
        JOIN compound_structures cs ON md.molregno = cs.molregno
        WHERE act.standard_value IS NOT NULL
          AND act.standard_relation IS NOT NULL
          AND act.standard_relation = '='
          AND cs.canonical_smiles IS NOT NULL
        GROUP BY a.chembl_id, a.description
        HAVING COUNT(*) >= 50 AND COUNT(DISTINCT act.molregno) >= 5
        ORDER BY activity_count DESC, a.chembl_id
        LIMIT ?
        ''',
        (args.limit * 4,),
    )
    rows = []
    for chembl_id, description, activity_count, molecule_count in cur.fetchall():
        case_id = f'chembl_downloader_assay_{chembl_id.lower()}_exact'
        if case_id in existing:
            continue
        rows.append({
            'case_id': case_id,
            'assay_chembl_id': chembl_id,
            'description': description[:160],
            'activity_count': activity_count,
            'molecule_count': molecule_count,
            'family': 'assay_exact',
            'template_key': 'chembl_downloader_assay_exact_export',
            'generation_path': 'grounded_sql -> PB_SQL -> PB_UP',
        })
        if len(rows) >= args.limit:
            break
    conn.close()

    payload = {
        'limit': args.limit,
        'n_candidates': len(rows),
        'family': 'assay_exact',
        'template_key': 'chembl_downloader_assay_exact_export',
        'candidates': rows,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2) + '\n')

    lines = [
        '# Assay-Exact Wave 1 Candidates v4.8',
        '',
        f"- Candidate count: {len(rows)}",
        '- Generation path: `grounded_sql -> PB_SQL -> PB_UP`',
        '',
        '## Top candidates',
        '',
    ]
    for row in rows[:40]:
        lines.append(f"- `{row['assay_chembl_id']}` `{row['case_id']}` activities={row['activity_count']} molecules={row['molecule_count']}")
    OUT_MD.write_text('\n'.join(lines) + '\n')
    print(json.dumps({'out_json': str(OUT_JSON.resolve()), 'out_md': str(OUT_MD.resolve()), 'n_candidates': len(rows)}, indent=2))


if __name__ == '__main__':
    main()
