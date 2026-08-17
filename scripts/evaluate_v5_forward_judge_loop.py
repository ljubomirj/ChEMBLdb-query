#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

import argparse
import csv
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from compressed_io import read_text_maybe_compressed
from db_llm_runtime_v5 import ChEMBLLLMQuery, Iteration
from db_llm_v5.forward import run_res
from db_llm_v5.io import load_case_manifest, load_prompt_pack, resolve_case_manifest_path
from db_llm_v5.provider import EndpointConfig, resolve_profile, write_json

DEFAULT_SPLIT = REPO_ROOT / "cases" / "v5.1010" / "splits" / "case_splits_v5.1010.json"
DEFAULT_MANIFEST_ROOT = REPO_ROOT / "cases" / "v5.1010" / "cases"
DEFAULT_EVAL_ROOT = REPO_ROOT / "runs"


def _parse_history_window_arg(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"all", "*"}:
        return None
    parsed = int(text)
    if parsed < 0:
        raise ValueError(f"History window must be >= 0, got {parsed}")
    return parsed


def _load_uq_text(manifest, repo_root: Path) -> str:
    if manifest.artifacts.uq_surface is None:
        raise ValueError("Manifest is missing uq_surface")
    path = repo_root / manifest.artifacts.uq_surface
    return read_text_maybe_compressed(path).strip()


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
        "judge_model": it.judge_model,
        "judge_score": it.judge_score,
        "judge_decision": it.judge_decision,
    }


def _resolve_profile(
    profile: Optional[str],
    endpoint_provider: Optional[str] = None,
    endpoint_model: Optional[str] = None,
    endpoint_base_url: Optional[str] = None,
    endpoint_temperature: float = 0.2,
    endpoint_timeout: int = 1200,
) -> tuple[EndpointConfig, list[EndpointConfig]]:
    direct_values = (endpoint_provider, endpoint_model, endpoint_base_url)
    if any(value is not None for value in direct_values):
        if not all(value is not None for value in direct_values):
            raise ValueError(
                "Direct endpoint mode requires --endpoint-provider, --endpoint-model, "
                "and --endpoint-base-url together."
            )
        return (
            EndpointConfig(
                provider=str(endpoint_provider),
                model=str(endpoint_model),
                base_url=str(endpoint_base_url),
                temperature=endpoint_temperature,
                timeout=endpoint_timeout,
            ),
            [],
        )
    resolved = resolve_profile(profile)
    if resolved[0] is None:
        raise ValueError("Multi-endpoint profile required")
    endpoint, fallback = resolved
    fallback_list: list[EndpointConfig] = []
    if fallback is not None:
        if isinstance(fallback, list):
            fallback_list = list(fallback)
        else:
            fallback_list = [fallback]
    return endpoint, fallback_list


def build_llm(
    *,
    endpoint: EndpointConfig,
    fallback: list[EndpointConfig],
    max_iterations: int,
    history_window_up_sql: Optional[int],
    judge_history_window: int,
    judge_score_threshold: float,
    judge_no_override_threshold: float,
    judge_call_retries: int,
    up_max_tokens: int,
    sql_max_tokens: int,
    judge_max_tokens: int,
    local_enable_thinking: bool,
    local_reasoning_budget_tokens: int | None,
    local_reasoning_budget_message: str | None,
    case_context: dict[str, Any] | None = None,
) -> ChEMBLLLMQuery:
    quota_provider = fallback[0] if fallback else None
    quota_provider_2 = fallback[1] if len(fallback) > 1 else None
    return ChEMBLLLMQuery(
        provider=endpoint.provider,
        provider_base_url=endpoint.base_url,
        sql_model=endpoint.model,
        judge_model=endpoint.model,
        max_retries=max_iterations,
        history_window_up_sql=history_window_up_sql,
        judge_history_window=judge_history_window,
        judge_score_threshold=judge_score_threshold,
        judge_no_override_threshold=judge_no_override_threshold,
        judge_call_retries=judge_call_retries,
        up_max_tokens=up_max_tokens,
        sql_max_tokens=sql_max_tokens,
        judge_max_tokens=judge_max_tokens,
        local_enable_thinking=local_enable_thinking,
        local_reasoning_budget_tokens=local_reasoning_budget_tokens,
        local_reasoning_budget_message=local_reasoning_budget_message,
        min_context=100000,
        save_intermediate=False,
        quota_fallback_provider=quota_provider.provider if quota_provider else None,
        quota_fallback_base_url=quota_provider.base_url if quota_provider else None,
        quota_fallback_model=quota_provider.model if quota_provider else None,
        quota_fallback_provider_2=quota_provider_2.provider if quota_provider_2 else None,
        quota_fallback_base_url_2=quota_provider_2.base_url if quota_provider_2 else None,
        quota_fallback_model_2=quota_provider_2.model if quota_provider_2 else None,
        case_context=case_context,
    )


