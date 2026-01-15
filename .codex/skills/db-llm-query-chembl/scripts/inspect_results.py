#!/usr/bin/env python3
"""Quick inspector for db_llm_query CSV outputs (Polars only)."""

from __future__ import annotations

import argparse
from pathlib import Path

import polars as pl


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect a CSV output from db_llm_query.")
    parser.add_argument("csv_path", help="Path to CSV file")
    parser.add_argument("--head", type=int, default=5, help="Rows to show from head (default: 5)")
    parser.add_argument("--tail", type=int, default=5, help="Rows to show from tail (default: 5)")
    parser.add_argument("--sample", type=int, default=0, help="Sample rows to show (default: 0)")
    parser.add_argument("--columns", nargs="*", default=None, help="Optional subset of columns")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    csv_path = Path(args.csv_path)

    df = pl.read_csv(csv_path)

    print(f"File: {csv_path}")
    print(f"Rows: {df.height}")
    print(f"Columns ({len(df.columns)}): {', '.join(df.columns)}")

    if args.columns:
        missing = [col for col in args.columns if col not in df.columns]
        if missing:
            raise SystemExit(f"Missing columns: {', '.join(missing)}")
        df = df.select(args.columns)

    if args.head:
        print("\nHead:")
        print(df.head(args.head))

    if args.tail:
        print("\nTail:")
        print(df.tail(args.tail))

    if args.sample:
        if df.height == 0:
            print("\nSample: <empty>")
        else:
            n = min(args.sample, df.height)
            print("\nSample:")
            print(df.sample(n=n, seed=42))


if __name__ == "__main__":
    main()
