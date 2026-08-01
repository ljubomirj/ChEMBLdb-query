#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from compressed_io import read_text_maybe_compressed
from db_llm_v5.execution import execute_sql_to_csv, summarize_result_csv
from db_llm_v5.evaluation import score_result_against_gold
from db_llm_v5.io import load_case_manifest, load_prompt_pack
from db_llm_v5.prompting import build_pf_judge_prompt, build_pf_sql_prompt, build_pf_up_prompt
from db_llm_v5.provider import EndpointConfig, build_provider, resolve_profile, run_json_call_with_retry, write_json
from db_llm_v5.workspace import default_run_root, persist_generated_step


REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Forward v5 ChEMBL query scaffold.")
    parser.add_argument(
        "--prompt-pack",
        default=str(REPO_ROOT / "experiments" / "prompt_pack_v5.0.yaml"),
        help="Path to the v5 prompt-pack YAML",
    )
    parser.add_argument("--case-manifest", help="Path to a v5 case manifest")
    parser.add_argument("--step", choices=["up", "sql", "res", "judge"], default="up", help="Forward step to run")
    parser.add_argument("--execute", action="store_true", help="Execute the selected step")
    parser.add_argument("--multi-endpoint-profile", default=None, help="Convenience endpoint profile")
    parser.add_argument("--provider", default=None, help="Explicit provider override")
    parser.add_argument("--provider-base-url", default=None, help="Explicit provider base URL override")
    parser.add_argument("--model", default=None, help="Explicit model override")
    parser.add_argument("--temperature", type=float, default=0.2, help="Provider temperature")
    parser.add_argument("--timeout", type=int, default=1200, help="Provider timeout in seconds")
    parser.add_argument("--quota-fallback-provider", default=None, help="Fallback provider when quota is hit")
    parser.add_argument("--quota-fallback-base-url", default=None, help="Fallback provider base URL")
    parser.add_argument("--quota-fallback-model", default=None, help="Fallback provider model")
    parser.add_argument("--up-max-tokens", type=int, default=1200, help="Max output tokens for PF_UP")
    parser.add_argument("--sql-max-tokens", type=int, default=4000, help="Max output tokens for PF_SQL")
    parser.add_argument("--judge-max-tokens", type=int, default=1200, help="Max output tokens for PF_J")
    parser.add_argument("--output-path", default=None, help="Optional JSON output path for executed step")
    parser.add_argument("--up-exec-path", default=None, help="Optional UP artifact input for PF_SQL or PF_J")
    parser.add_argument("--sql-path", default=None, help="Optional SQL artifact input for RES or PF_J")
    parser.add_argument("--result-path", default=None, help="Optional result CSV input for PF_J")
    parser.add_argument("--run-root", default=None, help="Optional v5 run workspace root")
    parser.add_argument(
        "--persist-generated-artifacts",
        action="store_true",
        help="Persist generated artifacts and a generated manifest into the run workspace",
    )
    parser.add_argument("--print-summary", action="store_true", help="Print JSON summary")
    args = parser.parse_args()

    prompt_pack = load_prompt_pack(args.prompt_pack)
    manifest = load_case_manifest(args.case_manifest) if args.case_manifest else None
    payload: dict[str, object] = {
        "mode": "forward",
        "prompt_pack_path": str(Path(args.prompt_pack).resolve()),
        "prompt_pack_version": prompt_pack.version,
        "selected_step": args.step,
        "pf_sections": ["up", "sql", "judge"],
        "pb_sections_present": ["sql_to_up", "up_to_uq", "res_sql_to_intent"],
    }
    if manifest is not None:
        payload.update(
            {
                "case_manifest_path": str(Path(args.case_manifest).resolve()),
                "case_id": manifest.case_id,
                "corpus": manifest.corpus,
                "split": manifest.split,
                "family": manifest.metadata.family,
                "realism_level": manifest.metadata.realism_level,
            }
        )

    should_run = args.execute or args.step == "res"
    if should_run:
        if manifest is None:
            raise ValueError("selected step requires --case-manifest")
        if args.step in {"up", "sql", "judge"}:
            endpoint, fallback = _resolve_endpoint_args(args)
            provider = build_provider(endpoint=endpoint, fallback=fallback)
        if args.step == "up":
            rendered = build_pf_up_prompt(prompt_pack=prompt_pack, manifest=manifest, repo_root=REPO_ROOT)
            result = run_json_call_with_retry(
                provider=provider,
                system_prompt=rendered.system_prompt,
                user_prompt=rendered.user_prompt,
                max_tokens=args.up_max_tokens,
                temperature=args.temperature,
                expected_key="up",
                max_attempts=3,
            )
            payload["execution"] = _call_payload(provider, result)
            _persist_if_requested(args, manifest, payload, step_name="pf_up")
        elif args.step == "sql":
            up_exec_path = _resolve_up_exec_path(args.up_exec_path, manifest)
            rendered = build_pf_sql_prompt(
                prompt_pack=prompt_pack,
                manifest=manifest,
                repo_root=REPO_ROOT,
                up_exec_text=read_text_maybe_compressed(up_exec_path).strip(),
            )
            result = run_json_call_with_retry(
                provider=provider,
                system_prompt=rendered.system_prompt,
                user_prompt=rendered.user_prompt,
                max_tokens=args.sql_max_tokens,
                temperature=args.temperature,
                expected_key="sql",
                max_attempts=3,
            )
            payload["up_exec_path"] = str(up_exec_path.resolve())
            payload["execution"] = _call_payload(provider, result)
            _persist_if_requested(args, manifest, payload, step_name="pf_sql")
        elif args.step == "res":
            sql_path = _resolve_sql_path(args.sql_path, manifest)
            sql_text = read_text_maybe_compressed(sql_path).strip()
            run_root = Path(args.run_root) if args.run_root else default_run_root(REPO_ROOT, prefix="forward")
            result_csv_path = Path(args.result_path) if args.result_path else run_root / manifest.case_id / "result.generated.csv"
            execution = execute_sql_to_csv(
                db_path=REPO_ROOT / manifest.db_path,
                sql_text=sql_text,
                out_path=result_csv_path,
            )
            payload["sql_path"] = str(sql_path.resolve())
            payload["result_path"] = str(result_csv_path.resolve())
            payload["result"] = {
                "success": execution.success,
                "result_path": execution.result_path,
                "row_count": execution.row_count,
                "column_names": execution.column_names,
                "error": execution.error,
            }
            if execution.success and manifest.artifacts.res_gold:
                payload["deterministic_score"] = score_result_against_gold(
                    manifest=manifest,
                    repo_root=REPO_ROOT,
                    actual_path=result_csv_path,
                )
            _persist_or_write_nonllm(args, manifest, payload, step_name="pf_res")
        elif args.step == "judge":
            up_exec_path = _resolve_up_exec_path(args.up_exec_path, manifest)
            sql_path = _resolve_sql_path(args.sql_path, manifest)
            result_path = _resolve_result_path(args.result_path)
            rendered = build_pf_judge_prompt(
                prompt_pack=prompt_pack,
                manifest=manifest,
                repo_root=REPO_ROOT,
                up_exec_text=read_text_maybe_compressed(up_exec_path).strip(),
                sql_text=read_text_maybe_compressed(sql_path).strip(),
                result_summary=summarize_result_csv(result_path),
            )
            result = run_json_call_with_retry(
                provider=provider,
                system_prompt=rendered.system_prompt,
                user_prompt=rendered.user_prompt,
                max_tokens=args.judge_max_tokens,
                temperature=args.temperature,
                expected_key=None,
                max_attempts=2,
            )
            payload["up_exec_path"] = str(up_exec_path.resolve())
            payload["sql_path"] = str(sql_path.resolve())
            payload["result_path"] = str(result_path.resolve())
            payload["execution"] = _call_payload(provider, result)
            _persist_if_requested(args, manifest, payload, step_name="pf_judge")

    if args.print_summary:
        print(json.dumps(payload, indent=2))
    else:
        print(json.dumps(payload))