def gather_case_items(split_payload: dict[str, Any], splits: list[str], limit: Optional[int]) -> list[tuple[str, str, str]]:
    items: list[tuple[str, str, str]] = []
    for split in splits:
        for entry in split_payload["splits"][split]:
            items.append((split, entry["corpus"], entry["id"]))
    if limit is not None:
        items = items[:limit]
    return items


def _load_json(path: Path) -> dict[str, Any] | list[Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _completed_case_result(case_root: Path) -> dict[str, Any] | None:
    pf_res_path = case_root / "pf_res.output.json"
    if pf_res_path.exists():
        pf_res_payload = _load_json(pf_res_path)
        if isinstance(pf_res_payload, dict):
            det = pf_res_payload.get("deterministic_score") or {}
            result = pf_res_payload.get("result") or {}
            result_row: dict[str, Any] = {
                "case_id": pf_res_payload.get("case_id"),
                "split": pf_res_payload.get("split"),
                "corpus": pf_res_payload.get("corpus"),
                "family": pf_res_payload.get("family"),
                "status": str(det.get("status", "fail")),
                "score": float(det.get("score", 0.0)) if det else 0.0,
                "result_success": bool(result.get("success")),
                "case_root": str(case_root.resolve()),
            }
            llm_provenance = pf_res_payload.get("llm_provenance")
            if isinstance(llm_provenance, dict) and llm_provenance:
                result_row["llm_provenance"] = llm_provenance

            iterations_payload = _load_json(case_root / "judge_loop_iterations.json")
            if isinstance(iterations_payload, list) and iterations_payload:
                result_row["iterations"] = len(iterations_payload)
                last_iteration = iterations_payload[-1]
                if isinstance(last_iteration, dict):
                    result_row["judge_decision"] = last_iteration.get("judge_decision")
                    result_row["judge_score"] = last_iteration.get("judge_score")
            return result_row

    case_error_path = case_root / "case_error.json"
    if not case_error_path.exists():
        return None
    case_error = _load_json(case_error_path)
    if not isinstance(case_error, dict):
        return None
    return {
        "case_id": case_error.get("case_id"),
        "split": case_error.get("split"),
        "corpus": case_error.get("corpus"),
        "family": case_error.get("family"),
        "status": "fail",
        "score": 0.0,
        "result_success": False,
        "judge_decision": None,
        "judge_score": None,
        "case_root": str(case_root.resolve()),
        "error_stage": case_error.get("error_stage"),
        "error": case_error.get("error"),
    }


def _aggregate_report_cases(
    *,
    eval_root: Path,
    case_items: list[tuple[str, str, str]],
    selected_splits: list[str],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, float | int]], list[dict[str, str]]]:
    results: list[dict[str, Any]] = []
    split_stats: dict[str, dict[str, float | int]] = {
        split: {
            "n_target_cases": 0,
            "n_cases": 0,
            "n_pass": 0,
            "n_incomplete": 0,
            "mean_score": 0.0,
        }
        for split in selected_splits
    }
    incomplete_cases: list[dict[str, str]] = []

    for ordinal, (split_name, corpus, case_id) in enumerate(case_items, start=1):
        split_stats[split_name]["n_target_cases"] += 1
        case_root = eval_root / split_name / corpus / case_id
        result_row = _completed_case_result(case_root)
        if result_row is None:
            split_stats[split_name]["n_incomplete"] += 1
            incomplete_cases.append(
                {
                    "ordinal": ordinal,
                    "case_id": case_id,
                    "split": split_name,
                    "corpus": corpus,
                    "case_root": str(case_root.resolve()),
                }
            )
            continue
        result_row["ordinal"] = ordinal
        results.append(result_row)
        split_stats[split_name]["n_cases"] += 1
        split_stats[split_name]["n_pass"] += 1 if result_row["status"] == "pass" else 0
        split_stats[split_name]["mean_score"] += float(result_row["score"])

    for stat in split_stats.values():
        n_cases = int(stat["n_cases"])
        stat["mean_score"] = round(float(stat["mean_score"]) / n_cases, 6) if n_cases else 0.0
        stat["pass_rate"] = round(int(stat["n_pass"]) / n_cases, 6) if n_cases else 0.0

    return results, split_stats, incomplete_cases


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full J-Judge loop over a split of v5 cases.")
    parser.add_argument("--prompt-pack", default=str(REPO_ROOT / "experiments" / "prompt_pack_v5.0.yaml"))
    parser.add_argument("--split-file", default=str(DEFAULT_SPLIT))
    parser.add_argument("--split", action="append", choices=["train", "val", "test"], help="Split(s) to evaluate; default all")
    parser.add_argument("--manifest-root", default=str(DEFAULT_MANIFEST_ROOT))
    parser.add_argument("--eval-root", default=str(DEFAULT_EVAL_ROOT))
    parser.add_argument("--eval-label", default=None)
    parser.add_argument("--multi-endpoint-profile", default="zai-glm47-local-fallbacks")
    parser.add_argument(
        "--endpoint-provider",
        default=None,
        help="Direct provider override, for example llamacpp. Requires the other --endpoint-* values.",
    )
    parser.add_argument(
        "--endpoint-model",
        default=None,
        help="Direct model id advertised by the endpoint. Requires the other --endpoint-* values.",
    )
    parser.add_argument(
        "--endpoint-base-url",
        default=None,
        help="Direct OpenAI-compatible endpoint base URL. Requires the other --endpoint-* values.",
    )
    parser.add_argument("--endpoint-temperature", type=float, default=0.2)
    parser.add_argument("--endpoint-timeout", type=int, default=1200)
    parser.add_argument("--max-iterations", type=int, default=10)
    parser.add_argument("--history-window-up-sql", default="all")
    parser.add_argument("--judge-history-window", type=int, default=1)
    parser.add_argument("--judge-score-threshold", type=float, default=0.5)
    parser.add_argument("--judge-no-override-threshold", type=float, default=0.99)
    parser.add_argument("--judge-call-retries", type=int, default=3)
    parser.add_argument("--up-max-tokens", type=int, default=4096)
    parser.add_argument("--sql-max-tokens", type=int, default=4096)
    parser.add_argument("--judge-max-tokens", type=int, default=4096)
    parser.add_argument(
        "--local-enable-thinking",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable llama.cpp-local chat-template thinking for local providers/fallbacks (default: enabled)",
    )
    parser.add_argument("--local-reasoning-budget-tokens", type=int, default=None)
    parser.add_argument("--local-reasoning-budget-message", default=None)
    parser.add_argument("--min-rows", type=int, default=1)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--fallback-provider", default=None)
    parser.add_argument("--fallback-model", default=None)
    parser.add_argument("--fallback-base-url", default=None)
    args = parser.parse_args()

    if args.eval_label:
        label = args.eval_label
    else:
        from datetime import datetime

        label = f"v5_1010_judge_loop_{datetime.now():%Y%m%d_%H%M%S}"

    prompt_pack = load_prompt_pack(args.prompt_pack)
    split_payload = json.loads(Path(args.split_file).read_text(encoding="utf-8"))
    selected_splits = args.split or ["train", "val", "test"]
    case_items = gather_case_items(split_payload, selected_splits, args.limit)

    eval_root = Path(args.eval_root) / label
    eval_root.mkdir(parents=True, exist_ok=True)

    endpoint, fallback_list = _resolve_profile(
        args.multi_endpoint_profile,
        endpoint_provider=args.endpoint_provider,
        endpoint_model=args.endpoint_model,
        endpoint_base_url=args.endpoint_base_url,
        endpoint_temperature=args.endpoint_temperature,
        endpoint_timeout=args.endpoint_timeout,
    )
    if args.fallback_provider:
        fallback_list = [
            EndpointConfig(
                provider=args.fallback_provider,
                model=args.fallback_model,
                base_url=args.fallback_base_url,
            )
        ]
    history_window = _parse_history_window_arg(args.history_window_up_sql)

    n_skipped_existing = 0

    total_cases = len(case_items)
    for case_index, (split_name, corpus, case_id) in enumerate(case_items, start=1):
        case_root = eval_root / split_name / corpus / case_id
        case_root.mkdir(parents=True, exist_ok=True)
        if args.skip_existing and (case_root / "pf_res.output.json").exists():
            if not (case_root / "run.log").exists() or not (case_root / "run.events.jsonl").exists():
                _start_case_logs(case_root)
            _append_case_event(case_root, "case_reused_existing", case_id=case_id, split=split_name, corpus=corpus)
            _append_transcript(
                case_root,
                "Case Reused Existing",
                _format_key_values({"case_id": case_id, "split": split_name, "corpus": corpus}),
            )
            logging.info(
                "Skipping existing case %s/%s %s/%s/%s",
                case_index,
                total_cases,
                split_name,
                corpus,
                case_id,
            )
            n_skipped_existing += 1
            continue

        _start_case_logs(case_root)
        _append_case_event(
            case_root,
            "case_start",
            ordinal=case_index,
            total_cases=total_cases,
            case_id=case_id,
            split=split_name,
            corpus=corpus,
            prompt_pack_path=str(Path(args.prompt_pack).resolve()),
            prompt_pack_version=prompt_pack.version,
            max_iterations=args.max_iterations,
            judge_score_threshold=args.judge_score_threshold,
            judge_no_override_threshold=args.judge_no_override_threshold,
            judge_max_tokens=args.judge_max_tokens,
            local_enable_thinking=args.local_enable_thinking,
            local_reasoning_budget_tokens=args.local_reasoning_budget_tokens,
        )
        logging.info(
            "Starting case %s/%s %s/%s/%s",
            case_index,
            total_cases,
            split_name,
            corpus,
            case_id,
        )

        try:
            manifest = load_case_manifest(resolve_case_manifest_path(args.manifest_root, corpus, case_id))
        except Exception as exc:
            _append_case_event(case_root, "case_error", error_stage="manifest", error=str(exc))
            _append_transcript(case_root, "Case Error", _format_key_values({"error_stage": "manifest", "error": str(exc)}))
            logging.error("Manifest load failed (%s): %s", case_id, exc)
            write_json(
                case_root / "case_error.json",
                {
                    "case_id": case_id,
                    "split": split_name,
                    "corpus": corpus,
                    "error_stage": "manifest",
                    "error": str(exc),
                },
            )
            continue

        try:
            uq = _load_uq_text(manifest, REPO_ROOT)
        except Exception as exc:
            _append_case_event(case_root, "case_error", error_stage="uq", error=str(exc))
            _append_transcript(case_root, "Case Error", _format_key_values({"error_stage": "uq", "error": str(exc)}))
            logging.error("Failed to load UQ (%s): %s", case_id, exc)
            write_json(
                case_root / "case_error.json",
                {
                    "case_id": case_id,
                    "split": split_name,
                    "corpus": corpus,
                    "error_stage": "uq",
                    "error": str(exc),
                },
            )
            continue

        _append_transcript(
            case_root,
            "Case Start",
            _render_case_intro(
                manifest=manifest,
                manifest_path=resolve_case_manifest_path(args.manifest_root, corpus, case_id),
                prompt_pack=prompt_pack,
                prompt_pack_path=Path(args.prompt_pack),
                split_name=split_name,
                corpus=corpus,
                ordinal=case_index,
                total_cases=total_cases,
                max_iterations=args.max_iterations,
                judge_score_threshold=args.judge_score_threshold,
                judge_no_override_threshold=args.judge_no_override_threshold,
                judge_max_tokens=args.judge_max_tokens,
                local_enable_thinking=args.local_enable_thinking,
                local_reasoning_budget_tokens=args.local_reasoning_budget_tokens,
                history_window_up_sql=args.history_window_up_sql,
                judge_history_window=args.judge_history_window,
            ),
        )
        result_path = case_root / "result.generated.csv"
        runtime_log_handler: logging.Handler | None = None
        llm: ChEMBLLLMQuery | None = None
        try:
            _append_transcript(
                case_root,
                "Runtime Log",
                "Captured from the live judge-loop runtime while this case ran. "
                "This includes failed attempts that may not become accepted Iteration objects.",
            )
            runtime_log_handler = _attach_case_runtime_log(case_root)
            try:
                case_context = {
                    "case": f"{case_index} / {total_cases}",
                    "ordinal": case_index,
                    "total_cases": total_cases,
                    "split": split_name,
                    "corpus": corpus,
                    "case_id": case_id,
                    "family": manifest.metadata.family,
                    "manifest_path": str((resolve_case_manifest_path(args.manifest_root, corpus, case_id)).resolve()),
                    "case_dir": str(case_root.resolve()),
                    "metric_mode": "judge-loop-eval",
                }
                llm = build_llm(
                    endpoint=endpoint,
                    fallback=fallback_list,
                    max_iterations=args.max_iterations,
                    history_window_up_sql=history_window,
                    judge_history_window=args.judge_history_window,
            judge_score_threshold=args.judge_score_threshold,
            judge_no_override_threshold=args.judge_no_override_threshold,
            judge_call_retries=args.judge_call_retries,
            up_max_tokens=args.up_max_tokens,
            sql_max_tokens=args.sql_max_tokens,
            judge_max_tokens=args.judge_max_tokens,
                    local_enable_thinking=args.local_enable_thinking,
                    local_reasoning_budget_tokens=args.local_reasoning_budget_tokens,
                    local_reasoning_budget_message=args.local_reasoning_budget_message,
                    case_context=case_context,
                )
                df = llm.query(
                    uq,
                    save_to_file=result_path,
                    min_rows=args.min_rows,
                    case_label=f"{case_index}/{total_cases} {split_name}/{corpus}/{case_id}",
                )
            finally:
                _detach_case_runtime_log(runtime_log_handler)
                runtime_log_handler = None
            if df is None:
                raise RuntimeError("Query returned no result")
            sql_text = llm.latest_sql
            if not sql_text:
                raise RuntimeError("No SQL produced")
            for it in llm.latest_iterations:
                _append_case_event(
                    case_root,
                    "iteration_done",
                    iteration=it.n,
                    sql_model=it.sql_model,
                    judge_model=it.judge_model,
                    judge_score=it.judge_score,
                    judge_decision=it.judge_decision,
                    res_row_count=it.res_row_count,
                    res_error=it.res_error,
                )
            pf_res_payload = run_res(
                manifest=manifest,
                repo_root=REPO_ROOT,
                sql_text=sql_text,
                result_path=result_path,
            )
            pf_res_payload.update(
                {
                    "prompt_pack_path": str(Path(args.prompt_pack).resolve()),
                    "prompt_pack_version": prompt_pack.version,
                    "case_id": manifest.case_id,
                    "split": split_name,
                    "corpus": corpus,
                    "selected_step": "res",
                }
            )
            pf_res_payload["llm_provenance"] = {
                "sql_provider": {
                    "provider": llm.sql_provider.provider,
                    "model": llm.sql_provider.model,
                    "base_url": llm.sql_provider.base_url,
                },
                "judge_provider": {
                    "provider": llm.judge_provider.provider,
                    "model": llm.judge_provider.model,
                    "base_url": llm.judge_provider.base_url,
                },
            }
            write_json(case_root / "pf_res.output.json", pf_res_payload)

            iterations_data = [ _iteration_to_dict(it) for it in llm.latest_iterations ]
            if iterations_data:
                (case_root / "judge_loop_iterations.json").write_text(
                    json.dumps(iterations_data, indent=2), encoding="utf-8"
                )

            det = pf_res_payload.get("deterministic_score") or {}
            status = det.get("status", "fail")
            score = float(det.get("score", 0.0)) if det else 0.0
            judge_info = llm.latest_iterations[-1] if llm.latest_iterations else None
            result_row = {
                "case_id": case_id,
                "split": split_name,
                "corpus": corpus,
                "family": manifest.metadata.family,
                "status": status,
                "score": score,
                "result_success": pf_res_payload["result"]["success"],
                "judge_decision": judge_info.judge_decision if judge_info else None,
                "judge_score": judge_info.judge_score if judge_info else None,
                "returned_iteration": llm.latest_returned_iteration_n,
                "judge_loop_exhausted": llm.latest_exhausted,
                "case_root": str(case_root.resolve()),
            }
            if judge_info:
                result_row["iterations"] = len(iterations_data)
            _append_transcript(
                case_root,
                "Judge Loop Transcript",
                _render_judge_loop_transcript(
                    uq=uq,
                    iterations=llm.latest_iterations,
                    result_path=result_path,
                    pf_res_payload=pf_res_payload,
                ),
            )
            _append_case_event(
                case_root,
                "case_complete",
                status=status,
                score=score,
                result_success=pf_res_payload["result"]["success"],
                iterations=len(iterations_data),
                judge_decision=judge_info.judge_decision if judge_info else None,
                judge_score=judge_info.judge_score if judge_info else None,
            )
            _append_transcript(
                case_root,
                "Case Complete",
                _format_key_values(
                    {
                        "status": status,
                        "score": score,
                        "result_success": pf_res_payload["result"]["success"],
                        "iterations": len(iterations_data),
                        "judge_decision": judge_info.judge_decision if judge_info else None,
                        "judge_score": judge_info.judge_score if judge_info else None,
                    }
                ),
            )
        except Exception as exc:
            if runtime_log_handler is not None:
                _detach_case_runtime_log(runtime_log_handler)
            _append_case_event(case_root, "case_error", error_stage="chain", error=str(exc))
            partial_iterations = list(getattr(llm, "latest_iterations", []) or [])
            if partial_iterations:
                _append_transcript(
                    case_root,
                    "Partial Judge Loop Transcript",
                    _render_judge_loop_transcript(
                        uq=uq,
                        iterations=partial_iterations,
                        result_path=result_path,
                        pf_res_payload=None,
                    ),
                )
            _append_transcript(case_root, "Case Error", _format_key_values({"error_stage": "chain", "error": str(exc)}))
            logging.exception("Case %s failed", case_id)
            write_json(
                case_root / "case_error.json",
                {
                    "case_id": case_id,
                    "split": split_name,
                    "corpus": corpus,
                    "error_stage": "chain",
                    "error": str(exc),
                },
            )
            continue

    results, split_stats, incomplete_cases = _aggregate_report_cases(
        eval_root=eval_root,
        case_items=case_items,
        selected_splits=selected_splits,
    )
    n_cases = len(results)
    n_pass = sum(1 for item in results if item["status"] == "pass")
    mean_score = round(sum(float(item["score"]) for item in results) / n_cases, 6) if n_cases else 0.0

    report = {
        "prompt_pack_path": str(Path(args.prompt_pack).resolve()),
        "prompt_pack_version": prompt_pack.version,
        "split_file": str(Path(args.split_file).resolve()),
        "selected_splits": selected_splits,
        "eval_root": str(eval_root.resolve()),
        "summary": {
            "n_cases": n_cases,
            "n_pass": n_pass,
            "pass_rate": round(n_pass / n_cases, 6) if n_cases else 0.0,
            "mean_score": mean_score,
            "n_target_cases": len(case_items),
            "n_incomplete": len(incomplete_cases),
            "n_skipped_existing": n_skipped_existing,
        },
        "by_split": split_stats,
        "cases": results,
        "incomplete_cases": incomplete_cases,
    }
    write_json(eval_root / "report.json", report)
    logging.info("Report written: %s", eval_root / "report.json")


