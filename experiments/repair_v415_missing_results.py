#!/usr/bin/env python3
"""Repair v4.15 evaluation cases that failed after SQL generation but before result.csv.

This script re-executes `generated_sql` captured in the original evaluation
report, materializes results with the current patched `db_llm_query_v4` row
builder, and rescoring those cases without any new LLM calls.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiments.evaluate_prompt_pack_v4 import _load_case_catalog, _score_case
from src.db_llm_query_v4 import ChEMBLLLMQuery

ORIG_REPORT = REPO_ROOT / "experiments/evals/v4.15_on_v4.7_1000/eval_prompt_pack_v4.15_20260320_v47_1000/report.json"
OUT_ROOT = REPO_ROOT / "experiments/evals/v4.15_on_v4.7_1000_repaired"
OUT_REPORT = OUT_ROOT / "report.json"


def _result_output_path(split: str, corpus: str, case_id: str) -> Path:
    return OUT_ROOT / split / corpus / case_id / "result.csv"


def _repair_case(case: dict[str, Any], case_catalog: dict[tuple[str, str], dict[str, Any]], split: str) -> tuple[dict[str, Any], bool]:
    result_path = case.get("result_path")
    if result_path and Path(result_path).exists():
        return case, False

    generated_sql = case.get("generated_sql")
    if not generated_sql:
        return case, False

    key = (case["corpus"], str(case["id"]))
    case_def = case_catalog[key]
    db_path = REPO_ROOT / case_def["db_path"]
    out_path = _result_output_path(split, case["corpus"], case["id"])
    out_path.parent.mkdir(parents=True, exist_ok=True)

    repaired_case = dict(case)
    repaired_case["repair_mode"] = "offline_sql_reexecute"
    repaired_case["repaired_from_report"] = str(ORIG_REPORT.resolve())

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.execute(str(generated_sql))
        rows = cur.fetchall()
        cols = [d[0] for d in (cur.description or [])]
        df = ChEMBLLLMQuery._rows_to_dataframe(rows, cols)
        df.write_csv(out_path)
        repaired_case.update(
            {
                "run_exit_code": 0,
                "result_path": str(out_path.resolve()),
                "repair_row_count": int(df.height),
            }
        )
        repaired_case.update(_score_case(case_def, out_path))
        return repaired_case, True
    except Exception as exc:
        repaired_case.update(
            {
                "status": "run_failed",
                "score": 0.0,
                "repair_error": str(exc),
                "result_path": str(out_path.resolve()),
            }
        )
        return repaired_case, True
    finally:
        try:
            conn.close()  # type: ignore[name-defined]
        except Exception:
            pass


def _repair_case_worker(payload: tuple[str, dict[str, Any]]) -> tuple[str, dict[str, Any], bool]:
    split, case = payload
    case_catalog = _load_case_catalog()
    repaired_case, changed = _repair_case(case, case_catalog, split)
    return split, repaired_case, changed


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair v4.15 evaluation cases that failed before result.csv materialization.")
    parser.add_argument("--max-workers", type=int, default=8, help="Parallel worker count for offline SQL re-execution")
    args = parser.parse_args()

    report = json.loads(ORIG_REPORT.read_text())
    repaired_count = 0
    improved_to_result = 0
    merged = {
        "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "eval_label": "eval_prompt_pack_v4.15_20260320_v47_1000_repaired",
        "prompt_pack_path": report["prompt_pack_path"],
        "split_file": report["split_file"],
        "reuse_existing": False,
        "db_llm_script": report["db_llm_script"],
        "db_llm_args": report["db_llm_args"],
        "repaired_from_report": str(ORIG_REPORT.resolve()),
        "repair_method": "offline_sql_reexecute_for_missing_result_cases",
        "splits": {},
    }

    work_items: list[tuple[str, dict[str, Any]]] = []
    passthrough_cases: dict[tuple[str, str, str], dict[str, Any]] = {}
    for split in ("train", "val", "test"):
        for case in report["splits"][split]["cases"]:
            result_path = case.get("result_path")
            if result_path and not Path(result_path).exists() and case.get("generated_sql"):
                work_items.append((split, case))
            else:
                passthrough_cases[(split, case["corpus"], case["id"])] = case

    repaired_cases: dict[tuple[str, str, str], dict[str, Any]] = {}
    if work_items:
        with concurrent.futures.ProcessPoolExecutor(max_workers=max(1, int(args.max_workers))) as executor:
            futures = [executor.submit(_repair_case_worker, item) for item in work_items]
            for future in concurrent.futures.as_completed(futures):
                split, repaired_case, changed = future.result()
                key = (split, repaired_case["corpus"], repaired_case["id"])
                repaired_cases[key] = repaired_case
                if changed:
                    repaired_count += 1
                    if repaired_case.get("status") != "run_failed":
                        improved_to_result += 1

    total_cases = total_pass = 0
    total_score = 0.0
    for split in ("train", "val", "test"):
        new_cases = []
        for case in report["splits"][split]["cases"]:
            key = (split, case["corpus"], case["id"])
            if key in repaired_cases:
                new_cases.append(repaired_cases[key])
            else:
                new_cases.append(passthrough_cases.get(key, case))

        n_cases = len(new_cases)
        n_pass = sum(1 for c in new_cases if c.get("status") == "pass")
        mean_score = sum(float(c.get("score", 0.0) or 0.0) for c in new_cases) / n_cases if n_cases else 0.0
        merged["splits"][split] = {
            "n_cases": n_cases,
            "n_pass": n_pass,
            "pass_rate": round(n_pass / n_cases, 6) if n_cases else 0.0,
            "mean_score": round(mean_score, 6),
            "cases": new_cases,
        }
        total_cases += n_cases
        total_pass += n_pass
        total_score += sum(float(c.get("score", 0.0) or 0.0) for c in new_cases)

    merged["summary"] = {
        "n_cases": total_cases,
        "n_pass": total_pass,
        "pass_rate": round(total_pass / total_cases, 6) if total_cases else 0.0,
        "mean_score": round(total_score / total_cases, 6) if total_cases else 0.0,
    }
    merged["repair_summary"] = {
        "cases_reprocessed": repaired_count,
        "cases_materialized": improved_to_result,
    }
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text(json.dumps(merged, indent=2) + "\n")
    print(
        json.dumps(
            {
                "report_path": str(OUT_REPORT.resolve()),
                "summary": merged["summary"],
                "repair_summary": merged["repair_summary"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