def _call_payload(provider, result) -> dict[str, object]:
    return {
        "provider": provider.provider,
        "model": provider.model,
        "base_url": provider.base_url,
        "raw_text": result.text,
        "parsed_json": result.parsed_json,
    }


def _persist_or_write_nonllm(args: argparse.Namespace, manifest, payload: dict[str, object], *, step_name: str) -> None:
    if not args.persist_generated_artifacts:
        if args.output_path:
            write_json(args.output_path, payload)
        return
    run_root = Path(args.run_root) if args.run_root else default_run_root(REPO_ROOT, prefix="forward")
    written_paths = persist_generated_step(
        repo_root=REPO_ROOT,
        run_root=run_root,
        manifest=manifest,
        source_manifest_path=Path(args.case_manifest),
        prompt_pack_path=Path(args.prompt_pack),
        step=step_name,
        payload=payload,
    )
    if "result_path" in payload:
        written_paths["result_path"] = str(Path(str(payload["result_path"])).resolve().relative_to(REPO_ROOT.resolve()))
    payload["written_paths"] = written_paths
    if args.output_path:
        write_json(args.output_path, payload)


def _persist_if_requested(args: argparse.Namespace, manifest, payload: dict[str, object], *, step_name: str) -> None:
    if not args.persist_generated_artifacts:
        if args.output_path:
            write_json(args.output_path, payload)
        return
    run_root = Path(args.run_root) if args.run_root else default_run_root(REPO_ROOT, prefix="forward")
    written_paths = persist_generated_step(
        repo_root=REPO_ROOT,
        run_root=run_root,
        manifest=manifest,
        source_manifest_path=Path(args.case_manifest),
        prompt_pack_path=Path(args.prompt_pack),
        step=step_name,
        payload=payload,
    )
    payload["written_paths"] = written_paths
    if args.output_path:
        write_json(args.output_path, payload)


def _resolve_endpoint_args(args: argparse.Namespace) -> tuple[EndpointConfig, EndpointConfig | None]:
    endpoint = None
    fallback = None
    if args.multi_endpoint_profile:
        endpoint, fallback = resolve_profile(args.multi_endpoint_profile)
    if endpoint is None:
        if not args.provider or not args.model:
            raise ValueError("Either --multi-endpoint-profile or both --provider and --model are required for execute")
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


def _resolve_up_exec_path(explicit_path: str | None, manifest) -> Path:
    if explicit_path:
        return Path(explicit_path).resolve()
    if manifest.artifacts.up_exec:
        return (REPO_ROOT / manifest.artifacts.up_exec).resolve()
    raise ValueError("step requires --up-exec-path or a manifest with artifacts.up_exec")


def _resolve_sql_path(explicit_path: str | None, manifest) -> Path:
    if explicit_path:
        return Path(explicit_path).resolve()
    if manifest.artifacts.sql_gold:
        return (REPO_ROOT / manifest.artifacts.sql_gold).resolve()
    if manifest.artifacts.sqlite_sql:
        return (REPO_ROOT / manifest.artifacts.sqlite_sql).resolve()
    raise ValueError("step requires --sql-path or a manifest with artifacts.sql_gold/sqlite_sql")


def _resolve_result_path(explicit_path: str | None) -> Path:
    if not explicit_path:
        raise ValueError("judge step requires --result-path")
    return Path(explicit_path).resolve()


if __name__ == "__main__":
    main()
