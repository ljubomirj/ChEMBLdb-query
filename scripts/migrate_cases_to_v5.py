#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from compressed_io import read_text_maybe_compressed
from db_llm_v5.artifacts import V5ArtifactPaths, V5CaseManifest, V5CaseMetadata
from db_llm_v5.io import save_case_manifest


DEFAULT_REGISTRY = REPO_ROOT / "tests/cases/web_scrape_hq_cases.json"
DEFAULT_OUT_DIR = REPO_ROOT / "tests/v5_manifests/web_scrape_hq"


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate v4 case registry entries to v5 case manifests.")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY), help="Path to the v4 case registry JSON")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Directory for emitted v5 manifests")
    parser.add_argument("--limit", type=int, default=None, help="Optional cap on migrated cases")
    args = parser.parse_args()

    registry_path = Path(args.registry)
    out_dir = Path(args.out_dir)
    cases = json.loads(registry_path.read_text())
    if not isinstance(cases, list):
        raise TypeError(f"registry must be a list: {registry_path}")

    migrated = 0
    items = cases[: args.limit] if args.limit else cases
    for case in items:
        manifest = _migrate_case(dict(case))
        save_case_manifest(manifest, out_dir / f"{manifest.case_id}.json")
        migrated += 1

    print(
        json.dumps(
            {
                "registry_path": str(registry_path.resolve()),
                "out_dir": str(out_dir.resolve()),
                "migrated_cases": migrated,
            },
            indent=2,
        )
    )


def _migrate_case(case: dict[str, object]) -> V5CaseManifest:
    case_id = str(case["id"])
    fixture_dir = Path(str(case["sqlite_sql_path"])).parent
    metadata = _load_fixture_metadata(fixture_dir)
    uq_surface = _choose_existing_path(
        metadata.get("uq_path"),
        fixture_dir / "uq.txt",
    )
    uq_benchmark_spec = _choose_existing_path_optional(
        metadata.get("benchmark_spec_uq_path"),
        fixture_dir / "benchmark_spec_uq.txt",
    )
    documentation = _choose_existing_path_optional(
        metadata.get("documentation_path"),
        fixture_dir / "documentation.txt",
    )
    res_gold = _choose_gold_result_path(fixture_dir, case)

    source_title = _optional_str(metadata.get("source_title"))
    source_url = _optional_str(case.get("source_url")) or _optional_str(metadata.get("source_url"))
    family = _infer_family(case_id)
    realism_level = _infer_realism_level(metadata)
    ambiguity_level = "mildly_ambiguous" if family == "faq" else "unambiguous"
    size_class = _optional_str(case.get("size_class"))
    sort_keys = [str(v) for v in (case.get("sort_keys") or [])]
    expected_output_columns = _read_csv_header(res_gold)
    if not expected_output_columns:
        expected_output_columns = sort_keys.copy()
    column_rename_map = _build_v5_column_rename_map(
        legacy_map={str(k): str(v) for k, v in dict(case.get("column_rename_map") or {}).items()},
        expected_output_columns=expected_output_columns,
    )
    sort_keys = _rewrite_sort_keys(sort_keys=sort_keys, expected_output_columns=expected_output_columns)
    tags = [family]
    if size_class:
        tags.append(size_class)

    return V5CaseManifest(
        case_id=case_id,
        corpus="web_scrape_hq",
        split=None,
        db_path=str(case["db_path"]),
        artifacts=V5ArtifactPaths(
            uq_surface=_relpath(uq_surface),
            up_exec=None,
            sql_gold=_relpath(REPO_ROOT / str(case["sqlite_sql_path"])),
            res_gold=_relpath(res_gold),
            uq_benchmark_spec=_relpath(uq_benchmark_spec) if uq_benchmark_spec else None,
            res_gold_presentation=None,
            source_sql=_relpath(REPO_ROOT / str(case["source_sql_path"])),
            sqlite_sql=_relpath(REPO_ROOT / str(case["sqlite_sql_path"])),
            documentation=_relpath(documentation) if documentation else None,
        ),
        metadata=V5CaseMetadata(
            family=family,
            origin=_optional_str(metadata.get("uq_origin_kind")) or _optional_str(metadata.get("uq_origin")) or "legacy_v4_case",
            source_title=source_title,
            source_url=source_url,
            realism_level=realism_level,  # type: ignore[arg-type]
            ambiguity_level=ambiguity_level,  # type: ignore[arg-type]
            size_class=size_class,
            expected_output_columns=expected_output_columns,
            sort_keys=sort_keys,
            tags=tags,
            allows_multiple_sql_forms=True,
            requires_schema_alias_fidelity=bool(column_rename_map),
            normalize=dict(case.get("normalize") or {}),
            column_rename_map=column_rename_map,
            float_cols=[str(v) for v in (case.get("float_cols") or [])],
            int_cols=[str(v) for v in (case.get("int_cols") or [])],
            float_tol=float(case.get("float_tol", 1e-6)),
            notes="Migrated automatically from the v4 web_scrape_hq registry.",
        ),
    )


