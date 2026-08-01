# Non-Target Expansion Execution Plan for Next Corpus Version

## Scope

This plan assumes the next expansion wave will avoid new web scraping for now.
The expansion should instead use the existing `v5` backward path machinery to generate new non-`target_pchembl` cases from grounded SQL patterns we already trust.

This is a synthetic expansion plan, but not a free-form synthetic plan.
The starting point must still be validated SQL/query families, not invented user questions.

## Core principle

Use the backward path to generate artifacts in this order:

1. start from grounded SQL family or SQL template
2. instantiate executable SQL
3. execute SQL and materialize `res_gold`
4. run `PB_SQL`: `SQL -> UP_exec`
5. run `PB_UP`: `UP_exec -> UQ_surface`
6. curate realism and metadata
7. add case to the new active corpus

So the synthetic path is:

- grounded SQL -> executable case -> backward-generated language artifacts

not:

- random UQ -> guessed SQL

## Why this is the right next move

The current 1000-case corpus is 90.2% `target_pchembl`.

Current family counts:

- `target_pchembl`: 902
- `other`: 29
- `document`: 29
- `assay_exact`: 27
- `salts`: 10
- `metabolism`: 3

So the limiting factor is not total corpus size.
It is representativeness.

The fastest way to improve representativeness is to grow non-target families using known-good SQL families plus the backward packs.

## What to keep unchanged

1. Keep the current 1000-case corpus as archive.
2. Do not delete or rewrite the existing target-heavy registry.
3. Do not expand `target_pchembl` further in the next wave.

## Deliverables for the next wave

### 1. Archive freeze

Freeze the current corpus as an archive snapshot.

Suggested names:

- archive registry snapshot: `web_scrape_hq_cases_archive_v4.7_1000.json`
- archive split snapshot: `case_splits_archive_v4.7_1000.json`

### 2. New active corpus definition

Create a new active benchmark registry/split that will eventually become the balanced benchmark.

Do not require it to stay at exactly 1000 while under construction.
The first priority is family balance, not hitting a round number.

### 3. Wave-1 non-target expansion

Target roughly +350 new non-target cases.

Suggested wave-1 targets:

- `assay_exact`: +80
- `document`: +80
- `salts`: +40
- `metabolism`: +30
- `other`: +120

## Family-by-family execution plan

### A. Assay-exact

#### Goal
Expand exact activity-export and assay-metadata cases with more assay IDs and more schema-sensitive variants.

#### Input sources
- existing `assay_exact` SQL families already in fixtures
- existing `bioassay metadata` cases
- existing `chembl_downloader_assay_*_exact` patterns

#### Generation method
1. enumerate more assay IDs from ChEMBL that match the family constraints
2. instantiate SQL using the known-good assay skeletons
3. execute and materialize `ground-truth.csv.zst`
4. generate `UP_exec` via `PB_SQL`
5. generate realistic `UQ_surface` via `PB_UP`
6. review for alias realism and row-multiplicity wording

#### Important constraints
- preserve exact activity row multiplicity
- preserve alias-sensitive outputs
- avoid DISTINCT unless explicitly required
- use INNER JOIN to `compound_structures` when canonical smiles are required

### B. Document

#### Goal
Expand publication/provenance cases and document-linked exports.

#### Input sources
- existing document family fixtures
- current approved-drug/document-linked cases
- existing SQL that joins `docs`, `compound_records`, and activities

#### Generation method
1. identify more grounded SQL templates from existing document-oriented cases
2. parameterize on target, document, DOI/PubMed, or publication filters
3. materialize results locally
4. reconstruct `UP_exec` and `UQ_surface` through backward steps
5. review realism for publication-facing questions

#### Important constraints
- preserve DOI / PubMed behavior exactly
- avoid adding document filters not present in the gold SQL
- keep requested ordering when publication metadata is part of the task

### C. Salts

#### Goal
Expand parent-and-salts provenance cases beyond the current tiny set.

#### Input sources
- existing FAQ-style salts SQL family already in fixtures
- current salts cases that now pass under `v5.7`

