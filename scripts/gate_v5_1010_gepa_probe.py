#!/usr/bin/env python3
"""Decide whether a v5.1010 stratified GEPA probe is safe to scale to full 1010."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def main() -> None:
    parser = argparse.ArgumentParser(description="Gate full v5.1010 GEPA after stratified probe.")
    parser.add_argument("--baseline-report", required=True)
    parser.add_argument("--gepa-summary", required=True)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    baseline = json.loads(Path(args.baseline_report).read_text())
    gepa_summary = json.loads(Path(args.gepa_summary).read_text())
    probe_report = gepa_summary["test_report"]

    baseline_summary = baseline["summary"]
    probe_summary = probe_report["summary"]
    probe_errors = [
        row
        for row in probe_report.get("cases", [])
        if row.get("status") == "run_failed" or row.get("error")
    ]
    decision = {
        "baseline_report": str(Path(args.baseline_report).resolve()),
        "gepa_summary": str(Path(args.gepa_summary).resolve()),
        "baseline_summary": baseline_summary,
        "probe_summary": probe_summary,
        "probe_error_count": len(probe_errors),
        "n_cases_match": int(baseline_summary["n_cases"]) == int(probe_summary["n_cases"]),
        "pass_rate_non_regression": int(probe_summary["n_pass"]) >= int(baseline_summary["n_pass"]),
        "mean_score_non_regression": float(probe_summary["mean_score"]) >= float(baseline_summary["mean_score"]),
        "safe_to_scale": False,
    }
    decision["safe_to_scale"] = bool(
        decision["n_cases_match"]
        and decision["pass_rate_non_regression"]
        and decision["mean_score_non_regression"]
        and len(probe_errors) == 0
    )

    if args.out:
        Path(args.out).write_text(json.dumps(decision, indent=2) + "\n")
    print(json.dumps(decision, indent=2))
    raise SystemExit(0 if decision["safe_to_scale"] else 1)


if __name__ == "__main__":
    main()