def _load_fixture_metadata(fixture_dir: Path) -> dict[str, object]:
    metadata_path = REPO_ROOT / fixture_dir / "metadata.json"
    if not metadata_path.exists():
        return {}
    data = json.loads(metadata_path.read_text())
    return data if isinstance(data, dict) else {}


def _choose_existing_path(preferred: object, fallback: Path) -> Path:
    path = _choose_existing_path_optional(preferred, fallback)
    if path is None:
        raise FileNotFoundError(f"missing required artifact path: preferred={preferred!r} fallback={fallback}")
    return path


def _choose_existing_path_optional(preferred: object, fallback: Path) -> Path | None:
    if preferred:
        preferred_path = REPO_ROOT / str(preferred)
        if preferred_path.exists():
            return preferred_path
    fallback_path = REPO_ROOT / fallback
    if fallback_path.exists():
        return fallback_path
    return None


def _choose_gold_result_path(fixture_dir: Path, case: dict[str, object]) -> Path:
    for candidate in (
        REPO_ROOT / fixture_dir / "ground-truth.csv",
        REPO_ROOT / fixture_dir / "ground-truth.csv.zst",
    ):
        if candidate.exists():
            return candidate
    fallback = REPO_ROOT / str(case["result_csv_path"])
    if fallback.exists():
        return fallback
    raise FileNotFoundError(f"missing gold result for {case['id']}: {fixture_dir}")


def _relpath(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


def _read_csv_header(path: Path) -> list[str]:
    try:
        text = read_text_maybe_compressed(path)
    except Exception:
        return []
    first_line = text.splitlines()[0].strip() if text.splitlines() else ""
    if not first_line:
        return []
    return [part.strip() for part in first_line.split(",") if part.strip()]


def _build_v5_column_rename_map(*, legacy_map: dict[str, str], expected_output_columns: list[str]) -> dict[str, str]:
    if not legacy_map and not expected_output_columns:
        return {}
    expected = {col.lower(): col for col in expected_output_columns}
    rewritten: dict[str, str] = {}
    for key, value in legacy_map.items():
        value_key = value.lower()
        if value_key in expected:
            rewritten[key] = expected[value_key]

    # Restore useful generic aliases against the gold header instead of preserving
    # v4's internal normalization targets such as chembl_id.
    if "molecule_chembl_id" in expected and "chembl_id" not in rewritten:
        rewritten["chembl_id"] = expected["molecule_chembl_id"]
    if "assay_chembl_id" in expected and "chembl_id" not in rewritten:
        rewritten["chembl_id"] = expected["assay_chembl_id"]
    if "compound_chembl_id" in expected:
        rewritten.setdefault("chembl_id", expected["compound_chembl_id"])
        rewritten.setdefault("molecule_chembl_id", expected["compound_chembl_id"])
    return rewritten


def _rewrite_sort_keys(*, sort_keys: list[str], expected_output_columns: list[str]) -> list[str]:
    if not sort_keys:
        return []
    expected = {col.lower(): col for col in expected_output_columns}
    rewritten: list[str] = []
    for key in sort_keys:
        lower = key.lower()
        if lower in expected:
            rewritten.append(expected[lower])
            continue
        if lower == "chembl_id":
            if "molecule_chembl_id" in expected:
                rewritten.append(expected["molecule_chembl_id"])
                continue
            if "assay_chembl_id" in expected:
                rewritten.append(expected["assay_chembl_id"])
                continue
            if "compound_chembl_id" in expected:
                rewritten.append(expected["compound_chembl_id"])
                continue
        rewritten.append(key)
    return rewritten


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _infer_family(case_id: str) -> str:
    if "target_" in case_id and "pchembl" in case_id:
        return "target_pchembl"
    if "assay_" in case_id:
        return "assay_exact"
    if "document_" in case_id:
        return "document"
    if "salt" in case_id:
        return "salts"
    if "metabolism" in case_id:
        return "metabolism"
    if case_id.startswith("faq_"):
        return "faq"
    return "other"


def _infer_realism_level(metadata: dict[str, object]) -> str:
    style = _optional_str(metadata.get("uq_style"))
    if style == "realistic_uq":
        return "realistic_surface"
    if style == "benchmark_spec_uq":
        return "benchmark_spec_only"
    origin = _optional_str(metadata.get("uq_origin_kind")) or _optional_str(metadata.get("uq_origin"))
    if origin and "templated" in origin:
        return "templated_surface"
    return "realistic_surface"


if __name__ == "__main__":
    main()
