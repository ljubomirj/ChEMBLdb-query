#!/usr/bin/env python3
"""Expand the executable target_pchembl corpus from the current registry toward 1000 cases."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sqlite3
import subprocess
from pathlib import Path
from typing import Iterable


BASE_DIR = Path("/Users/ljubomir/ChEMBLdb-query")
DB_PATH = BASE_DIR / "database/latest/chembl_36/chembl_36_sqlite/chembl_36.db"
MAIN_CASES = BASE_DIR / "tests/cases/web_scrape_hq_cases.json"
DEFAULT_SNAPSHOT = BASE_DIR / "tests/cases/web_scrape_hq_cases_v4.7.json"
FIXTURES_BASE = BASE_DIR / "tests/fixtures"
DEFAULT_SUMMARY_PATH = BASE_DIR / "experiments/v4.7_expansion_to_1000_summary.json"
DEFAULT_REPORT_PATH = BASE_DIR / "experiments/v4.7_to_1000_report.md"


def _load_cases(path: Path) -> list[dict]:
    return json.loads(path.read_text())


def _select_candidates(existing_ids: set[str], *, target_count: int) -> list[tuple[str, str, str]]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT DISTINCT td.chembl_id, td.pref_name
        FROM target_dictionary td
        JOIN assays a ON td.tid = a.tid
        JOIN activities act ON a.assay_id = act.assay_id
        WHERE td.target_type = 'SINGLE PROTEIN'
          AND td.tax_id = '9606'
          AND act.standard_type = 'IC50'
          AND act.pchembl_value IS NOT NULL
        ORDER BY td.chembl_id
        LIMIT ?
        """,
        (target_count * 12,),
    )
    rows = cur.fetchall()
    conn.close()

    candidates: list[tuple[str, str, str]] = []
    for chembl_id, pref_name in rows:
        case_id = f"chembl_downloader_target_{chembl_id.lower()}_ic50_human_pchembl"
        if case_id in existing_ids:
            continue
        candidates.append((chembl_id, pref_name, case_id))
        if len(candidates) >= target_count:
            break
    return candidates


def _write_csv(sql: str, out_csv: Path) -> int:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(sql)
        cols = [d[0] for d in cur.description]
        n_rows = 0
        with out_csv.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=cols, quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()
            for row in cur:
                n_rows += 1
                writer.writerow({c: "" if row[c] is None else str(row[c]) for c in cols})
        return n_rows
    finally:
        conn.close()


