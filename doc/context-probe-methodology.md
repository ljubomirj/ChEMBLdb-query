# Context Limit Probe Methodology

How to determine the effective context window of any LLM API.

## Why

API providers advertise context limits (e.g. "1M tokens") but the effective
limit may be lower due to:
- Provider-side proxy limits (OpenCode Go caps at ~25K tokens for DS4-Flash)
- Model routing to smaller variants
- Internal prompt processing overhead

Knowing the real limit lets you design prompts that fit reliably.

## Probe Strategy

Binary search on token count using the model's own tokenizer.

### Step 1: Get the tokenizer

For open-weight models, the tokenizer is on HuggingFace:

```python
from transformers import AutoTokenizer
tok = AutoTokenizer.from_pretrained("deepseek-ai/DeepSeek-V4-Flash",
    trust_remote_code=True)
```

For closed models (GPT-5, Claude, Gemini), use `tiktoken` (OpenAI) or
the `tokenizers` library with the model's known tokenizer file.

### Step 2: Build a token-accurate probe text

Use SQL or other domain-appropriate text that resembles your actual payload:

```python
base = "SELECT assay_id, tid, chembl_id FROM assays WHERE tid > 0"
text = ""
while len(tok.encode(text)) < target_tokens:
    text += base + "; "
```

### Step 3: Binary search

Send increasingly large prompts to the API. Track status code:

```python
resp = requests.post(f"{base_url}/v1/chat/completions",
    headers={"Authorization": f"Bearer {key}"},
    json={"model": model, "messages": [{"role": "user", "content": text}],
          "max_tokens": 3, "temperature": 0})
```

- HTTP 200 → increase target
- HTTP 400/500 → decrease target
- Stop when the gap is < 10K tokens

### Step 4: Persist results

Save to a JSON file for reuse:

```json
{
  "deepseek-v4-flash": {
    "provider": "opencode-go",
    "effective_context_tokens": 25000,
    "probed_at": "2026-07-11"
  }
}
```

## Character-to-Token Mapping

For models without an accessible tokenizer, use the ratio for mixed
English + SQL text:

| Text type | chars/token |
|-----------|:----------:|
| Repetitive English | ~6.0 |
| Mixed SQL + English | ~4.0 |
| SQL-heavy | ~3.8 |
| **Conservative default** | **3.5** |

When probing without a tokenizer, estimate tokens as `chars / 3.5`.

## Caching

Probe once per (provider, model) pair at the start of a run. Cache the
result in `doc/context-probe-cache.json`. If the (provider, model) is already
in the cache, skip the probe.

## Critical Finding: Provider Limits != Model Limits

OpenCode Go and DeepSeek's direct API serve the same model but have different
effective context limits:

| Endpoint | Effective limit |
|----------|:--------------:|
| OpenCode Go `/zen/go/v1` | ~50K tokens |
| DeepSeek direct `api.deepseek.com` | 100K+ tokens (confirmed) |

**Always probe the actual endpoint**, not just the model. A provider proxy may
impose its own context limit independent of the model's advertised capacity.

## Files

- Probe results: `doc/context-probe-cache.json`
- This methodology: `doc/context-probe-methodology.md`