def _start_case_logs(case_root: Path) -> None:
    (case_root / "run.events.jsonl").write_text("", encoding="utf-8")
    (case_root / "run.log").write_text("", encoding="utf-8")


def _append_case_event(case_root: Path, event: str, **payload: Any) -> None:
    line = {
        "ts": datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds"),
        "event": event,
    }
    line.update(payload)
    with (case_root / "run.events.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(line, ensure_ascii=False, sort_keys=True) + "\n")


def _append_transcript(case_root: Path, title: str, body: str) -> None:
    timestamp = datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds")
    with (case_root / "run.log").open("a", encoding="utf-8") as handle:
        handle.write(f"\n{'=' * 88}\n")
        handle.write(f"{title} [{timestamp}]\n")
        handle.write(f"{'=' * 88}\n\n")
        handle.write(body.rstrip() + "\n")


def _attach_case_runtime_log(case_root: Path) -> logging.Handler:
    handler = logging.FileHandler(case_root / "run.log", mode="a", encoding="utf-8")
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(stage)s - %(message)s"))
    logging.getLogger().addHandler(handler)
    return handler


def _detach_case_runtime_log(handler: logging.Handler) -> None:
    root = logging.getLogger()
    root.removeHandler(handler)
    handler.close()


def _render_case_intro(
    *,
    manifest: Any,
    manifest_path: Path,
    prompt_pack: Any,
    prompt_pack_path: Path,
    split_name: str,
    corpus: str,
    ordinal: int,
    total_cases: int,
    max_iterations: int,
    judge_score_threshold: float,
    judge_no_override_threshold: float,
    judge_max_tokens: int,
    local_enable_thinking: bool,
    local_reasoning_budget_tokens: int | None,
    history_window_up_sql: str,
    judge_history_window: int,
) -> str:
    artifacts = manifest.artifacts
    parts = [
        _format_key_values(
            {
                "case": f"{ordinal}/{total_cases}",
                "case_id": manifest.case_id,
                "split": split_name,
                "corpus": corpus,
                "family": manifest.metadata.family,
                "manifest_path": str(manifest_path.resolve()),
                "prompt_pack_path": str(prompt_pack_path.resolve()),
                "prompt_pack_version": prompt_pack.version,
                "db_path": manifest.db_path,
                "max_iterations": max_iterations,
                "judge_score_threshold": judge_score_threshold,
                "judge_no_override_threshold": judge_no_override_threshold,
                "judge_max_tokens": judge_max_tokens,
                "local_enable_thinking": local_enable_thinking,
                "local_reasoning_budget_tokens": local_reasoning_budget_tokens,
                "history_window_up_sql": history_window_up_sql,
                "judge_history_window": judge_history_window,
            }
        ),
        _render_file_block("Original user question", artifacts.uq_surface),
        _render_file_block("Documentation", artifacts.documentation),
        _format_key_values(
            {
                "schema_block_path": prompt_pack.system.schema_block_path,
                "hint_block_path": prompt_pack.system.hint_block_path,
                "gold_sql_path": artifacts.sql_gold,
                "gold_result_path": artifacts.res_gold,
            }
        ),
        _render_text_block("System about block", prompt_pack.system.about_block),
        _render_text_block("Forward UP prompt", prompt_pack.pf.up),
        _render_text_block("Forward SQL prompt", prompt_pack.pf.sql),
        _render_text_block("Forward judge prompt", prompt_pack.pf.judge),
    ]
    return "\n\n".join(part for part in parts if part.strip())


def _render_judge_loop_transcript(
    *,
    uq: str,
    iterations: list[Iteration],
    result_path: Path,
    pf_res_payload: dict[str, Any] | None,
) -> str:
    parts = [_render_text_block("UQ", uq)]
    for it in iterations:
        parts.append(
            "\n\n".join(
                [
                    _format_key_values(
                        {
                            "iteration": it.n,
                            "sql_model": it.sql_model,
                            "judge_model": it.judge_model,
                        }
                    ),
                    _render_text_block(f"UP_{it.n}", it.up),
                    _render_text_block(f"SQL_{it.n}", it.sql),
                    _render_text_block(f"PLAN_{it.n}", it.plan_summary),
                    _render_text_block(
                        f"RES_{it.n}",
                        _format_key_values(
                            {
                                "row_count": it.res_row_count,
                                "columns": list(it.res_columns),
                                "error": it.res_error,
                                "samples": _format_res_samples(it.res_samples),
                            }
                        ),
                    ),
                    _render_text_block(f"J_{it.n}", it.judge_text),
                    _format_key_values(
                        {
                            "judge_score": it.judge_score,
                            "judge_decision": it.judge_decision,
                        }
                    ),
                ]
            )
        )
    if pf_res_payload is not None:
        parts.extend(
            [
                _render_text_block("Final PF_RES result", json.dumps(pf_res_payload.get("result"), indent=2, ensure_ascii=False)),
                _render_text_block(
                    "Final deterministic score",
                    json.dumps(pf_res_payload.get("deterministic_score"), indent=2, ensure_ascii=False),
                ),
            ]
        )
    parts.append(_render_csv_preview(result_path, max_rows=20))
    return "\n\n".join(part for part in parts if part.strip())


def _format_res_samples(samples: Tuple[Tuple[str, Tuple[str, ...]], ...]) -> str:
    if not samples:
        return ""
    lines = []
    for position, row in samples:
        lines.append(f"{position}: " + " | ".join(str(cell) for cell in row))
    return "\n".join(lines)


def _render_file_block(title: str, repo_relative_path: str | None, *, max_chars: int = 12000) -> str:
    if not repo_relative_path:
        return ""
    path = REPO_ROOT / repo_relative_path
    try:
        text = read_text_maybe_compressed(path)
    except Exception as exc:
        return _format_key_values({title: repo_relative_path, "read_error": str(exc)})
    return _render_text_block(f"{title} ({repo_relative_path})", _truncate_text(text, max_chars=max_chars))


def _render_text_block(title: str, text: str | None) -> str:
    content = "" if text is None else str(text).rstrip()
    return f"--- {title} ---\n{content}\n--- end {title} ---"


def _render_csv_preview(path: Path, *, max_rows: int) -> str:
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
            _render_text_block("CSV preview", "\n".join(rendered_rows)),
            "Preview includes header plus first rows only; see full CSV at path above.",
        ]
    )


def _csv_quote(value: str) -> str:
    if any(ch in value for ch in [",", '"', "\n", "\r"]):
        return '"' + value.replace('"', '""') + '"'
    return value


def _format_key_values(values: dict[str, Any]) -> str:
    lines = []
    for key, value in values.items():
        if value is None:
            continue
        if isinstance(value, (dict, list)):
            value = json.dumps(value, indent=2, ensure_ascii=False)
        lines.append(f"{key}: {value}")
    return "\n".join(lines)


def _truncate_text(text: str, *, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n\n[truncated after {max_chars} characters]"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
