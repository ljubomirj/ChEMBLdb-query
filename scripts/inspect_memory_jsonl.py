#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from compressed_io import append_target_path, iter_jsonl_records, read_candidates, resolve_read_path, rotated_jsonl_archives


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect live and rotated MEMORY JSONL archives.")
    parser.add_argument("--memory-path", default="MEMORY-ChEMBLdb-query.jsonl")
    parser.add_argument("--top-run-labels", type=int, default=10)
    parser.add_argument("--output-json", default=None)
    parser.add_argument("--print-summary", action="store_true")
    args = parser.parse_args()

    memory_path = append_target_path(Path(args.memory_path))
    live_exists = any(candidate.exists() for candidate in read_candidates(memory_path, prefer_compressed=False))
    rotated = rotated_jsonl_archives(memory_path)

    files: list[dict[str, Any]] = []
    if live_exists:
        resolved_live = resolve_read_path(memory_path, prefer_compressed=False)
        files.append(_inspect_one_file(resolved_live, include_rotated=False))
    for archive_path in rotated:
        files.append(_inspect_one_file(archive_path, include_rotated=False))

    all_records = list(iter_jsonl_records(memory_path, include_rotated=True, prefer_compressed=False))
    run_label_counts = Counter(
        str(record.get("run_label"))
        for record in all_records
        if isinstance(record, dict) and record.get("run_label")
    )
    top_run_labels = [
        {"run_label": label, "count": count}
        for label, count in run_label_counts.most_common(args.top_run_labels)
    ]

    summary = {
        "memory_path": str(memory_path.resolve()),
        "live_exists": live_exists,
        "resolved_live_path": str(resolve_read_path(memory_path, prefer_compressed=False)),
        "rotated_archive_count": len(rotated),
        "total_records": len(all_records),
        "ts_utc_min": _min_ts(all_records),
        "ts_utc_max": _max_ts(all_records),
        "top_run_labels": top_run_labels,
    }
    payload = {
        "summary": summary,
        "files": files,
    }
    if args.output_json:
        out_path = Path(args.output_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if args.print_summary:
        print(json.dumps(payload, indent=2))
    else:
        print(json.dumps(payload))


def _inspect_one_file(path: Path, *, include_rotated: bool) -> dict[str, Any]:
    records = list(iter_jsonl_records(path, include_rotated=include_rotated, prefer_compressed=False))
    stat = path.stat()
    return {
        "path": str(path.resolve()),
        "size_bytes": stat.st_size,
        "size_mb": round(stat.st_size / (1024 * 1024), 3),
        "mtime_epoch": stat.st_mtime,
        "n_records": len(records),
        "ts_utc_min": _min_ts(records),
        "ts_utc_max": _max_ts(records),
    }


def _min_ts(records: list[dict[str, Any]]) -> str | None:
    values = [str(record.get("ts_utc")) for record in records if isinstance(record, dict) and record.get("ts_utc")]
    return min(values) if values else None


def _max_ts(records: list[dict[str, Any]]) -> str | None:
    values = [str(record.get("ts_utc")) for record in records if isinstance(record, dict) and record.get("ts_utc")]
    return max(values) if values else None


if __name__ == "__main__":
    main()
