#!/usr/bin/env python3
"""Compute RDKit Tanimoto similarity for ChEMBL CSV exports."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Iterable

import polars as pl

try:
    from rdkit import Chem, DataStructs
    from rdkit.Chem import AllChem
except ImportError as exc:  # pragma: no cover - runtime dependency
    raise SystemExit(
        "RDKit is required. Install optional deps with `uv sync --extra chemistry` "
        "(if wheels are available) or ensure RDKit is importable in this env."
    ) from exc


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute RDKit Tanimoto similarity vs a query SMILES."
    )
    parser.add_argument("csv_path", help="Input CSV with SMILES column")
    parser.add_argument("--query-smiles", required=True, help="Query SMILES")
    parser.add_argument("--smiles-col", default="canonical_smiles", help="SMILES column name")
    parser.add_argument("--id-col", default="molecule_chembl_id", help="ID column name")
    parser.add_argument("--top", type=int, default=50, help="Max results (default: 50)")
    parser.add_argument("--threshold", type=float, default=0.6, help="Min similarity (default: 0.6)")
    parser.add_argument("--radius", type=int, default=2, help="Morgan radius (default: 2)")
    parser.add_argument("--bits", type=int, default=2048, help="Fingerprint bits (default: 2048)")
    parser.add_argument("--max-rows", type=int, default=0, help="Limit input rows (default: 0=all)")
    parser.add_argument("--out", default=None, help="Output CSV path (default: logs/rdkit_similarity_<timestamp>.csv)")
    return parser.parse_args()


def _iter_rows(df: pl.DataFrame) -> Iterable[dict]:
    for row in df.to_dicts():
        yield row


def main() -> None:
    args = _parse_args()
    csv_path = Path(args.csv_path)

    df = pl.read_csv(csv_path)
    if args.smiles_col not in df.columns:
        raise SystemExit(f"Missing SMILES column: {args.smiles_col}")
    if args.id_col not in df.columns:
        raise SystemExit(f"Missing ID column: {args.id_col}")

    df = df.select([args.id_col, args.smiles_col])
    if args.max_rows and args.max_rows > 0:
        df = df.head(args.max_rows)

    query_mol = Chem.MolFromSmiles(args.query_smiles)
    if query_mol is None:
        raise SystemExit("Invalid query SMILES")

    query_fp = AllChem.GetMorganFingerprintAsBitVect(query_mol, args.radius, nBits=args.bits)

    results = []
    invalid = 0
    for row in _iter_rows(df):
        smi = row.get(args.smiles_col)
        if not smi:
            invalid += 1
            continue
        mol = Chem.MolFromSmiles(str(smi))
        if mol is None:
            invalid += 1
            continue
        fp = AllChem.GetMorganFingerprintAsBitVect(mol, args.radius, nBits=args.bits)
        sim = DataStructs.TanimotoSimilarity(query_fp, fp)
        if sim >= args.threshold:
            results.append(
                {
                    args.id_col: row.get(args.id_col),
                    args.smiles_col: smi,
                    "tanimoto": float(sim),
                }
            )

    results.sort(key=lambda r: r["tanimoto"], reverse=True)
    if args.top and args.top > 0:
        results = results[: args.top]

    out_dir = Path("logs")
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.out:
        out_path = Path(args.out)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = out_dir / f"rdkit_similarity_{timestamp}.csv"

    out_df = pl.DataFrame(results)
    out_df.write_csv(out_path)

    print(f"Input rows: {df.height}")
    print(f"Invalid SMILES: {invalid}")
    print(f"Matches: {len(results)}")
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
