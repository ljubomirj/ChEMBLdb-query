#!/usr/bin/env python3
"""Golden SQL result comparisons for ChEMBL queries."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from tests.helpers.chembl_asserts import (
    assert_frames_equal,
    execute_sql,
    load_cases,
    normalize_df,
)
from tests.helpers.metric_helpers import (
    HUMAN_GOLD_PATH,
    compute_metrics,
)

CASES = load_cases()


@pytest.mark.integration
@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_gold_query(case: dict) -> None:
    db_path = Path(case["db_path"])
    sql_path = Path(case["sql_path"])
    csv_path = Path(case["csv_path"])

    if not db_path.exists():
        pytest.skip(f"DB not found: {db_path}")
    if not sql_path.exists():
        pytest.skip(f"SQL not found: {sql_path}")
    if not csv_path.exists():
        pytest.skip(f"CSV not found: {csv_path}")

    sql = sql_path.read_text()
    actual = execute_sql(db_path=db_path, sql=sql, temp_table=case.get("temp_table"))
    expected = pl.read_csv(csv_path)
    human_gold = pl.read_csv(HUMAN_GOLD_PATH)

    normalize = case.get("normalize", {})
    lowercase_columns = bool(normalize.get("lowercase_columns", False))
    strip_values = bool(normalize.get("strip_values", False))
    lowercase_values = normalize.get("lowercase_values", [])

    float_cols = case.get("float_cols", [])
    int_cols = case.get("int_cols", [])
    sort_keys = case.get("sort_keys")
    column_map = case.get("metric_column_map")

    if lowercase_columns:
        float_cols = [c.lower() for c in float_cols]
        int_cols = [c.lower() for c in int_cols]
        lowercase_values = [c.lower() for c in lowercase_values]
        if sort_keys:
            sort_keys = [c.lower() for c in sort_keys]
        if column_map:
            column_map = {k.lower(): v.lower() for k, v in column_map.items()}

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
    human_gold = normalize_df(
        human_gold,
        lowercase_columns=lowercase_columns,
        strip_values=strip_values,
        lowercase_values=lowercase_values,
        float_cols=float_cols,
        int_cols=int_cols,
    )

    expected_cols = expected.columns
    actual_cols = actual.columns
    if set(actual_cols) != set(expected_cols):
        raise AssertionError(f"Column set mismatch: actual={actual_cols}, expected={expected_cols}")
    actual = actual.select(expected_cols)

    if sort_keys is None:
        sort_keys = list(expected_cols)
    actual = actual.sort(sort_keys)
    expected = expected.sort(sort_keys)

    result_path = csv_path.with_name(f"{csv_path.stem}-test-result-last{csv_path.suffix}")
    actual.write_csv(result_path)

    metrics_payload = compute_metrics(
        case_id=case["id"],
        actual=actual,
        expected=expected,
        human_gold=human_gold,
        result_path=result_path,
        gold_path=csv_path,
        sort_keys=sort_keys,
        float_cols=float_cols,
        column_map=column_map,
    )

    float_tol = float(case.get("float_tol", 1e-6))
    assert_frames_equal(actual, expected, float_cols=float_cols, float_tol=float_tol)
    if not metrics_payload.get("pass", {}).get("overall", False):
        thresholds = metrics_payload.get("thresholds", {})
        scores = metrics_payload.get("scores", {})
        raise AssertionError(
            f"Similarity metrics out of range: m1={scores.get('m1')} thr1={thresholds.get('m1')}, "
            f"m2={scores.get('m2')} thr2={thresholds.get('m2')}"
        )
