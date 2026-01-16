# Providers and Model IDs

This project supports multiple LLM providers. OpenRouter is the default unless overridden.

## OpenRouter (default)
Env: `OPENROUTER_API_KEY`  
CLI: `--provider openrouter`  
Default model: `openai/gpt-5.1-codex-mini`

Recommended IDs (subset):
- `openai/gpt-5.1-codex-mini`
- `qwen/qwen-2.5-coder-32b-instruct`
- `qwen/qwen3-coder-30b-a3b-instruct`
- `deepseek/deepseek-chat`
- `deepseek/deepseek-r1`
- `meta-llama/llama-3.1-70b-instruct`
- `anthropic/claude-3.5-sonnet`
- `anthropic/claude-opus-4-20250514`

Context filtering:
- When using OpenRouter model lists, `--min-context` filters models by context length via OpenRouter `/models` (default is 100000).
- The filtered SQL/judge lists are logged at startup.

## Cerebras
Env: `CEREBRAS_API_KEY`  
CLI: `--provider cerebras`  
Default model: `zai-glm-4.7`

Allowed IDs:
- `zai-glm-4.7`

## DeepSeek
Env: `DEEPSEEK_API_KEY`  
CLI: `--provider deepseek`  
Default model: `deepseek-reasoner`

Allowed IDs:
- `deepseek-reasoner`
- `deepseek-chat`

## Anthropic (direct)
Env: `ANTHROPIC_API_KEY`  
CLI: `--provider anthropic`  
Default model: `claude-sonnet-4.5`

Allowed IDs (short names):
- `claude-haiku-4.5`
- `claude-sonnet-4.5`
- `claude-opus-4.5`

## Local (transformers)
CLI: `--provider local` or `--no-provider`  
Default model: `Qwen/Qwen2.5-3B-Instruct`

## Provider env var
You can avoid passing `--provider` by setting:
```
TEXT2SQL_PROVIDER=openrouter|cerebras|deepseek|anthropic|local|auto
```
