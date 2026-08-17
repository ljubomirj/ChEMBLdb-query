#!/usr/bin/env python3
"""Run GEPA on the v4 UP-writer template only.

This optimizer mutates only the `up_task_template` block inside a full prompt
pack and evaluates candidates with a composite score:

- primary term: benchmark result-set agreement from `_score_case`
- penalty term: runtime UQ->UP echoing measured from the generated UP in run.log

The goal is to improve the UP writer without changing SQL/J templates or other
prompt-pack text.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import sys
import time
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
from experiments.gepa_optimize_prompt_pack_v4 import _build_reflection_lm


TOP_LEVEL_BLOCK_RE = re.compile(
    r"(?ms)^up_task_template: \|\n(?P<body>.*?)(?=^[A-Za-z0-9_]+:\s*(?:\||$)|\Z)"
)
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2} ")
UP_HEADER_RE = re.compile(r" - DEBUG - ITER_\d+ - UP_\d+:$")


def _load_seed_pack_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_up_task_template(pack_text: str) -> str:
    match = TOP_LEVEL_BLOCK_RE.search(pack_text)
    if not match:
        raise SystemExit("Could not find top-level up_task_template block in seed prompt pack.")
    body = match.group("body")
    lines = body.splitlines()
    dedented: list[str] = []
    for line in lines:
        if line.startswith("  "):
            dedented.append(line[2:])
        elif not line:
            dedented.append("")
        else:
            dedented.append(line)
    return "\n".join(dedented).rstrip("\n")


def _render_pack_with_up_task_template(seed_pack_text: str, up_task_template: str) -> str:
    indented_body = "\n".join(f"  {line}" if line else "" for line in up_task_template.splitlines())
    replacement = f"up_task_template: |\n{indented_body}\n"
    rendered, n = TOP_LEVEL_BLOCK_RE.subn(replacement, seed_pack_text, count=1)
    if n != 1:
        raise RuntimeError("Failed to replace up_task_template in prompt pack.")
    return rendered


def _persist_full_pack_candidate(
    *,
    run_dir: Path,
    seed_pack_text: str,
    up_task_template: str,
) -> tuple[Path, Path]:
    cand_hash = hashlib.sha256(up_task_template.encode("utf-8")).hexdigest()[:16]
    cache_dir = run_dir / "candidate_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    template_path = cache_dir / f"up_task_template_{cand_hash}.txt"
    pack_path = cache_dir / f"candidate_{cand_hash}.yaml"
    if not template_path.exists():
        template_path.write_text(up_task_template, encoding="utf-8")
    if not pack_path.exists():
        pack_text = _render_pack_with_up_task_template(seed_pack_text, up_task_template)
        pack_path.write_text(pack_text, encoding="utf-8")
    return template_path, pack_path


def _extract_last_up_from_log(log_path: Path) -> str | None:
    if not log_path.exists():
        return None
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    starts = [idx for idx, line in enumerate(lines) if UP_HEADER_RE.search(line)]
    if not starts:
        return None
    idx = starts[-1] + 1
    collected: list[str] = []
    while idx < len(lines) and not TIMESTAMP_RE.match(lines[idx]):
        collected.append(lines[idx])
        idx += 1
    if not collected:
        return None
    return "\n".join(collected).strip()


def _normalized_echo_ratio(uq: str, up: str) -> float:
    uq_norm = " ".join((uq or "").split())
    up_norm = " ".join((up or "").split())
    if not uq_norm and not up_norm:
        return 1.0
    return difflib.SequenceMatcher(None, uq_norm, up_norm).ratio()


def _echo_penalty(
    *,
    ratio: float,
    threshold: float,
    weight: float,
) -> float:
    if ratio < threshold:
        return 0.0
    scaled = (ratio - threshold) / max(1e-9, 1.0 - threshold)
    scaled = min(1.0, max(0.0, scaled))
    return weight * scaled


def _build_background(split_file: Path, train_split: str, val_split: str, threshold: float, weight: float) -> str:
    return "\n".join(
        [
            "You are optimizing only the UP-writer template inside a ChEMBL Text-to-SQL prompt pack.",
            "The SQL and Judge templates are fixed; only the `up_task_template` block may change.",
            "Goal 1: preserve or improve final result-set agreement against executable benchmark cases.",
            "Goal 2: reduce runtime UQ->UP echoing. The UP should be a better specification for the SQL writer, not a near-copy of the original user question.",
            f"Echo penalty starts at similarity >= {threshold:.2f} and scales up to weight {weight:.2f}.",
            f"Split file: {split_file}",
            f"Train split: {train_split}",
            f"Validation split: {val_split}",
            "Prefer concise UP-writer instructions that force abstraction, explicit schema requirements, and reduction of superficial restatement.",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Optimize only the UP-writer template inside the v4 prompt-pack.")
    parser.add_argument("--seed-prompt-pack", default=str(REPO_ROOT / "experiments" / "prompt_pack_v4.11.yaml"))
    parser.add_argument("--output-prompt-pack", default=str(REPO_ROOT / "experiments" / "prompt_pack_v4.15.yaml"))
    parser.add_argument(
        "--output-up-template",
        default=str(REPO_ROOT / "experiments" / "prompt_pack_v4.15_up_task_template.txt"),
        help="Where to write the best UP task template text.",
    )
    parser.add_argument("--split-file", default=str(DEFAULT_SPLIT_PATH))
    parser.add_argument("--train-split", default="train")
    parser.add_argument("--val-split", default="val")
    parser.add_argument("--test-split", default="test")
    parser.add_argument("--db-llm-script", default=str(DEFAULT_V4_SCRIPT))
    parser.add_argument("--run-dir", default=None)
    parser.add_argument("--reflection-lm", default=None)
    parser.add_argument("--reflection-model", default="glm-4.7")
    parser.add_argument("--reflection-base-url", default="https://api.z.ai/api/anthropic")
    parser.add_argument("--reflection-timeout", type=int, default=180)
    parser.add_argument("--reflection-temperature", type=float, default=0.7)
    parser.add_argument("--reflection-fallback-base-url", default="http://192.168.1.251:8081/v1")
    parser.add_argument("--reflection-fallback-model", default="Qwen3.5-35B-A3B")
    parser.add_argument("--max-metric-calls", type=int, default=300)
    parser.add_argument("--parallel", action="store_true")
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--echo-threshold", type=float, default=0.95)
    parser.add_argument("--echo-penalty-weight", type=float, default=0.15)
    parser.add_argument("db_llm_args", nargs=argparse.REMAINDER)
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
    seed_pack_text = _load_seed_pack_text(seed_path)
    seed_candidate = _extract_up_task_template(seed_pack_text)
    run_stamp = time.strftime("%Y%m%d_%H%M%S")
    run_dir = Path(args.run_dir) if args.run_dir else (DEFAULT_EVAL_ROOT / f"gepa_v4_up_only_{run_stamp}")
    run_dir.mkdir(parents=True, exist_ok=True)

    objective = (
        "Optimize the UP-writer template so db_llm_query_v4 produces better result tables while generating user prompts "
        "that are meaningfully better than the original user question rather than near-copies of it."
    )
    background = _build_background(
        split_file,
        args.train_split,
        args.val_split,
        float(args.echo_threshold),
        float(args.echo_penalty_weight),
    )
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

    def evaluator(up_task_template: str, example: dict[str, Any]) -> tuple[float, dict[str, Any]]:
        case_key = _case_ref_key(example)
        case = case_catalog[case_key]
        template_path, candidate_path = _persist_full_pack_candidate(
            run_dir=run_dir,
            seed_pack_text=seed_pack_text,
            up_task_template=up_task_template,
        )
        run_exit, result_path, log_path = _run_live_case(
            case=case,
            split_name=f"gepa_up_only_{args.train_split}_{args.val_split}",
            prompt_pack_path=candidate_path,
            eval_root=run_dir,
            v4_script=Path(args.db_llm_script),
            db_llm_args=db_llm_args,
            quiet=bool(args.quiet),
            run_prefix="gepa_up_only",
        )

        side_info: dict[str, Any] = {
            "case_id": case["id"],
            "corpus": case["corpus"],
            "uq": case["uq"],
            "run_exit_code": int(run_exit),
            "result_path": str(result_path.resolve()),
            "log_path": str(log_path.resolve()),
            "candidate_path": str(candidate_path.resolve()),
            "up_template_path": str(template_path.resolve()),
        }
        side_info.update(_parse_log_snippets(log_path))

        if run_exit != 0 or not result_path.exists():
            side_info.update(
                {
                    "status": "run_failed",
                    "score": 0.0,
                    "base_score": 0.0,
                    "adjusted_score": 0.0,
                    "up_echo_ratio": None,
                    "up_echo_penalty": None,
                    "generated_up": _extract_last_up_from_log(log_path),
                }
            )
            oa.log(json.dumps(side_info, ensure_ascii=False))
            return 0.0, side_info

        scored = _score_case(case, result_path)
        generated_up = _extract_last_up_from_log(log_path)
        echo_ratio = _normalized_echo_ratio(case["uq"], generated_up or "")
        penalty = _echo_penalty(
            ratio=echo_ratio,
            threshold=float(args.echo_threshold),
            weight=float(args.echo_penalty_weight),
        )
        base_score = float(scored["score"])
        adjusted_score = max(0.0, min(1.0, base_score - penalty))
        merged = {
            **side_info,
            **scored,
            "generated_up": generated_up,
            "base_score": round(base_score, 6),
            "up_echo_ratio": round(echo_ratio, 6),
            "up_echo_penalty": round(penalty, 6),
            "adjusted_score": round(adjusted_score, 6),
            "scores": {
                "result_score": round(base_score, 6),
                "up_non_echo_score": round(max(0.0, 1.0 - penalty), 6),
            },
        }
        merged["score"] = round(adjusted_score, 6)
        oa.log(json.dumps(merged, ensure_ascii=False))
        return adjusted_score, merged

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

    best_up_template = result.best_candidate
    if not isinstance(best_up_template, str):
        raise SystemExit(f"Expected best_candidate to be str, got {type(best_up_template)!r}")

    output_pack_path = Path(args.output_prompt_pack)
    output_up_path = Path(args.output_up_template)
    output_up_path.write_text(best_up_template, encoding="utf-8")
    output_pack_path.write_text(
        _render_pack_with_up_task_template(seed_pack_text, best_up_template),
        encoding="utf-8",
    )

    summary = {
        "run_dir": str(run_dir.resolve()),
        "best_prompt_pack": str(output_pack_path.resolve()),
        "best_up_task_template": str(output_up_path.resolve()),
        "seed_prompt_pack": str(seed_path.resolve()),
        "train_split": args.train_split,
        "val_split": args.val_split,
        "test_split": args.test_split,
        "max_metric_calls": int(args.max_metric_calls),
        "echo_threshold": float(args.echo_threshold),
        "echo_penalty_weight": float(args.echo_penalty_weight),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
