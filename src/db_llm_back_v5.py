#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from compressed_io import read_text_maybe_compressed
from db_llm_v5.io import load_case_manifest, load_prompt_pack
from db_llm_v5.prompting import build_pb_sql_prompt, build_pb_up_prompt
from db_llm_v5.provider import EndpointConfig, build_provider, resolve_profile, run_json_call_with_retry, write_json
from db_llm_v5.workspace import default_run_root, persist_generated_step


REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Backward v5 ChEMBL curation scaffold.")
    parser.add_argument(
        "--prompt-pack",
        default=str(REPO_ROOT / "experiments" / "prompt_pack_v5.0.yaml"),
        help="Path to the v5 prompt-pack YAML",
    )
    parser.add_argument(
        "--case-manifest",
        required=True,
        help="Path to the v5 case manifest",
    )
    parser.add_argument(
        "--step",
        choices=["sql_to_up", "up_to_uq"],
        default="sql_to_up",
        help="Backward step to run",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute the selected backward prompt via an LLM provider",
    )
    parser.add_argument(
        "--multi-endpoint-profile",
        default=None,
        help="Convenience endpoint profile, e.g. zai-glm-5-turbo or zai-glm-4.7-anthropic",
    )
    parser.add_argument("--provider", default=None, help="Explicit provider override")
    parser.add_argument("--provider-base-url", default=None, help="Explicit provider base URL override")
    parser.add_argument("--model", default=None, help="Explicit model override")
    parser.add_argument("--temperature", type=float, default=0.2, help="Provider temperature")
    parser.add_argument("--timeout", type=int, default=1200, help="Provider timeout in seconds")
    parser.add_argument("--quota-fallback-provider", default=None, help="Fallback provider when quota is hit")
    parser.add_argument("--quota-fallback-base-url", default=None, help="Fallback provider base URL")
    parser.add_argument("--quota-fallback-model", default=None, help="Fallback provider model")
    parser.add_argument("--max-tokens", type=int, default=1200, help="Max output tokens")
    parser.add_argument("--output-path", default=None, help="Optional JSON output path for executed backward step")
    parser.add_argument("--up-exec-path", default=None, help="Optional UP artifact input for up_to_uq")
    parser.add_argument("--run-root", default=None, help="Optional v5 run workspace root")
    parser.add_argument(
        "--persist-generated-artifacts",
        action="store_true",
        help="Persist generated artifacts and a generated manifest into the run workspace",
    )
    parser.add_argument(
        "--print-summary",
        action="store_true",
        help="Print loaded prompt-pack and case summary as JSON",
    )
    args = parser.parse_args()

    prompt_pack = load_prompt_pack(args.prompt_pack)
    manifest = load_case_manifest(args.case_manifest)
    payload: dict[str, object] = {
        "mode": "backward",
        "prompt_pack_path": str(Path(args.prompt_pack).resolve()),
        "case_manifest_path": str(Path(args.case_manifest).resolve()),
        "prompt_pack_version": prompt_pack.version,
        "case_id": manifest.case_id,
        "family": manifest.metadata.family,
        "selected_step": args.step,
        "backward_steps": [
            "sql_to_up",
            "up_to_uq",
            "res_sql_to_intent",
        ],
    }

    if args.execute:
        endpoint, fallback = _resolve_endpoint_args(args)
        provider = build_provider(endpoint=endpoint, fallback=fallback)
        if args.step == "sql_to_up":
            rendered = build_pb_sql_prompt(prompt_pack=prompt_pack, manifest=manifest, repo_root=REPO_ROOT)
        else:
            up_exec_path = _resolve_up_exec_path(args.up_exec_path, manifest)
            rendered = build_pb_up_prompt(
                prompt_pack=prompt_pack,
                manifest=manifest,
                repo_root=REPO_ROOT,
                up_exec_text=read_text_maybe_compressed(up_exec_path).strip(),
            )
            payload["up_exec_path"] = str(up_exec_path.resolve())

        result = run_json_call_with_retry(
            provider=provider,
            system_prompt=rendered.system_prompt,
            user_prompt=rendered.user_prompt,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            expected_key="up_exec" if args.step == "sql_to_up" else "uq_surface",
            max_attempts=3,
        )
        payload["execution"] = {
            "provider": provider.provider,
            "model": provider.model,
            "base_url": provider.base_url,
            "raw_text": result.text,
            "parsed_json": result.parsed_json,
        }
        if args.output_path:
            write_json(args.output_path, payload)
        if args.persist_generated_artifacts:
            run_root = Path(args.run_root) if args.run_root else default_run_root(REPO_ROOT, prefix="backward")
            written_paths = persist_generated_step(
                repo_root=REPO_ROOT,
                run_root=run_root,
                manifest=manifest,
                source_manifest_path=Path(args.case_manifest),
                prompt_pack_path=Path(args.prompt_pack),
                step=f"pb_{args.step}",
                payload=payload,
            )
            payload["written_paths"] = written_paths
            if args.output_path:
                write_json(args.output_path, payload)

    if args.print_summary:
        print(json.dumps(payload, indent=2))
    else:
        print(json.dumps(payload))


def _resolve_endpoint_args(args: argparse.Namespace) -> tuple[EndpointConfig, EndpointConfig | None]:
    endpoint = None
    fallback = None
    if args.multi_endpoint_profile:
        endpoint, fallback = resolve_profile(args.multi_endpoint_profile)
    if endpoint is None:
        if not args.provider or not args.model:
            raise ValueError("Either --multi-endpoint-profile or both --provider and --model are required for --execute")
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
    raise ValueError("up_to_uq requires --up-exec-path or a manifest with artifacts.up_exec")


if __name__ == "__main__":
    main()
