#!/usr/bin/env python3
"""Large promoted web-scrape cases that compare live LLM runs against SQL ground truth."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from tests.helpers.chembl_asserts import (
    assert_frames_equal,
    execute_sql,
    load_cases,
    normalize_df,
    read_csv_maybe_zstd,
)


WEB_SCRAPE_LARGE_CASES = load_cases("cases/registries/archive/web_scrape_large_cases.json")


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


def _ground_truth_csv_path(case: dict) -> Path:
    return Path(case["sqlite_sql_path"]).with_name("ground-truth.csv")


@pytest.mark.parametrize(
    "case",
    [pytest.param(case, id=case["id"], marks=(pytest.mark.web_scrape_large,)) for case in WEB_SCRAPE_LARGE_CASES],
)
def test_web_scrape_large_result_matches_sql(case: dict) -> None:
    db_path = Path(case["db_path"])
    sql_path = Path(case["sqlite_sql_path"])
    result_path = Path(case["result_csv_path"])

    if not db_path.exists():
        pytest.skip(f"DB not found: {db_path}")
    if not sql_path.exists():
        pytest.skip(f"SQLite ground-truth SQL not found: {sql_path}")
    if not result_path.exists():
        pytest.skip(
            f"Result CSV not found: {result_path} "
            f"(run tests/run_web_scrape_large_case.py --case-id {case['id']} -- <db_llm_query args>)"
        )

    ground_truth_path = _ground_truth_csv_path(case)
    if ground_truth_path.exists() or ground_truth_path.with_name(ground_truth_path.name + ".zst").exists():
        expected = read_csv_maybe_zstd(ground_truth_path)
    else:
        sql = sql_path.read_text()
        expected = execute_sql(db_path=db_path, sql=sql, temp_table=case.get("temp_table"))

    actual = pl.read_csv(result_path, infer_schema_length=10_000)

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

    expected_cols = expected.columns
    actual_cols = actual.columns
    missing_cols = [col for col in expected_cols if col not in actual_cols]
    if missing_cols:
        raise AssertionError(
            f"Actual result is missing expected columns: missing={missing_cols}, actual={actual_cols}"
        )
    actual = actual.select(expected_cols)

    if sort_keys is None:
        sort_keys = list(expected_cols)
    actual = actual.sort(sort_keys)
    expected = expected.sort(sort_keys)

    float_tol = float(case.get("float_tol", 1e-6))
    assert_frames_equal(actual, expected, float_cols=float_cols, float_tol=float_tol)
