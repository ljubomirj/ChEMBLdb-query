from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from compressed_io import read_text_maybe_compressed

from .artifacts import V5CaseManifest, V5PromptPack


@dataclass(slots=True)
class RenderedPrompt:
    system_prompt: str
    user_prompt: str


def build_system_prompt(prompt_pack: V5PromptPack, repo_root: Path) -> str:
    parts: list[str] = [prompt_pack.system.about_block.strip()]
    if prompt_pack.system.schema_block_path:
        parts.append(read_text_maybe_compressed(repo_root / prompt_pack.system.schema_block_path).strip())
    if prompt_pack.system.hint_block_path:
        parts.append(read_text_maybe_compressed(repo_root / prompt_pack.system.hint_block_path).strip())
    if prompt_pack.system.examples_block:
        parts.append(prompt_pack.system.examples_block.strip())
    return "\n\n".join(part for part in parts if part)


def build_pf_up_prompt(
    *,
    prompt_pack: V5PromptPack,
    manifest: V5CaseManifest,
    repo_root: Path,
) -> RenderedPrompt:
    uq_text = read_text_maybe_compressed(repo_root / manifest.artifacts.uq_surface).strip()
    system_prompt = build_system_prompt(prompt_pack, repo_root)
    user_parts = [
        prompt_pack.pf.up.strip(),
        "",
        f"<CASE_ID>\n{manifest.case_id}\n</CASE_ID>",
        f"<FAMILY>\n{manifest.metadata.family}\n</FAMILY>",
        f"<REALISM_LEVEL>\n{manifest.metadata.realism_level}\n</REALISM_LEVEL>",
        f"<UQ>\n{uq_text}\n</UQ>",
    ]
    if manifest.metadata.expected_output_columns:
        user_parts.append(
            "<EXPECTED_OUTPUT_COLUMNS>\n"
            + "\n".join(manifest.metadata.expected_output_columns)
            + "\n</EXPECTED_OUTPUT_COLUMNS>"
        )
    if manifest.metadata.sort_keys:
        user_parts.append("<SORT_KEYS>\n" + "\n".join(manifest.metadata.sort_keys) + "\n</SORT_KEYS>")
    if manifest.artifacts.uq_benchmark_spec:
        spec_text = read_text_maybe_compressed(repo_root / manifest.artifacts.uq_benchmark_spec).strip()
        user_parts.append(f"<BENCHMARK_SPEC>\n{spec_text}\n</BENCHMARK_SPEC>")
    return RenderedPrompt(system_prompt=system_prompt, user_prompt="\n".join(user_parts))


def build_pf_sql_prompt(
    *,
    prompt_pack: V5PromptPack,
    manifest: V5CaseManifest,
    repo_root: Path,
    up_exec_text: str,
) -> RenderedPrompt:
    uq_text = read_text_maybe_compressed(repo_root / manifest.artifacts.uq_surface).strip()
    system_prompt = build_system_prompt(prompt_pack, repo_root)
    user_parts = [
        prompt_pack.pf.sql.strip(),
        "",
        f"<CASE_ID>\n{manifest.case_id}\n</CASE_ID>",
        f"<FAMILY>\n{manifest.metadata.family}\n</FAMILY>",
        f"<REALISM_LEVEL>\n{manifest.metadata.realism_level}\n</REALISM_LEVEL>",
        f"<UQ>\n{uq_text}\n</UQ>",
        f"<UP_EXEC>\n{up_exec_text.strip()}\n</UP_EXEC>",
    ]
    if manifest.metadata.expected_output_columns:
        user_parts.append(
            "<EXPECTED_OUTPUT_COLUMNS>\n"
            + "\n".join(manifest.metadata.expected_output_columns)
            + "\n</EXPECTED_OUTPUT_COLUMNS>"
        )
    if manifest.metadata.sort_keys:
        user_parts.append("<SORT_KEYS>\n" + "\n".join(manifest.metadata.sort_keys) + "\n</SORT_KEYS>")
    if manifest.artifacts.uq_benchmark_spec:
        spec_text = read_text_maybe_compressed(repo_root / manifest.artifacts.uq_benchmark_spec).strip()
        user_parts.append(f"<BENCHMARK_SPEC>\n{spec_text}\n</BENCHMARK_SPEC>")
    return RenderedPrompt(system_prompt=system_prompt, user_prompt="\n".join(user_parts))


