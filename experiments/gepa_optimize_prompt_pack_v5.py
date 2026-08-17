#!/usr/bin/env python3
"""Run GEPA optimize_anything on the v5 prompt-pack artifact."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
SRC_DIR = REPO_ROOT / "src"
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
GEPA_SRC = REPO_ROOT / "contrib" / "gepa" / "src"
if GEPA_SRC.exists() and str(GEPA_SRC) not in sys.path:
    sys.path.insert(0, str(GEPA_SRC))

try:
    import gepa.optimize_anything as oa
    from gepa.optimize_anything import EngineConfig, GEPAConfig, ReflectionConfig, optimize_anything
except Exception as exc:  # pragma: no cover
    raise SystemExit(
        "Unable to import GEPA. Ensure contrib/gepa/src is present or install gepa. "
        f"Original error: {exc}"
    )

from compressed_io import read_text_maybe_compressed
from openai import OpenAI
from text2sql.anthropic_direct import AnthropicProvider

from db_llm_runtime_v5 import ChEMBLLLMQuery, Iteration
from db_llm_v5.forward import run_pf_sql, run_pf_up, run_res
from db_llm_v5.io import load_case_manifest, load_prompt_pack
from db_llm_v5.provider import EndpointConfig, build_provider, resolve_profile, write_json
from db_llm_v5.workspace import persist_generated_step

LOGGER = logging.getLogger(__name__)
DEFAULT_SPLIT_FILE = REPO_ROOT / "experiments" / "case_splits_v5.0_balanced.json"
DEFAULT_MANIFEST_ROOT = REPO_ROOT / "tests" / "v5_manifests"
DEFAULT_EVAL_ROOT = REPO_ROOT / "experiments" / "evals" / "v5_forward_eval"


def _looks_like_zai_quota_error(exc: Exception) -> bool:
    text = str(exc)
    return ("1308" in text) or ("Usage limit reached" in text)


def _looks_like_zai_auth_error(exc: Exception) -> bool:
    text = str(exc)
    return ("Authentication Failed" in text) or ('"type":"1000"' in text) or ("401" in text)


def _load_seed_candidate(path: Path) -> str:
    load_prompt_pack(path)
    return path.read_text(encoding="utf-8")


def _candidate_hash(candidate_text: str) -> str:
    return hashlib.sha256(candidate_text.encode("utf-8")).hexdigest()[:16]


def _sanitize_candidate_text(candidate_text: str) -> str:
    try:
        payload = yaml.safe_load(candidate_text)
    except Exception:
        return candidate_text
    if not isinstance(payload, dict):
        return candidate_text
    version = payload.get("version")
    if isinstance(version, str) and version.startswith("v5"):
        return candidate_text
    payload["version"] = "v5.gepa"
    sanitized = yaml.safe_dump(payload, sort_keys=False)
    return sanitized if sanitized.endswith("\n") else sanitized + "\n"


def _persist_candidate_text(run_dir: Path, candidate_text: str) -> Path:
    candidate_text = _sanitize_candidate_text(candidate_text)
    out_dir = run_dir / "candidate_cache"
    out_dir.mkdir(parents=True, exist_ok=True)
    candidate_path = out_dir / f"candidate_{_candidate_hash(candidate_text)}.yaml"
    if not candidate_path.exists():
        tmp_path = out_dir / f".{candidate_path.name}.{os.getpid()}.{time.time_ns()}.tmp"
        tmp_path.write_text(candidate_text, encoding="utf-8")
        os.replace(tmp_path, candidate_path)
    return candidate_path


def _score_objectives(family: str | None, score: float) -> dict[str, float]:
    rounded = round(float(score), 6)
    objectives = {"deterministic": rounded}
    if family:
        objectives[f"family::{family}"] = rounded
    return objectives


def _case_key(case: dict[str, Any], default_split: str) -> tuple[str, str, str]:
    return (
        str(case.get("split", default_split)),
        str(case["corpus"]),
        str(case["id"]),
    )


def _load_yaml_mapping(text: str) -> dict[str, Any]:
    payload = yaml.safe_load(text)
    if not isinstance(payload, dict):
        raise ValueError("Prompt-pack candidate must be a YAML mapping.")
    return payload


def _dump_yaml_mapping(payload: dict[str, Any]) -> str:
    text = yaml.safe_dump(payload, sort_keys=False)
    return text if text.endswith("\n") else text + "\n"


def _project_candidate_text(seed_text: str, candidate_text: str, mutable_fields: set[str]) -> str:
    """Freeze non-mutable nested v5 prompt-pack fields before scoring a candidate."""
    seed = _load_yaml_mapping(seed_text)
    candidate = _load_yaml_mapping(candidate_text)
    if "version" in candidate:
        candidate["version"] = "v5.gepa"
    if "system" not in mutable_fields:
        candidate["system"] = seed.get("system")
    if "pf.up" not in mutable_fields:
        candidate.setdefault("pf", {})["up"] = (seed.get("pf") or {}).get("up")
    if "pf.sql" not in mutable_fields:
        candidate.setdefault("pf", {})["sql"] = (seed.get("pf") or {}).get("sql")
    if "pf.judge" not in mutable_fields:
        candidate.setdefault("pf", {})["judge"] = (seed.get("pf") or {}).get("judge")
    if "pb" not in mutable_fields:
        candidate["pb"] = seed.get("pb")
    if "scoring" not in mutable_fields:
        candidate["scoring"] = seed.get("scoring")
    return _dump_yaml_mapping(candidate)


def _parse_mutable_fields(raw: str) -> set[str]:
    if raw.strip().lower() in {"all", "*"}:
        return {"system", "pf.up", "pf.sql", "pf.judge", "pb", "scoring"}
    fields = {item.strip() for item in raw.split(",") if item.strip()}
    allowed = {"system", "pf.up", "pf.sql", "pf.judge", "pb", "scoring"}
    unknown = sorted(fields - allowed)
    if unknown:
        raise ValueError(f"Unknown mutable field(s): {unknown}; allowed={sorted(allowed)}")
    return fields


def _runtime_template(text: str, placeholders: tuple[str, ...]) -> str:
    """Escape YAML prompt braces for runtime `.format(...)`, then restore known placeholders."""
    escaped = text.replace("{", "{{").replace("}", "}}")
    for placeholder in placeholders:
        escaped = escaped.replace("{{" + placeholder + "}}", "{" + placeholder + "}")
    return escaped


def _write_runtime_prompt_pack(candidate_path: Path, out_path: Path) -> Path:
    """Adapt nested v5 prompt-pack YAML to db_llm_runtime_v5's flattened prompt-pack format."""
    payload = _load_yaml_mapping(candidate_path.read_text(encoding="utf-8"))
    system = payload.get("system") or {}
    pf = payload.get("pf") or {}
    if not isinstance(system, dict) or not isinstance(pf, dict):
        raise ValueError("Candidate prompt pack must contain mapping keys `system` and `pf`.")
    runtime_payload = {
        "version": str(payload.get("version", "v5.gepa.runtime")),
        "prompt_hints_path": str((REPO_ROOT / (system.get("hint_block_path") or "doc/chembl_prompt_hints_v4.11.md")).resolve()),
        "about_block": system.get("about_block") or "",
        "examples_block": system.get("examples_block") or "",
        "up_task_template": _runtime_template(str(pf.get("up") or ""), ("next_n", "prev_judge")),
        "sql_task_template": _runtime_template(str(pf.get("sql") or ""), ("n",)),
        "judge_task_template": _runtime_template(
            str(pf.get("judge") or ""),
            ("n", "judge_score_threshold", "judge_yes_score_threshold", "judge_no_override_threshold"),
        ),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(_dump_yaml_mapping(runtime_payload), encoding="utf-8")
    return out_path


def _append_run_log(run_dir: Path, title: str, payload: dict[str, Any] | str) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y-%m-%d %H:%M:%S %Z")
    body = payload if isinstance(payload, str) else json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
    with (run_dir / "run.log").open("a", encoding="utf-8") as handle:
        handle.write(f"\n{'=' * 88}\n{title} [{ts}]\n{'=' * 88}\n{body.rstrip()}\n")


def _attach_case_runtime_log(case_root: Path) -> logging.Handler:
    case_root.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(case_root / "run.log", mode="a", encoding="utf-8")
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(stage)s - %(message)s"))
    logging.getLogger().addHandler(handler)
    return handler


def _detach_case_runtime_log(handler: logging.Handler) -> None:
    root = logging.getLogger()
    root.removeHandler(handler)
    handler.close()


def _iteration_to_dict(it: Iteration) -> dict[str, Any]:
    return {
        "n": it.n,
        "up": it.up,
        "sql": it.sql,
        "sql_model": it.sql_model,
        "plan_summary": it.plan_summary,
        "res_row_count": it.res_row_count,
        "res_columns": list(it.res_columns),
        "res_error": it.res_error,
        "judge_text": it.judge_text,
        "judge_model": it.judge_model,
        "judge_score": it.judge_score,
        "judge_decision": it.judge_decision,
    }


def _text_block(title: str, text: Any) -> str:
    content = "" if text is None else str(text).rstrip()
    return f"--- {title} ---\n{content}\n--- end {title} ---"


def _format_key_values(values: dict[str, Any]) -> str:
    lines: list[str] = []
    for key, value in values.items():
        if value is None:
            continue
        if isinstance(value, (dict, list)):
            value = json.dumps(value, indent=2, ensure_ascii=False)
        lines.append(f"{key}: {value}")
    return "\n".join(lines)


def _csv_preview(path: Path, *, max_rows: int = 20) -> str:
    if not path.exists():
        return _format_key_values({"csv_path": str(path.resolve()), "csv_preview": "missing"})
    rows: list[list[str]] = []
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            for index, row in enumerate(reader):
                rows.append(row)
                if index >= max_rows:
                    break
    except Exception as exc:
        return _format_key_values({"csv_path": str(path.resolve()), "csv_preview_error": str(exc)})
    if not rows:
        return _format_key_values({"csv_path": str(path.resolve()), "csv_preview": "empty"})
    rendered_rows = [",".join(_csv_quote(cell) for cell in row) for row in rows]
    return "\n".join(
        [
            _format_key_values({"csv_path": str(path.resolve()), "csv_preview_rows": len(rows)}),
            _text_block("CSV preview", "\n".join(rendered_rows)),
            "Preview includes header plus first rows only; see full CSV at path above.",
        ]
    )


def _csv_quote(value: str) -> str:
    if any(ch in value for ch in [",", '"', "\n", "\r"]):
        return '"' + value.replace('"', '""') + '"'
    return value


def _append_case_log(case_root: Path, title: str, body: str) -> None:
    with (case_root / "run.log").open("a", encoding="utf-8") as handle:
        handle.write(f"\n\n{'=' * 88}\n{title}\n{'=' * 88}\n")
        handle.write(body.rstrip() + "\n")


def _render_judge_loop_transcript(
    *,
    uq: str,
    iterations: list[Iteration],
    result_path: Path,
    pf_res_payload: dict[str, Any] | None,
    latest_up: str | None,
    latest_sql: str | None,
) -> str:
    parts = [_text_block("UQ", uq)]
    for it in iterations:
        parts.append(
            "\n\n".join(
                [
                    _format_key_values(
                        {
                            "iteration": it.n,
                            "sql_model": it.sql_model,
                            "judge_model": it.judge_model,
                            "res_row_count": it.res_row_count,
                            "res_columns": list(it.res_columns),
                            "res_error": it.res_error,
                            "judge_score": it.judge_score,
                            "judge_decision": it.judge_decision,
                        }
                    ),
                    _text_block(f"UP_{it.n}", it.up),
                    _text_block(f"SQL_{it.n}", it.sql),
                    _text_block(f"PLAN_{it.n}", it.plan_summary),
                    _text_block(f"RES_{it.n} samples", _format_res_samples(it.res_samples)),
                    _text_block(f"J_{it.n}", it.judge_text),
                ]
            )
        )
    if not iterations:
        parts.append(
            "\n\n".join(
                [
                    "No accepted judge-loop Iteration objects were exposed by the runtime.",
                    _text_block("Latest UP", latest_up),
                    _text_block("Latest SQL", latest_sql),
                ]
            )
        )
    if pf_res_payload is not None:
        parts.extend(
            [
                _text_block("Final PF_RES result", json.dumps(pf_res_payload.get("result"), indent=2, ensure_ascii=False)),
                _text_block(
                    "Final deterministic score",
                    json.dumps(pf_res_payload.get("deterministic_score"), indent=2, ensure_ascii=False),
                ),
            ]
        )
    parts.append(_csv_preview(result_path, max_rows=20))
    return "\n\n".join(part for part in parts if part.strip())


def _format_res_samples(samples: tuple[tuple[str, tuple[str, ...]], ...]) -> str:
    if not samples:
        return ""
    lines = []
    for position, row in samples:
        lines.append(f"{position}: " + " | ".join(str(cell) for cell in row))
    return "\n".join(lines)


def _build_background(split_file: Path, train_split: str, val_split: str, test_split: str) -> str:
    return "\n".join(
        [
            "You are optimizing a ChEMBL v5 prompt-pack YAML.",
            "The candidate artifact is the full YAML prompt pack used by the v5 forward chain.",
            "Optimize for executable result-set agreement, not judge wording.",
            "Use the train split for learning, the val split for selection, and keep the test split untouched until after optimization.",
            f"Split file: {split_file}",
            f"Train split: {train_split}",
            f"Validation split: {val_split}",
            f"Held-out test split: {test_split}",
            "Prefer compact prompt changes that improve column fidelity, join choice, and exact filter semantics.",
        ]
    )


def _build_reflection_lm(
    *,
    reflection_lm: str | None,
    reflection_model: str,
    reflection_base_url: str | None,
    reflection_timeout: int,
    reflection_temperature: float,
    reflection_verbose: bool,
    reflection_fallback_base_url: str | None,
    reflection_fallback_model: str,
):
    if reflection_lm:
        return reflection_lm

    provider = AnthropicProvider(
        api_key=os.getenv("ZAI_ANTHROPIC_AUTH_TOKEN"),
        model=reflection_model,
        base_url=reflection_base_url,
        timeout=reflection_timeout,
        temperature=reflection_temperature,
        verbose=reflection_verbose,
    )
    if not provider.is_available():
        raise SystemExit("ZAI_ANTHROPIC_AUTH_TOKEN is not available for GEPA reflection LM.")

    fallback_client = OpenAI(
        base_url=(reflection_fallback_base_url or "http://127.0.0.1:18081/v1"),
        api_key="EMPTY",
    )
    fallback_active = False

    def _fallback_reflection(prompt: str | list[dict[str, Any]]) -> str:
        input_payload: Any = prompt
        response = fallback_client.responses.create(
            model=reflection_fallback_model,
            input=input_payload,
            max_output_tokens=8192,
            temperature=reflection_temperature,
        )
        text = getattr(response, "output_text", None)
        if text:
            return text
        raise RuntimeError("Local fallback reflection LM returned no text.")

    def _reflection(prompt: str | list[dict[str, Any]]) -> str:
        nonlocal fallback_active
        if fallback_active:
            return _fallback_reflection(prompt)
        if isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        else:
            messages = prompt
        try:
            text = provider.generate_text(messages, temperature=reflection_temperature, max_tokens=8192)
        except Exception as exc:
            if not (_looks_like_zai_quota_error(exc) or _looks_like_zai_auth_error(exc)):
                raise
            fallback_active = True
            LOGGER.warning(
                "GEPA reflection switching to local fallback after Z.AI issue (%s): %s at %s",
                type(exc).__name__,
                reflection_fallback_model,
                reflection_fallback_base_url or "http://127.0.0.1:18081/v1",
            )
            return _fallback_reflection(prompt)
        if text is None:
            raise RuntimeError("Z.AI reflection LM returned no text.")
        return text

    return _reflection


def _split_cases(split_payload: dict[str, Any], split_name: str, limit: int | None) -> list[dict[str, Any]]:
    cases = [{"split": split_name, **dict(item)} for item in split_payload["splits"][split_name]]
    return cases[:limit] if limit is not None else cases


def _evaluate_case(
    *,
    candidate_text: str,
    candidate_path: Path,
    split_name: str,
    case: dict[str, Any],
    manifest_root: Path,
    repo_root: Path,
    eval_root: Path,
    provider,
    up_max_tokens: int,
    sql_max_tokens: int,
    temperature: float,
) -> tuple[float, dict[str, Any]]:
    manifest_path = manifest_root / str(case["corpus"]) / f'{case["id"]}.json'
    manifest = load_case_manifest(manifest_path)
    candidate_id = _candidate_hash(candidate_text)
    split_root = eval_root / candidate_id / split_name / str(case["corpus"])
    case_root = split_root / str(case["id"])
    case_root.mkdir(parents=True, exist_ok=True)
    try:
        candidate_pack = load_prompt_pack(candidate_path)
    except Exception as exc:
        side_info = {
            "prompt_pack_path": str(candidate_path.resolve()),
            "case_manifest_path": str(manifest_path.resolve()),
            "case_id": manifest.case_id,
            "split": split_name,
            "corpus": manifest.corpus,
            "family": manifest.metadata.family,
            "candidate_hash": candidate_id,
            "status": "invalid_candidate",
            "score": 0.0,
            "scores": _score_objectives(manifest.metadata.family, 0.0),
            "error": str(exc),
        }
        write_json(case_root / "case_error.json", side_info)
        oa.log(json.dumps(side_info, ensure_ascii=False))
        return 0.0, side_info

    base = {
        "prompt_pack_path": str(candidate_path.resolve()),
        "prompt_pack_version": candidate_pack.version,
        "case_manifest_path": str(manifest_path.resolve()),
        "case_id": manifest.case_id,
        "split": split_name,
        "corpus": manifest.corpus,
        "family": manifest.metadata.family,
        "candidate_hash": candidate_id,
    }

    try:
        pf_up = run_pf_up(
            prompt_pack=candidate_pack,
            manifest=manifest,
            repo_root=repo_root,
            provider=provider,
            max_tokens=up_max_tokens,
            temperature=temperature,
        )
        pf_up_payload = {**base, "selected_step": "up", **pf_up}
        pf_up_written = persist_generated_step(
            repo_root=repo_root,
            run_root=split_root,
            manifest=manifest,
            source_manifest_path=manifest_path,
            prompt_pack_path=candidate_path,
            step="pf_up",
            payload=pf_up_payload,
        )
        if "up_exec" not in pf_up_written:
            raise ValueError("PF_UP produced no up_exec artifact")
        up_exec_text = read_text_maybe_compressed(repo_root / pf_up_written["up_exec"]).strip()

        pf_sql = run_pf_sql(
            prompt_pack=candidate_pack,
            manifest=manifest,
            repo_root=repo_root,
            provider=provider,
            up_exec_text=up_exec_text,
            max_tokens=sql_max_tokens,
            temperature=temperature,
        )
        pf_sql_payload = {**base, "selected_step": "sql", **pf_sql}
        pf_sql_written = persist_generated_step(
            repo_root=repo_root,
            run_root=split_root,
            manifest=manifest,
            source_manifest_path=manifest_path,
            prompt_pack_path=candidate_path,
            step="pf_sql",
            payload=pf_sql_payload,
        )
        if "sql" not in pf_sql_written:
            raise ValueError("PF_SQL produced no sql artifact")
        sql_text = read_text_maybe_compressed(repo_root / pf_sql_written["sql"]).strip()

        result_path = case_root / "result.generated.csv"
        pf_res = run_res(manifest=manifest, repo_root=repo_root, sql_text=sql_text, result_path=result_path)
        pf_res_payload = {**base, "selected_step": "res", **pf_res}
        pf_res_written = persist_generated_step(
            repo_root=repo_root,
            run_root=split_root,
            manifest=manifest,
            source_manifest_path=manifest_path,
            prompt_pack_path=candidate_path,
            step="pf_res",
            payload=pf_res_payload,
        )
        pf_res_written["result_path"] = str(result_path.resolve().relative_to(repo_root.resolve()))
        pf_res_payload["written_paths"] = pf_res_written
        write_json(case_root / "pf_res.output.json", pf_res_payload)

        det = pf_res_payload.get("deterministic_score") or {}
        status = str(det.get("status", "fail"))
        score = float(det.get("score", 0.0)) if det else 0.0
        result_success = bool(pf_res_payload["result"]["success"])
        result_rows = int(pf_res_payload["result"]["row_count"] or 0)
        result_cols = list(pf_res_payload["result"]["column_names"] or [])
        side_info = {
            **base,
            "status": status,
            "score": round(score, 6),
            "result_success": result_success,
            "result_rows": result_rows,
            "result_cols": result_cols,
            "result_path": str(result_path.resolve()),
            "scores": _score_objectives(manifest.metadata.family, score),
            "written_paths": pf_res_written,
        }
        if pf_res_payload["result"]["error"]:
            side_info["error"] = pf_res_payload["result"]["error"]
        oa.log(json.dumps(side_info, ensure_ascii=False))
        return score, side_info
    except Exception as exc:
        side_info = {
            **base,
            "status": "run_failed",
            "score": 0.0,
            "scores": _score_objectives(manifest.metadata.family, 0.0),
            "error": str(exc),
        }
        write_json(case_root / "case_error.json", side_info)
        oa.log(json.dumps(side_info, ensure_ascii=False))
        return 0.0, side_info


def _load_uq_text(manifest, repo_root: Path) -> str:
    if manifest.artifacts.uq_surface is None:
        raise ValueError("Manifest is missing uq_surface")
    return read_text_maybe_compressed(repo_root / manifest.artifacts.uq_surface).strip()


def _normalize_fallbacks(fallback: Any) -> list[EndpointConfig]:
    if fallback is None:
        return []
    if isinstance(fallback, list):
        return list(fallback)
    return [fallback]


def _endpoint_to_dict(endpoint: EndpointConfig) -> dict[str, Any]:
    return {
        "provider": endpoint.provider,
        "model": endpoint.model,
        "base_url": endpoint.base_url,
        "temperature": endpoint.temperature,
        "timeout": endpoint.timeout,
    }


def _build_judge_loop_llm(
    *,
    endpoint: EndpointConfig,
    fallback: Any,
    prompt_pack_path: Path,
    max_iterations: int,
    history_window_up_sql: str,
    judge_history_window: int,
    judge_score_threshold: float,
    judge_no_override_threshold: float,
    judge_call_retries: int,
    judge_max_tokens: int,
    timeout: int,
    temperature: float,
    local_enable_thinking: bool,
    local_reasoning_budget_tokens: int | None,
    local_reasoning_budget_message: str | None,
    case_context: dict[str, Any] | None = None,
) -> ChEMBLLLMQuery:
    fallback_list = _normalize_fallbacks(fallback)
    quota_provider = fallback_list[0] if fallback_list else None
    quota_provider_2 = fallback_list[1] if len(fallback_list) > 1 else None
    history_window = None if history_window_up_sql.strip().lower() in {"all", "*"} else int(history_window_up_sql)
    return ChEMBLLLMQuery(
        provider=endpoint.provider,
        provider_base_url=endpoint.base_url,
        sql_model=endpoint.model,
        judge_model=endpoint.model,
        max_retries=max_iterations,
        timeout=timeout,
        writer_timeout=timeout,
        judge_timeout=timeout,
        history_window_up_sql=history_window,
        judge_history_window=judge_history_window,
        judge_score_threshold=judge_score_threshold,
        judge_no_override_threshold=judge_no_override_threshold,
        judge_call_retries=judge_call_retries,
        judge_max_tokens=judge_max_tokens,
        local_enable_thinking=local_enable_thinking,
        local_reasoning_budget_tokens=local_reasoning_budget_tokens,
        local_reasoning_budget_message=local_reasoning_budget_message,
        min_context=100000,
        schema_docs_path=str((REPO_ROOT / "doc/chembl_database_schema.md").resolve()),
        save_intermediate=False,
        prompt_pack_path=str(prompt_pack_path),
        sql_temperature=temperature,
        prompt_writer_temperature=temperature,
        judge_temperature=temperature,
        memory_json_path=None,
        quota_fallback_provider=quota_provider.provider if quota_provider else None,
        quota_fallback_base_url=quota_provider.base_url if quota_provider else None,
        quota_fallback_model=quota_provider.model if quota_provider else None,
        quota_fallback_provider_2=quota_provider_2.provider if quota_provider_2 else None,
        quota_fallback_base_url_2=quota_provider_2.base_url if quota_provider_2 else None,
        quota_fallback_model_2=quota_provider_2.model if quota_provider_2 else None,
        case_context=case_context,
    )


def _evaluate_case_judge_loop(
    *,
    candidate_text: str,
    candidate_path: Path,
    split_name: str,
    case: dict[str, Any],
    manifest_root: Path,
    repo_root: Path,
    eval_root: Path,
    endpoint: EndpointConfig,
    fallback: Any,
    max_iterations: int,
    history_window_up_sql: str,
    judge_history_window: int,
    judge_score_threshold: float,
    judge_no_override_threshold: float,
    judge_call_retries: int,
    judge_max_tokens: int,
    timeout: int,
    temperature: float,
    local_enable_thinking: bool,
    local_reasoning_budget_tokens: int | None,
    local_reasoning_budget_message: str | None,
    case_ordinal: int | None = None,
    case_total: int | None = None,
) -> tuple[float, dict[str, Any]]:
    manifest_path = manifest_root / str(case["corpus"]) / f'{case["id"]}.json'
    manifest = load_case_manifest(manifest_path)
    candidate_id = _candidate_hash(candidate_text)
    case_root = eval_root / candidate_id / split_name / str(case["corpus"]) / str(case["id"])
    case_root.mkdir(parents=True, exist_ok=True)
    (case_root / "run.log").write_text("", encoding="utf-8")
    (case_root / "run.events.jsonl").write_text("", encoding="utf-8")
    base = {
        "prompt_pack_path": str(candidate_path.resolve()),
        "case_manifest_path": str(manifest_path.resolve()),
        "case_id": manifest.case_id,
        "split": split_name,
        "corpus": manifest.corpus,
        "family": manifest.metadata.family,
        "candidate_hash": candidate_id,
        "metric_mode": "judge-loop",
    }
    case_context = {
        "case": (
            f"{case_ordinal} / {case_total}"
            if case_ordinal is not None and case_total is not None
            else None
        ),
        "ordinal": case_ordinal,
        "total_cases": case_total,
        "split": split_name,
        "corpus": manifest.corpus,
        "case_id": manifest.case_id,
        "family": manifest.metadata.family,
        "manifest_path": str(manifest_path.resolve()),
        "case_dir": str(case_root.resolve()),
        "candidate_hash": candidate_id,
        "metric_mode": "judge-loop",
    }
    case_context = {key: value for key, value in case_context.items() if value is not None}

    runtime_prompt_path = case_root / "runtime_prompt_pack.yaml"
    handler: logging.Handler | None = None
    try:
        load_prompt_pack(candidate_path)
        _write_runtime_prompt_pack(candidate_path, runtime_prompt_path)
        uq = _load_uq_text(manifest, repo_root)
        result_path = case_root / "result.generated.csv"
        llm = _build_judge_loop_llm(
            endpoint=endpoint,
            fallback=fallback,
            prompt_pack_path=runtime_prompt_path,
            max_iterations=max_iterations,
            history_window_up_sql=history_window_up_sql,
            judge_history_window=judge_history_window,
            judge_score_threshold=judge_score_threshold,
            judge_no_override_threshold=judge_no_override_threshold,
            judge_call_retries=judge_call_retries,
            judge_max_tokens=judge_max_tokens,
            timeout=timeout,
            temperature=temperature,
            local_enable_thinking=local_enable_thinking,
            local_reasoning_budget_tokens=local_reasoning_budget_tokens,
            local_reasoning_budget_message=local_reasoning_budget_message,
            case_context=case_context,
        )
        (case_root / "run.events.jsonl").write_text(
            json.dumps({**base, "event": "case_start"}, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        with (case_root / "run.log").open("a", encoding="utf-8") as handle:
            handle.write(
                "\n".join(
                    [
                        "=" * 88,
                        "Case Start",
                        "=" * 88,
                        json.dumps(
                            {
                                **base,
                                "runtime_prompt_pack": str(runtime_prompt_path.resolve()),
                                "case_context": case_context,
                            },
                            indent=2,
                            ensure_ascii=False,
                            sort_keys=True,
                        ),
                        "",
                        "--- UQ ---",
                        uq,
                        "--- end UQ ---",
                        "",
                    ]
                )
            )
        handler = _attach_case_runtime_log(case_root)
        try:
            df = llm.query(
                uq,
                save_to_file=result_path,
                min_rows=1,
                case_label=(
                    f"{case_ordinal}/{case_total} {split_name}/{case['corpus']}/{case['id']}"
                    if case_ordinal is not None and case_total is not None
                    else f"{split_name}/{case['corpus']}/{case['id']}"
                ),
            )
        finally:
            if handler is not None:
                _detach_case_runtime_log(handler)
                handler = None
        if df is None:
            raise RuntimeError("Judge-loop query returned no result")
        if not llm.latest_sql:
            raise RuntimeError("Judge-loop produced no SQL")

        if llm.latest_up is not None:
            write_json(case_root / "pf_up.output.json", {**base, "selected_step": "up", "text": llm.latest_up})
        write_json(case_root / "pf_sql.output.json", {**base, "selected_step": "sql", "text": llm.latest_sql})
        pf_res = run_res(manifest=manifest, repo_root=repo_root, sql_text=llm.latest_sql, result_path=result_path)
        pf_res_payload = {**base, "selected_step": "res", **pf_res}
        write_json(case_root / "pf_res.output.json", pf_res_payload)
        iterations_data = [_iteration_to_dict(it) for it in llm.latest_iterations]
        write_json(case_root / "judge_loop_iterations.json", iterations_data)

        det = pf_res_payload.get("deterministic_score") or {}
        status = str(det.get("status", "fail"))
        score = float(det.get("score", 0.0)) if det else 0.0
        result_success = bool(pf_res_payload["result"]["success"])
        side_info = {
            **base,
            "status": status,
            "score": round(score, 6),
            "result_success": result_success,
            "result_rows": int(pf_res_payload["result"]["row_count"] or 0),
            "result_cols": list(pf_res_payload["result"]["column_names"] or []),
            "result_path": str(result_path.resolve()),
            "scores": _score_objectives(manifest.metadata.family, score),
            "iterations": len(iterations_data),
            "judge_decision": llm.latest_judge_decision,
            "judge_score": llm.latest_judge_score,
            "returned_iteration": llm.latest_returned_iteration_n,
            "judge_loop_exhausted": llm.latest_exhausted,
            "runtime_prompt_pack": str(runtime_prompt_path.resolve()),
        }
        if pf_res_payload["result"]["error"]:
            side_info["error"] = pf_res_payload["result"]["error"]
        _append_case_log(
            case_root,
            "Judge Loop Transcript",
            _render_judge_loop_transcript(
                uq=uq,
                iterations=list(llm.latest_iterations),
                result_path=result_path,
                pf_res_payload=pf_res_payload,
                latest_up=llm.latest_up,
                latest_sql=llm.latest_sql,
            ),
        )
        with (case_root / "run.events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({**side_info, "event": "case_complete"}, ensure_ascii=False, sort_keys=True) + "\n")
        _append_case_log(case_root, "Case Complete", json.dumps(side_info, indent=2, ensure_ascii=False, sort_keys=True))
        oa.log(json.dumps(side_info, ensure_ascii=False))
        return score, side_info
    except Exception as exc:
        if handler is not None:
            _detach_case_runtime_log(handler)
        side_info = {
            **base,
            "status": "run_failed",
            "score": 0.0,
            "scores": _score_objectives(manifest.metadata.family, 0.0),
            "error": str(exc),
        }
        if "llm" in locals():
            latest_iterations = list(getattr(llm, "latest_iterations", []) or [])
            latest_up = getattr(llm, "latest_up", None)
            latest_sql = getattr(llm, "latest_sql", None)
            if latest_iterations:
                latest_up = latest_up or latest_iterations[-1].up
                latest_sql = latest_sql or latest_iterations[-1].sql
            if latest_up is not None:
                write_json(case_root / "pf_up.output.json", {**base, "selected_step": "up", "text": latest_up})
            if latest_sql is not None:
                write_json(case_root / "pf_sql.output.json", {**base, "selected_step": "sql", "text": latest_sql})
            _append_case_log(
                case_root,
                "Partial Judge Loop Transcript",
                _render_judge_loop_transcript(
                    uq=locals().get("uq", ""),
                    iterations=latest_iterations,
                    result_path=locals().get("result_path", case_root / "result.generated.csv"),
                    pf_res_payload=None,
                    latest_up=latest_up,
                    latest_sql=latest_sql,
                ),
            )
        write_json(case_root / "case_error.json", side_info)
        with (case_root / "run.events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({**side_info, "event": "case_error"}, ensure_ascii=False, sort_keys=True) + "\n")
        _append_case_log(case_root, "Case Error", json.dumps(side_info, indent=2, ensure_ascii=False, sort_keys=True))
        oa.log(json.dumps(side_info, ensure_ascii=False))
        return 0.0, side_info


def _evaluate_split(
    *,
    candidate_text: str,
    candidate_path: Path,
    split_name: str,
    cases: list[dict[str, Any]],
    manifest_root: Path,
    repo_root: Path,
    eval_root: Path,
    provider,
    endpoint: EndpointConfig | None = None,
    fallback: Any = None,
    up_max_tokens: int,
    sql_max_tokens: int,
    temperature: float,
    metric_mode: str = "one-shot",
    judge_loop_max_iterations: int = 10,
    history_window_up_sql: str = "all",
    judge_history_window: int = 1,
    judge_score_threshold: float = 0.5,
    judge_no_override_threshold: float = 0.99,
    judge_call_retries: int = 3,
    judge_max_tokens: int = 4096,
    timeout: int = 600,
    local_enable_thinking: bool = True,
    local_reasoning_budget_tokens: int | None = None,
    local_reasoning_budget_message: str | None = None,
    write_report: bool = False,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    family_stats: dict[str, dict[str, float | int]] = {}
    total_cases = len(cases)
    for case_ordinal, case in enumerate(cases, start=1):
        if metric_mode == "judge-loop":
            if endpoint is None:
                raise ValueError("endpoint is required for judge-loop metric mode")
            score, side_info = _evaluate_case_judge_loop(
                candidate_text=candidate_text,
                candidate_path=candidate_path,
                split_name=split_name,
                case=case,
                manifest_root=manifest_root,
                repo_root=repo_root,
                eval_root=eval_root,
                endpoint=endpoint,
                fallback=fallback,
                max_iterations=judge_loop_max_iterations,
                history_window_up_sql=history_window_up_sql,
                judge_history_window=judge_history_window,
                judge_score_threshold=judge_score_threshold,
                judge_no_override_threshold=judge_no_override_threshold,
                judge_call_retries=judge_call_retries,
                judge_max_tokens=judge_max_tokens,
                timeout=timeout,
                temperature=temperature,
                local_enable_thinking=local_enable_thinking,
                local_reasoning_budget_tokens=local_reasoning_budget_tokens,
                local_reasoning_budget_message=local_reasoning_budget_message,
                case_ordinal=case_ordinal,
                case_total=total_cases,
            )
        else:
            score, side_info = _evaluate_case(
                candidate_text=candidate_text,
                candidate_path=candidate_path,
                split_name=split_name,
                case=case,
                manifest_root=manifest_root,
                repo_root=repo_root,
                eval_root=eval_root,
                provider=provider,
                up_max_tokens=up_max_tokens,
                sql_max_tokens=sql_max_tokens,
                temperature=temperature,
            )
        row = {
            "case_id": case["id"],
            "split": split_name,
            "corpus": case["corpus"],
            "family": side_info.get("family"),
            "status": side_info["status"],
            "score": float(score),
            "result_success": side_info.get("result_success", False),
            "result_rows": side_info.get("result_rows"),
            "result_cols": side_info.get("result_cols"),
            "case_root": str((eval_root / _candidate_hash(candidate_text) / split_name / str(case["corpus"]) / str(case["id"])).resolve()),
        }
        if "error" in side_info:
            row["error"] = side_info["error"]
        results.append(row)
        family = str(side_info.get("family") or "unknown")
        stats = family_stats.setdefault(family, {"n_cases": 0, "n_pass": 0, "mean_score": 0.0})
        stats["n_cases"] += 1
        stats["n_pass"] += 1 if side_info["status"] == "pass" else 0
        stats["mean_score"] += float(score)

    for family, stats in family_stats.items():
        n_cases = int(stats["n_cases"])
        stats["mean_score"] = round(float(stats["mean_score"]) / n_cases, 6) if n_cases else 0.0
        stats["pass_rate"] = round(int(stats["n_pass"]) / n_cases, 6) if n_cases else 0.0

    n_cases = len(results)
    n_pass = sum(1 for row in results if row["status"] == "pass")
    mean_score = round(sum(float(row["score"]) for row in results) / n_cases, 6) if n_cases else 0.0
    report = {
        "candidate_hash": _candidate_hash(candidate_text),
        "candidate_path": str(candidate_path.resolve()),
        "split": split_name,
        "manifest_root": str(manifest_root.resolve()),
        "eval_root": str((eval_root / _candidate_hash(candidate_text) / split_name).resolve()),
        "summary": {
            "n_cases": n_cases,
            "n_pass": n_pass,
            "pass_rate": round(n_pass / n_cases, 6) if n_cases else 0.0,
            "mean_score": mean_score,
        },
        "by_family": family_stats,
        "cases": results,
    }
    if write_report:
        report_path = eval_root / _candidate_hash(candidate_text) / split_name / "report.json"
        write_json(report_path, report)
        report["report_path"] = str(report_path.resolve())
    return report


def _resolve_endpoint_args(args: argparse.Namespace) -> tuple[EndpointConfig, EndpointConfig | None]:
    endpoint = None
    fallback = None
    if args.multi_endpoint_profile:
        endpoint, fallback = resolve_profile(args.multi_endpoint_profile)
    if endpoint is None:
        if not args.provider or not args.model:
            raise ValueError("Either --multi-endpoint-profile or both --provider and --model are required")
        endpoint = EndpointConfig(
            provider=args.provider,
            model=args.model,
            base_url=args.provider_base_url,
            temperature=args.temperature,
            timeout=args.timeout,
        )
    if args.quota_fallback_provider:
        fallback = EndpointConfig(
            provider=args.quota_fallback_provider,
            model=args.quota_fallback_model or "",
            base_url=args.quota_fallback_base_url,
            temperature=args.temperature,
            timeout=args.timeout,
        )
    return endpoint, fallback


def main() -> None:
    parser = argparse.ArgumentParser(description="Optimize the v5 prompt-pack YAML with GEPA optimize_anything.")
    parser.add_argument("--seed-prompt-pack", default=str(REPO_ROOT / "experiments" / "prompt_pack_v5.9.yaml"), help="Seed prompt-pack YAML")
    parser.add_argument("--output-prompt-pack", default=None, help="Where to write the best optimized prompt-pack YAML")
    parser.add_argument("--split-file", default=str(DEFAULT_SPLIT_FILE), help="Case split JSON")
    parser.add_argument("--manifest-root", default=str(DEFAULT_MANIFEST_ROOT), help="Root directory containing v5 case manifests")
    parser.add_argument("--eval-root", default=str(DEFAULT_EVAL_ROOT), help="Directory for GEPA outputs")
    parser.add_argument("--train-split", default="train", help="Train split name")
    parser.add_argument("--val-split", default="val", help="Validation split name")
    parser.add_argument("--test-split", default="test", help="Held-out test split name")
    parser.add_argument("--multi-endpoint-profile", default="zai-glm47-local-fallbacks", help="Provider profile for the v5 forward chain")
    parser.add_argument("--provider", default=None, help="Primary provider name, if not using a profile")
    parser.add_argument("--provider-base-url", default=None, help="Primary provider base URL, if not using a profile")
    parser.add_argument("--model", default=None, help="Primary model name, if not using a profile")
    parser.add_argument("--temperature", type=float, default=0.2, help="Forward-chain provider temperature")
    parser.add_argument("--timeout", type=int, default=600, help="Forward-chain provider timeout")
    parser.add_argument("--quota-fallback-provider", default=None, help="Fallback provider name")
    parser.add_argument("--quota-fallback-base-url", default=None, help="Fallback provider base URL")
    parser.add_argument("--quota-fallback-model", default=None, help="Fallback provider model name")
    parser.add_argument(
        "--local-enable-thinking",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable llama.cpp-local chat-template thinking for local providers/fallbacks (default: enabled)",
    )
    parser.add_argument("--local-reasoning-budget-tokens", type=int, default=None, help="Per-call llama.cpp local thinking budget")
    parser.add_argument("--local-reasoning-budget-message", default=None, help="Optional local thinking budget exhaustion message")
    parser.add_argument("--up-max-tokens", type=int, default=1200, help="Max tokens for PF_UP")
    parser.add_argument("--sql-max-tokens", type=int, default=4000, help="Max tokens for PF_SQL")
    parser.add_argument("--metric-mode", choices=["one-shot", "judge-loop"], default="one-shot", help="Candidate evaluator: one-shot PF_UP/PF_SQL/PF_RES or full judge loop")
    parser.add_argument("--mutable-fields", default="all", help="Comma-separated prompt-pack fields GEPA may affect during scoring: system,pf.up,pf.sql,pf.judge,pb,scoring or all")
    parser.add_argument("--judge-loop-max-iterations", type=int, default=10, help="Max UP/SQL/Judge iterations when --metric-mode judge-loop")
    parser.add_argument("--history-window-up-sql", default="all", help="Judge-loop history window for UP/SQL prompts")
    parser.add_argument("--judge-history-window", type=int, default=1, help="Judge-loop history window for judge prompts")
    parser.add_argument(
        "--judge-score-threshold",
        type=float,
        default=0.5,
        help="Judge-loop YES acceptance threshold; kept for compatibility (default: 0.5)",
    )
    parser.add_argument(
        "--judge-no-override-threshold",
        type=float,
        default=0.99,
        help="Judge-loop NO decisions above this score are treated as effective YES (default: 0.99)",
    )
    parser.add_argument("--judge-call-retries", type=int, default=3, help="Judge-loop judge retries per SQL candidate")
    parser.add_argument("--judge-max-tokens", type=int, default=4096, help="Max output tokens for judge calls")
    parser.add_argument("--max-metric-calls", type=int, default=120, help="GEPA metric-call budget")
    parser.add_argument("--parallel", action="store_true", help="Enable GEPA parallel evaluation")
    parser.add_argument("--max-workers", type=int, default=4, help="Worker count when --parallel is enabled")
    parser.add_argument("--reflection-lm", default=None, help="Raw GEPA reflection LM string")
    parser.add_argument("--reflection-model", default="glm-4.7", help="Z.AI reflection model")
    parser.add_argument("--reflection-base-url", default="https://api.z.ai/api/anthropic", help="Z.AI Anthropic-compatible base URL")
    parser.add_argument("--reflection-timeout", type=int, default=180, help="Timeout for Z.AI reflection calls")
    parser.add_argument("--reflection-temperature", type=float, default=0.7, help="Temperature for Z.AI reflection calls")
    parser.add_argument("--reflection-fallback-base-url", default="http://127.0.0.1:18081/v1", help="OpenAI-compatible base URL for local reflection fallback")
    parser.add_argument("--reflection-fallback-model", default="nemotron-cascade-2-30b-a3b", help="Model name for local reflection fallback")
    parser.add_argument("--reflection-minibatch-size", type=int, default=3, help="Examples shown to GEPA reflection per step")
    parser.add_argument("--train-limit", type=int, default=None, help="Optional cap on train cases for smoke runs")
    parser.add_argument("--val-limit", type=int, default=None, help="Optional cap on val cases for smoke runs")
    parser.add_argument("--test-limit", type=int, default=None, help="Optional cap on test cases for smoke runs")
    parser.add_argument("--run-dir", default=None, help="GEPA run directory")
    parser.add_argument("db_llm_args", nargs=argparse.REMAINDER, help="Reserved for future CLI parity with the forward runner")
    args = parser.parse_args()

    split_file = Path(args.split_file)
    split_payload = json.loads(read_text_maybe_compressed(split_file))
    split_data = split_payload["splits"]
    for split_name in (args.train_split, args.val_split, args.test_split):
        if split_name and split_name not in split_data:
            raise SystemExit(f"Unknown split: {split_name}")

    trainset = _split_cases(split_payload, args.train_split, args.train_limit)
    valset = _split_cases(split_payload, args.val_split, args.val_limit)
    testset = _split_cases(split_payload, args.test_split, args.test_limit)

    seed_path = Path(args.seed_prompt_pack)
    seed_candidate = _load_seed_candidate(seed_path)
    mutable_fields = _parse_mutable_fields(args.mutable_fields)
    run_stamp = time.strftime("%Y%m%d_%H%M%S")
    run_dir = Path(args.run_dir) if args.run_dir else (Path(args.eval_root) / f"gepa_v5_{run_stamp}")
    run_dir.mkdir(parents=True, exist_ok=True)
    seed_candidate_for_eval = _project_candidate_text(seed_candidate, seed_candidate, mutable_fields)
    seed_candidate_path = _persist_candidate_text(run_dir, seed_candidate_for_eval)

    endpoint, fallback = _resolve_endpoint_args(args)
    provider = build_provider(endpoint=endpoint, fallback=fallback)
    reflection_lm = _build_reflection_lm(
        reflection_lm=args.reflection_lm,
        reflection_model=args.reflection_model,
        reflection_base_url=args.reflection_base_url,
        reflection_timeout=int(args.reflection_timeout),
        reflection_temperature=float(args.reflection_temperature),
        reflection_verbose=True,
        reflection_fallback_base_url=args.reflection_fallback_base_url,
        reflection_fallback_model=args.reflection_fallback_model,
    )

    objective = (
        "Optimize the ChEMBL v5 prompt-pack YAML so the forward chain produces result tables that match the "
        "executable benchmark ground truth across held-out natural-language-to-SQL cases."
    )
    background = _build_background(split_file, args.train_split, args.val_split, args.test_split)
    _append_run_log(
        run_dir,
        "GEPA Run Start",
        {
            "seed_prompt_pack": str(seed_path.resolve()),
            "split_file": str(split_file.resolve()),
            "split_counts": {"train": len(trainset), "val": len(valset), "test": len(testset)},
            "metric_mode": args.metric_mode,
            "mutable_fields": sorted(mutable_fields),
            "judge_score_threshold": float(args.judge_score_threshold),
            "judge_no_override_threshold": float(args.judge_no_override_threshold),
            "judge_max_tokens": int(args.judge_max_tokens),
            "local_enable_thinking": bool(args.local_enable_thinking),
            "local_reasoning_budget_tokens": args.local_reasoning_budget_tokens,
            "max_metric_calls": int(args.max_metric_calls),
            "parallel": bool(args.parallel),
            "max_workers": int(args.max_workers),
            "endpoint": _endpoint_to_dict(endpoint),
            "fallback": [_endpoint_to_dict(item) for item in _normalize_fallbacks(fallback)],
        },
    )
    case_ordinals: dict[tuple[str, str, str], int] = {}
    case_totals: dict[str, int] = {}
    for set_split_name, set_cases in (
        (args.train_split, trainset),
        (args.val_split, valset),
        (args.test_split, testset),
    ):
        case_totals[str(set_split_name)] = len(set_cases)
        for ordinal, case in enumerate(set_cases, start=1):
            case_ordinals[_case_key(case, str(set_split_name))] = ordinal

    def evaluator(candidate_text: str, example: dict[str, Any], opt_state: Any | None = None) -> tuple[float, dict[str, Any]]:
        _ = opt_state
        try:
            candidate_for_eval = _project_candidate_text(seed_candidate, candidate_text, mutable_fields)
        except Exception as exc:
            side_info = {
                "status": "invalid_candidate",
                "score": 0.0,
                "scores": _score_objectives(None, 0.0),
                "error": str(exc),
                "split": str(example.get("split", args.val_split)),
                "corpus": example.get("corpus"),
                "case_id": example.get("id"),
            }
            _append_run_log(run_dir, "Metric Case", side_info)
            oa.log(json.dumps(side_info, ensure_ascii=False))
            return 0.0, side_info
        current_candidate_path = _persist_candidate_text(run_dir, candidate_for_eval)
        example_split = str(example.get("split", args.val_split))
        example_key = _case_key(example, example_split)
        if args.metric_mode == "judge-loop":
            score, side_info = _evaluate_case_judge_loop(
                candidate_text=candidate_for_eval,
                candidate_path=current_candidate_path,
                split_name=example_split,
                case=example,
                manifest_root=Path(args.manifest_root),
                repo_root=REPO_ROOT,
                eval_root=run_dir / "candidate_evals",
                endpoint=endpoint,
                fallback=fallback,
                max_iterations=int(args.judge_loop_max_iterations),
                history_window_up_sql=str(args.history_window_up_sql),
                judge_history_window=int(args.judge_history_window),
                judge_score_threshold=float(args.judge_score_threshold),
                judge_no_override_threshold=float(args.judge_no_override_threshold),
                judge_call_retries=int(args.judge_call_retries),
                judge_max_tokens=int(args.judge_max_tokens),
                timeout=int(args.timeout),
                temperature=float(args.temperature),
                local_enable_thinking=bool(args.local_enable_thinking),
                local_reasoning_budget_tokens=args.local_reasoning_budget_tokens,
                local_reasoning_budget_message=args.local_reasoning_budget_message,
                case_ordinal=case_ordinals.get(example_key),
                case_total=case_totals.get(example_split),
            )
        else:
            score, side_info = _evaluate_case(
                candidate_text=candidate_for_eval,
                candidate_path=current_candidate_path,
                split_name=example_split,
                case=example,
                manifest_root=Path(args.manifest_root),
                repo_root=REPO_ROOT,
                eval_root=run_dir / "candidate_evals",
                provider=provider,
                up_max_tokens=int(args.up_max_tokens),
                sql_max_tokens=int(args.sql_max_tokens),
                temperature=float(args.temperature),
            )
        _append_run_log(
            run_dir,
            "Metric Case",
            {
                "candidate_hash": side_info.get("candidate_hash"),
                "split": side_info.get("split"),
                "corpus": side_info.get("corpus"),
                "case_id": side_info.get("case_id"),
                "status": side_info.get("status"),
                "score": side_info.get("score"),
                "judge_decision": side_info.get("judge_decision"),
                "judge_score": side_info.get("judge_score"),
                "iterations": side_info.get("iterations"),
                "error": side_info.get("error"),
            },
        )
        return score, side_info

    gepa_config = GEPAConfig(
        engine=EngineConfig(
            run_dir=str(run_dir),
            max_metric_calls=int(args.max_metric_calls),
            parallel=bool(args.parallel),
            max_workers=int(args.max_workers),
            cache_evaluation=True,
            cache_evaluation_storage="disk",
            track_best_outputs=True,
            display_progress_bar=True,
        ),
        reflection=ReflectionConfig(
            reflection_lm=reflection_lm,
            reflection_minibatch_size=int(args.reflection_minibatch_size),
        ),
    )

    result = optimize_anything(
        seed_candidate=seed_candidate,
        evaluator=evaluator,
        dataset=trainset,
        valset=valset,
        objective=objective,
        background=background,
        config=gepa_config,
    )

    best_candidate = result.best_candidate
    if not isinstance(best_candidate, str):
        raise SystemExit(f"Expected best_candidate to be str, got {type(best_candidate)!r}")
    best_candidate = _project_candidate_text(seed_candidate, best_candidate, mutable_fields)

    output_path = Path(args.output_prompt_pack) if args.output_prompt_pack else (run_dir / "best_prompt_pack.yaml")
    output_path.write_text(best_candidate, encoding="utf-8")
    load_prompt_pack(output_path)

    best_candidate_path = _persist_candidate_text(run_dir, best_candidate)
    test_report = _evaluate_split(
        candidate_text=best_candidate,
        candidate_path=best_candidate_path,
        split_name=args.test_split,
        cases=testset,
        manifest_root=Path(args.manifest_root),
        repo_root=REPO_ROOT,
        eval_root=run_dir / "heldout_test",
        provider=provider,
        endpoint=endpoint,
        fallback=fallback,
        up_max_tokens=int(args.up_max_tokens),
        sql_max_tokens=int(args.sql_max_tokens),
        temperature=float(args.temperature),
        metric_mode=str(args.metric_mode),
        judge_loop_max_iterations=int(args.judge_loop_max_iterations),
        history_window_up_sql=str(args.history_window_up_sql),
        judge_history_window=int(args.judge_history_window),
        judge_score_threshold=float(args.judge_score_threshold),
        judge_no_override_threshold=float(args.judge_no_override_threshold),
        judge_call_retries=int(args.judge_call_retries),
        judge_max_tokens=int(args.judge_max_tokens),
        timeout=int(args.timeout),
        local_enable_thinking=bool(args.local_enable_thinking),
        local_reasoning_budget_tokens=args.local_reasoning_budget_tokens,
        local_reasoning_budget_message=args.local_reasoning_budget_message,
        write_report=True,
    )

    summary = {
        "run_dir": str(run_dir.resolve()),
        "best_prompt_pack": str(output_path.resolve()),
        "seed_prompt_pack": str(seed_path.resolve()),
        "seed_candidate_path": str(seed_candidate_path.resolve()),
        "best_candidate_path": str(best_candidate_path.resolve()),
        "train_split": args.train_split,
        "val_split": args.val_split,
        "test_split": args.test_split,
        "train_cases": len(trainset),
        "val_cases": len(valset),
        "test_cases": len(testset),
        "metric_mode": args.metric_mode,
        "mutable_fields": sorted(mutable_fields),
        "judge_loop_max_iterations": int(args.judge_loop_max_iterations),
        "judge_score_threshold": float(args.judge_score_threshold),
        "judge_no_override_threshold": float(args.judge_no_override_threshold),
        "judge_max_tokens": int(args.judge_max_tokens),
        "local_enable_thinking": bool(args.local_enable_thinking),
        "local_reasoning_budget_tokens": args.local_reasoning_budget_tokens,
        "max_metric_calls": int(args.max_metric_calls),
        "reflection_minibatch_size": int(args.reflection_minibatch_size),
        "test_report": test_report,
    }
    write_json(run_dir / "summary.json", summary)
    _append_run_log(run_dir, "GEPA Run Complete", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
