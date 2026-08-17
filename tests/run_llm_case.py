#!/usr/bin/env python3
"""Run a long LLM case and update the last-result CSV."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def load_cases(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text())


def _find_case(cases: list[dict[str, Any]], case_id: str) -> dict[str, Any]:
    for case in cases:
        if case.get("id") == case_id:
            return case
    raise SystemExit(f"Unknown case_id: {case_id}")


def run_case(case: dict[str, Any]) -> int:
    result_path = Path(case["result_csv_path"]).resolve()
    result_path.parent.mkdir(parents=True, exist_ok=True)
    log_path = Path(case.get("log_path") or result_path.with_suffix(".log")).resolve()

    run_label = f"{case['id']}_{time.strftime('%Y%m%d_%H%M%S')}"
    cmd = case["command"].format(output_csv=str(result_path), run_label=run_label)
    timeout_seconds = int(case.get("timeout_seconds", 7200))

    env = os.environ.copy()
    if case.get("env"):
        env.update({str(k): str(v) for k, v in case["env"].items()})

    log_path.parent.mkdir(parents=True, exist_ok=True)
    quiet = bool(case.get("quiet", True))
    with log_path.open("w", encoding="utf-8") as log:
        log.write(f"Command: {cmd}\n")
        log.write(f"Started: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        log.flush()

        proc = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            bufsize=1,
        )
        start = time.time()
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
                if time.time() - start > timeout_seconds:
                    proc.terminate()
                    log.write("\nTIMEOUT reached; process terminated.\n")
                    log.flush()
                    return 124
        finally:
            if proc.stdout:
                proc.stdout.close()

        log.write(f"\nFinished: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        log.write(f"Exit code: {proc.returncode}\n")
        log.flush()

    return int(proc.returncode or 0)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an LLM test case and update its last-result CSV.")
    parser.add_argument("--case-id", help="Case id from cases/registries/archive/llm_cases.json")
    parser.add_argument(
        "--cases",
        default="cases/registries/archive/llm_cases.json",
        help="Path to LLM cases registry (default: cases/registries/archive/llm_cases.json)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available case ids and their commands",
    )
    args = parser.parse_args()

    cases = load_cases(Path(args.cases))
    if args.list:
        for case in cases:
            case_id = case.get("id", "<missing-id>")
            cmd = case.get("command", "<missing-command>")
            print(f"{case_id}: {cmd}")
        return

    if not args.case_id:
        raise SystemExit("Missing --case-id (or use --list to see available cases).")

    case = _find_case(cases, args.case_id)
    code = run_case(case)
    if code != 0:
        log_path = Path(case.get("log_path") or Path(case["result_csv_path"]).with_suffix(".log")).resolve()
        print(f"LLM case failed (exit={code}). See log: {log_path}")
        raise SystemExit(code)


if __name__ == "__main__":
    main()
