#!/usr/bin/env python3
"""
OpenRouter API-based Text-to-SQL provider.
"""

import os
import re
import logging
import hashlib
import json
from typing import Optional
import requests

from .base import Text2SQLProvider

logger = logging.getLogger(__name__)


class OpenRouterProvider(Text2SQLProvider):
    """
    Text-to-SQL provider using OpenRouter API.

    Supports multiple models with different cost/quality tradeoffs.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = 'openai/gpt-5.1-codex-mini',
        timeout: int = 180,
        verbose: bool = False,
        base_url: Optional[str] = None,
        temperature: float = 1.0,
    ):
        """
        Initialize OpenRouter provider.

        Args:
            api_key: OpenRouter API key (reads from OPENROUTER_API_KEY env if None)
            model: Model identifier on OpenRouter
            timeout: Request timeout in seconds
            verbose: If True, print full API request/response for debugging
        """
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        self.model = model
        self.timeout = timeout
        self.verbose = verbose
        self.temperature = float(temperature)
        self.base_url = base_url or os.getenv('OPENROUTER_BASE_URL') or 'https://openrouter.ai/api/v1'
        if self.base_url:
            cleaned = self.base_url.rstrip('/')
            if not cleaned.endswith('/v1'):
                cleaned = f"{cleaned}/v1"
            self.base_url = cleaned

        if not self.api_key:
            logger.warning("OpenRouter API key not found. Set OPENROUTER_API_KEY environment variable.")

    def is_available(self) -> bool:
        """Check if OpenRouter is available (API key present)."""
        return bool(self.api_key)

    @property
    def name(self) -> str:
        """Provider name."""
        return f"OpenRouter ({self.model})"

    def generate_sql(
        self,
        question: str,
        schema_docs: str,
        conversation_history: Optional[list] = None
    ) -> Optional[str]:
        """
        Generate SQL using OpenRouter API.

        Args:
            question: Natural language question
            schema_docs: Database schema documentation (IGNORED when conversation_history is provided)
            conversation_history: Optional list of previous messages for retry context

        Returns:
            Generated SQL query, or None if failed
        """
        if not self.is_available():
            logger.error("OpenRouter API key not available", exc_info=True)
            return None

        # Build messages array
        if conversation_history:
            # Use provided conversation history (for retries)
            # The conversation already has system message with schema from db_llm_query_v1.py
            messages = conversation_history
        else:
            # Legacy path: Build system prompt (should not be used in v4)
            # This is kept for backward compatibility with older code
            system_prompt = """You are a SQL expert for a chemistry database called ChEMBLdb.
Generate ONLY valid SQLITE SQL queries. Do not include explanations or markdown.

CRITICAL RULES:
1. Return ONLY the SQL query - no explanations, no markdown, no ```sql``` blocks
2. For temporal tables (*_attributes, index_members), ALWAYS use the "latest data pattern"
3. Start temporal queries with: WITH latest AS (SELECT MAX(asof_utc) as max_date FROM table_name)
4. Market cap is in USD - divide by 1e9 for billions, 1e12 for trillions
5. Join via labels: equities.company_label → companies.label
6. Only generate SELECT queries (no INSERT/UPDATE/DELETE/DROP)
7. The 'equities' table uses valid_from/valid_to, NOT asof_utc
8. Only *_attributes tables and index_members have asof_utc

DATA MATCHING TIPS:
9. For country filters, use LIKE or IN with variations (e.g., country LIKE '%United States%' OR country LIKE '%USA%' OR country = 'US')
10. For sector/industry filters, use LIKE with wildcards (e.g., gics_sub_industry LIKE '%Biotech%' instead of exact match)
11. If unsure about exact values, use LIKE with partial matches or check distinct values first
12. Country names may vary: "United States", "USA", "US", "United States of America"
13. Sector names are case-sensitive - try variations if needed

LISTS VS INDEXES - IMPORTANT!
14. When users ask for "FTSE100", "S&P 500", "Russell 3000", etc., they might mean:
   - INDEXES table: Market indices with temporal members (index_members table)
   - LISTS table: Curated lists with list_members table (labels end with -L)
15. Key mappings:
   • FTSE100/FTSE 100/UK 100 → Try list_label = 'ftse100-L' in list_members
   • SP500/S&P 500 → Try list_label = 'sp500-L' in list_members
   • Russell3000/Russell 3000 → Try list_label = 'russell_3000-L' in list_members
   • STOXX600/Europe 600 → Try list_label = 'stoxx_europe_600-L' in list_members