#### Generation method
1. enumerate more grounded parent compounds and target pairs
2. instantiate the FAQ salts skeleton exactly
3. materialize result tables locally
4. reconstruct `UP_exec` and `UQ_surface` via backward steps
5. review output realism and projection wording

#### Important constraints
- compound set must come from `molecule_hierarchy`
- provenance path must go through `compound_records -> docs -> activities -> assays -> target_dictionary`
- `assay_description` must come from `assays.description`
- do not add ORDER BY unless required

### D. Metabolism

#### Goal
Expand substrate/parent/metabolite cases and first-N export cases.

#### Input sources
- current metabolism fixtures
- existing SQL patterns already validated in the repo

#### Generation method
1. clone validated metabolism skeletons with new entity variants
2. keep the row-stream semantics where relevant
3. materialize outputs locally
4. generate `UP_exec` and `UQ_surface` via backward steps
5. review for realism and ambiguity

#### Important constraints
- preserve first-N semantics without invented sorting
- distinguish substrate vs parent naming cleanly
- keep optional enrichment joins optional

### E. Other realistic tasks

#### Goal
Expand non-target realistic asks that are still executable and benchmarkable.

#### Input sources
- existing `other` fixtures already in the corpus
- grounded SQL patterns already present in the repo

#### Candidate subfamilies
- molecule smiles by target and organism
- target descriptions / target names
- approved drugs with indications
- ranking/top-N exports
- counts / aggregations

#### Generation method
1. cluster existing `other` cases into stable subfamilies
2. choose only subfamilies with reusable SQL skeletons
3. instantiate and materialize locally
4. use backward generation to create `UP_exec` and `UQ_surface`
5. manually review a sample from each subfamily

## Role of the backward path

### `PB_SQL`
Use `PB_SQL` to reconstruct execution-oriented `UP_exec` from trusted SQL.

Primary purpose:
- derive a consistent execution-plan artifact from grounded SQL

### `PB_UP`
Use `PB_UP` to reconstruct realistic `UQ_surface` from `UP_exec`.

Primary purpose:
- make the benchmark more user-facing without losing the grounded SQL semantics

### Manual review
Backward generation should not be fully unsupervised.

Required review points:
- schema leakage
- unrealistic wording
- over-specific benchmark-spec phrasing
- ambiguity drift

## Acceptance criteria for new cases

A new case is admissible only if:

1. SQL executes locally
2. `ground-truth.csv.zst` is materialized
3. `PB_SQL` generates a usable `UP_exec`
4. `PB_UP` generates a plausible `UQ_surface`
5. metadata is assigned:
   - family
   - realism level
   - ambiguity level
6. case passes schema/column sanity checks

## Recommended workflow

### Phase 1: freeze and scaffold
1. freeze current 1000 as archive
2. define the new active corpus registry
3. create wave-1 output directories and manifest conventions

### Phase 2: SQL-family harvesting from existing repo assets
1. enumerate grounded non-target SQL families already in the repo
2. group them into the five expansion families
3. select wave-1 templates for each family

### Phase 3: synthetic generation via backward path
1. instantiate SQL variants
2. materialize results
3. run `PB_SQL`
4. run `PB_UP`
5. review and register new cases

### Phase 4: quality gating
1. run a family-level smoke evaluation on the new wave
2. check realism of generated `UQ_surface`
3. patch prompts or case generation rules if needed

### Phase 5: active benchmark refresh
1. build a new balanced split
2. run a forward `v5` evaluation on a mixed slice
3. only then consider a larger baseline or GEPA cycle

## Immediate concrete next steps

1. Freeze the current 1000-case corpus as archive artifacts.
2. Write a small inventory of existing non-target SQL families already present in the repo.
3. Select the first wave-1 family templates:
   - assay_exact
   - document
   - salts
   - metabolism
   - other
4. Build generator scripts for those families using existing grounded SQL skeletons.
5. Route artifact generation through `PB_SQL` and `PB_UP`.
6. Review the first batch before scaling out.

## What not to do next

- do not add more `target_pchembl` in the next wave
- do not start a full new GEPA cycle first
- do not generate free-form synthetic user questions without grounded SQL
