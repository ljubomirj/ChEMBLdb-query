#!/usr/bin/env python3
"""Materialize FAQ HQ SQLite ground-truth queries to CSV files."""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import zstandard as zstd

from tests.helpers.chembl_asserts import (
    _apply_temp_table,
    count_csv_rows_maybe_zstd,
    load_cases,
    resolve_csv_or_zstd_path,
    zstd_path_for_csv,
)


DEFAULT_CASES_PATH = Path("cases/registries/archive/faq_hq_cases.json")
DEFAULT_OUTPUT_NAME = "ground-truth.csv"
DEFAULT_SUMMARY_PATH = Path("tests/fixtures/faq_hq/ground-truth-summary.json")
FETCH_BATCH_SIZE = 50_000
PROGRESS_EVERY_ROWS = 250_000
COMPRESS_CHUNK_SIZE = 1024 * 1024


def clean_sql(sql: str) -> str:
    cleaned_lines: list[str] = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("."):
            continue
        if stripped.lower().startswith(".mode") or stripped.lower().startswith(".headers"):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip().rstrip(";")


def output_path_for_case(case: dict[str, Any], output_name: str) -> Path:
    sqlite_sql_path = Path(case["sqlite_sql_path"])
    return sqlite_sql_path.with_name(output_name)


def compressed_path_for_output(output_path: Path) -> Path:
    return zstd_path_for_csv(output_path)


def count_csv_rows(path: Path) -> int:
    return count_csv_rows_maybe_zstd(path)


def compress_csv(output_path: Path) -> Path:
    compressed_path = compressed_path_for_output(output_path)
    cctx = zstd.ZstdCompressor(level=3)
    with output_path.open("rb") as src, compressed_path.open("wb") as dst:
        with cctx.stream_writer(dst) as compressor:
            while True:
                chunk = src.read(COMPRESS_CHUNK_SIZE)
                if not chunk:
                    break
                compressor.write(chunk)
    return compressed_path


def summarize_existing(case: dict[str, Any], *, output_name: str, compress: bool) -> dict[str, Any]:
    output_path = output_path_for_case(case, output_name)
    resolved_path = resolve_csv_or_zstd_path(output_path)
    if not resolved_path.exists():
        raise FileNotFoundError(f"Missing existing ground-truth CSV or .zst: {output_path}")
    row_count = count_csv_rows(output_path)
    summary: dict[str, Any] = {
        "id": case["id"],
        "size_class": case.get("size_class", "small"),
        "output_csv_path": str(output_path),
        "row_count": row_count,
        "size_bytes": output_path.stat().st_size if output_path.exists() else None,
        "elapsed_seconds": 0.0,
    }
    compressed_path = compressed_path_for_output(output_path)
    if compress and output_path.exists():
        compressed_path = compress_csv(output_path)
        summary["compressed_csv_path"] = str(compressed_path)
        summary["compressed_size_bytes"] = compressed_path.stat().st_size
    elif compressed_path.exists():
        summary["compressed_csv_path"] = str(compressed_path)
        summary["compressed_size_bytes"] = compressed_path.stat().st_size
    return summary


def materialize_case(
    case: dict[str, Any],
    *,
    output_name: str,
    batch_size: int,
    compress: bool,
    skip_existing: bool,
) -> dict[str, Any]:
    output_path = output_path_for_case(case, output_name)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if skip_existing and resolve_csv_or_zstd_path(output_path).exists():
        print(f"[skip-existing] {case['id']} -> {output_path}")
        return summarize_existing(case, output_name=output_name, compress=compress)

    db_path = Path(case["db_path"])
    sql_path = Path(case["sqlite_sql_path"])

    sql = clean_sql(sql_path.read_text())
    started = time.time()
    row_count = 0

    print(f"[start] {case['id']} -> {output_path}")
    with sqlite3.connect(str(db_path)) as con:
        cur = con.cursor()
        temp_table = case.get("temp_table")
        if temp_table:
            _apply_temp_table(cur, temp_table)
        cur.execute(sql)
        columns = [desc[0] for desc in cur.description]
        with output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(columns)
            while True:
                rows = cur.fetchmany(batch_size)
                if not rows:
                    break
                writer.writerows(rows)
                row_count += len(rows)
                if row_count and row_count % PROGRESS_EVERY_ROWS == 0:
                    elapsed = time.time() - started
                    print(f"[progress] {case['id']}: rows={row_count} elapsed_s={elapsed:.1f}")

    elapsed = time.time() - started
    size_bytes = output_path.stat().st_size
    summary = {
        "id": case["id"],
        "size_class": case.get("size_class", "small"),
        "output_csv_path": str(output_path),
        "row_count": row_count,
        "size_bytes": size_bytes,
        "elapsed_seconds": round(elapsed, 3),
    }
    if compress:
        compressed_path = compress_csv(output_path)
        summary["compressed_csv_path"] = str(compressed_path)
        summary["compressed_size_bytes"] = compressed_path.stat().st_size
    print(
        f"[done] {case['id']}: rows={row_count} size_bytes={size_bytes} "
        f"elapsed_s={elapsed:.1f}"
    )
    return summary


def build_case_index(cases: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(case["id"]): case for case in cases}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Materialize FAQ HQ SQLite SQL to CSV files.")
    parser.add_argument(
        "--cases",
        default=str(DEFAULT_CASES_PATH),
        help=f"Path to FAQ case registry (default: {DEFAULT_CASES_PATH})",
    )
    parser.add_argument("--case-id", action="append", help="Specific FAQ case id(s) to materialize")
    parser.add_argument("--all", action="store_true", help="Materialize all FAQ HQ cases")
    parser.add_argument(
        "--output-name",
        default=DEFAULT_OUTPUT_NAME,
        help=f"Output filename in each case directory (default: {DEFAULT_OUTPUT_NAME})",
    )
    parser.add_argument(
        "--summary-path",
        default=str(DEFAULT_SUMMARY_PATH),
        help=f"Write JSON summary to this path (default: {DEFAULT_SUMMARY_PATH})",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=FETCH_BATCH_SIZE,
        help=f"SQLite fetchmany batch size (default: {FETCH_BATCH_SIZE})",
    )
    parser.add_argument(
        "--compress",
        action="store_true",
        help="Also write a .zst compressed copy next to each CSV",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Reuse existing CSVs instead of rerunning SQL; row counts are recomputed from the CSV",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cases = load_cases(args.cases)
    case_index = build_case_index(cases)

    selected_ids: list[str] = []
    if args.all:
        selected_ids.extend(str(case["id"]) for case in cases)
    if args.case_id:
        selected_ids.extend(args.case_id)

    deduped_ids: list[str] = []
    seen: set[str] = set()
    for case_id in selected_ids:
        if case_id not in seen:
            deduped_ids.append(case_id)
            seen.add(case_id)

    if not deduped_ids:
        raise SystemExit("No cases selected. Use --all or pass --case-id.")

    summaries: list[dict[str, Any]] = []
    for case_id in deduped_ids:
        case = case_index.get(case_id)
        if case is None:
            raise SystemExit(f"Unknown case_id: {case_id}")
        summaries.append(
            materialize_case(
                case,
                output_name=args.output_name,
                batch_size=args.batch_size,
                compress=bool(args.compress),
                skip_existing=bool(args.skip_existing),
            )
        )

    summary_path = Path(args.summary_path)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summaries, indent=2) + "\n")
    print(f"[summary] wrote {summary_path}")


if __name__ == "__main__":
    main()
