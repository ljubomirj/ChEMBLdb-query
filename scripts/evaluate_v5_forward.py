#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from compressed_io import read_text_maybe_compressed
from db_llm_v5.forward import run_pf_judge, run_pf_sql, run_pf_up, run_res
from db_llm_v5.io import load_case_manifest, load_prompt_pack
from db_llm_v5.provider import EndpointConfig, build_provider, resolve_profile, write_json
from db_llm_v5.workspace import persist_generated_step

DEFAULT_SPLIT = REPO_ROOT / "experiments" / "case_splits_v4.7.json"
DEFAULT_MANIFEST_ROOT = REPO_ROOT / "tests" / "v5_manifests"
DEFAULT_EVAL_ROOT = REPO_ROOT / "runs"


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the v5 forward chain over a split of migrated case manifests.")
    parser.add_argument("--prompt-pack", default=str(REPO_ROOT / "experiments" / "prompt_pack_v5.0.yaml"))
    parser.add_argument("--split-file", default=str(DEFAULT_SPLIT))
    parser.add_argument("--split", action="append", choices=["train", "val", "test"], help="Split(s) to evaluate; default all")
    parser.add_argument("--manifest-root", default=str(DEFAULT_MANIFEST_ROOT))
    parser.add_argument("--eval-root", default=str(DEFAULT_EVAL_ROOT))
    parser.add_argument("--eval-label", default=None)
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
    parser.add_argument("--with-judge", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--skip-existing", action="store_true", help="Reuse complete per-case artifacts already present under the eval label.")
    parser.add_argument("--print-summary", action="store_true")
    args = parser.parse_args()

    prompt_pack = load_prompt_pack(args.prompt_pack)
    endpoint, fallback = _resolve_endpoint_args(args)
    provider = build_provider(endpoint=endpoint, fallback=fallback)
    split_payload = json.loads(read_text_maybe_compressed(Path(args.split_file)))
    selected_splits = args.split or ["train", "val", "test"]
    eval_label = args.eval_label or Path(args.prompt_pack).stem
    eval_root = Path(args.eval_root) / eval_label
    eval_root.mkdir(parents=True, exist_ok=True)

    case_items = []
    for split_name in selected_splits:
        for item in split_payload["splits"][split_name]:
            case_items.append((split_name, str(item["corpus"]), str(item["id"])))
    if args.limit is not None:
        case_items = case_items[: args.limit]

    results: list[dict[str, Any]] = []
    split_stats: dict[str, dict[str, float | int]] = {s: {"n_cases": 0, "n_pass": 0, "mean_score": 0.0} for s in selected_splits}
    n_skipped_existing = 0

    total_cases = len(case_items)
    for case_index, (split_name, corpus, case_id) in enumerate(case_items, start=1):
        manifest_path = Path(args.manifest_root) / corpus / f"{case_id}.json"
        case_root = eval_root / split_name / corpus / case_id
        case_root.mkdir(parents=True, exist_ok=True)
        if args.skip_existing:
            existing_result = _completed_case_result(case_root, with_judge=args.with_judge)
            if existing_result is not None:
                if not (case_root / "run.log").exists() or not (case_root / "run.events.jsonl").exists():
                    _start_case_logs(case_root)
                _append_case_event(
                    case_root,
                    "case_reused_existing",
                    status=existing_result.get("status"),
                    score=existing_result.get("score"),
                    result_success=existing_result.get("result_success"),
                    judge_decision=existing_result.get("judge_decision"),
                )
                _append_transcript(
                    case_root,
                    "Case Reused Existing",
                    _format_key_values(
                        {
                            "status": existing_result.get("status"),
                            "score": existing_result.get("score"),
                            "result_success": existing_result.get("result_success"),
                            "judge_decision": existing_result.get("judge_decision"),
                        }
                    ),
                )
                existing_result["resumed_from_existing"] = True
                results.append(existing_result)
                split_stats[split_name]["n_cases"] += 1
                split_stats[split_name]["n_pass"] += 1 if existing_result["status"] == "pass" else 0
                split_stats[split_name]["mean_score"] += float(existing_result["score"])
                n_skipped_existing += 1
                continue
        _start_case_logs(case_root)
        _append_case_event(
            case_root,
            "case_start",
            case_id=case_id,
            split=split_name,
            corpus=corpus,
            prompt_pack_path=str(Path(args.prompt_pack).resolve()),
            prompt_pack_version=prompt_pack.version,
            case_manifest_path=str(manifest_path.resolve()),
            ordinal=case_index,
            total_cases=total_cases,
        )
        manifest = None
        try:
            manifest = load_case_manifest(manifest_path)
        except Exception as exc:
            error_text = str(exc)
            _append_transcript(
                case_root,
                "Case Start",
                _format_key_values(
                    {
                        "case": f"{case_index} / {total_cases}",
                        "case_id": case_id,
                        "split": split_name,
                        "corpus": corpus,
                        "manifest_path": str(manifest_path.resolve()),
                        "prompt_pack_path": str(Path(args.prompt_pack).resolve()),
                        "prompt_pack_version": prompt_pack.version,
                    }
                ),
            )
            _append_case_event(
                case_root,
                "case_error",
                error_stage="manifest",
                error=error_text,
            )
            write_json(
                case_root / "case_error.json",
                {
                    "case_id": case_id,
                    "split": split_name,
                    "corpus": corpus,
                    "case_manifest_path": str(manifest_path.resolve()),
                    "error_stage": "manifest",
                    "error": error_text,
                },
            )
            results.append(
                {
                    "case_id": case_id,
                    "split": split_name,
                    "corpus": corpus,
                    "family": None,
                    "status": "fail",
                    "score": 0.0,
                    "result_success": False,
                    "judge_decision": None,
                    "case_root": str(case_root.resolve()),
                    "error_stage": "manifest",
                    "error": error_text,
                }
            )
            split_stats[split_name]["n_cases"] += 1
            continue

        base = {
            "prompt_pack_path": str(Path(args.prompt_pack).resolve()),
            "prompt_pack_version": prompt_pack.version,
            "case_manifest_path": str(manifest_path.resolve()),
            "case_id": manifest.case_id,
            "split": split_name,
            "corpus": corpus,
            "family": manifest.metadata.family,
        }
        status = "fail"
        score = 0.0
        result_success = False
        judge_decision = None
        llm_provenance: dict[str, dict[str, Any]] = {}
        error_stage = None
        error_text = None
        try:
            _append_transcript(
                case_root,
                "Case Start",
                _render_case_intro(
                    manifest=manifest,
                    manifest_path=manifest_path,
                    prompt_pack=prompt_pack,
                    prompt_pack_path=Path(args.prompt_pack),
                    split_name=split_name,
                    corpus=corpus,
                    ordinal=case_index,
                    total_cases=total_cases,
                ),
            )
            _append_case_event(
                case_root,
                "step_start",
                step="pf_up",
                max_tokens=int(args.up_max_tokens),
                temperature=float(args.temperature),
            )
            _append_transcript(
                case_root,
                "PF_UP Request",
                _render_pf_up_request(prompt_pack=prompt_pack, manifest=manifest),
            )
            pf_up = run_pf_up(prompt_pack=prompt_pack, manifest=manifest, repo_root=REPO_ROOT, provider=provider, max_tokens=args.up_max_tokens, temperature=args.temperature)
            pf_up_payload = {**base, "selected_step": "up", **pf_up}
            llm_provenance["pf_up"] = _execution_provenance(pf_up_payload)
            pf_up_written = persist_generated_step(repo_root=REPO_ROOT, run_root=eval_root / split_name / corpus, manifest=manifest, source_manifest_path=manifest_path, prompt_pack_path=Path(args.prompt_pack), step="pf_up", payload=pf_up_payload)
            if "up_exec" not in pf_up_written:
                raise ValueError("PF_UP produced no up_exec artifact")
            up_exec_text = read_text_maybe_compressed(REPO_ROOT / pf_up_written["up_exec"]).strip()
            _append_case_event(
                case_root,
                "step_done",
                step="pf_up",
                provenance=llm_provenance["pf_up"],
                written_paths=pf_up_written,
                up_exec_path=pf_up_written.get("up_exec"),
                up_exec_chars=len(up_exec_text),
            )
            _append_transcript(
                case_root,
                "PF_UP Response",
                _render_llm_step_response(
                    payload=pf_up_payload,
                    parsed_key="up",
                    artifact_label="up_exec.generated.txt",
                    artifact_text=up_exec_text,
                    written_paths=pf_up_written,
                ),
            )

            _append_case_event(
                case_root,
                "step_start",
                step="pf_sql",
                max_tokens=int(args.sql_max_tokens),
                temperature=float(args.temperature),
            )
            _append_transcript(
                case_root,
                "PF_SQL Request",
                _render_pf_sql_request(prompt_pack=prompt_pack, up_exec_text=up_exec_text),
            )
            pf_sql = run_pf_sql(prompt_pack=prompt_pack, manifest=manifest, repo_root=REPO_ROOT, provider=provider, up_exec_text=up_exec_text, max_tokens=args.sql_max_tokens, temperature=args.temperature)
            pf_sql_payload = {**base, "selected_step": "sql", **pf_sql}
            llm_provenance["pf_sql"] = _execution_provenance(pf_sql_payload)
            pf_sql_written = persist_generated_step(repo_root=REPO_ROOT, run_root=eval_root / split_name / corpus, manifest=manifest, source_manifest_path=manifest_path, prompt_pack_path=Path(args.prompt_pack), step="pf_sql", payload=pf_sql_payload)
            if "sql" not in pf_sql_written:
                raise ValueError("PF_SQL produced no sql artifact")
            sql_text = read_text_maybe_compressed(REPO_ROOT / pf_sql_written["sql"]).strip()
            _append_case_event(
                case_root,
                "step_done",
                step="pf_sql",
                provenance=llm_provenance["pf_sql"],
                written_paths=pf_sql_written,
                sql_path=pf_sql_written.get("sql"),
                sql_chars=len(sql_text),
            )
            _append_transcript(
                case_root,
                "PF_SQL Response",
                _render_llm_step_response(
                    payload=pf_sql_payload,
                    parsed_key="sql",
                    artifact_label="sql.generated.sql",
                    artifact_text=sql_text,
                    written_paths=pf_sql_written,
                ),
            )

            result_path = case_root / "result.generated.csv"
            _append_case_event(
                case_root,
                "step_start",
                step="pf_res",
                sql_path=pf_sql_written.get("sql"),
                result_path=str(result_path.resolve()),
            )
            _append_transcript(
                case_root,
                "PF_RES Request",
                _render_pf_res_request(sql_text=sql_text, result_path=result_path),
            )
            pf_res = run_res(manifest=manifest, repo_root=REPO_ROOT, sql_text=sql_text, result_path=result_path)
            pf_res_payload = {**base, "selected_step": "res", **pf_res}
            pf_res_written = persist_generated_step(repo_root=REPO_ROOT, run_root=eval_root / split_name / corpus, manifest=manifest, source_manifest_path=manifest_path, prompt_pack_path=Path(args.prompt_pack), step="pf_res", payload=pf_res_payload)
            pf_res_written["result_path"] = str(result_path.resolve().relative_to(REPO_ROOT.resolve()))
            pf_res_payload["written_paths"] = pf_res_written
            write_json(case_root / "pf_res.output.json", pf_res_payload)
            _append_case_event(
                case_root,
                "step_done",
                step="pf_res",
                written_paths=pf_res_written,
                result=pf_res_payload.get("result"),
                deterministic_score=pf_res_payload.get("deterministic_score"),
            )
            _append_transcript(
                case_root,
                "PF_RES Result",
                _render_pf_res_response(
                    payload=pf_res_payload,
                    result_path=result_path,
                    written_paths=pf_res_written,
                ),
            )

            judge_payload = None
            if args.with_judge and pf_res_payload["result"]["success"]:
                _append_case_event(
                    case_root,
                    "step_start",
                    step="pf_judge",
                    max_tokens=int(args.judge_max_tokens),
                    temperature=float(args.temperature),
                )
                _append_transcript(
                    case_root,
                    "PF_JUDGE Request",
                    _render_pf_judge_request(
                        prompt_pack=prompt_pack,
                        up_exec_text=up_exec_text,
                        sql_text=sql_text,
                        result_path=result_path,
                    ),
                )
                pf_judge = run_pf_judge(prompt_pack=prompt_pack, manifest=manifest, repo_root=REPO_ROOT, provider=provider, up_exec_text=up_exec_text, sql_text=sql_text, result_path=result_path, max_tokens=args.judge_max_tokens, temperature=args.temperature)
                judge_payload = {**base, "selected_step": "judge", **pf_judge}
                llm_provenance["pf_judge"] = _execution_provenance(judge_payload)
                pf_judge_written = persist_generated_step(repo_root=REPO_ROOT, run_root=eval_root / split_name / corpus, manifest=manifest, source_manifest_path=manifest_path, prompt_pack_path=Path(args.prompt_pack), step="pf_judge", payload=judge_payload)
                judge_payload["written_paths"] = pf_judge_written
                write_json(case_root / "pf_judge.output.json", judge_payload)
                _append_case_event(
                    case_root,
                    "step_done",
                    step="pf_judge",
                    provenance=llm_provenance["pf_judge"],
                    written_paths=pf_judge_written,
                    judge_decision=judge_payload.get("execution", {}).get("parsed_json", {}).get("decision"),
                    judge_score=judge_payload.get("execution", {}).get("parsed_json", {}).get("score"),
                )
                _append_transcript(
                    case_root,
                    "PF_JUDGE Response",
                    _render_llm_step_response(
                        payload=judge_payload,
                        parsed_key=None,
                        artifact_label="pf_judge.output.json",
                        artifact_text=json.dumps(judge_payload.get("execution", {}).get("parsed_json"), indent=2, ensure_ascii=False),
                        written_paths=pf_judge_written,
                    ),
                )

            det = pf_res_payload.get("deterministic_score") or {}
            status = str(det.get("status", "fail"))
            score = float(det.get("score", 0.0)) if det else 0.0
            result_success = bool(pf_res_payload["result"]["success"])
            judge_decision = judge_payload.get("execution", {}).get("parsed_json", {}).get("decision") if judge_payload else None
            _append_case_event(
                case_root,
                "case_complete",
                status=status,
                score=score,
                result_success=result_success,
                judge_decision=judge_decision,
            )
            _append_transcript(
                case_root,
                "Case Complete",
                _format_key_values(
                    {
                        "status": status,
                        "score": score,
                        "result_success": result_success,
                        "judge_decision": judge_decision,
                    }
                ),
            )
        except Exception as exc:
            error_stage = "chain"
            error_text = str(exc)
            _append_case_event(
                case_root,
                "case_error",
                error_stage=error_stage,
                error=error_text,
            )
            _append_transcript(
                case_root,
                "Case Error",
                _format_key_values({"error_stage": error_stage, "error": error_text}),
            )
            write_json(case_root / "case_error.json", {**base, "error_stage": error_stage, "error": error_text})

        passed = status == "pass"
        result_row = {
            "case_id": case_id,
            "split": split_name,
            "corpus": corpus,
            "family": manifest.metadata.family,
            "status": status,
            "score": score,
            "result_success": result_success,
            "judge_decision": judge_decision,
            "case_root": str(case_root.resolve()),
        }
        if llm_provenance:
            result_row["llm_provenance"] = llm_provenance
        if error_text:
            result_row["error_stage"] = error_stage
            result_row["error"] = error_text
        results.append(result_row)
        split_stats[split_name]["n_cases"] += 1
        split_stats[split_name]["n_pass"] += 1 if passed else 0
        split_stats[split_name]["mean_score"] += score

    for split_name, stat in split_stats.items():
        n_cases = int(stat["n_cases"])
        stat["mean_score"] = round(float(stat["mean_score"]) / n_cases, 6) if n_cases else 0.0
        stat["pass_rate"] = round(int(stat["n_pass"]) / n_cases, 6) if n_cases else 0.0

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
            "n_skipped_existing": n_skipped_existing,
        },
        "by_split": split_stats,
        "cases": results,
    }
    report_path = eval_root / "report.json"
    write_json(report_path, report)
    if args.print_summary:
        print(json.dumps({"report_path": str(report_path.resolve()), "summary": report["summary"]}, indent=2))
    else:
        print(json.dumps({"report_path": str(report_path.resolve()), "summary": report["summary"]}))


