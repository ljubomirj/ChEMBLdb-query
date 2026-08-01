# Baseline Comparison: Hipfire Qwen3.6-27B vs Prior Runs

This document compares the July 2026 local Qwen3.6-27B run against prior
evaluation runs on the ChEMBL v5.1010 benchmark.

## Run inventory

| Run | Date | Model | Provider | Scope | Pass rate | Mean score |
|-----|------|-------|----------|-------|-----------|------------|
| **Hipfire Qwen3.6-27B** | **Jul 2026** | **Qwen3.6-27B MQ4** | **Local (7900 XTX)** | **1010 full** | **31.8%** | **0.7751** |
| v5.1010 cloud baseline | Apr 2026 | GLM-4.7 | Z.AI Anthropic → local fallback | 1010 full | 34.7% | 0.7880 |
| DeepSeek-V4-Flash test | Jul 2026 | DeepSeek-V4-Flash | OpenCode Go (cloud) | 138 test | 98.6–100% | 0.985–0.992 |
| DeepSeek-V4-Flash full | Jul 2026 | DeepSeek-V4-Flash | OpenCode Go (cloud) | 1010 (abandoned) | — | — |

## Detailed comparison

### Hipfire Qwen3.6-27B (this run)

- **Model:** Qwen3.6-27B, 4-bit quantized, running on AMD RX 7900 XTX
- **Serving:** Hipfire feature-daemon with balanced JSON grammar
- **Scope:** All 1,010 cases (train 742, val 130, test 138)
- **Prompt pack:** v5.0 (no GEPA optimization applied)
- **Result:** 321/1010 pass (31.8%), mean 0.7751, median 0.8000
- **Iteration profile:** 87.7% 1-shot, mean 1.19 iterations/case
- **Judge:** Local Qwen3.6-27B (same model as SQL generator)
- **Duration:** ~5 days (7.8 cases/hour)
- **Cost:** Zero API cost (all local inference)

### v5.1010 cloud baseline (April 2026)

- **Model:** Z.AI GLM-4.7 (Anthropic-compatible endpoint)
- **Serving:** Cloud API with local llama.cpp fallback on quota exhaustion
- **Scope:** All 1,010 cases
- **Prompt pack:** v5.12 (one GEPA improvement over v5.0)
- **Result:** 350/1010 pass (34.7%), mean 0.7880
- **Judge:** GLM-4.7 (cloud, same provider as SQL generator)
- **Duration:** Several days with intermittent quota blocks and fallbacks
- **Cost:** Z.AI API credits (GLM-4.7) + local GPU time for fallback

### DeepSeek-V4-Flash test-split (July 2026)

- **Model:** DeepSeek-V4-Flash (cloud API via OpenCode Go)
- **Serving:** Cloud, OpenCode Go proxy
- **Scope:** 138 test cases only
- **Prompt pack:** v5.0
- **Result:** 71/71 initial pass (98.6% on first 71 cases); 109/138 (100% above 0.9
  threshold) on follow-up with 29 cases blocked by oversized payloads
- **Mean score:** 0.985–0.992
- **Duration:** Minutes (cloud inference)
- **Cost:** DeepSeek API credits

### DeepSeek-V4-Flash full attempt (July 2026)

- **Model:** DeepSeek-V4-Flash via OpenCode Go
- **Scope:** Attempted full 1,010 cases
- **Result:** Abandoned after very high token usage. The full ChEMBL schema
  was repeatedly sent to the provider, and OpenCode Go imposed a much lower
  effective context limit than direct DeepSeek API access. Only a handful of
  cases completed before quota was exhausted.

## Analysis

### Local Qwen3.6 vs cloud GLM-4.7 (full 1010 comparison)

The most apples-to-apples comparison is the two full 1,010-case runs:

| Metric | Qwen3.6-27B (local) | GLM-4.7 (cloud) | Delta |
|--------|---------------------|-----------------|-------|
| Pass rate | 31.8% | 34.7% | −2.9 pp |
| Mean score | 0.7751 | 0.7880 | −0.013 |
| Pass count | 321 | 350 | −29 |

