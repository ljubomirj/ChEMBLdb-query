#!/usr/bin/env python3
"""Build the v5.1010 diversified case registry, split, manifests, and report.

This extends v5.0_balanced without modifying any v5.0 files. It starts from the
982-entry balanced registry, deduplicates it to the 975 unique case IDs, creates
manifests for the two stale-but-recoverable registry entries whose fixture paths
were renamed, and adds enough unused document-wave candidates to reach exactly
1010 unique cases.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import zstandard as zstd

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from compressed_io import read_candidates, read_text_maybe_compressed
from db_llm_v5.artifacts import V5ArtifactPaths, V5CaseManifest, V5CaseMetadata
from db_llm_v5.io import load_case_manifest, save_case_manifest

BASE_REGISTRY = REPO_ROOT / "cases/registries/archive/web_scrape_hq_cases_v5.0_balanced.json"
BASE_SPLIT = REPO_ROOT / "experiments/case_splits_v5.0_balanced.json"
CANDIDATES = REPO_ROOT / "experiments/document_wave2_candidates_v4.9.json"
DB_PATH = REPO_ROOT / "database/latest/chembl_36/chembl_36_sqlite/chembl_36.db"
SOURCE_MANIFEST_ROOT = REPO_ROOT / "tests/v5_manifests/web_scrape_hq"
MANIFEST_ROOT = REPO_ROOT / "cases/v5.1010/cases"
FIXTURE_ROOT = REPO_ROOT / "tests/fixtures/web_scrape_1010"
OUT_REGISTRY = REPO_ROOT / "cases/registries/web_scrape_hq_cases_v5.1010.json"
OUT_SPLIT = REPO_ROOT / "cases/v5.1010/splits/case_splits_v5.1010.json"
OUT_REPORT_JSON = REPO_ROOT / "experiments/v5.1010_dataset_report.json"
OUT_REPORT_MD = REPO_ROOT / "experiments/v5.1010_dataset_report.md"
TARGET_TOTAL = 1010
SPLITS = ("train", "val", "test")

# The v5.0 registry contains two stale sanitized IDs whose fixtures exist under
# the original punctuation-preserving directory names. Creating explicit v5
# manifests lets v5.1010 include them without editing the v5.0 registry.
RECOVERABLE_FIXTURE_DIRS = {
    "target_ic50_with_pubmed_or_doi_phosphatidylinositol_4_5_bisphosphate_3_": Path(
        "tests/fixtures/web_scrape75/target_ic50_with_pubmed_or_doi_phosphatidylinositol_4,5_bisphosphate_3_"
    ),
    "human_isocitrate_dehydrogenase__nadp__cytoplas_molecule_smiles": Path(
        "tests/fixtures/web_scrape73/human_isocitrate_dehydrogenase_[nadp]_cytoplas_molecule_smiles"
    ),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the v5.1010 diversified dataset artifacts.")
    parser.add_argument("--target-total", type=int, default=TARGET_TOTAL)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.target_total < 1001:
        raise ValueError("target_total must be >1000 for the 1010 diversified dataset")

    registry = _read_json(BASE_REGISTRY)
    if not isinstance(registry, list):
        raise TypeError(f"registry must be a list: {BASE_REGISTRY}")

    unique_registry, duplicate_ids = _dedupe_cases(registry)
    base_manifest_paths = {
        p.relative_to(SOURCE_MANIFEST_ROOT).with_suffix("").as_posix(): p
        for p in SOURCE_MANIFEST_ROOT.rglob("*.json")
    }

    recovered: list[dict[str, str]] = []
    base_cases: list[dict[str, Any]] = []
    base_manifests: list[V5CaseManifest] = []
    patched_optional_artifacts: list[dict[str, str]] = []
    missing_after_recovery: list[str] = []
    for case in unique_registry:
        case_id = str(case["id"])
        if case_id in base_manifest_paths:
            manifest, patched = _manifest_from_source(base_manifest_paths[case_id])
            base_manifests.append(manifest)
            base_cases.append(_case_with_manifest(case, manifest))
            patched_optional_artifacts.extend(patched)
        elif case_id in RECOVERABLE_FIXTURE_DIRS:
            fixture_dir = REPO_ROOT / RECOVERABLE_FIXTURE_DIRS[case_id]
            manifest = _manifest_from_existing_fixture(case=case, fixture_dir=fixture_dir)
            base_manifests.append(manifest)
            base_cases.append(_case_with_manifest(case, manifest))
            recovered.append(
                {
                    "case_id": case_id,
                    "manifest": str(_manifest_path(case_id).relative_to(REPO_ROOT)),
                    "fixture_dir": str(RECOVERABLE_FIXTURE_DIRS[case_id]),
                }
            )
        else:
            missing_after_recovery.append(case_id)

    if missing_after_recovery:
        raise FileNotFoundError(f"unrecoverable missing manifests: {missing_after_recovery}")

    to_add = args.target_total - len(base_cases)
    if to_add < 0:
        raise ValueError(f"base registry already exceeds target: base={len(base_cases)} target={args.target_total}")

    existing_ids = {str(case["id"]) for case in base_cases}
    selected_candidates = _select_document_candidates(existing_ids, to_add)

    generated_entries: list[dict[str, Any]] = []
    generated_manifests: list[V5CaseManifest] = []
    for idx, candidate in enumerate(selected_candidates):
        entry, manifest = _build_document_case(candidate, index=idx)
        generated_entries.append(entry)
        generated_manifests.append(manifest)

    all_cases = [*base_cases, *generated_entries]
    if len({case["id"] for case in all_cases}) != len(all_cases):
        duplicates = [k for k, v in Counter(case["id"] for case in all_cases).items() if v > 1]
        raise ValueError(f"new registry still has duplicate IDs: {duplicates}")
    if len(all_cases) != args.target_total:
        raise AssertionError(f"expected {args.target_total} cases, built {len(all_cases)}")

    all_manifests = [*base_manifests, *generated_manifests]
    manifest_by_id = {manifest.case_id: manifest for manifest in all_manifests}
    splits = _build_split(all_cases, BASE_SPLIT, target_total=args.target_total, manifest_by_id=manifest_by_id)

    family_counts = _family_counts([str(case["id"]) for case in all_cases], manifest_by_id)
    split_family_counts = {
        split: _family_counts([str(item["id"]) for item in items], manifest_by_id)
        for split, items in splits.items()
    }
    report = {
        "version": "v5.1010",
        "target_total": args.target_total,
        "source_registry": str(BASE_REGISTRY.relative_to(REPO_ROOT)),
        "source_split": str(BASE_SPLIT.relative_to(REPO_ROOT)),
        "old_v4_7_corpus_used": False,
        "base_registry_entries": len(registry),
        "base_unique_cases": len(unique_registry),
        "base_cases_with_manifests_after_recovery": len(base_cases),
        "duplicate_ids_removed": duplicate_ids,
        "recovered_missing_manifests": recovered,
        "patched_missing_optional_artifacts": patched_optional_artifacts,
        "added_document_cases": [
            {
                "case_id": str(entry["id"]),
                "doc_chembl_id": str(candidate["doc_chembl_id"]),
                "doc_title": str(candidate.get("doc_title", "")),
                "row_count": manifest.metadata.notes.split("row_count=")[-1].split(";")[0]
                if manifest.metadata.notes and "row_count=" in manifest.metadata.notes
                else None,
            }
            for entry, candidate, manifest in zip(generated_entries, selected_candidates, generated_manifests)
        ],
        "registry_out": str(OUT_REGISTRY.relative_to(REPO_ROOT)),
        "split_out": str(OUT_SPLIT.relative_to(REPO_ROOT)),
        "manifest_root": str(MANIFEST_ROOT.relative_to(REPO_ROOT)),
        "source_manifest_root": str(SOURCE_MANIFEST_ROOT.relative_to(REPO_ROOT)),
        "fixture_root_for_added_cases": str(FIXTURE_ROOT.relative_to(REPO_ROOT)),
        "split_counts": {split: len(items) for split, items in splits.items()},
        "family_counts": family_counts,
        "split_family_counts": split_family_counts,
        "provider_policy_for_next_runs": {
            "primary": "Z.ai Anthropic-compatible /v1/messages, request GLM-4.7; do not spend GLM-5.1 quota",
            "fallback_1": "http://127.0.0.1:18081 nemotron-cascade-2-30b-a3b via SSH tunnel",
            "fallback_2": "http://127.0.0.1:8081 nemotron-cascade-2-30b-a3b local llama.cpp",
        },
        "gepa_promotion_rule": "Promote only iff both pass rate and mean evaluation score improve over baseline.",
        "full_1010_gepa_gate": "Do not launch full-1010 GEPA until the stratified GEPA search passes sanity checks.",
    }

    errors = _validate_constructed_outputs(all_cases, splits, manifest_by_id)
    if errors:
        raise ValueError("validation failed:\n" + "\n".join(errors[:100]))

    if args.dry_run:
        print(json.dumps({"dry_run": True, "report": report}, indent=2))
        return

    for manifest in all_manifests:
        save_case_manifest(manifest, _manifest_path(manifest.case_id))
    OUT_REGISTRY.write_text(json.dumps(all_cases, indent=2) + "\n")
    OUT_SPLIT.write_text(
        json.dumps(
            {
                "version": "v5.1010",
                "description": "v5 diversified 1010-case corpus derived from v5.0_balanced; deduped, missing manifests recovered, plus grounded document-wave extension. Old v4.7 1000 corpus not used.",
                "source": {
                    "base_registry": str(BASE_REGISTRY.relative_to(REPO_ROOT)),
                    "base_split": str(BASE_SPLIT.relative_to(REPO_ROOT)),
                    "added_candidates": str(CANDIDATES.relative_to(REPO_ROOT)),
                },
                "splits": splits,
            },
            indent=2,
        )
        + "\n"
    )
    OUT_REPORT_JSON.write_text(json.dumps(report, indent=2) + "\n")
    OUT_REPORT_MD.write_text(_render_report(report))

    errors = _validate_outputs(all_cases, splits)
    if errors:
        raise ValueError("post-write validation failed:\n" + "\n".join(errors[:100]))

    print(json.dumps(report, indent=2))


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def _dedupe_cases(cases: list[Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    duplicate_counts: Counter[str] = Counter()
    for raw in cases:
        case = dict(raw)
        case_id = str(case["id"])
        if case_id in seen:
            duplicate_counts[case_id] += 1
            continue
        seen.add(case_id)
        unique.append(case)
    duplicates = [{"id": case_id, "removed_extra_entries": count} for case_id, count in sorted(duplicate_counts.items())]
    return unique, duplicates


def _manifest_path(case_id: str) -> Path:
    return MANIFEST_ROOT / f"{case_id}.json"


def _manifest_from_source(manifest_path: Path) -> tuple[V5CaseManifest, list[dict[str, str]]]:
    manifest = V5CaseManifest.from_dict(_read_json(manifest_path))
    patched: list[dict[str, str]] = []
    artifacts = manifest.artifacts
    for name, value in artifacts.to_dict().items():
        if not value:
            continue
        artifact_path = REPO_ROOT / value
        if any(candidate.exists() for candidate in read_candidates(artifact_path)):
            continue
        if name != "up_exec":
            raise FileNotFoundError(f"required artifact missing in source manifest {manifest_path}: {name} -> {value}")
        setattr(artifacts, name, None)
        patched.append(
            {
                "case_id": manifest.case_id,
                "source_manifest": str(manifest_path.relative_to(REPO_ROOT)),
                "artifact": name,
                "missing_path": value,
                "action": "set to null in v5.1010 manifest copy",
            }
        )
    return manifest, patched


def _recover_missing_manifests(cases: list[dict[str, Any]], *, dry_run: bool) -> list[dict[str, str]]:
    recovered: list[dict[str, str]] = []
    by_id = {str(case["id"]): case for case in cases}
    for case_id, fixture_rel in RECOVERABLE_FIXTURE_DIRS.items():
        manifest_path = _manifest_path(case_id)
        if manifest_path.exists():
            continue
        case = by_id.get(case_id)
        if case is None:
            continue
        fixture_dir = REPO_ROOT / fixture_rel
        manifest = _manifest_from_existing_fixture(case=case, fixture_dir=fixture_dir)
        errors = manifest.validate(REPO_ROOT)
        if errors:
            raise ValueError(f"cannot recover manifest for {case_id}: {errors}")
        if not dry_run:
            save_case_manifest(manifest, manifest_path)
        recovered.append({"case_id": case_id, "manifest": str(manifest_path.relative_to(REPO_ROOT)), "fixture_dir": str(fixture_rel)})
    return recovered


def _manifest_from_existing_fixture(*, case: dict[str, Any], fixture_dir: Path) -> V5CaseManifest:
    case_id = str(case["id"])
    if not fixture_dir.exists():
        raise FileNotFoundError(f"fixture dir missing for {case_id}: {fixture_dir}")
    columns = _read_csv_header(fixture_dir / "ground-truth.csv.zst")
    if not columns:
        columns = [str(v) for v in case.get("sort_keys") or []]
    metadata_json = fixture_dir / "metadata.json"
    source_title = f"Recovered v5.1010 manifest for existing fixture {case_id}"
    if metadata_json.exists():
        metadata = json.loads(metadata_json.read_text())
        source_title = str(metadata.get("source_title") or metadata.get("title") or source_title)
    family = _infer_family(case_id)
    tags = [family, "v5.1010_recovered_manifest"]
    rel = fixture_dir.relative_to(REPO_ROOT).as_posix()
    return V5CaseManifest(
        case_id=case_id,
        corpus="web_scrape_hq",
        split=None,
        db_path=str(case.get("db_path") or "database/latest/chembl_36/chembl_36_sqlite/chembl_36.db"),
        artifacts=V5ArtifactPaths(
            uq_surface=f"{rel}/uq.txt",
            up_exec=f"{rel}/up_exec.txt" if (fixture_dir / "up_exec.txt").exists() else None,
            sql_gold=f"{rel}/sqlite.sql",
            res_gold=f"{rel}/ground-truth.csv.zst",
            uq_benchmark_spec=f"{rel}/benchmark_spec_uq.txt" if (fixture_dir / "benchmark_spec_uq.txt").exists() else None,
            source_sql=f"{rel}/source.sql",
            sqlite_sql=f"{rel}/sqlite.sql",
            documentation=f"{rel}/documentation.txt" if (fixture_dir / "documentation.txt").exists() else None,
        ),
        metadata=V5CaseMetadata(
            family=family,
            origin="v5.1010_recovered_existing_fixture",
            source_title=source_title,
            source_url=str(case.get("source_url") or "synthetic_generated"),
            realism_level="realistic_surface",
            ambiguity_level="unambiguous",
            size_class=str(case.get("size_class") or _size_class_from_row_count(_count_csv_rows(fixture_dir / "ground-truth.csv.zst"))),
            expected_output_columns=columns,
            sort_keys=[str(v) for v in (case.get("sort_keys") or columns)],
            tags=tags,
            allows_multiple_sql_forms=True,
            requires_schema_alias_fidelity=bool(case.get("column_rename_map")),
            normalize=dict(case.get("normalize") or {}),
            column_rename_map={str(k): str(v) for k, v in dict(case.get("column_rename_map") or {}).items()},
            float_cols=[str(v) for v in (case.get("float_cols") or [])],
            int_cols=[str(v) for v in (case.get("int_cols") or [])],
            string_cols=["pubmed_id_or_doi"] if case_id.startswith("target_ic50_with_pubmed_or_doi") else [],
            float_tol=float(case.get("float_tol", 1e-6)),
            notes="Recovered for v5.1010 because v5.0 registry path used sanitized punctuation while the fixture directory exists under the punctuation-preserving name.",
        ),
    )


def _case_with_manifest_paths(case: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    manifest = load_case_manifest(manifest_path)
    return _case_with_manifest(case, manifest)


def _case_with_manifest(case: dict[str, Any], manifest: V5CaseManifest) -> dict[str, Any]:
    out = dict(case)
    out["source_sql_path"] = manifest.artifacts.source_sql or out.get("source_sql_path")
    out["sqlite_sql_path"] = manifest.artifacts.sqlite_sql or manifest.artifacts.sql_gold or out.get("sqlite_sql_path")
    out["result_csv_path"] = str(Path(out["sqlite_sql_path"]).with_name("result-last.csv"))
    out["db_path"] = manifest.db_path
    out["sort_keys"] = manifest.metadata.sort_keys or out.get("sort_keys") or manifest.metadata.expected_output_columns
    out["normalize"] = manifest.metadata.normalize
    out["column_rename_map"] = manifest.metadata.column_rename_map
    out["size_class"] = manifest.metadata.size_class or out.get("size_class")
    if manifest.artifacts.uq_benchmark_spec:
        out["benchmark_spec_uq_path"] = str((REPO_ROOT / manifest.artifacts.uq_benchmark_spec).resolve())
    return out


def _select_document_candidates(existing_ids: set[str], count: int) -> list[dict[str, Any]]:
    payload = _read_json(CANDIDATES)
    candidates = [dict(c) for c in payload["candidates"]]
    selected: list[dict[str, Any]] = []
    seen = set(existing_ids)
    for candidate in candidates:
        case_id = str(candidate["case_id"])
        if case_id in seen:
            continue
        if _manifest_path(case_id).exists() or (SOURCE_MANIFEST_ROOT / f"{case_id}.json").exists():
            continue
        if candidate.get("template") != "chembl_downloader_document_molecules_export":
            continue
        selected.append(candidate)
        seen.add(case_id)
        if len(selected) == count:
            break
    if len(selected) != count:
        raise ValueError(f"needed {count} new document candidates, found {len(selected)}")
    return selected


def _build_document_case(candidate: dict[str, Any], *, index: int) -> tuple[dict[str, Any], V5CaseManifest]:
    case_id = str(candidate["case_id"])
    doc_id = str(candidate["doc_chembl_id"])
    title = str(candidate.get("doc_title") or "")
    sql = str(candidate["sql"]).rstrip() + "\n"
    fixture_dir = FIXTURE_ROOT / case_id
    rel = fixture_dir.relative_to(REPO_ROOT).as_posix()
    fixture_dir.mkdir(parents=True, exist_ok=True)
    (fixture_dir / "source.sql").write_text(sql)
    (fixture_dir / "sqlite.sql").write_text(sql)
    row_count, columns = _write_ground_truth(sql, fixture_dir / "ground-truth.csv.zst")
    uq = _placeholder_uq(doc_id, title)
    up_exec = _up_exec(doc_id, title)
    benchmark = _benchmark_spec_uq(doc_id, title)
    (fixture_dir / "uq.txt").write_text(uq + "\n")
    (fixture_dir / "up_exec.txt").write_text(up_exec + "\n")
    (fixture_dir / "benchmark_spec_uq.txt").write_text(benchmark + "\n")
    (fixture_dir / "documentation.txt").write_text(_doc_text(doc_id, title, row_count))
    pb_note = {
        "case_id": case_id,
        "generation": "deterministic_v5.1010_extension_no_llm_call",
        "reason": "Avoid GLM-5.1 quota and make grounded 1010 dataset construction reproducible.",
    }
    (fixture_dir / "pb_sql.output.json").write_text(json.dumps({**pb_note, "up_exec": up_exec}, indent=2) + "\n")
    (fixture_dir / "pb_up.output.json").write_text(json.dumps({**pb_note, "uq_surface": uq}, indent=2) + "\n")

    manifest = V5CaseManifest(
        case_id=case_id,
        corpus="web_scrape_hq",
        split=None,
        db_path="database/latest/chembl_36/chembl_36_sqlite/chembl_36.db",
        artifacts=V5ArtifactPaths(
            uq_surface=f"{rel}/uq.txt",
            up_exec=f"{rel}/up_exec.txt",
            sql_gold=f"{rel}/sqlite.sql",
            res_gold=f"{rel}/ground-truth.csv.zst",
            uq_benchmark_spec=f"{rel}/benchmark_spec_uq.txt",
            source_sql=f"{rel}/source.sql",
            sqlite_sql=f"{rel}/sqlite.sql",
            documentation=f"{rel}/documentation.txt",
        ),
        metadata=V5CaseMetadata(
            family="document",
            origin="v5.1010_document_wave2_grounded_sql_no_llm",
            source_title=f"chembl_downloader document molecules instantiated for {doc_id}: {title}"[:300],
            source_url="https://github.com/cthoyt/chembl-downloader/blob/main/src/chembl_downloader/queries.py",
            realism_level="templated_surface",
            ambiguity_level="unambiguous",
            size_class=_size_class_from_row_count(row_count),
            expected_output_columns=columns,
            sort_keys=columns,
            tags=["document", "v5.1010", "document_wave2", "grounded_sql", "no_llm_generation"],
            allows_multiple_sql_forms=True,
            requires_schema_alias_fidelity=False,
            normalize={"lowercase_columns": True, "strip_values": True, "lowercase_values": []},
            column_rename_map={},
            float_cols=[],
            int_cols=[],
            string_cols=[],
            float_tol=1e-6,
            notes=f"v5.1010 extension from unused document_wave2 candidate; row_count={row_count}; candidate_index={index}; title={title[:180]}",
        ),
    )
    errors = manifest.validate(REPO_ROOT)
    if errors:
        raise ValueError(f"invalid generated manifest for {case_id}: {errors}")
    (fixture_dir / "metadata.json").write_text(json.dumps(manifest.metadata.to_dict(), indent=2) + "\n")
    entry = {
        "id": case_id,
        "uq": uq,
        "source_url": manifest.metadata.source_url,
        "source_sql_path": f"{rel}/source.sql",
        "sqlite_sql_path": f"{rel}/sqlite.sql",
        "result_csv_path": f"{rel}/result-last.csv",
        "log_path": f"{rel}/run-last.log",
        "db_path": manifest.db_path,
        "size_class": manifest.metadata.size_class,
        "sort_keys": columns,
        "normalize": manifest.metadata.normalize,
        "column_rename_map": {},
        "benchmark_spec_uq_path": str((fixture_dir / "benchmark_spec_uq.txt").resolve()),
        "uq_style": "deterministic_v5.1010_placeholder",
    }
    return entry, manifest


def _write_ground_truth(sql: str, out_zst: Path) -> tuple[int, list[str]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(sql)
        columns = [desc[0] for desc in cur.description]
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(columns)
        row_count = 0
        for row in cur:
            row_count += 1
            writer.writerow(["" if row[col] is None else str(row[col]) for col in columns])
    finally:
        conn.close()
    out_zst.write_bytes(zstd.ZstdCompressor().compress(buf.getvalue().encode("utf-8")))
    return row_count, columns


def _read_csv_header(path: Path) -> list[str]:
    text = read_text_maybe_compressed(path)
    first_line = text.splitlines()[0] if text.splitlines() else ""
    if not first_line:
        return []
    return next(csv.reader([first_line]))


def _count_csv_rows(path: Path) -> int:
    text = read_text_maybe_compressed(path)
    if not text.strip():
        return 0
    return max(0, len(text.splitlines()) - 1)


def _size_class_from_row_count(row_count: int) -> str:
    if row_count < 100:
        return "small"
    if row_count < 1000:
        return "medium"
    if row_count < 10000:
        return "large"
    return "xlarge"


def _infer_family(case_id: str) -> str:
    if "document_molecules" in case_id or case_id.startswith("approved_drugs") or case_id.startswith("drug_indications"):
        return "document"
    if "assay" in case_id:
        return "assay_exact"
    if "salt" in case_id:
        return "salts"
    if "metabolism" in case_id:
        return "metabolism"
    if case_id.startswith("chembl_downloader_target") and "pchembl" in case_id:
        return "target_pchembl"
    return "other"


def _placeholder_uq(doc_id: str, title: str) -> str:
    if title:
        return f"Which compounds are reported in document {doc_id} ({title})?"
    return f"Which compounds are reported in document {doc_id}?"


def _up_exec(doc_id: str, title: str) -> str:
    label = f"{doc_id} ({title})" if title else doc_id
    return (
        f"Retrieve all distinct molecules associated with document {label}; "
        "return chembl_id, compound_name, and canonical_smiles, requiring canonical_smiles to be present."
    )


def _benchmark_spec_uq(doc_id: str, title: str) -> str:
    label = f"{doc_id} ({title})" if title else doc_id
    return (
        f"Retrieve all distinct molecules mentioned in document {label}, returning chembl_id, compound_name, "
        "and canonical_smiles. Only include molecules with canonical_smiles available."
    )


def _doc_text(doc_id: str, title: str, row_count: int) -> str:
    return (
        f"Document: {doc_id}\n\n"
        f"Title: {title}\n"
        f"Distinct molecules with structures: {row_count}\n"
        "Template family: chembl_downloader_document_molecules_export\n"
        "Generation: deterministic v5.1010 extension from grounded SQL; no LLM call.\n"
    )


def _build_split(
    all_cases: list[dict[str, Any]],
    base_split_path: Path,
    *,
    target_total: int,
    manifest_by_id: dict[str, V5CaseManifest],
) -> dict[str, list[dict[str, str]]]:
    base_split = _read_json(base_split_path)["splits"]
    all_ids = {str(case["id"]) for case in all_cases}
    splits: dict[str, list[dict[str, str]]] = {name: [] for name in SPLITS}
    assigned: set[str] = set()
    for split in SPLITS:
        for item in base_split.get(split, []):
            case_id = str(item["id"])
            if case_id in all_ids and case_id not in assigned:
                splits[split].append({"corpus": "web_scrape_hq", "id": case_id})
                assigned.add(case_id)

    target_counts = _target_split_counts(target_total, {split: len(base_split.get(split, [])) for split in SPLITS})
    remaining = [str(case["id"]) for case in all_cases if str(case["id"]) not in assigned]
    remaining.sort(key=lambda case_id: (manifest_by_id[case_id].metadata.family, _stable_hash(case_id), case_id))
    for case_id in remaining:
        rooms = {split: target_counts[split] - len(splits[split]) for split in SPLITS}
        candidates = [split for split in SPLITS if rooms[split] > 0]
        if not candidates:
            raise AssertionError("no split room left while assigning remaining cases")
        # Choose the split with most remaining target room; stable hash breaks ties.
        split = sorted(candidates, key=lambda s: (rooms[s], -_stable_hash(case_id + s)), reverse=True)[0]
        splits[split].append({"corpus": "web_scrape_hq", "id": case_id})
        assigned.add(case_id)

    for split in SPLITS:
        splits[split].sort(key=lambda item: item["id"])
    if assigned != all_ids:
        raise AssertionError(f"split did not assign all cases: missing={sorted(all_ids - assigned)[:10]}")
    return splits


def _target_split_counts(total: int, base_counts: dict[str, int]) -> dict[str, int]:
    base_total = sum(base_counts.values())
    raw = {split: total * base_counts[split] / base_total for split in SPLITS}
    counts = {split: int(raw[split]) for split in SPLITS}
    remaining = total - sum(counts.values())
    for split in sorted(SPLITS, key=lambda s: (raw[s] - counts[s], base_counts[s]), reverse=True):
        if remaining <= 0:
            break
        counts[split] += 1
        remaining -= 1
    return counts


def _stable_hash(value: str) -> int:
    return int(hashlib.sha256(value.encode("utf-8")).hexdigest()[:16], 16)


def _family_for_case_id(case_id: str) -> str:
    for root in (MANIFEST_ROOT, SOURCE_MANIFEST_ROOT):
        manifest_path = root / f"{case_id}.json"
        if manifest_path.exists():
            return str(_read_json(manifest_path)["metadata"]["family"])
    return _infer_family(case_id)


def _family_counts(case_ids: list[str], manifest_by_id: dict[str, V5CaseManifest]) -> dict[str, int]:
    return dict(sorted(Counter(manifest_by_id[case_id].metadata.family for case_id in case_ids).items()))


def _validate_constructed_outputs(
    all_cases: list[dict[str, Any]],
    splits: dict[str, list[dict[str, str]]],
    manifest_by_id: dict[str, V5CaseManifest],
) -> list[str]:
    errors: list[str] = []
    ids = [str(case["id"]) for case in all_cases]
    if len(ids) != len(set(ids)):
        errors.append("registry IDs are not unique")
    if set(ids) != set(manifest_by_id):
        errors.append(
            f"manifest ID set does not match registry IDs: missing_manifests={sorted(set(ids) - set(manifest_by_id))[:10]} "
            f"extra_manifests={sorted(set(manifest_by_id) - set(ids))[:10]}"
        )
    split_ids = [str(item["id"]) for items in splits.values() for item in items]
    if sorted(split_ids) != sorted(ids):
        errors.append("split IDs do not match registry IDs")
    for case_id, manifest in manifest_by_id.items():
        manifest_errors = manifest.validate(REPO_ROOT)
        if manifest_errors:
            errors.extend(f"manifest invalid before write: {case_id}: {error}" for error in manifest_errors)
    return errors


def _validate_outputs(all_cases: list[dict[str, Any]], splits: dict[str, list[dict[str, str]]]) -> list[str]:
    errors: list[str] = []
    ids = [str(case["id"]) for case in all_cases]
    if len(ids) != len(set(ids)):
        errors.append("registry IDs are not unique")
    split_ids = [str(item["id"]) for items in splits.values() for item in items]
    if sorted(split_ids) != sorted(ids):
        errors.append("split IDs do not match registry IDs")
    for case_id in ids:
        manifest_path = _manifest_path(case_id)
        if not manifest_path.exists():
            errors.append(f"manifest missing: {case_id}")
            continue
        try:
            manifest = load_case_manifest(manifest_path)
        except Exception as exc:  # intentionally surfaced in report
            errors.append(f"manifest invalid: {case_id}: {exc}")
            continue
        for name, value in manifest.artifacts.to_dict().items():
            if not value:
                continue
            artifact_path = REPO_ROOT / value
            if not any(candidate.exists() for candidate in read_candidates(artifact_path)):
                errors.append(f"artifact missing: {case_id}: {name} -> {value}")
    return errors


def _render_report(report: dict[str, Any]) -> str:
    lines = [
        "# v5.1010 Diversified Dataset Report",
        "",
        f"- Target total: {report['target_total']}",
        f"- Output registry: `{report['registry_out']}`",
        f"- Output split: `{report['split_out']}`",
        f"- Base registry entries: {report['base_registry_entries']}",
        f"- Base unique cases: {report['base_unique_cases']}",
        f"- Recovered missing manifests: {len(report['recovered_missing_manifests'])}",
        f"- Patched missing optional artifacts in copied manifests: {len(report['patched_missing_optional_artifacts'])}",
        f"- Added document cases: {len(report['added_document_cases'])}",
        f"- Old v4.7 corpus used: {report['old_v4_7_corpus_used']}",
        f"- Source manifest root: `{report['source_manifest_root']}`",
        f"- v5.1010 manifest root: `{report['manifest_root']}`",
        "",
        "## Split counts",
        "",
    ]
    for split, count in report["split_counts"].items():
        lines.append(f"- {split}: {count}")
    lines.extend(["", "## Family counts", ""])
    for family, count in report["family_counts"].items():
        lines.append(f"- {family}: {count}")
    lines.extend(["", "## Recovered manifests", ""])
    for item in report["recovered_missing_manifests"]:
        lines.append(f"- `{item['case_id']}` from `{item['fixture_dir']}`")
    lines.extend(["", "## Added cases", ""])
    for item in report["added_document_cases"]:
        lines.append(f"- `{item['case_id']}` ({item['doc_chembl_id']}), rows={item['row_count']}")
    lines.extend(
        [
            "",
            "## GEPA guardrails recorded with the dataset",
            "",
            f"- Promotion rule: {report['gepa_promotion_rule']}",
            f"- Full-1010 gate: {report['full_1010_gepa_gate']}",
            "- Provider policy: GLM-4.7 primary, then local 18081, then local 8081; do not spend GLM-5.1 quota.",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
