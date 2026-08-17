#!/usr/bin/env python3
"""Evaluate a v4 prompt-pack candidate against executable ChEMBL benchmark cases."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import polars as pl

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.helpers.chembl_asserts import (
    assert_frames_equal,
    execute_sql,
    load_cases,
    normalize_df,
    read_csv_maybe_zstd,
)
DEFAULT_SPLIT_PATH = REPO_ROOT / "experiments" / "case_splits_v4.1.json"
DEFAULT_EVAL_ROOT = REPO_ROOT / "experiments" / "evals"
DEFAULT_V4_SCRIPT = REPO_ROOT / "src" / "db_llm_query_v4.py"

CASE_REGISTRIES = {
    "faq_hq": REPO_ROOT / "tests" / "cases" / "faq_hq_cases.json",
    "web_scrape_hq": REPO_ROOT / "tests" / "cases" / "web_scrape_hq_cases.json",
    "web_scrape_large": REPO_ROOT / "tests" / "cases" / "web_scrape_large_cases.json",
}


def _load_case_catalog() -> dict[tuple[str, str], dict[str, Any]]:
    catalog: dict[tuple[str, str], dict[str, Any]] = {}
    for corpus, path in CASE_REGISTRIES.items():
        for case in load_cases(path):
            key = (corpus, str(case["id"]))
            if key in catalog:
                raise ValueError(f"Duplicate case key: {key}")
            item = dict(case)
            item["corpus"] = corpus
            catalog[key] = item
    return catalog


def _load_split_file(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _rename_actual_columns(actual: pl.DataFrame, rename_map: dict[str, str] | None) -> pl.DataFrame:
    if not rename_map:
        return actual
    actual_cols = set(actual.columns)
    used_dests: set[str] = set()
    safe_map: dict[str, str] = {}
    for src, dst in rename_map.items():
        if src not in actual_cols:
            continue
        if dst in actual_cols and dst != src:
            continue
        if dst in used_dests and dst != src:
            continue
        safe_map[src] = dst
        used_dests.add(dst)
    if safe_map:
        actual = actual.rename(safe_map)
    return actual


def _ground_truth_csv_path(case: dict[str, Any]) -> Path:
    return Path(case["sqlite_sql_path"]).with_name("ground-truth.csv")


def _load_expected_frame(case: dict[str, Any]) -> pl.DataFrame:
    db_path = REPO_ROOT / case["db_path"]
    sql_path = REPO_ROOT / case["sqlite_sql_path"]
    ground_truth_path = REPO_ROOT / _ground_truth_csv_path(case)
    if ground_truth_path.exists() or ground_truth_path.with_name(ground_truth_path.name + ".zst").exists():
        return read_csv_maybe_zstd(ground_truth_path)
    return execute_sql(db_path=db_path, sql=sql_path.read_text(), temp_table=case.get("temp_table"))


def _parse_log_snippets(log_path: Path) -> dict[str, Any]:
    if not log_path.exists():
        return {}
    text = log_path.read_text(encoding="utf-8", errors="replace")
    sql_text: Optional[str] = None
    judge_text: Optional[str] = None

    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if "Generated SQL_" in line:
            for j in range(idx + 1, min(idx + 8, len(lines))):
                candidate = lines[j].strip()
                if not candidate or candidate.endswith("===================="):
                    continue
                if candidate.startswith("SELECT") or candidate.startswith("WITH"):
                    sql_text = candidate
                    break
        if re.search(r"\bJ_\d+:\s*$", line):
            if idx + 1 < len(lines):
                candidate = lines[idx + 1].strip()
                if candidate.startswith("{"):
                    judge_text = candidate
    return {
        "generated_sql": sql_text,
        "judge_text": judge_text,
    }


def _result_output_paths(eval_root: Path, split_name: str, case: dict[str, Any]) -> tuple[Path, Path]:
    case_dir = eval_root / split_name / case["corpus"] / case["id"]
    case_dir.mkdir(parents=True, exist_ok=True)
    return case_dir / "result.csv", case_dir / "run.log"


def _has_explicit_verbosity(args: list[str]) -> bool:
    for arg in args:
        if arg == "--verbose" or arg.startswith("--verbose="):
            return True
        if arg.startswith("-") and len(arg) > 1 and set(arg[1:]) == {"v"}:
            return True
    return False


def _run_live_case(
    *,
    case: dict[str, Any],
    split_name: str,
    prompt_pack_path: Path,
    eval_root: Path,
    v4_script: Path,
    db_llm_args: list[str],
    quiet: bool,
    run_prefix: str,
) -> tuple[int, Path, Path]:
    result_path, log_path = _result_output_paths(eval_root, split_name, case)
    run_label = f"{run_prefix}_{case['id']}_{time.strftime('%Y%m%d_%H%M%S')}"
    effective_args = list(db_llm_args)
    if not _has_explicit_verbosity(effective_args):
        effective_args = ["-vv", *effective_args]
    cmd = [
        "uv",
        "run",
        "python",
        str(v4_script),
        "-f",
        "csv",
        "--run-label",
        run_label,
        "--output-file",
        str(result_path.resolve()),
        "--prompt-pack-path",
        str(prompt_pack_path.resolve()),
        "-q",
        str(case["uq"]),
        *effective_args,
    ]

    with log_path.open("w", encoding="utf-8") as log:
        log.write(f"Command: {' '.join(cmd)}\n")
        log.write(f"Started: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        log.write(f"Case: {case['id']}\n")
        log.write(f"Corpus: {case['corpus']}\n")
        log.write(f"Prompt pack: {prompt_pack_path}\n")
        log.write(f"UQ: {case['uq']}\n\n")
        log.flush()
        proc = subprocess.Popen(
            cmd,
            cwd=str(REPO_ROOT),
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
    return int(proc.returncode or 0), result_path, log_path


def _score_case(case: dict[str, Any], actual_path: Path) -> dict[str, Any]:
    expected = _load_expected_frame(case)
    actual = pl.read_csv(actual_path, infer_schema_length=10_000)

    normalize = case.get("normalize", {})
    lowercase_columns = bool(normalize.get("lowercase_columns", False))
    strip_values = bool(normalize.get("strip_values", False))
    lowercase_values = normalize.get("lowercase_values", [])
    float_cols = case.get("float_cols", [])
    int_cols = case.get("int_cols", [])
    sort_keys = case.get("sort_keys")
    rename_map = case.get("column_rename_map")

    if lowercase_columns:
        float_cols = [c.lower() for c in float_cols]
        int_cols = [c.lower() for c in int_cols]
        lowercase_values = [c.lower() for c in lowercase_values]
        if sort_keys:
            sort_keys = [c.lower() for c in sort_keys]
        if rename_map:
            rename_map = {k.lower(): v.lower() for k, v in rename_map.items()}

    actual = _rename_actual_columns(actual, rename_map)
    actual = normalize_df(
        actual,
        lowercase_columns=lowercase_columns,
        strip_values=strip_values,
        lowercase_values=lowercase_values,
        float_cols=float_cols,
        int_cols=int_cols,
    )
    expected = normalize_df(
        expected,
        lowercase_columns=lowercase_columns,
        strip_values=strip_values,
        lowercase_values=lowercase_values,
        float_cols=float_cols,
        int_cols=int_cols,
    )

    expected_cols = list(expected.columns)
    actual_cols = list(actual.columns)
    missing_cols = [col for col in expected_cols if col not in actual_cols]
    extra_cols = [col for col in actual_cols if col not in expected_cols]
    expected_rows = int(expected.height)
    actual_rows = int(actual.height)

    result: dict[str, Any] = {
        "expected_rows": expected_rows,
        "actual_rows": actual_rows,
        "expected_cols": expected_cols,
        "actual_cols": actual_cols,
        "missing_cols": missing_cols,
        "extra_cols": extra_cols,
    }

    if not missing_cols:
        actual = actual.select(expected_cols)
        if sort_keys is None:
            sort_keys = list(expected_cols)
        actual = actual.sort(sort_keys)
        expected = expected.sort(sort_keys)
        try:
            assert_frames_equal(actual, expected, float_cols=float_cols, float_tol=float(case.get("float_tol", 1e-6)))
            result.update({"status": "pass", "score": 1.0})
            return result
        except AssertionError as exc:
            result["compare_error"] = str(exc)

    col_recall = 0.0 if not expected_cols else (len(expected_cols) - len(missing_cols)) / len(expected_cols)
    if expected_rows <= 0 and actual_rows <= 0:
        row_ratio = 1.0
    elif expected_rows <= 0 or actual_rows <= 0:
        row_ratio = 0.0
    else:
        row_ratio = min(expected_rows, actual_rows) / max(expected_rows, actual_rows)
    score = round(0.6 * col_recall + 0.4 * row_ratio, 6)
    if "compare_error" in result:
        score = min(score, 0.85)
    result.update({
        "status": "partial" if score > 0 else "fail",
        "score": score,
        "column_recall": round(col_recall, 6),
        "row_ratio": round(row_ratio, 6),
    })
    return result


def _case_ref_key(item: dict[str, Any]) -> tuple[str, str]:
    return str(item["corpus"]), str(item["id"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a v4 prompt-pack candidate against executable benchmark cases.")
    parser.add_argument("--split-file", default=str(DEFAULT_SPLIT_PATH), help="Path to split definition JSON")
    parser.add_argument("--split", action="append", help="Split to run (repeatable). Default: train")
    parser.add_argument("--case-id", action="append", help="Restrict to specific case ids inside the selected splits")
    parser.add_argument("--list-splits", action="store_true", help="List available splits and counts")
    parser.add_argument("--reuse-existing", action="store_true", help="Score existing fixture result-last.csv files instead of running v4")
    parser.add_argument("--prompt-pack-path", default=str(REPO_ROOT / "experiments" / "prompt_pack_v4.0.yaml"), help="Prompt-pack YAML path")
    parser.add_argument("--eval-root", default=str(DEFAULT_EVAL_ROOT), help="Root directory for evaluation outputs")
    parser.add_argument("--db-llm-script", default=str(DEFAULT_V4_SCRIPT), help="Path to db_llm_query_v4.py")
    parser.add_argument("--eval-label", default=None, help="Optional label for this evaluation batch")
    parser.add_argument("--max-cases", type=int, default=None, help="Cap number of cases per selected split")
    parser.add_argument("--quiet", action="store_true", help="Suppress live stdout for live runs")
    parser.add_argument("db_llm_args", nargs=argparse.REMAINDER, help="Arguments passed through to db_llm_query_v4.py after '--'")
    args = parser.parse_args()

    split_data = _load_split_file(Path(args.split_file))
    splits: dict[str, list[dict[str, Any]]] = split_data["splits"]
    if args.list_splits:
        for name, items in splits.items():
            print(f"{name}: {len(items)}")
        return

    selected_splits = args.split or ["train"]
    for split_name in selected_splits:
        if split_name not in splits:
            raise SystemExit(f"Unknown split: {split_name}")

    db_llm_args = list(args.db_llm_args)
    if db_llm_args and db_llm_args[0] == "--":
        db_llm_args = db_llm_args[1:]
    if not args.reuse_existing and not db_llm_args:
        raise SystemExit("Live evaluation requires db_llm_query_v4 arguments after '--'.")

    catalog = _load_case_catalog()
    eval_label = args.eval_label or f"eval_{Path(args.prompt_pack_path).stem}_{time.strftime('%Y%m%d_%H%M%S')}"
    eval_root = Path(args.eval_root).resolve() / eval_label
    eval_root.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "eval_label": eval_label,
        "prompt_pack_path": str(Path(args.prompt_pack_path).resolve()),
        "split_file": str(Path(args.split_file).resolve()),
        "reuse_existing": bool(args.reuse_existing),
        "db_llm_script": str(Path(args.db_llm_script).resolve()),
        "db_llm_args": db_llm_args,
        "splits": {},
    }

    selected_case_ids = set(args.case_id or [])
    overall_scores: list[float] = []
    overall_passes = 0
    overall_cases = 0

    for split_name in selected_splits:
        items = list(splits[split_name])
        if selected_case_ids:
            items = [item for item in items if str(item["id"]) in selected_case_ids]
        if args.max_cases is not None:
            items = items[: max(0, int(args.max_cases))]

        split_results: list[dict[str, Any]] = []
        for item in items:
            key = _case_ref_key(item)
            case = catalog.get(key)
            if case is None:
                raise SystemExit(f"Case not found in catalog: {key}")

            if args.reuse_existing:
                result_path = REPO_ROOT / case["result_csv_path"]
                log_path = REPO_ROOT / (case.get("log_path") or case["result_csv_path"].replace(".csv", ".log"))
                run_exit = 0 if result_path.exists() else 1
            else:
                run_exit, result_path, log_path = _run_live_case(
                    case=case,
                    split_name=split_name,
                    prompt_pack_path=Path(args.prompt_pack_path),
                    eval_root=eval_root,
                    v4_script=Path(args.db_llm_script),
                    db_llm_args=db_llm_args,
                    quiet=bool(args.quiet),
                    run_prefix=eval_label,
                )

            case_result: dict[str, Any] = {
                "corpus": case["corpus"],
                "id": case["id"],
                "uq": case["uq"],
                "run_exit_code": int(run_exit),
                "result_path": str(result_path.resolve()),
                "log_path": str(log_path.resolve()),
            }
            case_result.update(_parse_log_snippets(log_path))

            if run_exit != 0 or not result_path.exists():
                case_result.update({
                    "status": "run_failed",
                    "score": 0.0,
                })
            else:
                case_result.update(_score_case(case, result_path))

            split_results.append(case_result)
            overall_scores.append(float(case_result["score"]))
            overall_cases += 1
            if case_result["status"] == "pass":
                overall_passes += 1

        pass_count = sum(1 for item in split_results if item["status"] == "pass")
        split_score = sum(float(item["score"]) for item in split_results) / len(split_results) if split_results else 0.0
        report["splits"][split_name] = {
            "n_cases": len(split_results),
            "n_pass": pass_count,
            "pass_rate": round(pass_count / len(split_results), 6) if split_results else 0.0,
            "mean_score": round(split_score, 6),
            "cases": split_results,
        }

    report["summary"] = {
        "n_cases": overall_cases,
        "n_pass": overall_passes,
        "pass_rate": round(overall_passes / overall_cases, 6) if overall_cases else 0.0,
        "mean_score": round(sum(overall_scores) / overall_cases, 6) if overall_cases else 0.0,
    }

    report_path = eval_root / "report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "report_path": str(report_path.resolve()),
        "summary": report["summary"],
    }, indent=2))


if __name__ == "__main__":
    main()