def build_pf_judge_prompt(
    *,
    prompt_pack: V5PromptPack,
    manifest: V5CaseManifest,
    repo_root: Path,
    up_exec_text: str,
    sql_text: str,
    result_summary: str,
) -> RenderedPrompt:
    uq_text = read_text_maybe_compressed(repo_root / manifest.artifacts.uq_surface).strip()
    system_prompt = build_system_prompt(prompt_pack, repo_root)
    user_parts = [
        prompt_pack.pf.judge.strip(),
        "",
        f"<CASE_ID>\n{manifest.case_id}\n</CASE_ID>",
        f"<FAMILY>\n{manifest.metadata.family}\n</FAMILY>",
        f"<UQ>\n{uq_text}\n</UQ>",
        f"<UP_EXEC>\n{up_exec_text.strip()}\n</UP_EXEC>",
        f"<SQL>\n{sql_text.strip()}\n</SQL>",
        f"<RES>\n{result_summary.strip()}\n</RES>",
    ]
    return RenderedPrompt(system_prompt=system_prompt, user_prompt="\n".join(user_parts))


def build_pb_sql_prompt(
    *,
    prompt_pack: V5PromptPack,
    manifest: V5CaseManifest,
    repo_root: Path,
) -> RenderedPrompt:
    sql_path = manifest.artifacts.sql_gold or manifest.artifacts.sqlite_sql or manifest.artifacts.source_sql
    if not sql_path:
        raise ValueError(f"case {manifest.case_id} has no SQL artifact for PB_SQL")
    sql_text = read_text_maybe_compressed(repo_root / sql_path).strip()

    system_prompt = build_system_prompt(prompt_pack, repo_root)
    user_parts = [
        prompt_pack.pb.sql_to_up.strip(),
        "",
        f"<CASE_ID>\n{manifest.case_id}\n</CASE_ID>",
        f"<FAMILY>\n{manifest.metadata.family}\n</FAMILY>",
        f"<REALISM_LEVEL>\n{manifest.metadata.realism_level}\n</REALISM_LEVEL>",
        f"<SQL>\n{sql_text}\n</SQL>",
    ]
    if manifest.metadata.expected_output_columns:
        user_parts.append(
            "<EXPECTED_OUTPUT_COLUMNS>\n"
            + "\n".join(manifest.metadata.expected_output_columns)
            + "\n</EXPECTED_OUTPUT_COLUMNS>"
        )
    if manifest.metadata.sort_keys:
        user_parts.append("<SORT_KEYS>\n" + "\n".join(manifest.metadata.sort_keys) + "\n</SORT_KEYS>")
    return RenderedPrompt(system_prompt=system_prompt, user_prompt="\n".join(user_parts))


def build_pb_up_prompt(
    *,
    prompt_pack: V5PromptPack,
    manifest: V5CaseManifest,
    repo_root: Path,
    up_exec_text: str,
) -> RenderedPrompt:
    system_prompt = build_system_prompt(prompt_pack, repo_root)
    user_parts = [
        prompt_pack.pb.up_to_uq.strip(),
        "",
        f"<CASE_ID>\n{manifest.case_id}\n</CASE_ID>",
        f"<FAMILY>\n{manifest.metadata.family}\n</FAMILY>",
        f"<REALISM_LEVEL>\n{manifest.metadata.realism_level}\n</REALISM_LEVEL>",
        f"<UP_EXEC>\n{up_exec_text.strip()}\n</UP_EXEC>",
    ]
    if manifest.artifacts.uq_benchmark_spec:
        spec_text = read_text_maybe_compressed(repo_root / manifest.artifacts.uq_benchmark_spec).strip()
        user_parts.append(f"<BENCHMARK_SPEC>\n{spec_text}\n</BENCHMARK_SPEC>")
    return RenderedPrompt(system_prompt=system_prompt, user_prompt="\n".join(user_parts))
