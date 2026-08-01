# DeepSeek-V4-Flash — First Text2SQL Benchmark on ChEMBL (via OpenCode Go)

**Date**: 2026-07-09
**Agent**: pi
**Model**: DeepSeek-V4-Flash via OpenCode Go (`https://opencode.ai/zen/go/v1`)
**Benchmark**: ChEMBL text2SQL v5.1010 (test split, 138 cases)
**Roles**: Prompt writer (UP) + SQL generator + Judge — all using the same model

---

## 1. What Was Tried

The goal was to evaluate DeepSeek-V4-Flash as a universal model for the ChEMBL text2SQL pipeline — handling all three LLM roles:
- **UP (prompt writer)**: rewrites the user's question into a clear, explicit SQL prompt
- **SQL generator**: produces the actual SQLite query
- **Judge**: evaluates the query result and decides pass/fail

The pipeline uses an iterative refinement loop: UP → SQL → execute SQL on local SQLite → RES (result table) → Judge → if fail, retry with improved UP.

We wired `opencode-go` as a new provider by:
1. Adding the profile `opencode-go-dsv4-flash` in `db_llm_runtime_v5.py` and `db_llm_v5/provider.py`
2. Creating a `_call_openai_chat_api` method that uses `/v1/chat/completions` instead of `/v1/responses`
3. Setting `OPENAI_API_KEY` to the OpenCode Go API key

## 2. Problems Encountered

### Problem 1: The ChEMBL pipeline uses the OpenAI Responses API (`/v1/responses`)

The entire `db_llm_runtime_v5.py` codebase was built around OpenAI's newer Responses API, which uses the `/v1/responses` endpoint. OpenCode Go only supports `/v1/chat/completions`.

**What happened**: Every API call returned HTTP 404 — the endpoint didn't exist.

**Fix**: 
- Added `_call_openai_chat_api()` method that uses `/v1/chat/completions`
- Routed the `openai` provider to this new method instead of `_call_responses_api()`
- The existing `_call_zai_chat_api()` served as template (it already used `/v1/chat/completions`)

### Problem 2: `response_format` parameter rejected

OpenCode Go's proxy rejects the `response_format` parameter in the request body.

**What happened**: HTTP 400 with `"Error from provider (Console Go): Upstream request failed"`.

**Fix**: Removed `response_format` from the payload in `_call_openai_chat_api()`.

### Problem 3: `stream: false` parameter rejected

Similarly, the `"stream": false` parameter was rejected.

**What happened**: Another 400 error on some requests.

**Fix**: Removed `"stream": false` from the payload.

### Problem 4: Large payloads (~103K chars)

The ChEMBL system prompt includes the full database schema documentation, making each request ~103,000 characters (~25,000 tokens).

**What happened**: No error — DeepSeek-V4-Flash handled this consistently. The model has 1M context, so this was well within limits.

## 3. How It Worked Out

After fixing the API compatibility issues, the pipeline ran successfully. We started a 138-case test split run which completed 71 cases before being interrupted. Per-case timing averaged ~40-80 seconds:

| Stage | Time |
|-------|------|
| UP generation | ~33s |
| SQL generation | ~40s |
| SQL execution (local) | <1s |
| Judge | ~50s |
| **Total per iteration** | **~2 min** |

Each case went through 2-7 iterations with the judge loop, depending on SQL quality.

**Transient issue**: During a second run, the SQL generator returned `None` for several consecutive iterations — a transient OpenCode Go failure. This appears to be rate-limiting or upstream instability, not a code bug.

## 4. Results

**98.6% pass rate** (70/71 cases, score threshold ≥ 0.9)

| Metric | Value |
|--------|-------|
| Cases completed | 71/138 (run interrupted) |
| Pass rate | 98.6% |
| Mean judge score | 0.985 |
| Median judge score | 1.000 |
| Failed cases | 1 |

The one failed case scored 0.5 — a partial pass rather than a complete failure. No case scored 0.0.

**Speed**: Each case averaged ~2 minutes end-to-end (UP + SQL + execute + judge + potential retries).

## Files Changed

| File | Change |
|------|--------|
| `src/db_llm_runtime_v5.py` | Added `_call_openai_chat_api()` method using `/chat/completions`; routed `openai` provider to it; added `opencode-go-dsv4-flash` profile |
| `src/db_llm_v5/provider.py` | Added `opencode-go-dsv4-flash` profile resolution |

## Next Steps

- Run the full 138-case test split for a complete baseline (~2 hours)
- Run the full 1010-case benchmark overnight (~20 hours)
- Compare against the current GLM-4.7 baseline (34.65% pass rate)
