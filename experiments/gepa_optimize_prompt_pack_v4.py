#!/usr/bin/env python3
"""Run GEPA optimize_anything on the v4 prompt-pack artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import logging
from pathlib import Path
from typing import Any

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

from text2sql.anthropic_direct import AnthropicProvider
from openai import OpenAI

from experiments.evaluate_prompt_pack_v4 import (
    DEFAULT_EVAL_ROOT,
    DEFAULT_SPLIT_PATH,
    DEFAULT_V4_SCRIPT,
    _case_ref_key,
    _load_case_catalog,
    _load_split_file,
    _parse_log_snippets,
    _run_live_case,
    _score_case,
)

LOGGER = logging.getLogger(__name__)


def _looks_like_zai_quota_error(exc: Exception) -> bool:
    text = str(exc)
    return ("1308" in text) or ("Usage limit reached" in text)


def _load_seed_candidate(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _persist_candidate_text(run_dir: Path, candidate_text: str) -> Path:
    candidate_hash = hashlib.sha256(candidate_text.encode("utf-8")).hexdigest()[:16]
    out_dir = run_dir / "candidate_cache"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"candidate_{candidate_hash}.yaml"
    if not out_path.exists():
        out_path.write_text(candidate_text, encoding="utf-8")
    return out_path


def _build_background(split_file: Path, train_split: str, val_split: str) -> str:
    return "\n".join(
        [
            "You are optimizing a ChEMBL Text-to-SQL prompt pack.",
            "The candidate artifact is the full YAML prompt pack used by src/db_llm_query_v4.py.",
            "Optimize for real result-set agreement against executable benchmark cases, not for self-judge agreement.",
            f"Split file: {split_file}",
            f"Train split: {train_split}",
            f"Validation split: {val_split}",
            "Prefer changes that improve column fidelity, exact filter semantics, and row-set correctness.",
            "Do not bloat the artifact with repetitive text or model-specific clutter unless it clearly improves benchmark performance.",
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
        base_url=(reflection_fallback_base_url or "http://192.168.1.251:8081/v1"),
        api_key="EMPTY",
    )
    fallback_active = False

    def _fallback_reflection(prompt: str | list[dict[str, Any]]) -> str:
        if isinstance(prompt, str):
            input_payload: Any = prompt
        else:
            input_payload = prompt
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
            if not _looks_like_zai_quota_error(exc):
                raise
            fallback_active = True
            LOGGER.warning(
                "GEPA reflection hit Z.AI quota; switching reflection LM to local fallback %s at %s",
                reflection_fallback_model,
                reflection_fallback_base_url or "http://192.168.1.251:8081/v1",
            )
            return _fallback_reflection(prompt)
        if text is None:
            raise RuntimeError("Z.AI reflection LM returned no text.")
        return text

    return _reflection


def main() -> None:
    parser = argparse.ArgumentParser(description="Optimize the v4 prompt-pack YAML with GEPA optimize_anything.")
    parser.add_argument("--seed-prompt-pack", default=str(REPO_ROOT / "experiments" / "prompt_pack_v4.0.yaml"), help="Seed prompt-pack YAML")
    parser.add_argument("--output-prompt-pack", default=None, help="Where to write the best optimized prompt-pack YAML")
    parser.add_argument("--split-file", default=str(DEFAULT_SPLIT_PATH), help="Case split JSON")
    parser.add_argument("--train-split", default="train", help="Train split name")
    parser.add_argument("--val-split", default="val", help="Validation split name")
    parser.add_argument("--test-split", default="test", help="Optional post-run evaluation split name")
    parser.add_argument("--db-llm-script", default=str(DEFAULT_V4_SCRIPT), help="Path to db_llm_query_v4.py")
    parser.add_argument("--run-dir", default=None, help="GEPA run directory")
    parser.add_argument("--reflection-lm", default=None, help="Raw GEPA reflection LM string. If omitted, use the Z.AI Anthropic-compatible callable below.")
    parser.add_argument("--reflection-model", default="glm-4.7", help="Z.AI reflection model (default: glm-4.7)")
    parser.add_argument("--reflection-base-url", default="https://api.z.ai/api/anthropic", help="Z.AI Anthropic-compatible base URL")
    parser.add_argument("--reflection-timeout", type=int, default=180, help="Timeout for Z.AI reflection calls")
    parser.add_argument("--reflection-temperature", type=float, default=0.7, help="Temperature for Z.AI reflection calls")
    parser.add_argument("--reflection-fallback-base-url", default="http://192.168.1.251:8081/v1", help="OpenAI-compatible base URL for local reflection fallback")
    parser.add_argument("--reflection-fallback-model", default="Qwen3.5-35B-A3B", help="Model name for local reflection fallback")
    parser.add_argument("--max-metric-calls", type=int, default=20, help="GEPA metric-call budget")
    parser.add_argument("--parallel", action="store_true", help="Enable GEPA parallel evaluation")
    parser.add_argument("--max-workers", type=int, default=4, help="Worker count when --parallel is enabled")
    parser.add_argument("--quiet", action="store_true", help="Suppress live stdout for db_llm_query runs")
    parser.add_argument("db_llm_args", nargs=argparse.REMAINDER, help="Arguments passed through to db_llm_query_v4.py after '--'")
    args = parser.parse_args()

    db_llm_args = list(args.db_llm_args)
    if db_llm_args and db_llm_args[0] == "--":
        db_llm_args = db_llm_args[1:]
    if not db_llm_args:
        raise SystemExit("Missing live db_llm_query_v4 arguments after '--'.")

    split_file = Path(args.split_file)
    split_data = _load_split_file(split_file)
    splits: dict[str, list[dict[str, Any]]] = split_data["splits"]
    for split_name in (args.train_split, args.val_split, args.test_split):
        if split_name and split_name not in splits:
            raise SystemExit(f"Unknown split: {split_name}")

    case_catalog = _load_case_catalog()
    trainset = list(splits[args.train_split])
    valset = list(splits[args.val_split])
    seed_path = Path(args.seed_prompt_pack)
    seed_candidate = _load_seed_candidate(seed_path)
    run_stamp = time.strftime("%Y%m%d_%H%M%S")
    run_dir = Path(args.run_dir) if args.run_dir else (DEFAULT_EVAL_ROOT / f"gepa_v4_{run_stamp}")
    run_dir.mkdir(parents=True, exist_ok=True)

    objective = (
        "Optimize the ChEMBL v4 prompt-pack YAML so db_llm_query_v4 produces result tables that match the executable "
        "benchmark ground truth across held-out natural-language-to-SQL cases."
    )
    background = _build_background(split_file, args.train_split, args.val_split)
    reflection_lm = _build_reflection_lm(
        reflection_lm=args.reflection_lm,
        reflection_model=args.reflection_model,
        reflection_base_url=args.reflection_base_url,
        reflection_timeout=int(args.reflection_timeout),
        reflection_temperature=float(args.reflection_temperature),
        reflection_verbose=not bool(args.quiet),
        reflection_fallback_base_url=args.reflection_fallback_base_url,
        reflection_fallback_model=args.reflection_fallback_model,
    )

    def evaluator(candidate_text: str, example: dict[str, Any]) -> tuple[float, dict[str, Any]]:
        case_key = _case_ref_key(example)
        case = case_catalog[case_key]
        candidate_path = _persist_candidate_text(run_dir, candidate_text)
        run_exit, result_path, log_path = _run_live_case(
            case=case,
            split_name=f"gepa_{args.train_split}_{args.val_split}",
            prompt_pack_path=candidate_path,
            eval_root=run_dir,
            v4_script=Path(args.db_llm_script),
            db_llm_args=db_llm_args,
            quiet=bool(args.quiet),
            run_prefix="gepa",
        )

        side_info: dict[str, Any] = {
            "case_id": case["id"],
            "corpus": case["corpus"],
            "uq": case["uq"],
            "run_exit_code": int(run_exit),
            "result_path": str(result_path.resolve()),
            "log_path": str(log_path.resolve()),
            "candidate_path": str(candidate_path.resolve()),
        }
        side_info.update(_parse_log_snippets(log_path))

        if run_exit != 0 or not result_path.exists():
            oa.log(json.dumps(side_info, ensure_ascii=False))
            return 0.0, {**side_info, "status": "run_failed", "score": 0.0}

        scored = _score_case(case, result_path)
        merged = {**side_info, **scored}
        oa.log(json.dumps(merged, ensure_ascii=False))
        return float(scored["score"]), merged

    gepa_config = GEPAConfig(
        engine=EngineConfig(
            run_dir=str(run_dir),
            max_metric_calls=int(args.max_metric_calls),
            parallel=bool(args.parallel),
            max_workers=int(args.max_workers),
            cache_evaluation=True,
            cache_evaluation_storage="disk",
            track_best_outputs=True,
        ),
        reflection=ReflectionConfig(
            reflection_lm=reflection_lm,
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

    output_path = Path(args.output_prompt_pack) if args.output_prompt_pack else (run_dir / "best_prompt_pack.yaml")
    output_path.write_text(best_candidate, encoding="utf-8")

    summary = {
        "run_dir": str(run_dir.resolve()),
        "best_prompt_pack": str(output_path.resolve()),
        "seed_prompt_pack": str(seed_path.resolve()),
        "train_split": args.train_split,
        "val_split": args.val_split,
        "test_split": args.test_split,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
