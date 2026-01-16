# Anthropic Direct Provider

Direct Anthropic API provider for text-to-SQL conversion using Claude models.

## Features

✅ **Direct Anthropic API** - No middleman, lowest latency
✅ **Full Prompt Caching** - 90% cost savings on cached tokens
✅ **Official SDK** - Well-supported Python library
✅ **Claude-Only** - Optimized for Haiku, Sonnet, Opus models
✅ **Automatic Caching** - Schema automatically cached for 5 minutes

## Installation

```bash
uv sync --extra anthropic
```

Set your API key:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Usage

These commands target the local ChEMBL SQLite database via `src/db_llm_query.py`.
Filter profiles: `none` (default), `strict`, `relaxed`.

### Command Line (single example)

```bash
RUN_LABEL="query1_kinase_after_2022_relaxed_$(date +%Y%m%d_%H%M%S)"; \
PYTHONUNBUFFERED=1 uv run python src/db_llm_query.py \
  --provider anthropic \
  --model claude-sonnet-4.5 \
  --filter-profile relaxed \
  --run-label "${RUN_LABEL}" \
  -f csv \
  -q "get the smiles, chembl_id, target_name, publication year, article doi, and IC50 for all kinase inhibitors published after 2022" \
  |& tee "logs/db_llm_${RUN_LABEL}.log"
```

This same query run is recorded in `logs/db_llm_query1_kinase_after_2022_relaxed_20260115_052049.log`.

## Supported Models

The provider automatically normalizes model names:

### Short Names (Recommended)
- `claude-haiku-4.5` → claude-haiku-4-5-20250429
- `claude-sonnet-4.5` → claude-sonnet-4-5-20250929
- `claude-opus-4.5` → claude-opus-4-5-20251101

### OpenRouter Format (Auto-converted)
- `anthropic/claude-sonnet-4.5` → claude-sonnet-4-5-20250929

### Full Model IDs (Used Directly)
- `claude-sonnet-4-5-20250929` → unchanged

## Prompt Caching

The provider automatically enables prompt caching on the system message (which contains the database schema).

### Cache Behavior

**First Request**:
```
System message (schema): ~15,000 tokens
└─> Cache creation: 15,000 tokens × write cost
User question: 50 tokens
Output: 200 tokens

Total cost: Cache write (15K) + User (50) + Output (200)
```

**Subsequent Requests** (within 5 minutes):
```
System message (schema): ~15,000 tokens
└─> Cache read: 15,000 tokens × read cost (90% cheaper!)
User question: 50 tokens
Output: 200 tokens

Total cost: Cache read (15K × 0.1) + User (50) + Output (200)
```

### Cost Savings

Claude Sonnet 4.5 pricing:
- **Input**: $3.00 / 1M tokens
- **Cache write**: $3.75 / 1M tokens (25% markup)
- **Cache read**: $0.30 / 1M tokens (90% discount)
- **Output**: $15.00 / 1M tokens

Example with 15K token schema:
- **Without caching**: $0.045 per query (15K × $3/1M)
- **With caching** (2nd+ request): $0.0045 per query (15K × $0.30/1M)
- **Savings**: 90% on schema tokens

## Verbose Output

Use `-v` to see cache statistics in the CLI output.

## When to Use Anthropic Direct

**✅ Use Anthropic when:**
- You want Claude models specifically
- You need lowest latency (direct API)
- You want full prompt caching benefits
- You're doing single-shot queries
- You want best caching efficiency

**❌ Use OpenRouter instead when:**
- You want multi-provider round-robin (DeepSeek, Qwen, Claude)
- You want to try cheap models first, escalate to Claude
- You want model diversity
- You don't have Anthropic API key

## Comparison: Anthropic vs OpenRouter

| Feature | Anthropic Direct | OpenRouter |
|---------|-----------------|------------|
| **Latency** | Lowest (direct) | Medium (+1 hop) |
| **Caching** | Full support | Passes through |
| **Models** | Claude only | All providers |
| **Round-robin** | Haiku/Sonnet/Opus | All models |
| **Cost** | Direct pricing | ~10-20% markup |
| **Setup** | ANTHROPIC_API_KEY | OPENROUTER_API_KEY |

## Auto-Detection

`--provider auto` selects Anthropic when a Claude model is chosen and `ANTHROPIC_API_KEY` is set; otherwise it falls back to OpenRouter. An explicit `--provider` flag always wins.

## Round-Robin with Claude Models

You can cycle through Claude models by changing `--model` between runs, or adjust model lists in `src/db_llm_query_v1.py`.

## Error Handling

The provider raises `anthropic.APITimeoutError` and `anthropic.APIError` for API issues, and `ImportError` if the SDK is missing.

## Migration from OpenRouter

Use `--provider anthropic` with Claude model names (no `anthropic/` prefix), or keep `--provider auto` and let it select Anthropic when a Claude model is specified.

## Troubleshooting

### "Anthropic provider not available"
Install the SDK with `uv sync --extra anthropic` and ensure `ANTHROPIC_API_KEY` is set in your environment.

### "API key not found"
Set `ANTHROPIC_API_KEY` in the environment or pass it directly when constructing the provider.

### Cache not working
- Cache lasts 5 minutes - make requests within that window
- System message must be identical between requests
- Check verbose output for cache statistics

### Model name not found
Use short names like `claude-sonnet-4.5` or full IDs like `claude-sonnet-4-5-20250929`.

## See Also

- [OpenRouter Provider](openrouter.py) - Multi-provider alternative
- [Text2SQL Base](base.py) - Provider interface
- [db_llm_query_v1.py](../db_llm_query_v1.py) - Main query tool
