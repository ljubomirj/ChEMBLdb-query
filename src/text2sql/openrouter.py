#!/usr/bin/env python3
"""
OpenRouter API-based Text-to-SQL provider.
"""

import os
import re
import logging
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
        timeout: int = 30,
        verbose: bool = False,
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
        self.base_url = 'https://openrouter.ai/api/v1'

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
    ) -> Optional[str]:
        """
        Generate free-form text using OpenRouter chat completions.

        Unlike generate_sql(), this does not post-process or truncate content.
        """
        if not self.is_available():
            logger.error("OpenRouter API key not available", exc_info=True)
            return None

        messages = self._with_prompt_caching(messages)

        request_payload = {
            'model': self.model,
            'messages': messages,
            'temperature': float(temperature),
            'max_tokens': int(max_tokens),
        }

        if self.verbose:
            print("\n" + "="*20)
            print("🔍 VERBOSE: OpenRouter API Request")
            print("="*20)
            print(f"\n📍 Endpoint: {self.base_url}/chat/completions")
            print(f"🤖 Model: {self.model}")

            print(f"\n💬 CONVERSATION ({len(messages)} messages):")
            print("-"*20)
            for i, msg in enumerate(messages):
                role = str(msg.get('role', '')).upper()
                content = msg.get('content', '')
                if isinstance(content, str):
                    preview = content[:200] + "..." if len(content) > 200 else content
                else:
                    preview = str(content)[:200] + "..."
                print(f"{i+1}. {role}: {preview}")
            print("-"*20)

            print(f"\n⚙️  API Parameters:")
            print(f"   temperature: {request_payload['temperature']}")
            print(f"   max_tokens: {request_payload['max_tokens']}")
            print(f"   timeout: {self.timeout}s")
            print("="*20 + "\n")

        try:
            response = requests.post(
                f'{self.base_url}/chat/completions',
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
                print("="*20)
                print("🔍 VERBOSE: OpenRouter API Response")
                print("="*20)
                print(f"\n📊 Response Status: {response.status_code}")
                if 'usage' in data:
                    usage = data['usage']
                    print(f"📈 Token Usage:")
                    print(f"   Prompt tokens: {usage.get('prompt_tokens', 0)}")
                    print(f"   Completion tokens: {usage.get('completion_tokens', 0)}")
                    print(f"   Total tokens: {usage.get('total_tokens', 0)}")
                    if 'cache_creation_input_tokens' in usage:
                        print(f"💾 Prompt Cache:")
                        print(f"   Cache creation tokens: {usage.get('cache_creation_input_tokens', 0)}")
                        print(f"   Cache read tokens: {usage.get('cache_read_input_tokens', 0)}")
                raw_content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                print(f"\n💬 RAW RESPONSE:\n{'-'*20}\n{raw_content}\n{'-'*20}")
                print("="*20 + "\n")

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

                logger.info(
                    f"OpenRouter API call: {usage.get('prompt_tokens', 0)} prompt + "
                    f"{usage.get('completion_tokens', 0)} completion = "
                    f"{usage.get('total_tokens', 0)} total tokens{cache_info}"
                )

            return data['choices'][0]['message']['content'].strip()

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
    'claude-3.5-sonnet': {
        'id': 'anthropic/claude-3.5-sonnet',
        'cost_per_query_usd': 0.0015,
        'description': 'Premium quality, very reliable'
    },
    'grok-code-fast': {
        'id': 'x-ai/grok-code-fast-1',
        'cost_per_query_usd': 0.0025,
        'description': 'xAI coding model, fast and accurate'
    },
    'claude-opus-4': {
        'id': 'anthropic/claude-opus-4-20250514',
        'cost_per_query_usd': 0.0075,
        'description': 'Highest quality, most expensive, best for critical queries'
    }
}
