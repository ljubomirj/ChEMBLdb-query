#!/usr/bin/env python3
"""Generate v5 manifests for cases that have v4-style registry entries but no v5 manifest."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from compressed_io import read_candidates
from db_llm_v5.artifacts import V5ArtifactPaths, V5CaseManifest, V5CaseMetadata


def family_from_id(case_id: str) -> str:
    if "document_molecules" in case_id:
        return "document"
    if "molecule_smiles" in case_id:
        return "other"
    if "pubmed_or_doi" in case_id:
        return "other"
    if "pchembl" in case_id:
        return "target_pchembl"
    if "assay_exact" in case_id or "assay_" in case_id:
        return "assay_exact"
    if "salt" in case_id:
        return "salts"
    if "metabolism" in case_id:
        return "metabolism"
    return "other"


def size_class_from_rows(rows: int) -> str:
    if rows < 100:
        return "small"
    if rows < 1000:
        return "medium"
    if rows < 10000:
        return "large"
    return "xlarge"


def count_ground_truth_rows(csv_path: Path) -> int:
    """Count rows in a compressed or plain CSV."""
    from compressed_io import read_csv_maybe_compressed
    try:
        df = read_csv_maybe_compressed(csv_path)
        return df.height
    except Exception:
        return 0


def main() -> None:
    registry_path = REPO_ROOT / "cases/registries/archive/web_scrape_hq_cases.json"
    manifest_dir = REPO_ROOT / "tests/v5_manifests" / "web_scrape_hq"
    manifest_dir.mkdir(parents=True, exist_ok=True)

    registry = json.load(open(registry_path))

    generated = 0
    skipped = 0

    for entry in registry:
        cid = entry["id"]
        dest = manifest_dir / f"{cid}.json"
        if dest.exists():
            skipped += 1
            continue

        # Derive fixture base from sqlite_sql_path
        sql_path = REPO_ROOT / entry["sqlite_sql_path"]
        if not sql_path.exists():
            print(f"  SKIP (no sql): {cid}")
            continue

        fixture_rel = str(sql_path.parent).replace(str(REPO_ROOT) + "/", "")
        fixture_dir = sql_path.parent

        # Find ground truth
        res_gold = None
        for candidate in read_candidates(fixture_dir / "ground-truth.csv"):
            if candidate.exists():
                res_gold = str(candidate).replace(str(REPO_ROOT) + "/", "")
                break
        if not res_gold:
            print(f"  SKIP (no ground truth): {cid}")
            continue

        # Count rows
        gt_path = REPO_ROOT / res_gold
        row_count = count_ground_truth_rows(gt_path)

        # Determine expected columns from sort_keys
        sort_keys = entry.get("sort_keys", [])
        expected_cols = list(sort_keys) if sort_keys else []

        # Build artifact paths
        artifacts = V5ArtifactPaths(
            uq_surface=f"{fixture_rel}/uq.txt",
            up_exec=f"{fixture_rel}/up_exec.txt",
            sql_gold=f"{fixture_rel}/sqlite.sql",
            res_gold=res_gold,
            uq_benchmark_spec=f"{fixture_rel}/benchmark_spec_uq.txt" if (fixture_dir / "benchmark_spec_uq.txt").exists() else None,
            source_sql=f"{fixture_rel}/source.sql" if (fixture_dir / "source.sql").exists() else None,
            documentation=f"{fixture_rel}/documentation.txt" if (fixture_dir / "documentation.txt").exists() else None,
        )

        metadata = V5CaseMetadata(
            family=family_from_id(cid),
            origin="promoted_from_web_scrape",
            source_title=entry.get("source_url", "unknown"),
            source_url=entry.get("source_url", "unknown"),
            realism_level="realistic_surface",
            ambiguity_level="unambiguous",
            size_class=entry.get("size_class", size_class_from_rows(row_count)),
            expected_output_columns=expected_cols,
            sort_keys=sort_keys,
            normalize=entry.get("normalize", {"lowercase_columns": True, "strip_values": True, "lowercase_values": []}),
            column_rename_map=entry.get("column_rename_map", {}),
            tags=[family_from_id(cid), "v4_promoted"],
            notes=f"Auto-generated v5 manifest from v4 registry entry.",
        )

        manifest = V5CaseManifest(
            case_id=cid,
            corpus="web_scrape_hq",
            split=None,
            db_path=str(REPO_ROOT / "database/latest/chembl_36/chembl_36_sqlite/chembl_36.db"),
            artifacts=artifacts,
            metadata=metadata,
        )

        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "w") as f:
            json.dump(manifest.to_dict(), f, indent=2)
        generated += 1

    print(f"Generated: {generated}, Skipped (already exist): {skipped}")


if __name__ == "__main__":
    main()
