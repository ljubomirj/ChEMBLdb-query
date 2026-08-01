#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from difflib import SequenceMatcher
from pathlib import Path
from statistics import mean
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from compressed_io import read_json_maybe_compressed, read_text_maybe_compressed


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit generated v5 artifacts in a run workspace.")
    parser.add_argument("--run-root", required=True, help="Run workspace root under experiments/v5_runs")
    parser.add_argument("--out-json", default=None, help="Optional JSON output path")
    parser.add_argument("--out-md", default=None, help="Optional Markdown output path")
    args = parser.parse_args()

    run_root = Path(args.run_root)
    records = sorted(run_root.glob("*/*.generated_artifact_record.json"))
    rows: list[dict[str, Any]] = []
    for record_path in records:
        record = read_json_maybe_compressed(record_path)
        source_manifest = read_json_maybe_compressed(Path(record["source_manifest_path"]))
        written = record["written_paths"]

        row = {
            "case_id": record["case_id"],
            "step": record["step"],
        }
        if "up_exec" in written:
            generated_up = _read_repo_path(written["up_exec"])
            gold_uq = _read_repo_path(source_manifest["artifacts"]["uq_surface"])
            spec_uq = _read_repo_path_optional(source_manifest["artifacts"].get("uq_benchmark_spec"))
            row["uq_vs_generated_up"] = _sim(gold_uq, generated_up)
            row["spec_vs_generated_up"] = _sim(spec_uq, generated_up)
        if "sql" in written:
            generated_sql = _read_repo_path(written["sql"])
            gold_sql = _read_repo_path_optional(source_manifest["artifacts"].get("sql_gold") or source_manifest["artifacts"].get("sqlite_sql"))
            row["gold_sql_vs_generated_sql"] = _sim(gold_sql, generated_sql)
        if "uq_surface" in written:
            generated_uq = _read_repo_path(written["uq_surface"])
            gold_uq = _read_repo_path(source_manifest["artifacts"]["uq_surface"])
            spec_uq = _read_repo_path_optional(source_manifest["artifacts"].get("uq_benchmark_spec"))
            row["gold_uq_vs_generated_uq"] = _sim(gold_uq, generated_uq)
            row["spec_uq_vs_generated_uq"] = _sim(spec_uq, generated_uq)
        step_output = _read_json_optional(written.get("step_output_json"))
        if isinstance(step_output, dict) and isinstance(step_output.get("deterministic_score"), dict):
            row["deterministic_status"] = step_output["deterministic_score"].get("status")
            row["deterministic_score"] = step_output["deterministic_score"].get("score")
        rows.append(row)

    summary = _summarize(rows)
    out_json = Path(args.out_json) if args.out_json else run_root / "generated_artifact_audit.json"
    out_md = Path(args.out_md) if args.out_md else run_root / "generated_artifact_audit.md"
    out_json.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2) + "\n")
    out_md.write_text(_render_markdown(summary, rows))
    print(json.dumps({"out_json": str(out_json.resolve()), "out_md": str(out_md.resolve()), "summary": summary}, indent=2))


def _read_repo_path(path_value: str) -> str:
    return read_text_maybe_compressed(REPO_ROOT / path_value).strip()


def _read_repo_path_optional(path_value: str | None) -> str | None:
    if not path_value:
        return None
    path = REPO_ROOT / path_value
    from compressed_io import read_candidates

    if not any(candidate.exists() for candidate in read_candidates(path)):
        return None
    return read_text_maybe_compressed(path).strip()


def _sim(left: str | None, right: str | None) -> float | None:
    if not left or not right:
        return None
    return round(SequenceMatcher(None, left, right).ratio(), 6)


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    keys = [
        "uq_vs_generated_up",
        "spec_vs_generated_up",
        "gold_sql_vs_generated_sql",
        "gold_uq_vs_generated_uq",
        "spec_uq_vs_generated_uq",
    ]
    summary: dict[str, Any] = {"n_rows": len(rows)}
    for key in keys:
        values = [row[key] for row in rows if row.get(key) is not None]
        summary[f"{key}_mean"] = round(mean(values), 6) if values else None
        summary[f"{key}_ge_095"] = sum(1 for value in values if value >= 0.95)
    return summary


def _read_json_optional(path_value: str | None) -> dict[str, Any] | None:
    if not path_value:
        return None
    path = REPO_ROOT / path_value
    from compressed_io import read_candidates

    if not any(candidate.exists() for candidate in read_candidates(path)):
        return None
    value = read_json_maybe_compressed(path)
    return value if isinstance(value, dict) else None


def _render_markdown(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    lines = [
        "# v5 Generated Artifact Audit",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Rows", ""])
    for row in rows:
        lines.append(f"- {json.dumps(row, sort_keys=True)}")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
