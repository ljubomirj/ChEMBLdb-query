from __future__ import annotations

import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "evaluate_v5_forward_judge_loop.py"

_SPEC = importlib.util.spec_from_file_location("evaluate_v5_forward_judge_loop", MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
judge_loop = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(judge_loop)


def test_completed_case_result_prefers_pf_res_over_stale_case_error(tmp_path: Path) -> None:
    case_root = tmp_path / "train" / "web_scrape_hq" / "example_case"
    case_root.mkdir(parents=True)
    (case_root / "case_error.json").write_text(
        json.dumps(
            {
                "case_id": "example_case",
                "split": "train",
                "corpus": "web_scrape_hq",
                "error_stage": "chain",
                "error": "old transient failure",
            }
        ),
        encoding="utf-8",
    )
    (case_root / "pf_res.output.json").write_text(
        json.dumps(
            {
                "case_id": "example_case",
                "split": "train",
                "corpus": "web_scrape_hq",
                "family": "target_lookup",
                "result": {"success": True},
                "deterministic_score": {"status": "pass", "score": 1.0},
                "llm_provenance": {
                    "sql_provider": {
                        "provider": "zai-anthropic",
                        "model": "glm-4.7",
                        "base_url": "https://api.z.ai/api/anthropic",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    (case_root / "judge_loop_iterations.json").write_text(
        json.dumps(
            [
                {"judge_decision": False, "judge_score": 0.2},
                {"judge_decision": True, "judge_score": 0.95},
            ]
        ),
        encoding="utf-8",
    )

    result = judge_loop._completed_case_result(case_root)

    assert result is not None
    assert result["status"] == "pass"
    assert result["score"] == 1.0
    assert result["judge_decision"] is True
    assert result["judge_score"] == 0.95
    assert result["iterations"] == 2
    assert result["llm_provenance"]["sql_provider"]["model"] == "glm-4.7"
    assert "error_stage" not in result


def test_aggregate_report_cases_counts_resolved_and_incomplete(tmp_path: Path) -> None:
    eval_root = tmp_path / "eval"
    success_root = eval_root / "train" / "web_scrape_hq" / "case_ok"
    success_root.mkdir(parents=True)
    (success_root / "pf_res.output.json").write_text(
        json.dumps(
            {
                "case_id": "case_ok",
                "split": "train",
                "corpus": "web_scrape_hq",
                "result": {"success": True},
                "deterministic_score": {"status": "pass", "score": 1.0},
            }
        ),
        encoding="utf-8",
    )

    error_root = eval_root / "train" / "faq_hq" / "case_fail"
    error_root.mkdir(parents=True)
    (error_root / "case_error.json").write_text(
        json.dumps(
            {
                "case_id": "case_fail",
                "split": "train",
                "corpus": "faq_hq",
                "error_stage": "chain",
                "error": "boom",
            }
        ),
        encoding="utf-8",
    )

    case_items = [
        ("train", "web_scrape_hq", "case_ok"),
        ("train", "faq_hq", "case_fail"),
        ("val", "web_scrape_hq", "case_pending"),
    ]

    results, split_stats, incomplete_cases = judge_loop._aggregate_report_cases(
        eval_root=eval_root,
        case_items=case_items,
        selected_splits=["train", "val"],
    )

    assert [row["case_id"] for row in results] == ["case_ok", "case_fail"]
    assert [row["ordinal"] for row in results] == [1, 2]
    assert incomplete_cases == [
        {
            "ordinal": 3,
            "case_id": "case_pending",
            "split": "val",
            "corpus": "web_scrape_hq",
            "case_root": str((eval_root / "val" / "web_scrape_hq" / "case_pending").resolve()),
        }
    ]
    assert split_stats["train"] == {
        "n_target_cases": 2,
        "n_cases": 2,
        "n_pass": 1,
        "n_incomplete": 0,
        "mean_score": 0.5,
        "pass_rate": 0.5,
    }
    assert split_stats["val"] == {
        "n_target_cases": 1,
        "n_cases": 0,
        "n_pass": 0,
        "n_incomplete": 1,
        "mean_score": 0.0,
        "pass_rate": 0.0,
    }
