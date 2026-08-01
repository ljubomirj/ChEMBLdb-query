#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from difflib import SequenceMatcher
from pathlib import Path
from statistics import mean
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST_DIR = REPO_ROOT / "tests/v5_manifests/web_scrape_hq"


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit v5 case manifests and artifact similarity.")
    parser.add_argument("--manifest-dir", default=str(DEFAULT_MANIFEST_DIR), help="Directory containing v5 case manifests")
    parser.add_argument("--limit", type=int, default=None, help="Optional cap on manifest count")
    parser.add_argument("--out-json", default=str(REPO_ROOT / "experiments" / "v5_case_audit.json"), help="Output JSON path")
    parser.add_argument("--out-md", default=str(REPO_ROOT / "experiments" / "v5_case_audit.md"), help="Output Markdown path")
    args = parser.parse_args()

    manifest_dir = Path(args.manifest_dir)
    manifest_paths = sorted(manifest_dir.glob("*.json"))
    if args.limit:
        manifest_paths = manifest_paths[: args.limit]

    rows: list[dict[str, Any]] = []
    for manifest_path in manifest_paths:
        manifest = json.loads(manifest_path.read_text())
        artifacts = manifest["artifacts"]
        metadata = manifest["metadata"]
        uq_surface = _read_optional(artifacts.get("uq_surface"))
        up_exec = _read_optional(artifacts.get("up_exec"))
        benchmark_spec = _read_optional(artifacts.get("uq_benchmark_spec"))
        rows.append(
            {
                "case_id": manifest["case_id"],
                "family": metadata["family"],
                "realism_level": metadata["realism_level"],
                "uq_up_similarity": _sim(uq_surface, up_exec),
                "uq_spec_similarity": _sim(uq_surface, benchmark_spec),
                "up_spec_similarity": _sim(up_exec, benchmark_spec),
                "has_up_exec": bool(up_exec),
                "has_benchmark_spec": bool(benchmark_spec),
            }
        )

    summary = _summarize(rows)
    out_json = Path(args.out_json)
    out_md = Path(args.out_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps({"summary": summary, "cases": rows}, indent=2) + "\n")
    out_md.write_text(_render_markdown(summary, rows))
    print(json.dumps({"out_json": str(out_json.resolve()), "out_md": str(out_md.resolve()), "summary": summary}, indent=2))


def _read_optional(path_value: object) -> str | None:
    if not path_value:
        return None
    path = REPO_ROOT / str(path_value)
    if not path.exists():
        return None
    return path.read_text().strip()


def _sim(left: str | None, right: str | None) -> float | None:
    if not left or not right:
        return None
    return round(SequenceMatcher(None, left, right).ratio(), 6)


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    uq_up = [row["uq_up_similarity"] for row in rows if row["uq_up_similarity"] is not None]
    uq_spec = [row["uq_spec_similarity"] for row in rows if row["uq_spec_similarity"] is not None]
    up_spec = [row["up_spec_similarity"] for row in rows if row["up_spec_similarity"] is not None]
    return {
        "n_cases": len(rows),
        "n_with_up_exec": sum(1 for row in rows if row["has_up_exec"]),
        "n_with_benchmark_spec": sum(1 for row in rows if row["has_benchmark_spec"]),
        "uq_up_mean_similarity": round(mean(uq_up), 6) if uq_up else None,
        "uq_spec_mean_similarity": round(mean(uq_spec), 6) if uq_spec else None,
        "up_spec_mean_similarity": round(mean(up_spec), 6) if up_spec else None,
        "uq_up_high_similarity_ge_095": sum(1 for value in uq_up if value >= 0.95),
        "uq_spec_high_similarity_ge_095": sum(1 for value in uq_spec if value >= 0.95),
    }


def _render_markdown(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    top_uq_spec = sorted(
        [row for row in rows if row["uq_spec_similarity"] is not None],
        key=lambda row: row["uq_spec_similarity"],
        reverse=True,
    )[:20]
    lines = [
        "# v5 Case Audit",
        "",
        "## Summary",
        "",
        f"- Cases: {summary['n_cases']}",
        f"- With `up_exec`: {summary['n_with_up_exec']}",
        f"- With `uq_benchmark_spec`: {summary['n_with_benchmark_spec']}",
        f"- Mean `uq_surface ~ up_exec` similarity: {summary['uq_up_mean_similarity']}",
        f"- Mean `uq_surface ~ uq_benchmark_spec` similarity: {summary['uq_spec_mean_similarity']}",
        f"- Mean `up_exec ~ uq_benchmark_spec` similarity: {summary['up_spec_mean_similarity']}",
        f"- `uq_surface ~ up_exec >= 0.95`: {summary['uq_up_high_similarity_ge_095']}",
        f"- `uq_surface ~ uq_benchmark_spec >= 0.95`: {summary['uq_spec_high_similarity_ge_095']}",
        "",
        "## Highest `uq_surface ~ uq_benchmark_spec` cases",
        "",
    ]
    for row in top_uq_spec:
        lines.append(
            f"- {row['case_id']}: family={row['family']} realism={row['realism_level']} uq_spec_similarity={row['uq_spec_similarity']}"
        )
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
