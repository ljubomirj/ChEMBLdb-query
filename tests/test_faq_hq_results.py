#!/usr/bin/env python3
"""High-quality FAQ cases that compare live LLM runs against SQL ground truth."""

from __future__ import annotations

from pathlib import Path
import os

import polars as pl
import pytest

from tests.helpers.chembl_asserts import (
    assert_frames_equal,
    execute_sql,
    load_cases,
    normalize_df,
    read_csv_maybe_zstd,
)

FAQ_HQ_CASES = load_cases("cases/registries/archive/faq_hq_cases.json")
PERSISTED_GROUND_TRUTH_ENV = "CHEMBL_FAQ_PREFER_PERSISTED_GROUND_TRUTH"
INCLUDE_LARGE_ENV = "CHEMBL_FAQ_INCLUDE_LARGE"
INCLUDE_MASSIVE_ENV = "CHEMBL_FAQ_INCLUDE_MASSIVE"


def _env_enabled(name: str, *, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _case_marks(case: dict) -> tuple[pytest.MarkDecorator, ...]:
    size_class = (case.get("size_class") or "small").strip().lower()
    marks: list[pytest.MarkDecorator] = [pytest.mark.faq_hq]
    if size_class == "large":
        marks.append(pytest.mark.faq_hq_large)
    elif size_class == "massive":
        marks.append(pytest.mark.faq_hq_massive)
    return tuple(marks)


def _case_param(case: dict) -> pytest.ParameterSet:
    return pytest.param(case, id=case["id"], marks=_case_marks(case))


def _maybe_skip_for_size(case: dict) -> None:
    size_class = (case.get("size_class") or "small").strip().lower()
    if size_class == "massive" and not _env_enabled(INCLUDE_MASSIVE_ENV, default=False):
        pytest.skip("Massive FAQ case disabled by default; set CHEMBL_FAQ_INCLUDE_MASSIVE=1 to enable.")
    if size_class == "large" and not _env_enabled(INCLUDE_LARGE_ENV, default=True):
        pytest.skip("Large FAQ case disabled; set CHEMBL_FAQ_INCLUDE_LARGE=1 to enable.")


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


def _load_expected_frame(case: dict, *, db_path: Path, sql_path: Path) -> pl.DataFrame:
    if _env_enabled(PERSISTED_GROUND_TRUTH_ENV, default=True):
        ground_truth_path = _ground_truth_csv_path(case)
        if ground_truth_path.exists() or ground_truth_path.with_name(ground_truth_path.name + ".zst").exists():
            return read_csv_maybe_zstd(ground_truth_path)

    sql = sql_path.read_text()
    return execute_sql(db_path=db_path, sql=sql, temp_table=case.get("temp_table"))


@pytest.mark.parametrize("case", [_case_param(case) for case in FAQ_HQ_CASES])
def test_faq_hq_result_matches_sql(case: dict) -> None:
    _maybe_skip_for_size(case)

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
            f"(run tests/run_faq_hq_case.py --case-id {case['id']} -- <db_llm_query args>)"
        )

    expected = _load_expected_frame(case, db_path=db_path, sql_path=sql_path)
    actual = pl.read_csv(result_path)

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
    actual = _rename_actual_columns(actual, rename_map)

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
