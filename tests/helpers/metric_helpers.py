#!/usr/bin/env python3
"""Metric helpers for comparing CSV outputs."""

from __future__ import annotations

from pathlib import Path
import json
import hashlib
from datetime import datetime

import polars as pl

from tests.helpers.chembl_asserts import (
    canonical_csv_lines,
    hybrid_edit_distance,
    zstd_diff_size,
)

FLOAT_DECIMALS = 3
TOLERANCE_PCT = 0.05
HUMAN_GOLD_PATH = Path("tests/fixtures/human/kinase_inhibitors_after_2022.csv")


def hash_lines(lines: list[str]) -> str:
    text = "\n".join(lines)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def within_pct(score: int, threshold: int, *, tol: float = TOLERANCE_PCT) -> bool:
    if threshold == 0:
        return score == 0
    return abs(score - threshold) <= abs(threshold) * tol


def prepare_metric_lines(
    df: pl.DataFrame,
    human_df: pl.DataFrame,
    *,
    sort_keys: list[str] | None,
    float_cols: list[str],
    df_label: str,
    human_label: str,
    column_map: dict[str, str] | None,
) -> tuple[list[str], list[str], list[str], list[str]]:
    metric_columns: list[str] = []
    if column_map:
        mapped_pairs: list[tuple[str, str]] = []
        for test_col, human_col in column_map.items():
            if test_col in df.columns and human_col in human_df.columns:
                mapped_pairs.append((test_col, human_col))
        mapped_test = {t for t, _ in mapped_pairs}
        mapped_human = {h for _, h in mapped_pairs}
        for col in human_df.columns:
            if col in df.columns and col not in mapped_test and col not in mapped_human:
                mapped_pairs.append((col, col))
        metric_columns = [t for t, _ in mapped_pairs]
        if mapped_pairs:
            df = df.select(metric_columns)
            human_select_cols = [h for _, h in mapped_pairs]
            human_df = human_df.select(human_select_cols)
            rename_map = {h: t for t, h in mapped_pairs if h != t}
            if rename_map:
                human_df = human_df.rename(rename_map)
    else:
        metric_columns = [c for c in human_df.columns if c in df.columns]
        if metric_columns:
            df = df.select(metric_columns)
            human_df = human_df.select(metric_columns)

    if not metric_columns:
        msg = (
            "No common columns between test data and human gold for metric comparison.\n"
            f"X label: {df_label}\n"
            f"Y label: {human_label}\n"
            f"X shape: {df.height} rows x {df.width} cols\n"
            f"Y shape: {human_df.height} rows x {human_df.width} cols\n"
            f"X columns: {df.columns}\n"
            f"Y columns: {human_df.columns}"
        )
        raise AssertionError(msg)

    if sort_keys:
        sort_keys = [c for c in sort_keys if c in metric_columns]
    if not sort_keys:
        sort_keys = list(metric_columns)
    float_cols = [c for c in float_cols if c in metric_columns]

    df_lines = canonical_csv_lines(
        df,
        sort_keys=sort_keys,
        float_cols=float_cols,
        float_decimals=FLOAT_DECIMALS,
    )
    human_lines = canonical_csv_lines(
        human_df,
        sort_keys=sort_keys,
        float_cols=float_cols,
        float_decimals=FLOAT_DECIMALS,
    )
    return df_lines, human_lines, metric_columns, sort_keys


def compute_metrics(
    *,
    case_id: str,
    actual: pl.DataFrame,
    expected: pl.DataFrame,
    human_gold: pl.DataFrame,
    result_path: Path,
    gold_path: Path,
    sort_keys: list[str] | None,
    float_cols: list[str],
    column_map: dict[str, str] | None,
) -> dict:
    metrics_path = gold_path.with_name(f"{gold_path.stem}-metrics-last.json")

    actual_lines, human_lines, metric_columns, metric_sort_keys = prepare_metric_lines(
        actual,
        human_gold,
        sort_keys=sort_keys,
        float_cols=float_cols,
        df_label=str(result_path),
        human_label=str(HUMAN_GOLD_PATH),
        column_map=column_map,
    )
    expected_lines, _, _, _ = prepare_metric_lines(
        expected,
        human_gold,
        sort_keys=sort_keys,
        float_cols=float_cols,
        df_label=str(gold_path),
        human_label=str(HUMAN_GOLD_PATH),
        column_map=column_map,
    )

    actual_hash = hash_lines(actual_lines)
    expected_hash = hash_lines(expected_lines)
    human_hash = hash_lines(human_lines)

    cached = None
    if metrics_path.exists():
        try:
            cached = json.loads(metrics_path.read_text())
        except Exception:
            cached = None

    if (
        cached
        and cached.get("hashes", {}).get("test_gold") == expected_hash
        and cached.get("hashes", {}).get("human_gold") == human_hash
        and cached.get("params", {}).get("float_decimals") == FLOAT_DECIMALS
        and cached.get("params", {}).get("metric_columns") == metric_columns
        and cached.get("params", {}).get("sort_keys") == metric_sort_keys
    ):
        thresholds = {
            "m1": int(cached.get("thresholds", {}).get("m1", 0)),
            "m2": int(cached.get("thresholds", {}).get("m2", 0)),
        }
    else:
        thresholds = {
            "m1": hybrid_edit_distance(expected_lines, human_lines),
            "m2": zstd_diff_size(expected_lines, human_lines),
        }

    scores = {
        "m1": hybrid_edit_distance(actual_lines, human_lines),
        "m2": zstd_diff_size(actual_lines, human_lines),
    }
    pass_m1 = within_pct(scores["m1"], thresholds["m1"], tol=TOLERANCE_PCT)
    pass_m2 = within_pct(scores["m2"], thresholds["m2"], tol=TOLERANCE_PCT)
    pass_overall = pass_m1 and pass_m2

    metrics_payload = {
        "case_id": case_id,
        "human_gold": str(HUMAN_GOLD_PATH),
        "test_gold": str(gold_path),
        "test_result": str(result_path),
        "params": {
            "float_decimals": FLOAT_DECIMALS,
            "metric_columns": metric_columns,
            "sort_keys": metric_sort_keys,
            "tolerance_pct": TOLERANCE_PCT,
            "metric_column_map": column_map or {},
        },
        "hashes": {
            "test_gold": expected_hash,
            "human_gold": human_hash,
            "test_result": actual_hash,
        },
        "thresholds": thresholds,
        "scores": scores,
        "pass": {
            "m1": pass_m1,
            "m2": pass_m2,
            "overall": pass_overall,
        },
        "method": {
            "m1": "hybrid_line_char_levenshtein",
            "m2": "unified_diff_zstd_bytes",
        },
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    metrics_path.write_text(json.dumps(metrics_payload, indent=2, sort_keys=True))
    return metrics_payload
