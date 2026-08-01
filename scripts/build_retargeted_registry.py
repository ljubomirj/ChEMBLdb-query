#!/usr/bin/env python3
"""Build retargeted active registry: 300 selected target_pchembl + all non-target cases.

Reads the subset from experiments/target_pchembl_subset_v4.9.json and the current
active registry. Produces a new staging registry and archives excluded cases.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SUBSET_PATH = REPO_ROOT / 'experiments/target_pchembl_subset_v4.9.json'
REGISTRY_PATH = REPO_ROOT / 'tests/cases/web_scrape_hq_cases.json'
STAGING_OUT = REPO_ROOT / 'tests/cases/web_scrape_hq_cases_v4.9_retargeted_staging.json'
ARCHIVE_OUT = REPO_ROOT / 'tests/cases/web_scrape_hq_cases_archive_v4.9_target_pchembl_excluded.json'
REPORT_OUT = REPO_ROOT / 'experiments/retargeted_registry_report_v4.9.md'


def main() -> None:
    subset = json.loads(SUBSET_PATH.read_text())
    registry = json.loads(REGISTRY_PATH.read_text())

    selected_ids = {e['id'] for e in subset['selected']}

    # Classify
    new_entries = []
    excluded_entries = []
    family_counts = {}

    for entry in registry:
        eid = entry['id']
        is_target_pchembl = 'pchembl' in eid.lower() or (
            eid.startswith('chembl_downloader_target_') and 'pchembl' in eid
        )
        if is_target_pchembl:
            if eid in selected_ids:
                new_entries.append(entry)
            else:
                excluded_entries.append(entry)
        else:
            new_entries.append(entry)

    # Count families
    for entry in new_entries:
        eid = entry['id']
        if 'pchembl' in eid.lower():
            family = 'target_pchembl'
        elif 'assay' in eid.lower() and 'exact' in eid.lower():
            family = 'assay_exact'
        elif 'document' in eid.lower():
            family = 'document'
        elif 'salt' in eid.lower():
            family = 'salts'
        elif 'metabol' in eid.lower():
            family = 'metabolism'
        else:
            family = 'other'
        family_counts[family] = family_counts.get(family, 0) + 1

    # Write staging registry
    STAGING_OUT.write_text(json.dumps(new_entries, indent=2) + '\n')

    # Write archive
    ARCHIVE_OUT.write_text(json.dumps(excluded_entries, indent=2) + '\n')

    # Write report
    lines = [
        '# Retargeted Registry Report v4.9',
        '',
        '## Counts',
        '',
        f'- Original active registry: {len(registry)}',
        f'- New staging registry: {len(new_entries)}',
        f'- Archived target_pchembl: {len(excluded_entries)}',
        '',
        '## Family breakdown',
        '',
        '| Family | Count |',
        '|--------|-------|',
    ]
    for fam, cnt in sorted(family_counts.items(), key=lambda x: -x[1]):
        lines.append(f'| {fam} | {cnt} |')
    lines.extend([
        f'| **Total** | **{sum(family_counts.values())}** |',
        '',
        '## Files',
        '',
        f'- Staging: `{STAGING_OUT.name}`',
        f'- Archive: `{ARCHIVE_OUT.name}`',
    ])
    REPORT_OUT.write_text('\n'.join(lines) + '\n')

    print(f"Staging registry: {len(new_entries)} entries -> {STAGING_OUT}")
    print(f"Archive: {len(excluded_entries)} entries -> {ARCHIVE_OUT}")
    for fam, cnt in sorted(family_counts.items(), key=lambda x: -x[1]):
        print(f"  {fam}: {cnt}")


if __name__ == '__main__':
    main()
