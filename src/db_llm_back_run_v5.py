#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from compressed_io import read_text_maybe_compressed
from db_llm_v5.backward import run_pb_sql, run_pb_up
from db_llm_v5.io import load_case_manifest, load_prompt_pack
from db_llm_v5.provider import EndpointConfig, build_provider, resolve_profile, write_json
from db_llm_v5.workspace import default_run_root, persist_generated_step

REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full v5 backward chain for one case.")
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
    parser.add_argument("--max-tokens", type=int, default=1200)
    parser.add_argument("--run-root", default=None)
    parser.add_argument("--output-path", default=None)
    parser.add_argument("--print-summary", action="store_true")
    args = parser.parse_args()

    prompt_pack = load_prompt_pack(args.prompt_pack)
    manifest = load_case_manifest(args.case_manifest)
    endpoint, fallback = _resolve_endpoint_args(args)
    provider = build_provider(endpoint=endpoint, fallback=fallback)
    run_root = Path(args.run_root) if args.run_root else default_run_root(REPO_ROOT, prefix="backward_chain")

    summary: dict[str, object] = {
        "mode": "backward_chain",
        "prompt_pack_path": str(Path(args.prompt_pack).resolve()),
        "prompt_pack_version": prompt_pack.version,
        "case_manifest_path": str(Path(args.case_manifest).resolve()),
        "case_id": manifest.case_id,
        "family": manifest.metadata.family,
        "realism_level": manifest.metadata.realism_level,
        "provider": {"provider": provider.provider, "model": provider.model, "base_url": provider.base_url},
        "run_root": str(run_root.resolve()),
    }

    pb_sql = run_pb_sql(
        prompt_pack=prompt_pack,
        manifest=manifest,
        repo_root=REPO_ROOT,
        provider=provider,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
    )
    pb_sql_payload = {**summary, "selected_step": "sql_to_up", **pb_sql}
    pb_sql_written = persist_generated_step(
        repo_root=REPO_ROOT,
        run_root=run_root,
        manifest=manifest,
        source_manifest_path=Path(args.case_manifest),
        prompt_pack_path=Path(args.prompt_pack),
        step="pb_sql_to_up",
        payload=pb_sql_payload,
    )
    up_exec_path = REPO_ROOT / pb_sql_written["up_exec"]
    up_exec_text = read_text_maybe_compressed(up_exec_path).strip()

    pb_up = run_pb_up(
        prompt_pack=prompt_pack,
        manifest=manifest,
        repo_root=REPO_ROOT,
        provider=provider,
        up_exec_text=up_exec_text,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
    )
    pb_up_payload = {**summary, "selected_step": "up_to_uq", "up_exec_path": str(up_exec_path.resolve()), **pb_up}
    pb_up_written = persist_generated_step(
        repo_root=REPO_ROOT,
        run_root=run_root,
        manifest=manifest,
        source_manifest_path=Path(args.case_manifest),
        prompt_pack_path=Path(args.prompt_pack),
        step="pb_up_to_uq",
        payload=pb_up_payload,
    )

    final_summary = {
        **summary,
        "written_paths": {
            "pb_sql_to_up": pb_sql_written,
            "pb_up_to_uq": pb_up_written,
        },
        "reconstructed_up_exec": up_exec_text,
        "reconstructed_uq_surface": pb_up.get("execution", {}).get("parsed_json", {}).get("uq_surface") if isinstance(pb_up.get("execution"), dict) else None,
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