16. If no results in index_members, ALWAYS check list_members with -L suffix
17. List labels in list_members end with '-L' (e.g., 'ftse100-L', 'sp500-L')
"""

            user_prompt = f"""DATABASE SCHEMA:
{schema_docs}

USER QUESTION: {question}

Generate the SQL query:"""
            messages = [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ]

        raw = self.generate_text(messages, temperature=self.temperature, max_tokens=100000)
        if raw is None:
            return None
        return self._clean_sql(raw)

    def generate_text(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        response_format: Optional[dict] = None,
    ) -> Optional[str]:
        """
        Generate free-form text using OpenRouter chat completions.

        Unlike generate_sql(), this does not post-process or truncate content.
        """
        if not self.is_available():
            logger.error("OpenRouter API key not available", exc_info=True)
            return None

        messages = self._with_prompt_caching(messages)
        input_items = [self._message_to_input_item(m) for m in messages]

        request_payload = {
            'model': self.model,
            'input': input_items,
            'max_output_tokens': int(max_tokens),
        }
        if temperature is not None:
            request_payload['temperature'] = float(temperature)
        if response_format:
            request_payload['response_format'] = response_format

        if self.verbose:
            def _hash_system_content(content: object) -> str:
                if isinstance(content, list):
                    parts: list[str] = []
                    for item in content:
                        if isinstance(item, dict) and 'text' in item:
                            parts.append(str(item.get('text', '')))
                        else:
                            parts.append(str(item))
                    text = "".join(parts)
                else:
                    text = str(content)
                return hashlib.sha256(text.encode('utf-8')).hexdigest()

            def _render_content(content: object) -> str:
                if isinstance(content, str):
                    return content
                try:
                    return json.dumps(content, ensure_ascii=True)
                except Exception:
                    return str(content)

            self._log_lines(logging.INFO, "\n".join(["", "=" * 20, "VERBOSE: OpenRouter API Request", "=" * 20]))
            body_lines = [
                f"Endpoint: {self.base_url}/responses",
                f"Model: {self.model}",
                f"CONVERSATION ({len(input_items)} messages):",
                "-" * 20,
            ]
            for i, msg in enumerate(messages):
                role = str(msg.get('role', '')).upper()
                content = msg.get('content', '')
                if role == 'SYSTEM':
                    body_lines.append(f"{i+1}. SYSTEM_SHA256: {_hash_system_content(content)}")
                else:
                    body_lines.append(f"{i+1}. {role}:")
                    body_lines.append(_render_content(content))
                body_lines.append("-" * 20)
            body_lines.extend(
                [
                    "API Parameters:",
                    f"   temperature: {request_payload.get('temperature', '<omitted>')}",
                    f"   max_output_tokens: {request_payload['max_output_tokens']}",
                    f"   timeout: {self.timeout}s",
                ]
            )
            if response_format:
                body_lines.append(f"   response_format: {_render_content(response_format)}")
            self._emit_raw_block("\n".join(body_lines))
            self._log_lines(logging.INFO, "\n".join(["=" * 20, ""]))

        try:
            response = requests.post(
                f'{self.base_url}/responses',
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'HTTP-Referer': 'https://github.com/ljubomirj',
                    'X-Title': 'ChEMBLdb Text2SQL'
                },
                json=request_payload,
                timeout=self.timeout
            )

            response.raise_for_status()
            data = response.json()

            if self.verbose:
                self._log_lines(logging.INFO, "\n".join(["=" * 20, "VERBOSE: OpenRouter API Response", "=" * 20]))
                body_lines = [
                    f"Response Status: {response.status_code}",
                ]
                if 'usage' in data:
                    usage = data['usage']
                    body_lines.extend(
                        [
                            "Token Usage:",
                            f"   Input tokens: {usage.get('input_tokens', usage.get('prompt_tokens', 0))}",
                            f"   Output tokens: {usage.get('output_tokens', usage.get('completion_tokens', 0))}",
                        ]
                    )
                    if 'cache_creation_input_tokens' in usage:
                        body_lines.extend(
                            [
                                "Prompt Cache:",
                                f"   Cache creation tokens: {usage.get('cache_creation_input_tokens', 0)}",
                                f"   Cache read tokens: {usage.get('cache_read_input_tokens', 0)}",
                            ]
                        )
                raw_content = self._extract_output_text(data) or ''
                body_lines.extend(
                    [
                        "RAW RESPONSE:",
                        "-" * 20,
                        raw_content,
                        "-" * 20,
                    ]
                )
                self._emit_raw_block("\n".join(body_lines))
                self._log_lines(logging.INFO, "\n".join(["=" * 20, ""]))

            # Log token usage for cost tracking
            if 'usage' in data:
                usage = data['usage']
                cache_info = ""
                if 'cache_read_input_tokens' in usage:
                    cache_read = usage.get('cache_read_input_tokens', 0)
                    cache_create = usage.get('cache_creation_input_tokens', 0)
                    if cache_read > 0:
                        cache_info = f" | 💾 Cache hit: {cache_read} tokens read"
                    elif cache_create > 0:
                        cache_info = f" | 💾 Cache created: {cache_create} tokens"

                input_tokens = usage.get('input_tokens', usage.get('prompt_tokens', 0))
                output_tokens = usage.get('output_tokens', usage.get('completion_tokens', 0))
                total_tokens = usage.get('total_tokens', input_tokens + output_tokens)
                logger.info(
                    f"OpenRouter API call: {input_tokens} input + "
                    f"{output_tokens} output = "
                    f"{total_tokens} total tokens{cache_info}"
                )

            content = self._extract_output_text(data)
            return content.strip() if content else ""

        except requests.exceptions.Timeout as e:
            logger.error(f"OpenRouter API timeout: {e}", exc_info=True)
            return None
        except requests.exceptions.RequestException as e:
            response = getattr(e, "response", None)
            if response is not None:
                try:
                    body = response.text
                except Exception:
                    body = "<unreadable response body>"
                logger.error(
                    "OpenRouter API error response: status=%s body=%s",
                    response.status_code,
                    body,
                )
            logger.error(f"OpenRouter API request failed: {e}", exc_info=True)
            return None
        except KeyError as e:
            logger.error(f"Unexpected OpenRouter API response format: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"OpenRouter generation failed: {e}", exc_info=True)
            return None

    def _with_prompt_caching(self, messages: list[dict]) -> list[dict]:
        """Wrap system prompt for Anthropic caching when routed through OpenRouter."""
        try:
            is_anthropic = self.model.startswith('anthropic/')
            if not is_anthropic or not messages or messages[0].get('role') != 'system':
                return messages

            system_content = messages[0].get('content', '')
            if not isinstance(system_content, str):
                return messages

            wrapped = list(messages)
            wrapped[0] = {
                'role': 'system',
                'content': [
                    {
                        'type': 'text',
                        'text': system_content,
                        'cache_control': {'type': 'ephemeral'}
                    }
                ]
            }
            logger.info(f"✓ Enabled prompt caching for {self.model}")
            return wrapped
        except Exception:
            logger.warning("Failed to enable OpenRouter prompt caching; continuing.", exc_info=True)
            return messages

    def _message_to_input_item(self, msg: dict) -> dict:
        role = msg.get('role', 'user')
        content = msg.get('content', '')
        parts: list[dict] = []
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and 'text' in part:
                    parts.append({'type': 'input_text', 'text': self._sanitize_text(str(part.get('text', '')))})
                elif isinstance(part, str):
                    parts.append({'type': 'input_text', 'text': self._sanitize_text(part)})
                else:
                    parts.append({'type': 'input_text', 'text': self._sanitize_text(str(part))})
        elif isinstance(content, str):
            parts.append({'type': 'input_text', 'text': self._sanitize_text(content)})
        else:
            parts.append({'type': 'input_text', 'text': self._sanitize_text(str(content))})
        return {'role': role, 'content': parts}

    def _extract_output_text(self, data: dict) -> Optional[str]:
        if not isinstance(data, dict):
            return None
        output_text = data.get('output_text')
        if isinstance(output_text, str) and output_text:
            return self._sanitize_text(output_text.strip())
        outputs = data.get('output')
        if not isinstance(outputs, list):
            return None
        chunks: list[str] = []
        for item in outputs:
            if not isinstance(item, dict):
                continue
            if item.get('type') == 'message':
                content = item.get('content', [])
                if isinstance(content, list):
                    for part in content:
                        if not isinstance(part, dict):
                            continue
                        if part.get('type') in {'output_text', 'text'} and 'text' in part:
                            chunks.append(self._sanitize_text(str(part.get('text', ''))))
            elif item.get('type') == 'output_text' and 'text' in item:
                chunks.append(self._sanitize_text(str(item.get('text', ''))))
        text = "\n".join(s for s in chunks if s)
        return text.strip() if text else None

    def _clean_sql(self, sql: str) -> str:
        """
        Clean up generated SQL.

        Args:
            sql: Raw SQL from LLM

        Returns:
            Cleaned SQL query
        """
        # Remove thinking/reasoning tags (common in some models)
        sql = re.sub(r'<think>.*?</think>', '', sql, flags=re.DOTALL | re.IGNORECASE)
        sql = re.sub(r'<reasoning>.*?</reasoning>', '', sql, flags=re.DOTALL | re.IGNORECASE)

        # Remove markdown code blocks
        sql = re.sub(r'```sql\n?', '', sql)
        sql = re.sub(r'```\n?', '', sql)

        # Remove leading/trailing whitespace
        sql = sql.strip()

        # Remove explanatory text after query
        # Look for double newline followed by text
        if '\n\n' in sql:
            parts = sql.split('\n\n')
            # Take first part if it looks like SQL
            first_upper = parts[0].upper().strip()
            if (first_upper.startswith('SELECT') or
                first_upper.startswith('WITH') or
                first_upper.startswith('INSERT') or
                first_upper.startswith('UPDATE') or
                first_upper.startswith('DELETE') or
                first_upper.startswith('CREATE')):
                sql = parts[0]

        # Take only up to first semicolon (if present)
        if ';' in sql:
            sql = sql.split(';')[0] + ';'

        return sql.strip()

    def _sanitize_text(self, text: str) -> str:
        if not isinstance(text, str):
            text = str(text)
        return text.encode('utf-8', 'replace').decode('utf-8')

    @staticmethod
    def _log_lines(level: int, message: str) -> None:
        text = str(message)
        lines = text.splitlines()
        if text.endswith("\n"):
            lines.append("")
        if not lines:
            lines = [""]
        for line in lines:
            logger.log(level, line)

    @staticmethod
    def _emit_raw_block(text: str) -> None:
        if text is None:
            return
        sanitized = text.encode('utf-8', 'replace').decode('utf-8')
        if not sanitized.endswith("\n"):
            sanitized += "\n"
        root = logging.getLogger()
        stream = None
        for handler in root.handlers:
            stream = getattr(handler, "stream", None)
            if stream is not None:
                break
        if stream is None:
            import sys as _sys
            stream = _sys.stderr
        try:
            stream.write(sanitized)
            stream.flush()
        except Exception:
            import sys as _sys
            _sys.stderr.write(sanitized)
            _sys.stderr.flush()


# Recommended models and their characteristics
# Updated 2025-12-04 based on OpenRouter programming models
# Costs are approximate based on ~2500 tokens per query
RECOMMENDED_MODELS = {
    'gemini-2.0-flash': {
        'id': 'google/gemini-2.0-flash-exp:free',
        'cost_per_query_usd': 0.0,
        'description': 'FREE, fast, good at SQL (rate limited)'
    },
    'deepseek-chat': {
        'id': 'deepseek/deepseek-chat',
        'cost_per_query_usd': 0.00007,
        'description': 'Cheapest option, good at SQL'
    },
    'gpt-5.1-codex-mini': {
        'id': 'openai/gpt-5.1-codex-mini',
        'cost_per_query_usd': 0.001,
        'description': 'Compact GPT-5.1 Codex for SQL (DEFAULT)'
    },
    'qwen3-coder-30b': {
        'id': 'qwen/qwen3-coder-30b-a3b-instruct',
        'cost_per_query_usd': 0.0001,
        'description': 'Latest Qwen3, excellent for code/SQL'
    },
    'deepseek-r1': {
        'id': 'deepseek/deepseek-r1',
        'cost_per_query_usd': 0.00014,
        'description': 'Reasoning model, very accurate for complex queries'
    },
    'llama-70b': {
        'id': 'meta-llama/llama-3.1-70b-instruct',
        'cost_per_query_usd': 0.00026,
        'description': 'Good balance of cost and quality'
    },
    'claude-sonnet-4.5': {
        'id': 'anthropic/claude-sonnet-4.5',
        'cost_per_query_usd': 0.0015,
        'description': 'Premium quality, very reliable'
    },
    'claude-haiku-4.5': {
        'id': 'anthropic/claude-haiku-4.5',
        'cost_per_query_usd': 0.0005,
        'description': 'Fast, low-cost Claude; great for quick SQL drafts'
    },
    'grok-code-fast': {
        'id': 'x-ai/grok-code-fast-1',
        'cost_per_query_usd': 0.0025,
        'description': 'xAI coding model, fast and accurate'
    },
    'claude-opus-4.5': {
        'id': 'anthropic/claude-opus-4.5',
        'cost_per_query_usd': 0.0075,
        'description': 'Highest quality, most expensive, best for critical queries'
    }
}
