#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

DEFAULT_FAMILY_TOTALS = {
    'metabolism': 3,
    'salts': 10,
    'assay_exact': 20,
    'document': 20,
    'other': 20,
    'target_pchembl': 27,
}


def largest_remainder(total: int, counts: dict[str, int]) -> dict[str, int]:
    total_count = sum(counts.values())
    if total_count <= 0:
        return {k: 0 for k in counts}
    raw = {k: total * v / total_count for k, v in counts.items()}
    alloc = {k: int(raw[k]) for k in counts}
    remaining = total - sum(alloc.values())
    order = sorted(counts, key=lambda k: (raw[k] - alloc[k], counts[k], k), reverse=True)
    for k in order:
        if remaining <= 0:
            break
        alloc[k] += 1
        remaining -= 1
    return alloc


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--source-split', default='experiments/case_splits_v4.7.json')
    ap.add_argument('--manifest-dir', default='tests/v5_manifests/web_scrape_hq')
    ap.add_argument('--out', required=True)
    ap.add_argument('--family-totals-json', default=None)
    ap.add_argument('--description', default='Stratified v5 forward evaluation split.')
    args = ap.parse_args()

    family_totals = dict(DEFAULT_FAMILY_TOTALS)
    if args.family_totals_json:
        family_totals = json.loads(Path(args.family_totals_json).read_text())

    split_payload = json.loads(Path(args.source_split).read_text())
    splits = split_payload['splits']
    manifest_dir = Path(args.manifest_dir)

    by_family_split: dict[str, dict[str, list[dict[str, str]]]] = defaultdict(lambda: defaultdict(list))
    for split_name, items in splits.items():
        for item in items:
            if item.get('corpus') != 'web_scrape_hq':
                continue
            manifest = json.loads((manifest_dir / f"{item['id']}.json").read_text())
            family = manifest['metadata']['family']
            by_family_split[family][split_name].append({'corpus': 'web_scrape_hq', 'id': item['id']})

    for family in by_family_split:
        for split_name in by_family_split[family]:
            by_family_split[family][split_name].sort(key=lambda x: x['id'])

    out_splits = {'train': [], 'val': [], 'test': []}
    summary: dict[str, Any] = {}
    for family, total in family_totals.items():
        available_counts = {s: len(by_family_split[family].get(s, [])) for s in out_splits}
        alloc = largest_remainder(total, available_counts)
        # clip to availability and redistribute any deficit
        deficit = 0
        for s in alloc:
            if alloc[s] > available_counts[s]:
                deficit += alloc[s] - available_counts[s]
                alloc[s] = available_counts[s]
        if deficit:
            for s in sorted(out_splits, key=lambda k: available_counts[k] - alloc[k], reverse=True):
                room = available_counts[s] - alloc[s]
                take = min(room, deficit)
                alloc[s] += take
                deficit -= take
                if deficit <= 0:
                    break
        summary[family] = {'requested_total': total, 'available': available_counts, 'allocated': alloc}
        for s in out_splits:
            out_splits[s].extend(by_family_split[family].get(s, [])[:alloc[s]])

    out_payload = {
        'version': Path(args.out).stem,
        'description': args.description,
        'family_totals': family_totals,
        'splits': out_splits,
        'family_summary': summary,
    }
    out_path = Path(args.out)
    out_path.write_text(json.dumps(out_payload, indent=2) + '\n')
    print(json.dumps({
        'out': str(out_path.resolve()),
        'n_cases': sum(len(v) for v in out_splits.values()),
        'by_split': {k: len(v) for k, v in out_splits.items()},
        'family_summary': summary,
    }, indent=2))


if __name__ == '__main__':
    main()
