#!/usr/bin/env python3
"""Run one or more promoted web-scrape cases and refresh their last-result CSVs."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def load_cases(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text())


def build_case_index(cases: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(case["id"]): case for case in cases}


def _has_explicit_db_llm_verbosity(args: list[str]) -> bool:
    for arg in args:
        if arg == "--verbose":
            return True
        if arg.startswith("--verbose="):
            return True
        if arg.startswith("-") and "v" in arg[1:] and all(ch == "v" for ch in arg[1:]):
            return True
    return False


def run_case(case: dict[str, Any], db_llm_args: list[str], *, quiet: bool, db_llm_script: str) -> int:
    result_path = Path(case["result_csv_path"]).resolve()
    log_path = Path(case.get("log_path") or result_path.with_suffix(".log")).resolve()
    result_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    run_label = f"{case['id']}_{time.strftime('%Y%m%d_%H%M%S')}"
    effective_db_llm_args = list(db_llm_args)
    if not _has_explicit_db_llm_verbosity(effective_db_llm_args):
        effective_db_llm_args = ["-vv", *effective_db_llm_args]
    cmd = [
        "uv",
        "run",
        "python",
        db_llm_script,
        "-f",
        "csv",
        "--run-label",
        run_label,
        "--output-file",
        str(result_path),
        "-q",
        str(case["uq"]),
        *effective_db_llm_args,
    ]

    with log_path.open("w", encoding="utf-8") as log:
        log.write(f"Command: {' '.join(cmd)}\n")
        log.write(f"Started: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        log.write(f"Case: {case['id']}\n")
        log.write(f"UQ: {case['uq']}\n\n")
        log.flush()

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        try:
            while True:
                line = proc.stdout.readline() if proc.stdout else ""
                if line:
                    if not quiet:
                        sys.stdout.write(line)
                        sys.stdout.flush()
                    log.write(line)
                    log.flush()
                if proc.poll() is not None:
                    break
        finally:
            if proc.stdout:
                proc.stdout.close()

        log.write(f"\nFinished: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        log.write(f"Exit code: {proc.returncode}\n")
        log.flush()

    return int(proc.returncode or 0)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run promoted web-scrape cases and write result-last.csv for each selected case."
    )
    parser.add_argument(
        "--case-id",
        action="append",
        help="Web-scrape case id from cases/registries/archive/web_scrape_hq_cases.json",
    )
    parser.add_argument("--all", action="store_true", help="Run all web-scrape cases in the selected registry")
    parser.add_argument(
        "--cases",
        default="cases/registries/archive/web_scrape_hq_cases.json",
        help="Path to promoted web-scrape case registry (default: cases/registries/archive/web_scrape_hq_cases.json)",
    )
    parser.add_argument("--list", action="store_true", help="List available web-scrape case ids with size class and UQ")
    parser.add_argument("--quiet", action="store_true", help="Suppress live stdout and write only to the case log")
    parser.add_argument(
        "--db-llm-script",
        default="src/db_llm_query.py",
        help="CLI script to invoke for case runs (default: src/db_llm_query.py)",
    )
    parser.add_argument(
        "db_llm_args",
        nargs=argparse.REMAINDER,
        help="Arguments passed through to src/db_llm_query.py after '--'",
    )
    args = parser.parse_args()

    cases = load_cases(Path(args.cases))
    case_index = build_case_index(cases)

    if args.list:
        for case in cases:
            print(f"{case['id']} [{case.get('size_class', 'small')}]: {case['uq']}")
        return

    db_llm_args = list(args.db_llm_args)
    if db_llm_args and db_llm_args[0] == "--":
        db_llm_args = db_llm_args[1:]

    selected_ids: list[str] = []
    if args.all:
        for case in cases:
            selected_ids.append(str(case["id"]))
    if args.case_id:
        selected_ids.extend(args.case_id)

    deduped_ids: list[str] = []
    seen: set[str] = set()
    for case_id in selected_ids:
        if case_id not in seen:
            deduped_ids.append(case_id)
            seen.add(case_id)

    if not deduped_ids:
        raise SystemExit("No cases selected. Use --list, pass --case-id, or use --all.")

    if not db_llm_args:
        raise SystemExit(
            "Missing db_llm_query arguments. Example: -- --multi-endpoint-profile zai-pony-alpha-2"
        )

    failures = 0
    for case_id in deduped_ids:
        case = case_index.get(case_id)
        if case is None:
            print(f"Unknown case_id: {case_id}", file=sys.stderr)
            failures += 1
            continue
        code = run_case(case, db_llm_args, quiet=bool(args.quiet), db_llm_script=str(args.db_llm_script))
        if code != 0:
            failures += 1
            log_path = Path(case.get("log_path") or Path(case["result_csv_path"]).with_suffix(".log")).resolve()
            print(f"Web-scrape case failed (exit={code}) for {case_id}. See log: {log_path}", file=sys.stderr)

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
