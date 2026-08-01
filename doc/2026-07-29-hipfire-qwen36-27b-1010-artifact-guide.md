# Hipfire Qwen3.6-27B 1010-Case Artifact Guide

**Artifact root:** `experiments/evals/v5_forward_eval/qwen36-27b-hipfire-local-full-1010/`

This guide describes the directory structure, file types, and contents of the
completed 1,010-case local Qwen3.6-27B evaluation run.

## Top-level layout

```
qwen36-27b-hipfire-local-full-1010/
├── evaluator.log                  # Full evaluator timeline (~31 MB)
├── server.log                     # Hipfire feature-daemon serving log
├── watchdog.log                   # Hourly health & result-count snapshots
├── manifest.txt                   # SHA-256 hashes of model, daemon, grammar, config
├── health.json                    # Server health endpoint snapshots
├── models.json                    # Endpoint configuration (port, model, limits)
├── episode-report.md              # Auto-generated run summary with failure analysis
├── launcher-resume-*.log          # Launcher output per resume session
├── evals/
│   └── hipfire_qwen36_27b_text2sql_1010/
│       ├── report.json            # Aggregate results: all 1010 cases with scores
│       ├── train/
│       │   └── web_scrape_hq/
│       │       └── <case_id>/     # 742 train case directories
│       ├── test/
│       │   └── web_scrape_hq/
│       │       └── <case_id>/     # 138 test case directories
│       └── (no val/ directory — val cases stored under train/)
```

Note: the validation cases (130) are stored under the `train/` split directory
in the eval tree. The `report.json` correctly assigns them to the `val` split.

## Per-case directory structure

Each of the 1,010 cases has its own directory under
`evals/hipfire_qwen36_27b_text2sql_1010/{split}/web_scrape_hq/{case_id}/`
containing:

```
<case_id>/
├── pf_res.output.json             # Final result: judge verdict + deterministic score
├── judge_loop_iterations.json     # Full transcript: all iterations (UP→SQL→RES→Judge)
├── result.generated.csv           # Actual SQL query result rows from ChEMBL
├── run.events.jsonl               # Sparse event timeline (case_start, iteration_done, ...)
├── run.log                        # Human-readable transcript with full prompts and responses
├── case_error.json                # Only present for the 4 failed cases
└── (no additional files for completed cases)
```

### File details

#### `pf_res.output.json`

The authoritative result file. Contains:

```json
{
  "case_id": "example_case",
  "status": "pass" | "partial" | "fail",
  "score": 0.7782,
  "result_success": true,
  "iterations": 1,
  "judge_decision": true,
  "judge_score": 1.0,
  "llm_provenance": {
    "sql_provider": { "provider": "llamacpp", "model": "qwen3.6:27b", "base_url": "..." },
    "judge_provider": { "provider": "llamacpp", "model": "qwen3.6:27b", "base_url": "..." }
  }
}
```

- `score`: deterministic score comparing generated CSV against gold standard
- `status`: `"pass"` if score = 1.0, `"partial"` if 0 < score < 1.0, `"fail"` if 0.0
- `judge_decision`: the final judge YES/NO
- `iterations`: how many UP→SQL→RES→J cycles were needed

#### `judge_loop_iterations.json`

A JSON array of iteration objects, one per judge-loop cycle. Each iteration
contains:

```json
{
  "n": 1,
  "up_text": "...",           // The UP writer's output
  "sql_text": "SELECT ...",   // The generated SQL
  "res_summary": {            // Query execution summary
    "row_count": 823,
    "columns": ["chembl_id", "pref_name", ...],
    "sample_rows": [...],
    "query_plan": "..."
  },
  "judge_decision": true,
  "judge_score": 1.0,
  "judge_text": "..."         // Judge's qualitative evaluation
}
```

This file provides the full reasoning trace for debugging and analysis. You
can see exactly what the model generated at each step and why the judge
accepted or rejected it.

#### `result.generated.csv`

The actual CSV output from running the generated SQL against the local ChEMBL
SQLite database. This is the raw query result, not compared against the gold
standard (the gold comparison happens in `pf_res.output.json`).

