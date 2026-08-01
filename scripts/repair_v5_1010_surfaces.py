#!/usr/bin/env python3
"""Repair v5.1010 surface artifacts in the copy-on-write manifest root.

The v5.1010 build intentionally avoided editing v5.0 artifacts in place. This
script keeps that contract: repairs are written either under the v5.1010 fixture
directory for newly added cases, or under a v5.1010 override directory for copied
source cases whose old manifests had missing optional UP artifacts.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from compressed_io import read_text_maybe_compressed
from db_llm_v5.artifacts import V5CaseManifest
from db_llm_v5.backward import run_pb_sql, run_pb_up
from db_llm_v5.io import load_case_manifest, load_prompt_pack, save_case_manifest
from db_llm_v5.provider import EndpointConfig, build_provider, write_json


DEFAULT_PROMPT_PACK = (
    REPO_ROOT
    / "experiments/evals/v5_forward_eval/gepa_v5_weakfamilies_glm47_reseed56d_20260406_011416"
    / "candidate_cache/candidate_56d01a91befd8d8a.yaml"
)
DEFAULT_MANIFEST_DIR = REPO_ROOT / "tests/v5_manifests_1010/web_scrape_hq"
DEFAULT_DATASET_REPORT = REPO_ROOT / "experiments/v5.1010_dataset_report.json"
OVERRIDE_ROOT = REPO_ROOT / "tests/fixtures_1010_overrides"
NEW_DOC_ORIGIN = "v5.1010_document_wave2_grounded_sql_no_llm"
REPAIR_TAG = "local_llm_surface_repair"


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair v5.1010 UQ/UP artifacts with LocalLLM.")
    parser.add_argument("--manifest-dir", default=str(DEFAULT_MANIFEST_DIR))
    parser.add_argument("--dataset-report", default=str(DEFAULT_DATASET_REPORT))
    parser.add_argument("--prompt-pack", default=str(DEFAULT_PROMPT_PACK))
    parser.add_argument("--case-id", action="append", default=None)
    parser.add_argument(
        "--only",
        choices=["all", "new-docs", "missing-up-exec"],
        default="all",
        help="Repair scope. all repairs generated document surfaces and copied manifests with missing up_exec.",
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--primary-base-url", default="http://127.0.0.1:18081")
    parser.add_argument("--fallback-base-url", default="http://127.0.0.1:8081")
    parser.add_argument("--model", default="nemotron-cascade-2-30b-a3b")
    parser.add_argument("--max-tokens-sql-to-up", type=int, default=1200)
    parser.add_argument("--max-tokens-up-to-uq", type=int, default=800)
    parser.add_argument("--temperature", type=float, default=0.2)
    args = parser.parse_args()

    manifest_dir = Path(args.manifest_dir)
    prompt_pack = load_prompt_pack(Path(args.prompt_pack))
    provider = build_provider(
        endpoint=EndpointConfig(
            provider="llamacpp",
            model=args.model,
            base_url=args.primary_base_url,
            temperature=args.temperature,
            timeout=1200,
        ),
        fallback=EndpointConfig(
            provider="llamacpp",
            model=args.model,
            base_url=args.fallback_base_url,
            temperature=args.temperature,
            timeout=1200,
        ),
    )

    patched_case_ids = _patched_case_ids(Path(args.dataset_report))
    targets = _target_manifests(
        manifest_dir=manifest_dir,
        only=args.only,
        case_ids=args.case_id,
        patched_case_ids=patched_case_ids,
    )
    if args.limit is not None:
        targets = targets[: args.limit]

    repaired: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for manifest_path in targets:
        try:
            repaired.append(
                _repair_manifest(
                    manifest_path=manifest_path,
                    prompt_pack=prompt_pack,
                    provider=provider,
                    temperature=args.temperature,
                    max_tokens_sql_to_up=args.max_tokens_sql_to_up,
                    max_tokens_up_to_uq=args.max_tokens_up_to_uq,
                )
            )
        except Exception as exc:  # keep batch moving; report failures explicitly
            failures.append({"manifest": str(manifest_path.relative_to(REPO_ROOT)), "error": str(exc)})

    summary = {
        "prompt_pack": str(Path(args.prompt_pack).resolve()),
        "manifest_dir": str(manifest_dir.resolve()),
        "requested": len(targets),
        "repaired": len(repaired),
        "failed": len(failures),
        "repaired_cases": repaired,
        "failures": failures,
        "primary": {"provider": "llamacpp", "base_url": args.primary_base_url, "model": args.model},
        "fallback": {"provider": "llamacpp", "base_url": args.fallback_base_url, "model": args.model},
    }
    out_path = REPO_ROOT / "experiments/v5.1010_surface_repair_report.json"
    write_json(out_path, summary)
    print(json.dumps(summary, indent=2))
    if failures:
        raise SystemExit(1)


def _patched_case_ids(report_path: Path) -> set[str]:
    if not report_path.exists():
        return set()
    payload = json.loads(report_path.read_text())
    return {str(item["case_id"]) for item in payload.get("patched_missing_optional_artifacts", [])}


def _target_manifests(
    *,
    manifest_dir: Path,
    only: str,
    case_ids: list[str] | None,
    patched_case_ids: set[str],
) -> list[Path]:
    if case_ids:
        paths = [manifest_dir / f"{case_id}.json" for case_id in case_ids]
    else:
        paths = sorted(manifest_dir.rglob("*.json"))

    targets: list[Path] = []
    for path in paths:
        manifest = load_case_manifest(path)
        is_new_doc = manifest.metadata.origin == NEW_DOC_ORIGIN
        is_missing_up = manifest.case_id in patched_case_ids and manifest.artifacts.up_exec is None
        already_repaired = REPAIR_TAG in manifest.metadata.tags
        if only == "new-docs" and not is_new_doc:
            continue
        if only == "missing-up-exec" and not is_missing_up:
            continue
        if only == "all" and not (is_new_doc or is_missing_up):
            continue
        if already_repaired:
            continue
        targets.append(path)
    return targets


def _repair_manifest(
    *,
    manifest_path: Path,
    prompt_pack,
    provider,
    temperature: float,
    max_tokens_sql_to_up: int,
    max_tokens_up_to_uq: int,
) -> dict[str, Any]:
    manifest = load_case_manifest(manifest_path)
    original_uq = read_text_maybe_compressed(REPO_ROOT / manifest.artifacts.uq_surface).strip()
    pb_sql_result = run_pb_sql(
        prompt_pack=prompt_pack,
        manifest=manifest,
        repo_root=REPO_ROOT,
        provider=provider,
        max_tokens=max_tokens_sql_to_up,
        temperature=temperature,
    )
    up_exec = str(pb_sql_result["execution"]["parsed_json"].get("up_exec", "")).strip()
    if not up_exec:
        raise ValueError("PB_SQL produced empty up_exec")

    repair_dir = _repair_dir_for_manifest(manifest)
    repair_dir.mkdir(parents=True, exist_ok=True)
    up_exec_path = repair_dir / "up_exec.txt"
    up_exec_path.write_text(up_exec + "\n")
    write_json(repair_dir / "pb_sql.output.json", pb_sql_result)
    manifest.artifacts.up_exec = str(up_exec_path.relative_to(REPO_ROOT))

    generated_uq: str | None = None
    if manifest.metadata.origin == NEW_DOC_ORIGIN:
        pb_up_result = run_pb_up(
            prompt_pack=prompt_pack,
            manifest=manifest,
            repo_root=REPO_ROOT,
            provider=provider,
            up_exec_text=up_exec,
            max_tokens=max_tokens_up_to_uq,
            temperature=temperature,
        )
        generated_uq = str(pb_up_result["execution"]["parsed_json"].get("uq_surface", "")).strip()
        if not generated_uq:
            raise ValueError("PB_UP produced empty uq_surface")
        uq_path = REPO_ROOT / manifest.artifacts.uq_surface
        uq_path.write_text(generated_uq + "\n")
        write_json(repair_dir / "pb_up.output.json", pb_up_result)
        manifest.metadata.realism_level = "realistic_surface"

    if REPAIR_TAG not in manifest.metadata.tags:
        manifest.metadata.tags.append(REPAIR_TAG)
    manifest.metadata.notes = _append_note(
        manifest.metadata.notes,
        "v5.1010 LocalLLM repair: generated up_exec via PB_SQL"
        + (" and rewrote deterministic document UQ via PB_UP." if generated_uq is not None else "."),
    )
    save_case_manifest(manifest, manifest_path)
    errors = manifest.validate(REPO_ROOT)
    if errors:
        raise ValueError("; ".join(errors))

    return {
        "case_id": manifest.case_id,
        "manifest": str(manifest_path.relative_to(REPO_ROOT)),
        "up_exec_path": manifest.artifacts.up_exec,
        "rewrote_uq_surface": generated_uq is not None,
        "original_uq": original_uq,
        "new_uq": generated_uq,
    }


def _repair_dir_for_manifest(manifest: V5CaseManifest) -> Path:
    uq_path = REPO_ROOT / manifest.artifacts.uq_surface
    if "tests/fixtures/web_scrape_1010/" in manifest.artifacts.uq_surface:
        return uq_path.parent
    return OVERRIDE_ROOT / manifest.case_id


def _append_note(existing: str | None, addition: str) -> str:
    if not existing:
        return addition
    if addition in existing:
        return existing
    return f"{existing}\n{addition}"


if __name__ == "__main__":
    main()
