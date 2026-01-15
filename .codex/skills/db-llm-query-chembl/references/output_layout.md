# Output Layout

## Final CSV

When `-f csv` is used:

- Default filename: `query_results_<run_label>.csv`
- Override with `--output-file <path>`
- If `--run-label` is not set, a timestamp is used

When `--auto` is used:

- Auto-save filename: `query_results_<run_label>.csv` (or `--output-file`)

## Intermediate CSVs (default on)

Per-iteration CSVs are saved to:

`logs/intermediate/query_results_<run_label>_iter<N>.csv`

Disable with `--no-save-intermediate`.

## Logging

Recommended pattern:

`|& tee logs/db_llm_<run_label>.log`
