from __future__ import annotations

import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

import polars as pl

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from db_llm_runtime_v5 import ChEMBLLLMQuery


@dataclass(slots=True)
class SQLExecutionResult:
    success: bool
    result_path: str | None
    row_count: int | None
    column_names: list[str]
    error: str | None


def execute_sql_to_csv(
    *,
    db_path: Path,
    sql_text: str,
    out_path: Path,
) -> SQLExecutionResult:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(sql_text)
        rows = cur.fetchall()
        cols = [d[0] for d in (cur.description or [])]
        df = ChEMBLLLMQuery._rows_to_dataframe(rows, cols)
        df.write_csv(out_path)
        return SQLExecutionResult(
            success=True,
            result_path=str(out_path.resolve()),
            row_count=int(df.height),
            column_names=list(df.columns),
            error=None,
        )
    except Exception as exc:
        return SQLExecutionResult(
            success=False,
            result_path=None,
            row_count=None,
            column_names=[],
            error=str(exc),
        )
    finally:
        conn.close()


def summarize_result_csv(path: Path, *, max_rows: int = 5) -> str:
    df = pl.read_csv(path, infer_schema_length=10_000)
    head = df.head(max_rows)
    return (
        f"row_count: {df.height}\n"
        f"columns: {list(df.columns)}\n"
        f"sample_rows_csv:\n{head.write_csv()}"
    )
