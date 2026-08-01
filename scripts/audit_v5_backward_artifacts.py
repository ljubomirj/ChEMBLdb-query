#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / 'src'
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from compressed_io import read_candidates, read_json_maybe_compressed, read_text_maybe_compressed
from db_llm_v5.io import load_case_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description='Audit v5 backward-chain generated artifacts against gold case artifacts.')
    parser.add_argument('--run-root', required=True, help='Backward chain workspace root under experiments/v5_runs')
    parser.add_argument('--output-json', default=None)
    parser.add_argument('--output-md', default=None)
    args = parser.parse_args()

    run_root = Path(args.run_root)
    rows: list[dict[str, Any]] = []
    for record_path in sorted(run_root.glob('*/pb_up_to_uq.generated_artifact_record.json')):
        record = read_json_maybe_compressed(record_path)
        case_dir = record_path.parent
        source_manifest = load_case_manifest(record['source_manifest_path'])
        gold_uq = _read_optional(REPO_ROOT / source_manifest.artifacts.uq_surface)
        gold_spec = _read_optional(REPO_ROOT / source_manifest.artifacts.uq_benchmark_spec) if source_manifest.artifacts.uq_benchmark_spec else None
        recon_uq = _read_optional(case_dir / 'uq_surface.generated.txt')
        recon_up = _read_optional(case_dir / 'up_exec.generated.txt')
        row = {
            'case_id': source_manifest.case_id,
            'family': source_manifest.metadata.family,
            'realism_level': source_manifest.metadata.realism_level,
            'uq_similarity': _sim(gold_uq, recon_uq),
            'spec_similarity': _sim(gold_spec, recon_up),
            'uq_vs_up_similarity': _sim(gold_uq, recon_up),
            'source_manifest_path': record['source_manifest_path'],
            'case_dir': str(case_dir.resolve()),
        }
        rows.append(row)

    summary = {
        'n_rows': len(rows),
        'gold_uq_vs_generated_uq_mean': _mean([r['uq_similarity'] for r in rows]),
        'spec_uq_vs_generated_up_mean': _mean([r['spec_similarity'] for r in rows]),
        'gold_uq_vs_generated_up_mean': _mean([r['uq_vs_up_similarity'] for r in rows]),
        'gold_uq_vs_generated_uq_ge_095': sum(1 for r in rows if r['uq_similarity'] is not None and r['uq_similarity'] >= 0.95),
        'spec_uq_vs_generated_up_ge_095': sum(1 for r in rows if r['spec_similarity'] is not None and r['spec_similarity'] >= 0.95),
        'gold_uq_vs_generated_up_ge_095': sum(1 for r in rows if r['uq_vs_up_similarity'] is not None and r['uq_vs_up_similarity'] >= 0.95),
    }

    payload = {'run_root': str(run_root.resolve()), 'summary': summary, 'rows': rows}
    out_json = Path(args.output_json) if args.output_json else run_root / 'backward_artifact_audit.json'
    out_md = Path(args.output_md) if args.output_md else run_root / 'backward_artifact_audit.md'
    out_json.write_text(json.dumps(payload, indent=2) + '\n')
    out_md.write_text(_to_md(payload))
    print(json.dumps({'out_json': str(out_json.resolve()), 'out_md': str(out_md.resolve()), 'summary': summary}, indent=2))


def _read_optional(path: Path) -> str | None:
    if not any(candidate.exists() for candidate in read_candidates(path)):
        return None
    text = read_text_maybe_compressed(path).strip()
    return text or None


def _sim(a: str | None, b: str | None) -> float | None:
    if not a or not b:
        return None
    return round(SequenceMatcher(None, a, b).ratio(), 6)


def _mean(values: list[float | None]) -> float | None:
    nums = [v for v in values if v is not None]
    if not nums:
        return None
    return round(sum(nums) / len(nums), 6)


def _to_md(payload: dict[str, Any]) -> str:
    lines = [
        '# V5 Backward Artifact Audit',
        '',
        f"- run_root: `{payload['run_root']}`",
        f"- n_rows: `{payload['summary']['n_rows']}`",
        f"- gold_uq_vs_generated_uq_mean: `{payload['summary']['gold_uq_vs_generated_uq_mean']}`",
        f"- spec_uq_vs_generated_up_mean: `{payload['summary']['spec_uq_vs_generated_up_mean']}`",
        f"- gold_uq_vs_generated_up_mean: `{payload['summary']['gold_uq_vs_generated_up_mean']}`",
        '',
        '| case_id | family | uq_similarity | spec_similarity | uq_vs_up_similarity |',
        '|---|---:|---:|---:|---:|',
    ]
    for row in payload['rows']:
        lines.append(
            f"| {row['case_id']} | {row['family']} | {row['uq_similarity']} | {row['spec_similarity']} | {row['uq_vs_up_similarity']} |"
        )
    lines.append('')
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    main()
