from __future__ import annotations

import json
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

from .artifacts import V5CaseManifest
from .io import load_case_manifest, save_case_manifest


def default_run_root(repo_root: Path, *, prefix: str) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    return repo_root / "experiments" / "v5_runs" / f"{prefix}_{stamp}"


def persist_generated_step(
    *,
    repo_root: Path,
    run_root: Path,
    manifest: V5CaseManifest,
    source_manifest_path: Path,
    prompt_pack_path: Path,
    step: str,
    payload: dict[str, Any],
) -> dict[str, str]:
    case_dir = run_root / manifest.case_id
    case_dir.mkdir(parents=True, exist_ok=True)

    json_path = case_dir / f"{step}.output.json"
    json_path.write_text(json.dumps(payload, indent=2) + "\n")

    generated_texts: dict[str, str] = {}
    execution = payload.get("execution")
    parsed = execution.get("parsed_json") if isinstance(execution, dict) else None
    if isinstance(parsed, dict):
        if "up" in parsed and parsed["up"]:
            generated_texts["up_exec"] = str(parsed["up"])
        if "up_exec" in parsed and parsed["up_exec"]:
            generated_texts["up_exec"] = str(parsed["up_exec"])
        if "uq_surface" in parsed and parsed["uq_surface"]:
            generated_texts["uq_surface"] = str(parsed["uq_surface"])
        if "sql" in parsed and parsed["sql"]:
            generated_texts["sql"] = str(parsed["sql"])

    written_paths: dict[str, str] = {"step_output_json": _rel(json_path, repo_root)}
    for key, text in generated_texts.items():
        ext = "sql" if key == "sql" else "txt"
        artifact_path = case_dir / f"{key}.generated.{ext}"
        artifact_path.write_text(text.strip() + "\n")
        written_paths[key] = _rel(artifact_path, repo_root)

    manifest_out = case_dir / "generated_case_manifest.json"
    base_manifest = load_case_manifest(manifest_out) if manifest_out.exists() else manifest
    generated_manifest = _build_generated_manifest(base_manifest, written_paths)
    save_case_manifest(generated_manifest, manifest_out)
    written_paths["generated_case_manifest"] = _rel(manifest_out, repo_root)

    metadata_out = case_dir / f"{step}.generated_artifact_record.json"
    metadata_out.write_text(
        json.dumps(
            {
                "case_id": manifest.case_id,
                "step": step,
                "source_manifest_path": str(source_manifest_path.resolve()),
                "prompt_pack_path": str(prompt_pack_path.resolve()),
                "written_paths": written_paths,
            },
            indent=2,
        )
        + "\n"
    )
    written_paths["generated_artifact_record"] = _rel(metadata_out, repo_root)
    latest_record = case_dir / "generated_artifact_record.json"
    latest_record.write_text(metadata_out.read_text())
    return written_paths


def _build_generated_manifest(manifest: V5CaseManifest, written_paths: dict[str, str]) -> V5CaseManifest:
    generated = replace(manifest)
    generated.artifacts = replace(generated.artifacts)
    if "up_exec" in written_paths:
        generated.artifacts.up_exec = written_paths["up_exec"]
    if "uq_surface" in written_paths:
        generated.artifacts.uq_surface = written_paths["uq_surface"]
    if "sql" in written_paths:
        generated.artifacts.sql_gold = written_paths["sql"]
        generated.artifacts.sqlite_sql = written_paths["sql"]
    return generated


def _rel(path: Path, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))