def _resolve_endpoint_args(args: argparse.Namespace) -> tuple[EndpointConfig, EndpointConfig | None]:
    endpoint = None
    fallback = None
    if args.multi_endpoint_profile:
        endpoint, fallback = resolve_profile(args.multi_endpoint_profile)
    if endpoint is None:
        if not args.provider or not args.model:
            raise ValueError("Either --multi-endpoint-profile or both --provider and --model are required")
        endpoint = EndpointConfig(provider=args.provider, model=args.model, base_url=args.provider_base_url, temperature=args.temperature, timeout=args.timeout)
    if args.quota_fallback_provider:
        fallback = EndpointConfig(provider=args.quota_fallback_provider, model=args.quota_fallback_model or "", base_url=args.quota_fallback_base_url, temperature=args.temperature, timeout=args.timeout)
    return endpoint, fallback


def _completed_case_result(case_root: Path, *, with_judge: bool) -> dict[str, Any] | None:
    case_error_path = case_root / "case_error.json"
    if case_error_path.exists():
        try:
            case_error = json.loads(case_error_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
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
            "case_root": str(case_root.resolve()),
            "error_stage": case_error.get("error_stage"),
            "error": case_error.get("error"),
        }

    pf_res_path = case_root / "pf_res.output.json"
    if not pf_res_path.exists():
        return None
    try:
        pf_res_payload = json.loads(pf_res_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    result = pf_res_payload.get("result") or {}
    result_success = bool(result.get("success"))
    judge_payload = None
    if with_judge and result_success:
        pf_judge_path = case_root / "pf_judge.output.json"
        if not pf_judge_path.exists():
            return None
        try:
            judge_payload = json.loads(pf_judge_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    det = pf_res_payload.get("deterministic_score") or {}
    status = str(det.get("status", "fail"))
    score = float(det.get("score", 0.0)) if det else 0.0
    judge_decision = (
        judge_payload.get("execution", {}).get("parsed_json", {}).get("decision")
        if judge_payload
        else None
    )
    result_row: dict[str, Any] = {
        "case_id": pf_res_payload.get("case_id"),
        "split": pf_res_payload.get("split"),
        "corpus": pf_res_payload.get("corpus"),
        "family": pf_res_payload.get("family"),
        "status": status,
        "score": score,
        "result_success": result_success,
        "judge_decision": judge_decision,
        "case_root": str(case_root.resolve()),
    }
    llm_provenance: dict[str, dict[str, Any]] = {}
    for step in ("pf_up", "pf_sql", "pf_judge"):
        step_path = case_root / f"{step}.output.json"
        if not step_path.exists():
            continue
        try:
            step_payload = json.loads(step_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        provenance = _execution_provenance(step_payload)
        if provenance:
            llm_provenance[step] = provenance
    if llm_provenance:
        result_row["llm_provenance"] = llm_provenance
    return result_row


def _execution_provenance(payload: dict[str, Any]) -> dict[str, Any]:
    execution = payload.get("execution")
    if not isinstance(execution, dict):
        return {}
    provenance = execution.get("provenance")
    if isinstance(provenance, dict):
        return {key: value for key, value in provenance.items() if value is not None}
    keys = ("provider", "model_id", "model", "responses_model_id", "dspy_model_id", "base_url")
    return {key: execution.get(key) for key in keys if execution.get(key) is not None}


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


def _render_case_intro(
    *,
    manifest: Any,
    manifest_path: Path,
    prompt_pack: Any,
    prompt_pack_path: Path,
    split_name: str,
    corpus: str,
    ordinal: int | None = None,
    total_cases: int | None = None,
) -> str:
    artifacts = manifest.artifacts
    case_progress = f"{ordinal} / {total_cases}" if ordinal is not None and total_cases is not None else None
    lines = [
        _format_key_values(
            {
                "case": case_progress,
                "case_id": manifest.case_id,
                "split": split_name,
                "corpus": corpus,
                "family": manifest.metadata.family,
                "manifest_path": str(manifest_path.resolve()),
                "prompt_pack_path": str(prompt_pack_path.resolve()),
                "prompt_pack_version": prompt_pack.version,
                "db_path": manifest.db_path,
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
        _render_text_block("Examples block", prompt_pack.system.examples_block),
    ]
    return "\n\n".join(part for part in lines if part.strip())


def _render_pf_up_request(*, prompt_pack: Any, manifest: Any) -> str:
    return "\n\n".join(
        [
            _render_text_block("Task prompt", prompt_pack.pf.up),
            _render_file_block("User question input", manifest.artifacts.uq_surface),
        ]
    )


def _render_pf_sql_request(*, prompt_pack: Any, up_exec_text: str) -> str:
    return "\n\n".join(
        [
            _render_text_block("Task prompt", prompt_pack.pf.sql),
            _render_text_block("UP input", up_exec_text),
        ]
    )


def _render_pf_res_request(*, sql_text: str, result_path: Path) -> str:
    return "\n\n".join(
        [
            _render_text_block("SQL to execute", sql_text),
            _format_key_values({"result_path": str(result_path.resolve())}),
        ]
    )


def _render_pf_judge_request(*, prompt_pack: Any, up_exec_text: str, sql_text: str, result_path: Path) -> str:
    return "\n\n".join(
        [
            _render_text_block("Task prompt", prompt_pack.pf.judge),
            _render_text_block("UP input", up_exec_text),
            _render_text_block("SQL input", sql_text),
            _render_csv_preview(result_path, max_rows=20),
        ]
    )


def _render_llm_step_response(
    *,
    payload: dict[str, Any],
    parsed_key: str | None,
    artifact_label: str,
    artifact_text: str,
    written_paths: dict[str, Any],
) -> str:
    execution = payload.get("execution") or {}
    parsed = execution.get("parsed_json")
    parsed_text = ""
    if isinstance(parsed, dict):
        if parsed_key and parsed_key in parsed:
            parsed_text = str(parsed[parsed_key])
        else:
            parsed_text = json.dumps(parsed, indent=2, ensure_ascii=False)
    return "\n\n".join(
        [
            _format_key_values(_execution_provenance(payload)),
            _render_text_block("Raw model response", str(execution.get("raw_text") or "")),
            _render_text_block(f"Parsed artifact ({artifact_label})", artifact_text or parsed_text),
            _format_key_values({"written_paths": json.dumps(written_paths, indent=2, ensure_ascii=False)}),
        ]
    )


def _render_pf_res_response(*, payload: dict[str, Any], result_path: Path, written_paths: dict[str, Any]) -> str:
    return "\n\n".join(
        [
            _render_text_block("Execution result", json.dumps(payload.get("result"), indent=2, ensure_ascii=False)),
            _render_text_block("Deterministic score", json.dumps(payload.get("deterministic_score"), indent=2, ensure_ascii=False)),
            _render_csv_preview(result_path, max_rows=20),
            _format_key_values({"written_paths": json.dumps(written_paths, indent=2, ensure_ascii=False)}),
        ]
    )


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
    omitted_note = "Preview includes header plus first rows only; see full CSV at path above."
    return "\n".join(
        [
            _format_key_values({"csv_path": str(path.resolve()), "csv_preview_rows": len(rows)}),
            _render_text_block("CSV preview", "\n".join(rendered_rows)),
            omitted_note,
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
    main()
