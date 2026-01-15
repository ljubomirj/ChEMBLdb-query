#!/usr/bin/env python3
"""
Anthropic API direct provider for Text-to-SQL.

Uses the official Anthropic Python SDK for direct Claude access.
Supports prompt caching for optimal performance with large schemas.
"""

import os
import re
import logging
from typing import Optional

try:
    import anthropic
except ImportError:
    anthropic = None

from .base import Text2SQLProvider

logger = logging.getLogger(__name__)


class AnthropicProvider(Text2SQLProvider):
    """
    Text-to-SQL provider using direct Anthropic API.

    Supports Claude models with full prompt caching.
    Optimized for low latency and cost efficiency.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = 'claude-sonnet-4.5',
        timeout: int = 180,
        verbose: bool = False,
        temperature: float = 1.0,
    ):
        """
        Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key (reads from ANTHROPIC_API_KEY env if None)
            model: Claude model identifier (claude-haiku-4.5, claude-sonnet-4.5, claude-opus-4.5)
            timeout: Request timeout in seconds
            verbose: If True, print full API request/response for debugging
        """
        if anthropic is None:
            raise ImportError(
                "anthropic package not installed. "
                "Install with: pip install anthropic"
            )

        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.model = self._normalize_model_name(model)
        self.timeout = timeout
        self.verbose = verbose
        self.temperature = float(temperature)

        if not self.api_key:
            logger.warning("Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable.")
            self.client = None
        else:
            self.client = anthropic.Anthropic(api_key=self.api_key)

    def _normalize_model_name(self, model: str) -> str:
        """
        Normalize model name to Anthropic format.

        Handles:
        - Short names: claude-haiku-4.5 → claude-haiku-4-5-20250429
        - Full names: claude-sonnet-4-5-20250429 → unchanged
        - OpenRouter format: anthropic/claude-sonnet-4.5 → claude-sonnet-4-5-20250429
        """
        # Remove anthropic/ prefix if present (from OpenRouter format)
        if model.startswith('anthropic/'):
            model = model.replace('anthropic/', '')

        # Map short names to full model IDs
        model_map = {
            'claude-haiku-4.5': 'claude-haiku-4-5-20250429',
            'claude-sonnet-4.5': 'claude-sonnet-4-5-20250929',
            'claude-opus-4.5': 'claude-opus-4-5-20251101',
            # Legacy mappings
            'claude-3.5-haiku': 'claude-3-5-haiku-20241022',
            'claude-3.5-sonnet': 'claude-3-5-sonnet-20241022',
            'claude-3-opus': 'claude-3-opus-20240229',
        }

        return model_map.get(model, model)

    def is_available(self) -> bool:
        """Check if Anthropic API is available (API key present)."""
        return bool(self.api_key and self.client)

    @property
    def name(self) -> str:
        """Provider name."""
        return f"Anthropic ({self.model})"

    def generate_sql(
        self,
        question: str,
        schema_docs: str,
        conversation_history: Optional[list] = None
    ) -> Optional[str]:
        """
        Generate SQL using Anthropic API.

        Args:
            question: Natural language question
            schema_docs: Database schema documentation (IGNORED when conversation_history provided)
            conversation_history: Optional list of previous messages for retry context

        Returns:
            Generated SQL query, or None if failed
        """
        if not self.is_available():
            logger.error("Anthropic API key not available", exc_info=True)
            return None

        # Prepare messages
        if conversation_history:
            # Use provided conversation (from db_llm_query_v1.py)
            messages = conversation_history
        else:
            # Legacy: build initial conversation (shouldn't be used in v4)
            logger.warning("Building legacy conversation - should use conversation_history")
            system_prompt = self._build_system_prompt()
            user_prompt = f"""DATABASE SCHEMA:
{schema_docs}

USER QUESTION: {question}