#### `run.events.jsonl`

Machine-readable event log, one JSON object per line:

```json
{"event": "case_start", "timestamp": "...", "ordinal": 42}
{"event": "iteration_done", "timestamp": "...", "iteration": 1, "judge_decision": true}
{"event": "case_complete", "timestamp": "...", "score": 0.85, "iterations": 2}
```

#### `run.log`

Full human-readable transcript. Includes:

- Case metadata (ordinal, split, case ID)
- The full System Prompt (SP) with SHA-256
- Each iteration's UP text, generated SQL, query execution details, sampled
  result rows, judge prompt, and judge response
- The final deterministic score and accepted iteration

This is the most verbose artifact — useful for deep debugging of individual
cases.

#### `case_error.json`

Only present for the 4 failed cases. Contains the error message and stack
trace.

## Aggregate report: `report.json`

The `report.json` file in the eval root contains the full aggregate across all
1,010 cases. Key sections:

### Summary

```json
{
  "summary": {
    "n_cases": 1010,
    "n_pass": 321,
    "pass_rate": 0.318,
    "mean_score": 0.7751,
    "n_incomplete": 0,
    "n_skipped_existing": 249
  }
}
```

### Per-split breakdown

```json
{
  "by_split": {
    "train": { "n_cases": 742, "n_pass": 237, "pass_rate": 0.319, "mean_score": 0.777 },
    "val":   { "n_cases": 130, "n_pass": 40,  "pass_rate": 0.308, "mean_score": 0.767 },
    "test":  { "n_cases": 138, "n_pass": 44,  "pass_rate": 0.319, "mean_score": 0.772 }
  }
}
```

### Per-case entries

The `cases` array contains one entry per case with:

- `case_id`, `split`, `corpus`, `family`
- `status` (pass/partial/fail), `score`, `result_success`
- `iterations`, `judge_decision`, `judge_score`
- `llm_provenance` (provider, model, base_url for SQL and judge)
- `ordinal` (1-based position in the eval order)
- `case_root` (absolute path to the per-case directory)

## Top-level logs

### `evaluator.log` (~31 MB)

Complete evaluator timeline. Contains every INFO/DEBUG log line from the
evaluation process, including per-case starts, iteration completions, provider
calls, and the final report generation.

Key entries to look for:
- `case_start` / `case_complete` lines for progress tracking
- `SP_FULL` for the system prompt hash
- `ITER_N > SQL_N` for generated SQL
- `JudgeResult` for judge decisions

### `server.log`

Hipfire feature-daemon log. Shows model loading, grammar compilation, request
handling, and thinking-budget behavior. Useful for diagnosing serving issues
(context limits, grammar rejections, timeout patterns).

### `watchdog.log`

Hourly snapshots from the cron watchdog:

```
[2026-07-27T22:07:01+01:00] healthy runner pid=3289557 results=723/1010
```

Shows the progression of the run over time and any pause/resume events.

### `manifest.txt`

SHA-256 hashes of the model weights, Hipfire daemon binary, grammar file, and
configuration. Essential for reproducibility — this uniquely identifies the
exact serving contract used for the run.

### `episode-report.md`

Auto-generated by the watchdog on completion. Contains:

- Configuration summary
- Final result counts
- Episode history (grammar fix, pauses, resume)
- Failure analysis
- Prevention notes for future runs

## How to inspect a case

Pick any case directory and read the three key files:

```bash
# The model's reasoning trace:
cat evals/hipfire_qwen36_27b_text2sql_1010/train/web_scrape_hq/<case_id>/judge_loop_iterations.json

# The judge verdict and deterministic score:
cat evals/hipfire_qwen36_27b_text2sql_1010/train/web_scrape_hq/<case_id>/pf_res.output.json

# The actual SQL output rows:
head -20 evals/hipfire_qwen36_27b_text2sql_1010/train/web_scrape_hq/<case_id>/result.generated.csv
```

## Total artifact size

~830 MB total:

- `evals/` per-case directories: ~710 MB
- `evaluator.log`: ~31 MB
- `server.log`: ~2 MB
- `watchdog.log`: small
- Other logs and manifests: small
