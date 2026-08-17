#!/usr/bin/env python3
"""Build a small stratified v5.1010 split for the first GEPA sanity run."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE_SPLIT = REPO_ROOT / "cases/v5.1010/splits/case_splits_v5.1010.json"
DEFAULT_MANIFEST_ROOT = REPO_ROOT / "cases/v5.1010/cases"
DEFAULT_OUT = REPO_ROOT / "cases/v5.1010/splits/case_splits_v5.1010_gepa_probe.json"

DEFAULT_QUOTAS = {
    "train": {
        "target_pchembl": 12,
        "document": 12,
        "other": 12,
        "assay_exact": 10,
        "metabolism": 6,
        "salts": 6,
    },
    "val": {
        "target_pchembl": 4,
        "document": 4,
        "other": 4,
        "assay_exact": 4,
        "metabolism": 2,
        "salts": 2,
    },
    "test": {
        "target_pchembl": 6,
        "document": 6,
        "other": 6,
        "assay_exact": 6,
        "metabolism": 2,
        "salts": 4,
    },
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a deterministic stratified v5.1010 GEPA probe split.")
    parser.add_argument("--source-split", default=str(DEFAULT_SOURCE_SPLIT))
    parser.add_argument("--manifest-root", default=str(DEFAULT_MANIFEST_ROOT))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--quotas-json", default=None)
    args = parser.parse_args()

    source_split = Path(args.source_split)
    manifest_root = Path(args.manifest_root)
    quotas = json.loads(Path(args.quotas_json).read_text()) if args.quotas_json else DEFAULT_QUOTAS
    payload = json.loads(source_split.read_text())

    by_split_family: dict[str, dict[str, list[dict[str, str]]]] = {
        split: {} for split in ("train", "val", "test")
    }
    for split, items in payload["splits"].items():
        for item in items:
            case_id = str(item["id"])
            manifest = json.loads((manifest_root / f"{case_id}.json").read_text())
            family = str(manifest["metadata"]["family"])
            by_split_family.setdefault(split, {}).setdefault(family, []).append(
                {"corpus": str(item["corpus"]), "id": case_id}
            )

    out_splits: dict[str, list[dict[str, str]]] = {}
    quota_summary: dict[str, Any] = {}
    for split, family_quotas in quotas.items():
        selected: list[dict[str, str]] = []
        quota_summary[split] = {}
        for family, quota in family_quotas.items():
            available = sorted(by_split_family.get(split, {}).get(family, []), key=lambda item: item["id"])
            take = min(int(quota), len(available))
            selected.extend(available[:take])
            quota_summary[split][family] = {"requested": int(quota), "available": len(available), "selected": take}
        out_splits[split] = sorted(selected, key=lambda item: item["id"])

    out_payload = {
        "version": "v5.1010_gepa_probe",
        "description": "Small stratified v5.1010 split for GEPA sanity run before full-1010 GEPA.",
        "source_split": str(source_split.relative_to(REPO_ROOT)),
        "manifest_root": str(manifest_root.relative_to(REPO_ROOT)),
        "quotas": quotas,
        "quota_summary": quota_summary,
        "splits": out_splits,
    }
    out_path = Path(args.out)
    out_path.write_text(json.dumps(out_payload, indent=2) + "\n")
    print(
        json.dumps(
            {
                "out": str(out_path.resolve()),
                "split_counts": {split: len(items) for split, items in out_splits.items()},
                "total": sum(len(items) for items in out_splits.values()),
                "quota_summary": quota_summary,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