Generate the SQL query:"""
            messages = [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ]
        raw = self._chat(messages, max_tokens=4096)
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
        # Anthropic supports temperature, but we keep default behavior unless needed.
        _ = temperature
        return self._chat(messages, max_tokens=int(max_tokens))

    def _chat(self, messages: list[dict], *, max_tokens: int) -> Optional[str]:
        """Chat-complete a messages array; returns raw text (no SQL cleaning)."""
        # Extract system message (Anthropic requires it as separate parameter)
        system_content = None
        user_messages: list[dict] = []

        for msg in messages:
            if msg.get('role') == 'system':
                content = msg.get('content', '')
                if isinstance(content, str):
                    system_content = [
                        {
                            'type': 'text',
                            'text': content,
                            'cache_control': {'type': 'ephemeral'}
                        }
                    ]
                else:
                    system_content = content
                    if isinstance(system_content, list) and len(system_content) > 0:
                        if 'cache_control' not in system_content[0]:
                            system_content[0]['cache_control'] = {'type': 'ephemeral'}
            else:
                user_messages.append(msg)

        if not system_content:
            system_content = [
                {
                    'type': 'text',
                    'text': 'You are a helpful assistant.',
                    'cache_control': {'type': 'ephemeral'}
                }
            ]

        if self.verbose:
            print("\n" + "="*20)
            print("🔍 VERBOSE: Anthropic API Request")
            print("="*20)
            print(f"\n📍 Model: {self.model}")
            print(f"\n💬 SYSTEM MESSAGE (cached):")
            print("-"*20)
            if isinstance(system_content, list):
                for item in system_content:
                    text = item.get('text', str(item))[:200]
                    print(f"{text}...")
            print("-"*20)

            print(f"\n💬 CONVERSATION ({len(user_messages)} messages):")
            print("-"*20)
            for i, msg in enumerate(user_messages):
                role = str(msg.get('role', '')).upper()
                content = msg.get('content', '')
                if isinstance(content, str):
                    content_preview = content[:200] + "..." if len(content) > 200 else content
                else:
                    content_preview = str(content)[:200] + "..."
                print(f"{i+1}. {role}: {content_preview}")
            print("-"*20)

            print(f"\n⚙️  API Parameters:")
            print(f"   max_tokens: {max_tokens}")
            print(f"   timeout: {self.timeout}s")
            print("="*20 + "\n")

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=int(max_tokens),
                system=system_content,
                messages=user_messages,
                timeout=self.timeout
            )

            if self.verbose:
                print("="*20)
                print("🔍 VERBOSE: Anthropic API Response")
                print("="*20)
                print("\n📊 Response Status: success")

                usage = response.usage
                print("📈 Token Usage:")
                print(f"   Input tokens: {usage.input_tokens}")
                print(f"   Output tokens: {usage.output_tokens}")

                if hasattr(usage, 'cache_creation_input_tokens') and usage.cache_creation_input_tokens:
                    print("💾 Prompt Cache:")
                    print(f"   Cache creation tokens: {usage.cache_creation_input_tokens}")
                if hasattr(usage, 'cache_read_input_tokens') and usage.cache_read_input_tokens:
                    print(f"   Cache read tokens: {usage.cache_read_input_tokens}")

                print("\n💬 RAW RESPONSE:")
                print("-"*20)
                print(response.content[0].text)
                print("-"*20)
                print("="*20 + "\n")

            text = response.content[0].text.strip()

            usage = response.usage
            cache_info = ""
            if hasattr(usage, 'cache_read_input_tokens') and usage.cache_read_input_tokens:
                cache_info = f" | 💾 Cache hit: {usage.cache_read_input_tokens} tokens read"
            elif hasattr(usage, 'cache_creation_input_tokens') and usage.cache_creation_input_tokens:
                cache_info = f" | 💾 Cache created: {usage.cache_creation_input_tokens} tokens"

            logger.info(
                f"Anthropic API call: {usage.input_tokens} input + "
                f"{usage.output_tokens} output = "
                f"{usage.input_tokens + usage.output_tokens} total tokens{cache_info}"
            )

            return text

        except anthropic.APITimeoutError as e:
            logger.error(f"Anthropic API timeout: {e}", exc_info=True)
            return None
        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Anthropic generation failed: {e}", exc_info=True)
            return None

    def _build_system_prompt(self) -> str:
        """Build system prompt for legacy mode."""
        return """You are a SQL expert for a chemistry database called ChEMBLdb.
Generate ONLY valid SQLITE SQL queries. Do not include explanations or markdown.

CRITICAL RULES:
1. Return ONLY the SQL query - no explanations, no markdown, no ```sql``` blocks
2. Use exact match on directory_name for list queries (e.g., l.directory_name = 'ftse100')
3. NEVER use LIKE patterns for list matching - they match multiple lists
4. Only generate SELECT queries (no INSERT/UPDATE/DELETE/DROP)

Generate the SQL query:"""

    def _clean_sql(self, sql: str) -> str:
        """
        Clean up generated SQL.

        Args:
            sql: Raw SQL from LLM

        Returns:
            Cleaned SQL query
        """
        # Remove thinking/reasoning tags
        sql = re.sub(r'<think>.*?</think>', '', sql, flags=re.DOTALL | re.IGNORECASE)
        sql = re.sub(r'<reasoning>.*?</reasoning>', '', sql, flags=re.DOTALL | re.IGNORECASE)

        # Remove markdown code blocks
        sql = re.sub(r'```sql\n?', '', sql)
        sql = re.sub(r'```\n?', '', sql)

        # Remove leading/trailing whitespace
        sql = sql.strip()

        # Remove explanatory text after query
        if '\n\n' in sql:
            parts = sql.split('\n\n')
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
