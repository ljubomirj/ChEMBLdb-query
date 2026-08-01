#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from compressed_io import read_text_maybe_compressed
from db_llm_v5.forward import run_pf_judge, run_pf_sql, run_pf_up, run_res
from db_llm_v5.io import load_case_manifest, load_prompt_pack
from db_llm_v5.provider import EndpointConfig, build_provider, resolve_profile, write_json
from db_llm_v5.workspace import default_run_root, persist_generated_step

REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full v5 forward chain for one case.")
    parser.add_argument("--prompt-pack", default=str(REPO_ROOT / "experiments" / "prompt_pack_v5.0.yaml"))
    parser.add_argument("--case-manifest", required=True)
    parser.add_argument("--multi-endpoint-profile", default=None)
    parser.add_argument("--provider", default=None)
    parser.add_argument("--provider-base-url", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--timeout", type=int, default=1200)
    parser.add_argument("--quota-fallback-provider", default=None)
    parser.add_argument("--quota-fallback-base-url", default=None)
    parser.add_argument("--quota-fallback-model", default=None)
    parser.add_argument("--up-max-tokens", type=int, default=1200)
    parser.add_argument("--sql-max-tokens", type=int, default=4000)
    parser.add_argument("--judge-max-tokens", type=int, default=1200)
    parser.add_argument("--run-root", default=None)
    parser.add_argument("--output-path", default=None)
    parser.add_argument("--print-summary", action="store_true")
    args = parser.parse_args()

    prompt_pack = load_prompt_pack(args.prompt_pack)
    manifest = load_case_manifest(args.case_manifest)
    endpoint, fallback = _resolve_endpoint_args(args)
    provider = build_provider(endpoint=endpoint, fallback=fallback)
    run_root = Path(args.run_root) if args.run_root else default_run_root(REPO_ROOT, prefix="chain")

    summary: dict[str, object] = {
        "mode": "forward_chain",
        "prompt_pack_path": str(Path(args.prompt_pack).resolve()),
        "prompt_pack_version": prompt_pack.version,
        "case_manifest_path": str(Path(args.case_manifest).resolve()),
        "case_id": manifest.case_id,
        "family": manifest.metadata.family,
        "realism_level": manifest.metadata.realism_level,
        "provider": {"provider": provider.provider, "model": provider.model, "base_url": provider.base_url},
        "run_root": str(run_root.resolve()),
    }

    pf_up = run_pf_up(
        prompt_pack=prompt_pack,
        manifest=manifest,
        repo_root=REPO_ROOT,
        provider=provider,
        max_tokens=args.up_max_tokens,
        temperature=args.temperature,
    )
    pf_up_payload = {**summary, "selected_step": "up", **pf_up}
    pf_up_written = persist_generated_step(
        repo_root=REPO_ROOT,
        run_root=run_root,
        manifest=manifest,
        source_manifest_path=Path(args.case_manifest),
        prompt_pack_path=Path(args.prompt_pack),
        step="pf_up",
        payload=pf_up_payload,
    )
    up_exec_path = REPO_ROOT / pf_up_written["up_exec"]
    up_exec_text = read_text_maybe_compressed(up_exec_path).strip()

    pf_sql = run_pf_sql(
        prompt_pack=prompt_pack,
        manifest=manifest,
        repo_root=REPO_ROOT,
        provider=provider,
        up_exec_text=up_exec_text,
        max_tokens=args.sql_max_tokens,
        temperature=args.temperature,
    )
    pf_sql_payload = {**summary, "selected_step": "sql", "up_exec_path": str(up_exec_path.resolve()), **pf_sql}
    pf_sql_written = persist_generated_step(
        repo_root=REPO_ROOT,
        run_root=run_root,
        manifest=manifest,
        source_manifest_path=Path(args.case_manifest),
        prompt_pack_path=Path(args.prompt_pack),
        step="pf_sql",
        payload=pf_sql_payload,
    )
    sql_path = REPO_ROOT / pf_sql_written["sql"]
    sql_text = read_text_maybe_compressed(sql_path).strip()

    result_path = run_root / manifest.case_id / "result.generated.csv"
    pf_res = run_res(
        manifest=manifest,
        repo_root=REPO_ROOT,
        sql_text=sql_text,
        result_path=result_path,
    )
    pf_res_payload = {
        **summary,
        "selected_step": "res",
        "up_exec_path": str(up_exec_path.resolve()),
        "sql_path": str(sql_path.resolve()),
        **pf_res,
    }
    pf_res_written = persist_generated_step(
        repo_root=REPO_ROOT,
        run_root=run_root,
        manifest=manifest,
        source_manifest_path=Path(args.case_manifest),
        prompt_pack_path=Path(args.prompt_pack),
        step="pf_res",
        payload=pf_res_payload,
    )
    pf_res_written["result_path"] = str(result_path.resolve().relative_to(REPO_ROOT.resolve()))
    pf_res_payload["written_paths"] = pf_res_written
    res_output_path = run_root / manifest.case_id / "pf_res.output.json"
    write_json(res_output_path, pf_res_payload)

    judge_payload = None
    pf_judge_written = None
    if pf_res_payload["result"]["success"]:
        pf_judge = run_pf_judge(
            prompt_pack=prompt_pack,
            manifest=manifest,
            repo_root=REPO_ROOT,
            provider=provider,
            up_exec_text=up_exec_text,
            sql_text=sql_text,
            result_path=result_path,
            max_tokens=args.judge_max_tokens,
            temperature=args.temperature,
        )
        judge_payload = {
            **summary,
            "selected_step": "judge",
            "up_exec_path": str(up_exec_path.resolve()),
            "sql_path": str(sql_path.resolve()),
            "result_path": str(result_path.resolve()),
            **pf_judge,
        }
        pf_judge_written = persist_generated_step(
            repo_root=REPO_ROOT,
            run_root=run_root,
            manifest=manifest,
            source_manifest_path=Path(args.case_manifest),
            prompt_pack_path=Path(args.prompt_pack),
            step="pf_judge",
            payload=judge_payload,
        )
        judge_payload["written_paths"] = pf_judge_written
        judge_output_path = run_root / manifest.case_id / "pf_judge.output.json"
        write_json(judge_output_path, judge_payload)
    final_summary = {
        **summary,
        "written_paths": {
            "pf_up": pf_up_written,
            "pf_sql": pf_sql_written,
            "pf_res": pf_res_written,
            "pf_judge": pf_judge_written,
            "result_csv": str(result_path.resolve()) if result_path.exists() else None,
        },
        "res_result": pf_res_payload.get("result"),
        "deterministic_score": pf_res_payload.get("deterministic_score"),
        "judge_execution": judge_payload.get("execution") if judge_payload else None,
    }
    if args.output_path:
        write_json(args.output_path, final_summary)
    if args.print_summary:
        print(json.dumps(final_summary, indent=2))
    else:
        print(json.dumps(final_summary))


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


if __name__ == "__main__":
    main()