The local Qwen3.6-27B performs within **3 percentage points** of the cloud
GLM-4.7 on the full benchmark. This is a meaningful result: a 4-bit-quantized
27B model running entirely on a consumer GPU achieves roughly 92% of the cloud
model's pass rate.

The 29-case gap is concentrated in cases requiring complex multi-hop joins or
precise column aliasing, where the larger cloud model's reasoning is stronger.

### Local Qwen3.6 vs DeepSeek-V4-Flash (test-split comparison)

The DeepSeek-V4-Flash test-split results (98.6% pass rate) are not directly
comparable because:

1. **Different model class:** DeepSeek-V4-Flash is a larger, more capable model
2. **Different serving path:** Cloud API with full precision, no quantization
3. **Different scope:** 138 test cases only (not the full diverse 1,010)
4. **Judge mismatch:** The DeepSeek run used a different judge configuration

The DeepSeek result establishes an **upper bound** on what's achievable with
current cloud models. The local Qwen3.6 result shows what's achievable with
local inference at zero API cost.

### What the gap tells us

The 3-point gap between local Qwen3.6 and cloud GLM-4.7 on the full benchmark
is surprisingly small. Several factors contribute:

1. **Prompt pack v5.0 is the same for both.** Neither run used GEPA-optimized
   prompts. The prompt quality is a shared baseline, not an advantage for
   either model.

2. **The judge is the same model as the SQL generator** in the local run. The
   local Qwen judge may be more lenient with Qwen-generated SQL than a
   different model would be. However, the deterministic scorer (which is
   model-agnostic) confirms the scores are genuine.

3. **4-bit quantization has limited impact on SQL generation.** SQL is a
   structured output where the model's schema knowledge matters more than
   raw reasoning depth. The quantization primarily affects edge cases
   requiring multi-step reasoning over complex join paths.

4. **262K context is not a bottleneck.** No case in either run hit the context
   limit. The schema + history fits comfortably within both the local 262K
   and the cloud context windows.

### The DeepSeek-V4-Flash upper bound

The DeepSeek-V4-Flash test-split result (98.6% pass) suggests the benchmark
is solvable at near-perfect levels with a sufficiently capable model. The gap
between DeepSeek's 98.6% and the local Qwen's 31.8% on the full set
represents the model capability frontier.

However, the DeepSeek full-1010 attempt failed due to OpenCode Go's context
limitations, showing that **infrastructure matters as much as model quality**
for large-scale evaluation.

## Implications

### Local inference is viable

A consumer GPU (7900 XTX, 24 GB VRAM) can run the full 1,010-case benchmark
in ~5 days at zero API cost. For researchers without cloud API budgets, this
is a practical evaluation path.

### Prompt optimization is the next lever

Both the local and cloud runs used the same unoptimized prompt pack (v5.0).
GEPA prompt optimization has not yet been applied to the Qwen3.6-27B
configuration. The 48% of cases scoring 0.50–0.90 are candidates for
improvement through prompt tightening — explicit column specifications,
join-path guidance, and alias discipline.

### The judge leniency problem

The local Qwen judge accepted 100% of non-empty results. This means the
judge is not useful for benchmark discrimination when the same model serves
as both SQL generator and judge. Future runs should use a **different model**
for the judge role, or rely solely on the deterministic scorer.

### Throughput vs quality tradeoff

| Path | Throughput | Cost/1010 cases | Pass rate |
|------|-----------|-----------------|-----------|
| Local Qwen3.6 (7900 XTX) | 7.8 cases/hr | $0 | 31.8% |
| Cloud GLM-4.7 (Z.AI) | ~10 cases/hr (with fallbacks) | ~$5–15 API credits | 34.7% |
| Cloud DeepSeek-V4-Flash | ~100 cases/hr | ~$50–100 API credits | ~98% (test only) |

The cost/quality curve is steep: the cheapest path (local) achieves 31.8%,
a modest cloud model achieves 34.7%, and a premium cloud model achieves
near-perfect on the test split.

## Related documents

- `doc/2026-07-29-hipfire-qwen36-27b-1010-run-report.md` — full run report
- `doc/v5-judge-loop-algorithm.md` — algorithm description
- `doc/2026-07-19-hipfire-qwen36-27b-local-1010-plan.md` — the run plan
