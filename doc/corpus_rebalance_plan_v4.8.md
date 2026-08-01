# Corpus Rebalance Plan for Next Active Benchmark Version

## Current state

The current 1000-case corpus is operationally useful but structurally imbalanced.

Family counts in the present corpus:

- `target_pchembl`: 902
- `other`: 29
- `document`: 29
- `assay_exact`: 27
- `salts`: 10
- `metabolism`: 3

This means `target_pchembl` is 90.2% of the corpus.

## Problem

A benchmark with this shape overstates general capability if sampled naively, because most evaluation mass falls on one query pattern. That creates three distortions:

1. Prompt optimization overfits to `target_pchembl`-style exports.
2. Failures in smaller families are under-measured and discovered late.
3. Forward and backward quality work look better than they are on realistic mixed workloads.

## Recommendation

Do not delete or rewrite the current 1000-case corpus.

Instead, split responsibilities:

1. Keep the current 1000 as an archived corpus.
2. Define a new active balanced benchmark corpus.
3. Keep a separate `target_pchembl` stress set for specialization tracking.

## Proposed corpus roles

### 1. Archive corpus

Keep the current 1000-case corpus unchanged for provenance and longitudinal comparison.

Suggested name:
- `archive_v4.7_1000`

### 2. Active balanced benchmark

Build a new active corpus by adding non-`target_pchembl` cases aggressively.

Target shape for the next active corpus version:

- `target_pchembl`: 250-350
- `assay_exact`: 120-160
- `document`: 120-160
- `salts`: 60-100
- `metabolism`: 40-80
- `other`: 180-260

This keeps `target_pchembl` important, but not dominant.

### 3. Target stress set

Define a separate stress set made mostly or entirely from `target_pchembl` cases.

Purpose:
- regression tracking for the biggest operational family
- cheap high-throughput prompt screening
- explicit separation between generalization and specialization

## Highest-priority expansion families

### Assay-exact

Need much more coverage of:

- exact activity exports
- assay metadata exports
- bioassay metadata queries
- alias-sensitive exports
- raw activity-row multiplicity cases

### Document

Need more document-centric cases:

- docs and publication provenance
- DOI / PubMed paths
- document-linked compound and activity exports
- publication filters and ordering

### Salts

Need more cases around:

- parent-plus-salts compound set definition
- provenance path fidelity
- projection fidelity with `activity_comment`
- ordering-sensitive export behavior

### Metabolism

Need more coverage of:

- substrate vs parent naming
- first-N exports without ordering
- optional enrichment joins
- metabolite-side joins

### Other realistic tasks

This bucket should be expanded deliberately with realistic user-facing asks, such as:

- molecule-smiles by target and organism
- target descriptions and target names
- approved drugs with indications
- ranking and top-N tasks
- counts and aggregations
- realistic lookup/export tasks that are not just target pChEMBL dumps

## Concrete expansion policy

### What to stop doing

- Stop growing the corpus mainly by adding more `target_pchembl` cases.
- Stop treating total corpus size growth as a quality gain by itself.

### What to do instead

1. Add non-target families first.
2. Preserve realistic `uq_surface` wording.
3. Preserve benchmark-spec text separately when needed.
4. Label new cases by family, realism, and ambiguity.
5. Keep the active benchmark balanced through the registry/split layer, not by deleting archive data.

## Suggested next expansion wave

Target: add roughly 400-600 new non-target cases before the next full active benchmark freeze.

Suggested first wave:

- `assay_exact`: +80
- `document`: +80
- `salts`: +40
- `metabolism`: +30
- `other`: +120

Total first wave: about +350

A second wave can then add another 200-300 non-target cases if needed.

## Source strategy

Prefer targeted non-`target_pchembl` acquisition.

Sources to prioritize:

1. Web-scraped ChEMBL examples and FAQ patterns that are not target exports
2. Public code examples and notebooks that exercise document, assay, metabolism, or salts patterns
3. Existing query families already represented in the corpus, but under-sampled
4. Synthetic expansions only after the source family and gold SQL pattern are clearly grounded

## Evaluation policy after rebalancing

Use three benchmark views:

1. `balanced_active`
- main quality number
- broad representative mix

2. `target_stress`
- specialization and throughput tracking

3. `archive_full`
- historical comparison against prior corpora

This keeps model quality, data quality, and process quality from being conflated.

## Immediate next steps

1. Finish the surgical `v5.7` retry for the four remaining `mixed500` misses.
2. Freeze the current 1000-case corpus as archive.
3. Create a new active benchmark spec document with target family counts.
4. Start non-target expansion wave 1.
5. Do not start another large GEPA cycle until the active corpus is materially more balanced.
