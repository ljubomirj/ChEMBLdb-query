from __future__ import annotations

from pathlib import Path
from typing import Any

from .artifacts import V5CaseManifest, V5PromptPack
from .prompting import build_pb_sql_prompt, build_pb_up_prompt
from .provider import run_json_call_with_retry

from db_llm_runtime_v5 import DspyProvider


def build_call_payload(provider: DspyProvider, result) -> dict[str, Any]:
    return {
        "provider": provider.provider,
        "model": provider.model,
        "base_url": provider.base_url,
        "raw_text": result.text,
        "parsed_json": result.parsed_json,
    }


def run_pb_sql(*, prompt_pack: V5PromptPack, manifest: V5CaseManifest, repo_root: Path, provider: DspyProvider, max_tokens: int, temperature: float) -> dict[str, Any]:
    rendered = build_pb_sql_prompt(prompt_pack=prompt_pack, manifest=manifest, repo_root=repo_root)
    result = run_json_call_with_retry(
        provider=provider,
        system_prompt=rendered.system_prompt,
        user_prompt=rendered.user_prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        expected_key="up_exec",
        max_attempts=3,
    )
    return {"execution": build_call_payload(provider, result)}


def run_pb_up(*, prompt_pack: V5PromptPack, manifest: V5CaseManifest, repo_root: Path, provider: DspyProvider, up_exec_text: str, max_tokens: int, temperature: float) -> dict[str, Any]:
    rendered = build_pb_up_prompt(
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
        expected_key="uq_surface",
        max_attempts=3,
    )
    return {"execution": build_call_payload(provider, result)}
