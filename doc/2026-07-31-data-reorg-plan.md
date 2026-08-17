# ChEMBLdb-query Data Re-organization Plan

**Date:** 2026-07-31  
**Status:** Plan — execution in progress (Phase 0/1)  
**Vocabulary:** aligned with [smevals](https://simonwillison.net/2026/Jul/31/smevals/) (evals/tasks/configs/runs/grades), adapted to our existing terms

## 1. Vocabulary (decided)

| Term | Meaning here | Path role |
|---|---|---|
| **case** | a collection of tasks about one query (UQ → SQL → RES, plus the judge task) | `cases/<case_id>/` |
| **task** | a single challenge within a case: UQ, UP, SQL, RES, judge | `cases/<case_id>/tasks/*` |
| **corpus / registry** | collection of cases (smevals *eval*) | `cases/registries/*.json` |
| **split** | train/val/test partition — part of the eval definition | `cases/<eval>/splits/*.json` |
| **config** | model + prompt pack + provider (+ params) | `configs/*.yaml` |
| **run** | one config executed over one eval (config × case) | `runs/<run-id>/` |
| **grader** | judges the judge; grades all tasks incl. the judge task | `report.json` (grade) |
| **deterministic scorer** | smevals *checks/checkers* | `report.json` score field |

Notes from LJ:
- The judge is itself a **task** in a case; a second model acting as judge-of-judge is the **grader**.
- We keep our existing word **case** (a collection of tasks), not smevals' *task* as top unit.

## 2. Current state (measured)

| Thing | Today | Size |
|---|---|---|
| Case manifests (1010) | `tests/v5_manifests_1010/web_scrape_hq/<case_id>.json` | 4.1 MB |
| Case fixtures (gold SQL/CSV, UQ text, provenance) | `tests/fixtures/<wave>/<case_id>/` | 1.3 GB |
| Registries (34 files) | `tests/cases/*.json` (incl. `web_scrape_hq_cases_v5.1010.json`) | 24 MB |
| Splits (8 for 1010) | `experiments/case_splits_v5.1010*.json` | small |
| Runs (88) | `experiments/evals/v5_forward_eval/<run>/` | 1.4 GB |
| Logs | `logs/` | 2.0 GB |
| Prompt packs (configs) | `experiments/prompt_pack_v*.yaml` | small |
| Stray v1–v3 CSVs | top-level `query_results*.csv` (33 files) | — |

**Code reference counts** (the real cost of moving; measured excluding data files that contain their own paths):
- `v5_forward_eval`: 5 code files
- `v5_manifests_1010`: 5 code files
- `case_splits_v5.1010`: 4 code files
- `web_scrape_hq_cases_v5.1010`: 1 code file
- `tests/fixtures`: 21 code files

**Fixture dir contents** (what must be preserved byte-for-byte in the move):
`uq.txt`, `up_exec.txt`, `sqlite.sql`, `source.sql`, `ground-truth.csv.zst`, `benchmark_spec_uq.txt`, `documentation.txt`, `metadata.json`, `pb_sql.output.json`, `pb_up.output.json` — i.e. task artifacts **and** provenance/model-output files. Every file moves as-is; the `tasks/` tree holds the canonical task artifacts, `provenance/` holds the rest.

## 3. Target layout

```
ChEMBLdb-query/
├── cases/                        # the eval definition (source of truth, git-private)
│   ├── registries/
│   │   ├── web_scrape_hq_cases_v5.1010.json   # canonical, 1010 cases
│   │   └── archive/              # old wave registries (web_scrape10.., v4.x)
│   ├── v5.1010/                  # one dir per eval
│   │   ├── splits/
│   │   │   ├── v5.1010.json      # train/val/test
│   │   │   ├── v5.1010_gepa_probe.json
│   │   │   └── ... (all 8)
│   │   └── cases/
│   │       └── <case_id>/
│   │           ├── manifest.json
│   │           ├── tasks/                    # canonical task artifacts (aliases where names differ)
│   │           │   ├── uq_surface.txt
│   │           │   ├── up_exec.txt
│   │           │   ├── sql_gold.sql
│   │           │   ├── res_gold.csv.zst
│   │           │   ├── benchmark_spec_uq.txt
│   │           │   └── judge_gold.json       # gold judge verdict (where present)
│   │           └── provenance/               # every original fixture file, byte-for-byte
│   │               ├── original/             # the whole <wave>/<case_id>/ dir, verbatim
│   │               │   ├── uq.txt
│   │               │   ├── sqlite.sql
│   │               │   ├── source.sql
│   │               │   ├── documentation.txt
│   │               │   ├── metadata.json
│   │               │   ├── pb_sql.output.json
│   │               │   └── pb_up.output.json
│   │               └── (task files referenced by manifest point here or to tasks/)
├── configs/                      # config = model + prompt pack + provider
│   ├── prompt_packs/             # v5.0.yaml ... v5.10.yaml (moved from experiments/)
│   └── <config-name>.yaml        # e.g. qwen36-27b-hipfire-local.yaml: model, pack, provider, params
├── runs/                         # run = config × eval
│   └── <eval>-<config>-<scope>-<timestamp>/
│       ├── report.json           # grade (smevals grade)
│       └── <split>/<corpus>/<case_id>/...    # per-case artifacts
├── logs/                         # unchanged
├── src/ scripts/ tests/          # code unchanged (paths updated)
└── experiments/                  # keeps GEPA/dev scratch, loses data-of-record
```

Run naming convention (from now on): `{eval}-{config}-{scope}-{YYYYMMDD_HHMMSS}`, e.g. `v5.1010-qwen36-27b-hipfire-local-full-20260719_231825`.

**Execution mode (LJ decision): symlink bridge.** Every moved path gets a symlink at its old location pointing to the new one, so nothing breaks mid-migration. The path-fix pass updates code/manifests to the new locations; after verification the symlinks are removed. Fixture move is byte-for-byte (`git mv` for tracked files).

## 4. Migration phases
### Phase 0 — Baseline snapshot
- [x] Ensure `.git-private` is the active repo (it is: `.git -> .git-private`)
- [ ] Commit current state as `data-reorg: baseline before move` (all data already committed) — **pending LJ commit**
- [x] Confirm pytest passes on the current tree (1 pre-existing failure noted in LEARNINGS; 4 passed, 12 deselected)

### Phase 1 — Registries
- [x] `mkdir cases/registries cases/registries/archive`
- [x] Move canonical `tests/cases/web_scrape_hq_cases_v5.1010.json` → `cases/registries/`
- [x] Move other 33 registries → `cases/registries/archive/` (symlink-bridged from `tests/cases/`)
- [ ] Update the 1 code file referencing `web_scrape_hq_cases_v5.1010` (`scripts/build_v5_1010_dataset.py:41`) — deferred to code-fix pass

### Phase 2 — Manifests + fixtures (the big one)
- [x] Move `tests/v5_manifests_1010/web_scrape_hq/*` → `cases/v5.1010/cases/<case_id>/manifest.json`
- [x] Move each fixture dir `tests/fixtures/<wave>/<case_id>/` → `cases/v5.1010/cases/<case_id>/provenance/original/` (byte-for-byte, whole dir)
- [x] Rewrite every manifest's `artifacts.*` paths to the new locations (scripted; 7007 refs rewritten, 0 missing after repair)
- [x] Leave symlinks at old manifest/fixture paths until code paths are updated and verified (596 bridges, all resolving)
- [x] Repaired 2 nested-case fixture moves (dapagliflozin, tylophorine — case IDs containing `/`)
- [ ] Update the 5 code files referencing `v5_manifests_1010` + the 21 referencing `tests/fixtures` — deferred to code-fix pass
- [x] pytest smoke: same single pre-existing failure, no new breakage

### Phase 3 — Splits
- [ ] Move `experiments/case_splits_v5.1010*.json` (8 files) → `cases/v5.1010/splits/`
- [ ] Update the 4 code files referencing `case_splits_v5.1010`

### Phase 4 — Configs
- [ ] Move `experiments/prompt_pack_v*.yaml` → `configs/prompt_packs/`
- [ ] Create named config YAMLs: `configs/qwen36-27b-hipfire-local.yaml` (model, prompt pack ref, provider, params) — captured from run provenance
- [ ] Update the 7 code files referencing `prompt_pack_v5.0`

### Phase 5 — Runs
- [ ] `git mv experiments/evals/v5_forward_eval runs`
- [ ] Normalize existing 88 run dir names to the new convention (or leave legacy names; new runs use convention)
- [ ] Update the 5 code files referencing `v5_forward_eval`

### Phase 6 — Cleanup
- [ ] Move 33 stray `query_results*.csv` → `archive/` (or delete with explicit approval)
- [ ] Verify `logs/` stays out of git (it is gitignored)

### Phase 7 — Docs
- [ ] Update `README.md` (paths), `doc/v5_design.md` (artifact model → new layout)
- [ ] Update `AGENTS.md` (conventions section)
- [ ] This plan doc becomes `doc/data-reorg-transition.md` (append results/decisions as we go)

### Phase 8 — Verify
- [ ] `pytest` smoke (web_scrape_hq lane)
- [ ] One small eval run end-to-end to prove paths resolve
- [ ] Confirm `git status` clean of strays

## 5. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Manifest `artifacts.*` paths break after move | Scripted rewrite + pytest re-verify; manifests are machine-readable, so the rewrite is verifiable |
| Fixture wave dirs are scattered (30+ waves) | Don't guess: drive the move from each manifest's existing `artifacts` paths |
| Provenance/model-output files (pb_*.json, metadata.json) stranded | Whole fixture dir moves byte-for-byte into `provenance/original/`; nothing is dropped |
| git history: moves vs deletes | Use `git mv` for tracked files to preserve history |
| gigul2 ↔ macbook2 sync | Do the move once, commit, let git replicate; both trees must converge on the new layout |
| 1.3 GB fixtures move | `git mv` is metadata-only on same filesystem |
| Code references missed | The 4–21 file counts per path are the audit list; `grep` again after each phase |
| Anything breaks mid-move | Symlink bridge keeps old paths live until verification |

## 6. Progress tracker

- [ ] Phase 0 — baseline
- [ ] Phase 1 — registries
- [ ] Phase 2 — manifests+fixtures
- [ ] Phase 3 — splits
- [ ] Phase 4 — configs
- [ ] Phase 5 — runs
- [ ] Phase 6 — cleanup
- [ ] Phase 7 — docs
- [ ] Phase 8 — verify
