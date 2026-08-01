#!/usr/bin/env python3
"""Select the best ~300 target_pchembl cases from the current 902.

Scoring: 0.5 * norm(uq_spec_similarity) + 0.3 * size_score + 0.2 * diversity_bonus
- norm(uq_spec_similarity): percentile rank
- size_score: prefer 50-5000 result rows
- diversity_bonus: cap 3 per target pref_name

Output: experiments/target_pchembl_subset_v4.9.json + .md
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / 'database/latest/chembl_36/chembl_36_sqlite/chembl_36.db'
AUDIT_PATH = REPO_ROOT / 'experiments/v5_case_audit.json'
REGISTRY_PATH = REPO_ROOT / 'tests/cases/web_scrape_hq_cases.json'
OUTPUT_JSON = REPO_ROOT / 'experiments/target_pchembl_subset_v4.9.json'
OUTPUT_MD = REPO_ROOT / 'experiments/target_pchembl_subset_v4.9.md'
TARGET_COUNT = 300


def count_ground_truth_rows(sqlite_sql_path: str) -> int:
    """Execute the sqlite.sql and return row count."""
    p = REPO_ROOT / sqlite_sql_path
    if not p.exists():
        return 0
    sql = p.read_text()
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        conn.close()
        return len(rows)
    except Exception:
        return 0


def size_score(row_count: int) -> float:
    """Prefer 50-5000 rows. Penalize tiny or huge results."""
    if row_count < 5:
        return 0.0
    if row_count < 50:
        return 0.3
    if row_count <= 5000:
        return 1.0
    if row_count <= 50000:
        return 0.5
    return 0.2


def main() -> None:
    audit = json.loads(AUDIT_PATH.read_text())
    registry = json.loads(REGISTRY_PATH.read_text())

    # Build audit lookup by case_id
    audit_by_id = {}
    for c in audit['cases']:
        if c.get('family') == 'target_pchembl':
            audit_by_id[c['case_id']] = c

    # Build registry lookup by id
    reg_by_id = {c['id']: c for c in registry}

    # Get all target_pchembl cases
    tp_cases = [c for c in registry if 'pchembl' in c.get('id', '').lower() or
                (c.get('id', '').startswith('chembl_downloader_target_') and 'pchembl' in c.get('id', ''))]

    # Extract target name from uq text (heuristic: look for target name in the uq)
    # Format: "target CHEMBLXXXX (Target Name)"
    # or from the case_id: chembl_downloader_target_chembl3706_ic50_human_pchembl
    def extract_target_name(case_id: str, uq: str) -> str:
        # Try from uq first: "target CHEMBLxxxx (Name)"
        import re
        m = re.search(r'target\s+CHEMBL\d+\s+\(([^)]+)\)', uq, re.IGNORECASE)
        if m:
            return m.group(1).lower().strip()
        # Fallback: use the chembl ID from case_id
        m = re.search(r'target_(chembl\d+)_', case_id, re.IGNORECASE)
        if m:
            return m.group(1).lower()
        return case_id.lower()

    # Score each case
    scored = []
    for c in tp_cases:
        cid = c['id']
        audit_entry = audit_by_id.get(cid, {})
        spec_sim = audit_entry.get('uq_spec_similarity', 0.0)
        target_name = extract_target_name(cid, c.get('uq', ''))

        # We'll compute row counts lazily - use a placeholder for now
        scored.append({
            'id': cid,
            'uq_spec_similarity': spec_sim,
            'target_name': target_name,
            'row_count': None,  # filled below
            'size_score': None,
            'registry_entry': c,
        })

    # Compute row counts (batch)
    print(f"Computing row counts for {len(scored)} cases...", flush=True)
    for i, entry in enumerate(scored):
        if i % 100 == 0:
            print(f"  {i}/{len(scored)}", flush=True)
        rc = count_ground_truth_rows(entry['registry_entry']['sqlite_sql_path'])
        entry['row_count'] = rc
        entry['size_score'] = size_score(rc)

    # Normalize spec similarity to percentile ranks
    sims = [e['uq_spec_similarity'] for e in scored]
    sorted_sims = sorted(sims)
    n = len(sorted_sims)
    for entry in scored:
        rank = sorted_sims.index(entry['uq_spec_similarity']) if entry['uq_spec_similarity'] in sorted_sims else 0
        # Handle ties by finding first occurrence
        for j, s in enumerate(sorted_sims):
            if abs(s - entry['uq_spec_similarity']) < 1e-10:
                rank = j
                break
        entry['norm_sim'] = rank / max(n - 1, 1)

    # Diversity bonus: group by target_name, sort within groups by score, cap at 3
    from collections import defaultdict
    by_target = defaultdict(list)
    for entry in scored:
        by_target[entry['target_name']].append(entry)

    # Compute preliminary combined score (without diversity)
    for entry in scored:
        entry['prelim_score'] = 0.5 * entry['norm_sim'] + 0.3 * entry['size_score']

    # Sort within each target group by prelim_score, assign diversity bonus
    for target_name, group in by_target.items():
        group.sort(key=lambda e: e['prelim_score'], reverse=True)
        for rank, entry in enumerate(group):
            if rank < 3:
                entry['diversity_bonus'] = 1.0
            elif rank < 5:
                entry['diversity_bonus'] = 0.5
            else:
                entry['diversity_bonus'] = 0.0

    # Final score
    for entry in scored:
        entry['final_score'] = entry['prelim_score'] + 0.2 * entry['diversity_bonus']

    # Select top TARGET_COUNT
    scored.sort(key=lambda e: e['final_score'], reverse=True)
    selected = scored[:TARGET_COUNT]
    excluded = scored[TARGET_COUNT:]

    # Write output JSON
    output = {
        'target_count': TARGET_COUNT,
        'total_target_pchembl': len(scored),
        'selected': [{
            'id': e['id'],
            'uq_spec_similarity': e['uq_spec_similarity'],
            'norm_sim': round(e['norm_sim'], 4),
            'row_count': e['row_count'],
            'size_score': round(e['size_score'], 2),
            'diversity_bonus': round(e['diversity_bonus'], 2),
            'final_score': round(e['final_score'], 4),
            'target_name': e['target_name'],
        } for e in selected],
        'excluded_count': len(excluded),
    }
    OUTPUT_JSON.write_text(json.dumps(output, indent=2) + '\n')

    # Write report markdown
    import statistics
    sel_sims = [e['uq_spec_similarity'] for e in selected]
    exc_sims = [e['uq_spec_similarity'] for e in excluded]
    sel_rows = [e['row_count'] for e in selected if e['row_count']]
    lines = [
        '# Target pChEMBL Subset Selection v4.9',
        '',
        f'- Total target_pchembl cases: {len(scored)}',
        f'- Selected: {len(selected)}',
        f'- Excluded: {len(excluded)}',
        '',
        '## Scoring',
        '',
        '`final_score = 0.5 * norm(uq_spec_similarity) + 0.3 * size_score + 0.2 * diversity_bonus`',
        '',
        '- `norm(uq_spec_similarity)`: percentile rank within 902',
        '- `size_score`: prefer 50-5000 result rows',
        '- `diversity_bonus`: cap 3 per target name, then 0.5 for ranks 4-5, 0 for 6+',
        '',
        '## Selected cases summary',
        '',
        f'- Mean uq_spec_similarity: {statistics.mean(sel_sims):.4f}' if sel_sims else '',
        f'- Median uq_spec_similarity: {statistics.median(sel_sims):.4f}' if sel_sims else '',
        f'- Mean row count: {statistics.mean(sel_rows):.0f}' if sel_rows else '',
        f'- Median row count: {statistics.median(sel_rows):.0f}' if sel_rows else '',
        f'- Unique target names: {len(set(e["target_name"] for e in selected))}',
        '',
        '## Excluded cases summary',
        '',
        f'- Mean uq_spec_similarity: {statistics.mean(exc_sims):.4f}' if exc_sims else '',
        f'- Median uq_spec_similarity: {statistics.median(exc_sims):.4f}' if exc_sims else '',
        '',
        '## Score distribution (selected)',
        '',
        f'| Metric | Min | Max | Mean |',
        f'|--------|-----|-----|------|',
        f'| uq_spec_similarity | {min(sel_sims):.4f} | {max(sel_sims):.4f} | {statistics.mean(sel_sims):.4f} |',
        f'| final_score | {min(e["final_score"] for e in selected):.4f} | {max(e["final_score"] for e in selected):.4f} | {statistics.mean([e["final_score"] for e in selected]):.4f} |',
    ]
    OUTPUT_MD.write_text('\n'.join(lines) + '\n')
    print(f"Selected {len(selected)} / {len(scored)} target_pchembl cases")
    print(f"Output: {OUTPUT_JSON}")
    print(f"Report: {OUTPUT_MD}")


if __name__ == '__main__':
    main()
