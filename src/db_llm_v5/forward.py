from __future__ import annotations

from pathlib import Path
from typing import Any

from .artifacts import V5CaseManifest, V5PromptPack
from .evaluation import score_result_against_gold
from .execution import execute_sql_to_csv, summarize_result_csv
from .prompting import build_pf_judge_prompt, build_pf_sql_prompt, build_pf_up_prompt
from .provider import run_json_call_with_retry

from db_llm_runtime_v5 import DspyProvider


def build_call_payload(provider: DspyProvider, result) -> dict[str, Any]:
    provenance = {
        "provider": provider.provider,
        "model_id": provider.model,
        "responses_model_id": provider.responses_model,
        "dspy_model_id": provider.dspy_model,
        "base_url": provider.base_url,
    }
    return {
        "provider": provider.provider,
        "model": provider.model,
        "model_id": provider.model,
        "responses_model_id": provider.responses_model,
        "dspy_model_id": provider.dspy_model,
        "base_url": provider.base_url,
        "provenance": provenance,
        "raw_text": result.text,
        "parsed_json": result.parsed_json,
    }


def run_pf_up(*, prompt_pack: V5PromptPack, manifest: V5CaseManifest, repo_root: Path, provider: DspyProvider, max_tokens: int, temperature: float) -> dict[str, Any]:
    rendered = build_pf_up_prompt(prompt_pack=prompt_pack, manifest=manifest, repo_root=repo_root)
    result = run_json_call_with_retry(
        provider=provider,
        system_prompt=rendered.system_prompt,
        user_prompt=rendered.user_prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        expected_key="up",
        max_attempts=3,
    )
    return {"execution": build_call_payload(provider, result)}


def run_pf_sql(*, prompt_pack: V5PromptPack, manifest: V5CaseManifest, repo_root: Path, provider: DspyProvider, up_exec_text: str, max_tokens: int, temperature: float) -> dict[str, Any]:
    rendered = build_pf_sql_prompt(
        prompt_pack=prompt_pack,
        manifest=manifest,
        repo_root=repo_root,
        up_exec_text=up_exec_text,
    )
    result = run_json_call_with_retry(
        provider=provider,
        system_prompt=rendered.system_prompt,
        user_prompt=rendered.user_prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        expected_key="sql",
        max_attempts=3,
    )
    return {"execution": build_call_payload(provider, result)}


def run_res(*, manifest: V5CaseManifest, repo_root: Path, sql_text: str, result_path: Path) -> dict[str, Any]:
    execution = execute_sql_to_csv(
        db_path=repo_root / manifest.db_path,
        sql_text=sql_text,
        out_path=result_path,
    )
    payload: dict[str, Any] = {
        "result_path": str(result_path.resolve()),
        "result": {
            "success": execution.success,
            "result_path": execution.result_path,
            "row_count": execution.row_count,
            "column_names": execution.column_names,
            "error": execution.error,
        }
    }
    if execution.success and manifest.artifacts.res_gold:
        payload["deterministic_score"] = score_result_against_gold(
            manifest=manifest,
            repo_root=repo_root,
            actual_path=result_path,
        )
    return payload


def run_pf_judge(*, prompt_pack: V5PromptPack, manifest: V5CaseManifest, repo_root: Path, provider: DspyProvider, up_exec_text: str, sql_text: str, result_path: Path, max_tokens: int, temperature: float) -> dict[str, Any]:
    rendered = build_pf_judge_prompt(
        prompt_pack=prompt_pack,
        manifest=manifest,
        repo_root=repo_root,
        up_exec_text=up_exec_text,
        sql_text=sql_text,
        result_summary=summarize_result_csv(result_path),
    )
    result = run_json_call_with_retry(
        provider=provider,
        system_prompt=rendered.system_prompt,
        user_prompt=rendered.user_prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        expected_key=None,
        max_attempts=2,
    )
    return {"execution": build_call_payload(provider, result)}
