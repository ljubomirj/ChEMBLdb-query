#!/usr/bin/env python3
"""
Test helpers for ChEMBL SQL golden comparisons.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import polars as pl
import zstandard as zstd

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from compressed_io import count_csv_rows_maybe_compressed, read_csv_maybe_compressed, resolve_read_path, zstd_path


CSV_COUNT_CHUNK_SIZE = 1024 * 1024


def load_cases(path: Path | str = Path("cases/registries/archive/cases.json")) -> List[Dict[str, Any]]:
    path = Path(path)
    return json.loads(path.read_text())


def zstd_path_for_csv(path: Path) -> Path:
    return zstd_path(path)


def resolve_csv_or_zstd_path(path: Path) -> Path:
    return resolve_read_path(path)


def read_csv_maybe_zstd(path: Path) -> pl.DataFrame:
    return read_csv_maybe_compressed(path)


def count_csv_rows_maybe_zstd(path: Path) -> int:
    return count_csv_rows_maybe_compressed(path)


def _normalize_cols(cols: Iterable[str], *, lowercase: bool) -> List[str]:
    if lowercase:
        return [c.lower() for c in cols]
    return list(cols)


def normalize_df(
    df: pl.DataFrame,
    *,
    lowercase_columns: bool,
    strip_values: bool,
    lowercase_values: Sequence[str],
    float_cols: Sequence[str],
    int_cols: Sequence[str],
) -> pl.DataFrame:
    if lowercase_columns:
        df = df.rename({c: c.lower() for c in df.columns})
    if strip_values:
        for col in df.columns:
            if df[col].dtype == pl.Utf8:
                df = df.with_columns(pl.col(col).str.strip_chars().alias(col))
    for col in lowercase_values:
        if col in df.columns:
            df = df.with_columns(
                pl.col(col).cast(pl.Utf8, strict=False).str.to_lowercase().alias(col)
            )
    for col in int_cols:
        if col in df.columns:
            df = df.with_columns(pl.col(col).cast(pl.Int64, strict=False).alias(col))
    for col in float_cols:
        if col in df.columns:
            df = df.with_columns(pl.col(col).cast(pl.Float64, strict=False).alias(col))
    return df


def _block_char_len(lines: Sequence[str]) -> int:
    if not lines:
        return 0
    return sum(len(line) for line in lines) + max(0, len(lines) - 1)


def levenshtein_distance(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            insert_cost = current[j - 1] + 1
            delete_cost = previous[j] + 1
            replace_cost = previous[j - 1] + (0 if ca == cb else 1)
            current.append(min(insert_cost, delete_cost, replace_cost))
        previous = current
    return previous[-1]


def hybrid_edit_distance(lines_a: Sequence[str], lines_b: Sequence[str]) -> int:
    import difflib

    matcher = difflib.SequenceMatcher(a=list(lines_a), b=list(lines_b))
    total = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag == "delete":
            total += _block_char_len(lines_a[i1:i2])
            continue
        if tag == "insert":
            total += _block_char_len(lines_b[j1:j2])
            continue
        if tag == "replace":
            text_a = "\n".join(lines_a[i1:i2])
            text_b = "\n".join(lines_b[j1:j2])
            total += levenshtein_distance(text_a, text_b)
            continue
    return total


def canonical_csv_lines(
    df: pl.DataFrame,
    *,
    sort_keys: Sequence[str],
    float_cols: Sequence[str],
    float_decimals: int,
) -> List[str]:
    if sort_keys:
        df = df.sort(list(sort_keys))
    for col in float_cols:
        if col in df.columns:
            fmt = f"{{:.{float_decimals}f}}"
            df = df.with_columns(
                pl.col(col)
                .map_elements(lambda v: fmt.format(v) if v is not None else None, return_dtype=pl.Utf8)
                .alias(col)
            )
    df = df.with_columns([pl.col(c).cast(pl.Utf8, strict=False).alias(c) for c in df.columns])
    from io import StringIO

    out = StringIO()
    df.write_csv(out)
    return out.getvalue().splitlines()


def zstd_diff_size(lines_a: Sequence[str], lines_b: Sequence[str]) -> int:
    import difflib

    diff_lines = difflib.unified_diff(lines_a, lines_b, lineterm="")
    diff_text = "\n".join(diff_lines)
    compressor = zstd.ZstdCompressor(level=3)
    compressed = compressor.compress(diff_text.encode("utf-8"))
    return len(compressed)


def _load_chembl_ids_from_uniprot(*, uniprot_csv: Path, mapping_tsv: Path) -> List[str]:
    uniprot_df = pl.read_csv(uniprot_csv)
    if uniprot_df.is_empty():
        raise RuntimeError(f"No UniProt entries found in {uniprot_csv}")
    uniprot_key = uniprot_df.columns[0]

    mapping_df = pl.read_csv(
        mapping_tsv,
        separator='\t',
        has_header=False,
        skip_rows=1,
        new_columns=['uniprot_id', 'chembl_id', 'name', 'protein_type'],
    )

    kinase_ids = mapping_df.join(uniprot_df, left_on='uniprot_id', right_on=uniprot_key, how='inner')
    chembl_ids = kinase_ids.select('chembl_id').unique().sort('chembl_id')
    return chembl_ids['chembl_id'].to_list()


def _apply_temp_table(cur: sqlite3.Cursor, spec: Dict[str, Any]) -> None:
    name = spec['name']
    schema = spec['schema']
    cur.execute(f"CREATE TEMP TABLE {name}({schema})")
    source = spec.get('source') or {}
    if source.get('type') == 'chembl_uniprot_mapping':
        ids = _load_chembl_ids_from_uniprot(
            uniprot_csv=Path(source['uniprot_csv']),
            mapping_tsv=Path(source['mapping_tsv']),
        )
        cur.executemany(f"INSERT INTO {name}(chembl_id) VALUES (?)", [(v,) for v in ids])
        return
    raise ValueError(f"Unsupported temp table source: {source}")


def execute_sql(
    *,
    db_path: Path,
    sql: str,
    temp_table: Optional[Dict[str, Any]] = None,
) -> pl.DataFrame:
    cleaned_lines = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith('.'):
            continue
        if stripped.lower().startswith('.mode') or stripped.lower().startswith('.headers'):
            continue
        cleaned_lines.append(line)
    cleaned_sql = "\n".join(cleaned_lines).strip()
    with sqlite3.connect(str(db_path)) as con:
        cur = con.cursor()
        if temp_table:
            _apply_temp_table(cur, temp_table)
        cur.execute(cleaned_sql)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
    return pl.DataFrame(rows, schema=cols, orient="row")


def assert_frames_equal(
    actual: pl.DataFrame,
    expected: pl.DataFrame,
    *,
    float_cols: Sequence[str],
    float_tol: float,
) -> None:
    if actual.columns != expected.columns:
        raise AssertionError(f"Column mismatch: actual={actual.columns}, expected={expected.columns}")
    if actual.height != expected.height:
        raise AssertionError(f"Row count mismatch: actual={actual.height}, expected={expected.height}")

    for col in actual.columns:
        a = actual[col]
        b = expected[col]
        null_mismatch = (a.is_null() != b.is_null()).any()
        if null_mismatch:
            raise AssertionError(f"Null mismatch in column '{col}'")
        mask = a.is_not_null() & b.is_not_null()
        if col in float_cols:
            if a.dtype != b.dtype:
                a = a.cast(pl.Float64, strict=False)
                b = b.cast(pl.Float64, strict=False)
            diffs = (a - b).abs().filter(mask)
            max_diff = diffs.max()
            if max_diff is None:
                max_diff = 0.0
            if max_diff > float_tol:
                raise AssertionError(f"Float mismatch in '{col}': max_diff={max_diff} tol={float_tol}")
        else:
            if a.dtype != b.dtype:
                a = a.cast(pl.String, strict=False)
                b = b.cast(pl.String, strict=False)
            neq = (a != b) & mask
            if neq.any():
                idx = int(neq.arg_max())
                raise AssertionError(
                    f"Value mismatch in '{col}' at row {idx}: actual={a[idx]!r}, expected={b[idx]!r}"
                )
