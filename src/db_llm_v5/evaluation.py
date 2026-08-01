from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import polars as pl

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from compressed_io import read_candidates, read_csv_maybe_compressed
from tests.helpers.chembl_asserts import assert_frames_equal

from .artifacts import V5CaseManifest


def score_result_against_gold(*, manifest: V5CaseManifest, repo_root: Path, actual_path: Path) -> dict[str, Any]:
    expected_path = repo_root / (manifest.artifacts.res_gold or "")
    if not any(candidate.exists() for candidate in read_candidates(expected_path)):
        raise FileNotFoundError(f"gold result missing for {manifest.case_id}: {expected_path}")

    # Build schema overrides for columns that must be strings (e.g., mixed PMID/DOI columns)
    string_cols = list(manifest.metadata.string_cols or [])
    schema_overrides = {col: pl.Utf8 for col in string_cols} if string_cols else None

    actual = read_csv_maybe_compressed(actual_path, schema_overrides=schema_overrides)
    expected = read_csv_maybe_compressed(expected_path, schema_overrides=schema_overrides)

    normalize = dict(manifest.metadata.normalize or {})
    lowercase_columns = bool(normalize.get("lowercase_columns", True))
    strip_values = bool(normalize.get("strip_values", True))
    lowercase_values = [str(v) for v in normalize.get("lowercase_values", [])]
    float_cols = list(manifest.metadata.float_cols)
    int_cols = list(manifest.metadata.int_cols)
    sort_keys = list(manifest.metadata.sort_keys or [])
    rename_map = dict(manifest.metadata.column_rename_map or {})

    if lowercase_columns:
        if sort_keys:
            sort_keys = [c.lower() for c in sort_keys]
        if rename_map:
            rename_map = {k.lower(): v.lower() for k, v in rename_map.items()}

    actual = _rename_actual_columns(actual, rename_map)
    actual = _normalize_df(
        actual,
        lowercase_columns=lowercase_columns,
        strip_values=strip_values,
        lowercase_values=lowercase_values,
        float_cols=float_cols,
        int_cols=int_cols,
    )
    expected = _normalize_df(
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
        if not sort_keys:
            sort_keys = list(expected_cols)
        actual = actual.sort(sort_keys)
        expected = expected.sort(sort_keys)
        try:
            assert_frames_equal(actual, expected, float_cols=float_cols, float_tol=float(manifest.metadata.float_tol))
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
    result.update(
        {
            "status": "partial" if score > 0 else "fail",
            "score": score,
            "column_recall": round(col_recall, 6),
            "row_ratio": round(row_ratio, 6),
        }
    )
    return result


def _normalize_df(df, *, lowercase_columns, strip_values, lowercase_values, float_cols, int_cols):
    from tests.helpers.chembl_asserts import normalize_df

    return normalize_df(
        df,
        lowercase_columns=lowercase_columns,
        strip_values=strip_values,
        lowercase_values=lowercase_values,
        float_cols=float_cols,
        int_cols=int_cols,
    )


def _rename_actual_columns(df, rename_map):
    if not rename_map:
        return df
    rename: dict[str, str] = {}
    for col in df.columns:
        key = col.lower()
        if key in rename_map and rename_map[key] != col:
            rename[col] = rename_map[key]
    if not rename:
        return df
    return df.rename(rename)
