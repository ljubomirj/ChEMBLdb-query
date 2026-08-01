# Aborted Full-Run Learnings — 2026-07-11

What went wrong when scaling from the 71-case test split to the full 1010-case
benchmark using DeepSeek-V4-Flash via OpenCode Go.

## What Happened

After a promising 71-case test split (98.6% pass rate), we launched the full
1010-case run. It ran for ~10-15 hours, consumed ~4% of the monthly OpenCode Go
token quota, and completed only **4 cases**.

The previous test split (71 cases) had completed in ~5 hours with reasonable
token usage. Something changed.

## Root Causes

### 1. Effective context limit is ~25K tokens, not 1M

DeepSeek-V4-Flash advertises 1M tokens. Via OpenCode Go, the effective limit is
~25K-50K tokens. The pipeline's judge payload was ~132K chars (~35K tokens)
which hit the ceiling. This caused repeated 400 errors, retries, and wasted
tokens.

**Lesson**: Never trust advertised context limits. Probe the actual limit for
every (provider, model) pair. See `doc/context-probe-methodology.md`.

### 2. Token cost per case is ~1M tokens

Each case triggers 9-15 LLM calls:
- 1-3 UP (prompt writer) calls
- 1-3 SQL generator calls
- 7-9 judge calls (with retries)

Each call sends the full system prompt (~100K chars / ~25K tokens). Total per
case: ~750K-1.5M tokens = ~$0.30-0.60 at OpenCode Go rates.

At that rate, 1010 cases would cost $300-600 and use 100% of a monthly quota.

### 3. The skipped-cases feature didn't work as expected

`--skip-existing` checked for `pf_res.output.json`, but the killed run's cases
only had intermediate files. Only 4 cases had the final output file, so the
incremental restart re-processed nearly everything from scratch.

**Lesson**: Verify that the skip marker file is written before assuming a case
is complete.

### 4. The judge is the most expensive role

The judge call has the largest payload: system prompt + UP + SQL + RES summary.
In the 71-case run it worked because the total was just under the limit. In the
full run, some cases had larger result sets that pushed the judge payload over
the edge.

## Recommendations

| Issue | Fix |
|-------|-----|
| Context limit mismatch | Probe before every run; cache results |
| High token cost | Use local model (hipfire) for UP + SQL; API only for judge |
| Skip verification | Check `pf_res.output.json` exists before skipping |
| Judge payload too large | Trim system prompt; reduce schema docs; cap result samples |
| Retry explosion | Lower `--max-iterations` from 10 to 3-5 |

## Open Questions

- What is DeepSeek-V4-Pro's effective context via OpenCode Go?
- Does the same limit apply to other providers (DeepSeek direct, OpenRouter)?
- Can we estimate token cost before launching a run?

## Related

- [Context probe methodology](context-probe-methodology.md)
- [DS4-Flash first run report](../reports/2026-07-09-deepseek-v4-flash-text2sql.md)

## Update 2026-07-11: The Real Limiter is OpenCode Go, Not DeepSeek

After investigating pi's `models.json` (which sets `contextWindow: 1048576` =
1M tokens for DS4-Flash) and probing both APIs:

| API | Max payload accepted |
|-----|:-------------------:|
| OpenCode Go (`/zen/go/v1`) | ~50K tokens (~200K chars) |
| DeepSeek direct (`api.deepseek.com`) | **100K+ tokens** (400K chars tested, ✅) |

**Conclusion**: OpenCode Go has its own proxy limit of ~50K tokens, independent
of DeepSeek's actual 1M context. The ChEMBL pipeline should use the DeepSeek
API directly when large contexts are needed. Pi's `contextWindow` values are
optimistic configured defaults, not verified limits.
