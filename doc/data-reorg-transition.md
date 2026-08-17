# ChEMBLdb-query Data Re-organization — Transition Record

**Plan:** `doc/2026-07-31-data-reorg-plan.md` (kept verbatim as the original)
**Executed:** 2026-08-04, gigul2 (git-private)
**Status:** COMPLETE — all phases done, verified, committed

## 1. Vocabulary (decided, in force)

| Term | Meaning here | Location |
|---|---|---|
| **case** | a collection of tasks about one query (UQ → SQL → RES, plus the judge task) | `cases/v5.1010/cases/<case_id>/` |
| **task** | a single challenge within a case: UQ, UP, SQL, RES, judge | `cases/<case_id>/tasks/` (aliases) + `provenance/original/` (verbatim) |
| **corpus / registry** | collection of cases (smevals *eval*) | `cases/registries/` (+ `archive/`) |
| **split** | train/val/test partition — part of the eval definition | `cases/v5.1010/splits/` |
| **config** | model + prompt pack + provider (+ params) | `configs/` |
| **run** | one config executed over one eval (config × case) | `runs/<run-name>/` |
| **grader** | judges the judge; grades all tasks incl. the judge task | `report.json` (grade) |
| **deterministic scorer** | smevals *checks/checkers* | `report.json` score field |

Notes from LJ:
- The judge is itself a **task** in a case; a second model acting as judge-of-judge is the **grader**.
- We keep our existing word **case** (a collection of tasks), not smevals' *task* as top unit.

## 2. Execution mode

**Symlink bridge** (LJ's choice): every moved path kept a relative symlink at its old
location until the code path-fix pass was verified; bridges were then removed.
Fixture move was byte-for-byte (`git mv` / `os.rename` on same filesystem).

Bridges removed: 2,018 fixture/manifest + 34 registry + 41 `fixtures_1010_overrides` = **2,093**.
Final state: **0 symlinks** in old paths, **0 code/doc references** to `tests/cases/`.

## 3. What moved (final layout)

| Old | New | Count |
|---|---|---|
| `tests/cases/*.json` (34 registries) | `cases/registries/` + `archive/` | 34 |
| `tests/v5_manifests_1010/web_scrape_hq/<id>.json` | `cases/v5.1010/cases/<id>/manifest.json` | 1,010 |
| `tests/fixtures/<wave>/<case>/` | `cases/v5.1010/cases/<id>/provenance/original/<wave>--<case>/` | ~10K files |
| `experiments/case_splits_v5.1010*.json` | `cases/v5.1010/splits/` | 8 |
| `experiments/prompt_pack_v*.yaml` | `configs/prompt_packs/` | 24 |
| `experiments/evals/v5_forward_eval/` | `runs/` (88 dirs hoisted, one level) | 88 dirs / 96,643 files |
| top-level `query_results*.csv` | `cases/archive/query_results_v1-3/` | 33 |

New: `configs/qwen36-27b-hipfire-local.yaml` — named config (model, pack, provider, params)
captured from run provenance.

## 4. Code changes

- `src/db_llm_v5/io.py` — added `resolve_case_manifest_path(manifest_root, corpus, case_id)`:
  resolves the new flat layout (`<root>/<safe_id>/manifest.json`, safe_id = case_id with `/`→`__`),
  falls back to legacy `<root>/<corpus>/<case_id>.json`.
- `scripts/evaluate_v5_forward_judge_loop.py` — defaults → new paths; 3 manifest-path sites use the resolver.
- `scripts/evaluate_v5_forward.py` — `DEFAULT_EVAL_ROOT` → `runs/`.
- `scripts/run_v5_1010_gepa_pipeline.sh`, `build_v5_1010_dataset.py`, `build_v5_1010_gepa_probe_split.py`,
  `repair_v5_1010_surfaces.py` — splits/manifest/registry paths updated.
- `src/db_llm_query_v4.py`, `src/db_llm_runtime_v5.py` + 4 generators — prompt-pack path → `configs/prompt_packs/`.
- 26 scripts + 15 tests/docs — registry refs `tests/cases/…` → `cases/registries/…` (canonical `web_scrape_hq_cases_v5.1010.json` stays in `cases/registries/`; all other registries in `archive/`).
- Docs: `README.md`, `doc/v5_design.md`, artifact guide (with reorg note).

## 5. Issues hit and resolved

1. **Nested case IDs (2 cases)** — case IDs containing `/` (`dapagliflozin_sodium/glucose_cotransporter_2_ic50_salts`,
   `(+/_)_tylophorine_raw264.7_ic50_salts`) had *nested* fixture dirs; the migration script treated the shared
   parent as one case's dir, leaving the sibling with a broken symlink. Repaired by moving each nested subdir to
   its own case's `provenance/original/`. Final: **7,007 artifact refs, 0 missing**.
2. **`runs/` tree missing from commit `60007b8d4`** — the phase-5 move deleted the 88 run dirs from
   `experiments/evals/v5_forward_eval/` but the follow-up `git add` did not cover `runs/`, so 96,643 files
   were absent from the committed tree (safe on disk). Recovered by staging `runs/` in `206c81003`.
3. **`git status` unreliable at 11K staged renames** — rename detection makes short-format status misleading;
   use `git diff --cached --name-only` for accurate counts.
4. **Registry archive location** — Phase 1 archived *all* registries except the canonical `web_scrape_hq_cases_v5.1010.json`; path rewrites had to point everything else at `archive/`.

## 6. Verification

- 7,007 manifest artifact refs resolve (0 missing) — via resolver, flat + nested cases
- 0 broken bridge symlinks during migration; 0 symlinks after removal
- pytest: 10 passed, 995 skipped, **1 pre-existing failure** (`test_local_responses_api_disables_llama_cpp_thinking` — expects `/v1/responses`, runtime moved to `/v1/chat/completions`; unrelated to reorg)
- End-to-end smoke: judge-loop runner loaded a case via new split → resolver → manifest → artifacts → LLM (live Hipfire), produced run tree under `runs/`
- All touched scripts compile

## 7. Commits

| Commit | Content |
|---|---|
| `ec7659384` | baseline before reorg |
| `568b5608d` | Phase 1: registries → `cases/registries/` (+ symlink bridge) |
| `60007b8d4` | Phases 2–6: `cases/`, `configs/`, code fixes, docs |
| `206c81003` | `runs/` tree + bridge-removal path fixes |

## 8. Follow-ups

- [ ] macbook2 must pull; old layout paths on macbook2 are stale until then
- [ ] Fix `test_local_responses_api_disables_llama_cpp_thinking` (provider test, pre-existing)
- [ ] Delete `doc/2026-07-31-data-reorg-plan.md` once this record is accepted
- [ ] Future run names follow `{eval}-{config}-{scope}-{YYYYMMDD_HHMMSS}` (e.g. `v5.1010-qwen36-27b-hipfire-local-full-20260719_231825`)