def _round_numbers(*, count: int, round_base: int, cases_per_round: int) -> Iterable[int]:
    for idx in range(count):
        yield round_base + (idx // cases_per_round)


def _case_entry(*, round_num: int, case_id: str, uq: str, fixture_dir: Path) -> dict:
    return {
        "id": case_id,
        "uq": uq,
        "source_url": "https://github.com/cthoyt/chembl-downloader/blob/main/src/chembl_downloader/queries.py",
        "source_sql_path": f"tests/fixtures/web_scrape{round_num}/{case_id}/source.sql",
        "sqlite_sql_path": f"tests/fixtures/web_scrape{round_num}/{case_id}/sqlite.sql",
        "result_csv_path": f"tests/fixtures/web_scrape{round_num}/{case_id}/result-last.csv",
        "log_path": f"tests/fixtures/web_scrape{round_num}/{case_id}/run-last.log",
        "db_path": "database/latest/chembl_36/chembl_36_sqlite/chembl_36.db",
        "size_class": "medium",
        "sort_keys": [
            "molecule_chembl_id",
            "assay_chembl_id",
            "canonical_smiles",
            "target_type",
            "tax_id",
            "standard_type",
            "pchembl_value",
        ],
        "column_rename_map": {
            "assay_chembl_id": "assay_chembl_id",
            "chembl_id": "molecule_chembl_id",
            "molecule_chembl_id": "molecule_chembl_id",
            "canonical_smiles": "canonical_smiles",
            "target_type": "target_type",
            "tax_id": "tax_id",
            "standard_type": "standard_type",
            "pchembl_value": "pchembl_value",
        },
        "normalize": {"lowercase_columns": True, "strip_values": True, "lowercase_values": []},
        "benchmark_spec_uq_path": str((fixture_dir / "benchmark_spec_uq.txt").resolve()),
        "uq_style": "realistic_uq",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the next target_pchembl wave toward 1000 executable cases.")
    parser.add_argument("--new-cases", type=int, default=500, help="Number of new executable cases to add")
    parser.add_argument("--target-rows-limit", type=int, default=1000, help="LIMIT for each target export query")
    parser.add_argument("--round-base", type=int, default=46, help="Starting fixture round number")
    parser.add_argument("--cases-per-round", type=int, default=25, help="How many cases to place in each fixture round")
    parser.add_argument("--snapshot-path", default=str(DEFAULT_SNAPSHOT), help="Snapshot case registry path")
    parser.add_argument("--summary-path", default=str(DEFAULT_SUMMARY_PATH), help="Summary JSON output")
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT_PATH), help="Markdown report output")
    args = parser.parse_args()

    cases = _load_cases(MAIN_CASES)
    existing_ids = {case["id"] for case in cases}
    previous_total = len(cases)

    candidates = _select_candidates(existing_ids, target_count=int(args.new_cases))
    if len(candidates) < int(args.new_cases):
        raise SystemExit(f"Requested {args.new_cases} new cases but only found {len(candidates)} eligible targets.")

    summary: dict[str, object] = {
        "previous_total": previous_total,
        "requested_new_cases": int(args.new_cases),
        "target_rows_limit": int(args.target_rows_limit),
        "round_base": int(args.round_base),
        "cases_per_round": int(args.cases_per_round),
        "targets": [],
    }

    new_entries: list[dict] = []
    for idx, ((chembl_id, pref_name, case_id), round_num) in enumerate(
        zip(candidates, _round_numbers(count=len(candidates), round_base=int(args.round_base), cases_per_round=int(args.cases_per_round))),
        start=1,
    ):
        fixture_dir = FIXTURES_BASE / f"web_scrape{round_num}" / case_id
        fixture_dir.mkdir(parents=True, exist_ok=True)

        sql = f"""SELECT
    ASSAYS.chembl_id AS assay_chembl_id,
    TARGET_DICTIONARY.target_type,
    TARGET_DICTIONARY.tax_id,
    COMPOUND_STRUCTURES.canonical_smiles,
    MOLECULE_DICTIONARY.chembl_id AS molecule_chembl_id,
    ACTIVITIES.standard_type,
    ACTIVITIES.pchembl_value
FROM TARGET_DICTIONARY
JOIN ASSAYS ON TARGET_DICTIONARY.tid = ASSAYS.tid
JOIN ACTIVITIES ON ASSAYS.assay_id = ACTIVITIES.assay_id
JOIN MOLECULE_DICTIONARY ON MOLECULE_DICTIONARY.molregno = ACTIVITIES.molregno
JOIN COMPOUND_STRUCTURES ON MOLECULE_DICTIONARY.molregno = COMPOUND_STRUCTURES.molregno
WHERE TARGET_DICTIONARY.chembl_id = '{chembl_id}'
  AND ACTIVITIES.pchembl_value IS NOT NULL
  AND TARGET_DICTIONARY.target_type = 'SINGLE PROTEIN'
  AND ACTIVITIES.standard_relation = '='
  AND ACTIVITIES.standard_type = 'IC50'
  AND TARGET_DICTIONARY.tax_id = '9606'
ORDER BY molecule_chembl_id, assay_chembl_id
LIMIT {int(args.target_rows_limit)}
"""
        uq = (
            f"Show the first {int(args.target_rows_limit)} IC50 activity rows with pChEMBL values for the human "
            f"single-protein target {chembl_id} ({pref_name}). Return assay ChEMBL ID, target type, tax_id, "
            f"canonical SMILES, molecule ChEMBL ID, standard type, and pChEMBL value. Use only exact standard "
            f"relation '=' rows with non-null pChEMBL values, and order the results by molecule ChEMBL ID and assay ChEMBL ID."
        )
        benchmark_spec_uq = (
            f"Retrieve the first {int(args.target_rows_limit)} rows of assay_chembl_id, target_type, tax_id, "
            f"canonical_smiles, molecule_chembl_id, standard_type, and pchembl_value for IC50 activities on human "
            f"single protein target {chembl_id} ({pref_name}) with pchembl_value not null and standard_relation '='. "
            f"Order rows by molecule_chembl_id, assay_chembl_id."
        )
        metadata = {
            "id": case_id,
            "source_title": f"chembl_downloader target export for {chembl_id}",
            "source_url": "https://github.com/cthoyt/chembl-downloader/blob/main/src/chembl_downloader/queries.py",
            "uq_origin": "templated_from_sql",
            "uq_style": "realistic_uq",
            "uq_origin_kind": "templated_from_sql",
            "uq_path": f"tests/fixtures/web_scrape{round_num}/{case_id}/uq.txt",
            "benchmark_spec_uq_path": f"tests/fixtures/web_scrape{round_num}/{case_id}/benchmark_spec_uq.txt",
            "sql_path": f"tests/fixtures/web_scrape{round_num}/{case_id}/source.sql",
            "documentation_path": f"tests/fixtures/web_scrape{round_num}/{case_id}/documentation.txt",
        }

        (fixture_dir / "source.sql").write_text(sql)
        (fixture_dir / "sqlite.sql").write_text(sql)
        (fixture_dir / "uq.txt").write_text(uq + "\n")
        (fixture_dir / "benchmark_spec_uq.txt").write_text(benchmark_spec_uq + "\n")
        (fixture_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
        (fixture_dir / "documentation.txt").write_text(f"Target: {chembl_id} ({pref_name})\n")

        row_count = _write_csv(sql, fixture_dir / "ground-truth.csv")
        subprocess.run(
            ["zstd", "-f", str(fixture_dir / "ground-truth.csv"), "-o", str(fixture_dir / "ground-truth.csv.zst")],
            check=True,
            capture_output=True,
        )

        new_entries.append(_case_entry(round_num=round_num, case_id=case_id, uq=uq, fixture_dir=fixture_dir))
        summary["targets"].append({"id": case_id, "rows": row_count, "round": round_num})
        print(f"[{idx}/{len(candidates)}] {case_id} rows={row_count} round={round_num}", flush=True)

    cases.extend(new_entries)
    MAIN_CASES.write_text(json.dumps(cases, indent=2) + "\n")
    Path(args.snapshot_path).write_text(json.dumps(cases, indent=2) + "\n")

    summary["new_cases"] = len(new_entries)
    summary["new_total"] = len(cases)
    summary["round_count"] = math.ceil(len(new_entries) / int(args.cases_per_round))
    summary["round_range"] = [int(args.round_base), int(args.round_base) + summary["round_count"] - 1]
    Path(args.summary_path).write_text(json.dumps(summary, indent=2) + "\n")

    report_lines = [
        "# V4.7 Dataset Expansion To 1000",
        "",
        f"- Previous total: {previous_total}",
        f"- New target cases: {summary['new_cases']}",
        f"- New total: {summary['new_total']}",
        f"- Target rows limit: {args.target_rows_limit}",
        f"- Fixture rounds: `web_scrape{summary['round_range'][0]}`-`web_scrape{summary['round_range'][1]}`",
        "",
        "This expansion continues the capped `target_pchembl` strategy that scaled the corpus cleanly to 500.",
        "All new cases are executable and preserve both `uq.txt` and `benchmark_spec_uq.txt`.",
    ]
    Path(args.report_path).write_text("\n".join(report_lines) + "\n")

    print(json.dumps({
        "previous_total": previous_total,
        "new_cases": len(new_entries),
        "new_total": len(cases),
        "round_range": summary["round_range"],
    }, indent=2))


if __name__ == "__main__":
    main()
