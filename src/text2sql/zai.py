#!/usr/bin/env python3
"""
Z.AI API-based Text-to-SQL provider (OpenAI-compatible).
"""

import os
import re
import logging
from typing import Optional

import requests

from .base import Text2SQLProvider

logger = logging.getLogger(__name__)


class ZAIProvider(Text2SQLProvider):
    """
    Text-to-SQL provider using Z.AI API.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = 'glm-4.7',
        timeout: int = 180,
        verbose: bool = False,
        base_url: Optional[str] = None,
        temperature: float = 1.0,
        use_coding_api: bool = True,
        thinking: Optional[dict] = None,
    ):
        """
        Initialize Z.AI provider.

        Args:
            api_key: Z.AI API key (reads from ZAI_API_KEY env if None)
            model: Z.AI model identifier (default: glm-4.7)
            timeout: Request timeout in seconds
            verbose: If True, print full API request/response for debugging
            base_url: Override API base URL (defaults to ZAI_CODING_BASE_URL or ZAI_BASE_URL)
            temperature: Sampling temperature
            use_coding_api: Use the coding endpoint by default
            thinking: Optional Z.AI thinking configuration dict
        """
        self.api_key = api_key or os.getenv('ZAI_API_KEY')
        self.model = self._normalize_model_name(model)
        self.timeout = timeout
        self.verbose = verbose
        self.base_url = self._resolve_base_url(base_url, use_coding_api)
        self.temperature = float(temperature)
        self.thinking = {"type": "enabled"} if thinking is None else thinking

        if not self.api_key:
            logger.warning("Z.AI API key not found. Set ZAI_API_KEY environment variable.")

    def _resolve_base_url(self, base_url: Optional[str], use_coding_api: bool) -> str:
        if base_url:
            return base_url.rstrip('/')
        coding_url = os.getenv('ZAI_CODING_BASE_URL')
        general_url = os.getenv('ZAI_BASE_URL')
        if use_coding_api:
            return (coding_url or general_url or 'https://api.z.ai/api/coding/paas/v4').rstrip('/')
        return (general_url or coding_url or 'https://api.z.ai/api/paas/v4').rstrip('/')

    @staticmethod
    def _normalize_model_name(model: str) -> str:
        normalized = (model or '').strip()
        if not normalized:
            return normalized
        if normalized.startswith('z-ai/'):
            normalized = normalized[len('z-ai/'):]
        if normalized.startswith('zai-'):
            normalized = normalized[len('zai-'):]
        if normalized.endswith(':free'):
            normalized = normalized.split(':', 1)[0]
        return normalized

    def is_available(self) -> bool:
        """Check if Z.AI is available (API key present)."""
        return bool(self.api_key)

    @property
    def name(self) -> str:
        """Provider name."""
        return f"Z.AI ({self.model})"

    def generate_sql(
        self,
        question: str,
        schema_docs: str,
        conversation_history: Optional[list] = None
    ) -> Optional[str]:
        """
        Generate SQL using Z.AI API.
        """
        if not self.is_available():
            logger.error("Z.AI API key not available", exc_info=True)
            return None

        if conversation_history:
            messages = conversation_history
        else:
            system_prompt = """You are a SQL expert for a chemistry database called ChEMBLdb.
Generate ONLY valid SQLITE SQL queries. Do not include explanations or markdown.

CRITICAL RULES:
1. Return ONLY the SQL query - no explanations, no markdown, no ```sql``` blocks
2. For temporal tables (*_attributes, index_members), ALWAYS use the "latest data pattern"
3. Start temporal queries with: WITH latest AS (SELECT MAX(asof_utc) as max_date FROM table_name)
4. Market cap is in USD - divide by 1e9 for billions, 1e12 for trillions
5. Join via labels: equities.company_label -> companies.label
6. Only generate SELECT queries (no INSERT/UPDATE/DELETE/DROP)
7. The 'equities' table uses valid_from/valid_to, NOT asof_utc
8. Only *_attributes tables and index_members have asof_utc
"""
            user_prompt = f"""DATABASE SCHEMA:
{schema_docs}

USER QUESTION: {question}

Generate the SQL query:"""
            messages = [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ]

        raw = self.generate_text(messages, temperature=self.temperature, max_tokens=15000)
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
        Generate free-form text using Z.AI chat completions.
        """
        if not self.is_available():
            logger.error("Z.AI API key not available", exc_info=True)
            return None

        request_payload = {
            'model': self.model,
            'messages': messages,
            'temperature': float(temperature),
            'max_tokens': int(max_tokens),
            'stream': False,
        }
        if self.thinking:
            request_payload['thinking'] = self.thinking

        if self.verbose:
            print("\n" + "="*20)
            print("VERBOSE: Z.AI API Request")
            print("="*20)
            print(f"\nEndpoint: {self.base_url}/chat/completions")
            print(f"Model: {self.model}")
            print(f"\nConversation ({len(messages)} messages):")
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
            print("\nAPI Parameters:")
            print(f"   temperature: {request_payload['temperature']}")
            print(f"   max_tokens: {request_payload['max_tokens']}")
            print(f"   timeout: {self.timeout}s")
            print("="*20 + "\n")

        response = None
        try:
            response = requests.post(
                f'{self.base_url}/chat/completions',
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                    'Accept-Language': 'en-US,en',
                },
                json=request_payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            if self.verbose:
                print("="*20)
                print("VERBOSE: Z.AI API Response")
                print("="*20)
                print(f"\nResponse Status: {response.status_code}")
                if 'usage' in data:
                    usage = data['usage']
                    print("Token Usage:")
                    print(f"   Prompt tokens: {usage.get('prompt_tokens', 0)}")
                    print(f"   Completion tokens: {usage.get('completion_tokens', 0)}")
                    print(f"   Total tokens: {usage.get('total_tokens', 0)}")
                raw_content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                print(f"\nRaw response:\n{'-'*20}\n{raw_content}\n{'-'*20}")
                print("="*20 + "\n")

            if 'usage' in data:
                usage = data['usage']
                logger.info(
                    f"Z.AI API call: {usage.get('prompt_tokens', 0)} prompt + "
                    f"{usage.get('completion_tokens', 0)} completion = "
                    f"{usage.get('total_tokens', 0)} total tokens"
                )

            message = data['choices'][0]['message']
            content = message.get('content', '')
            return content.strip()

        except requests.exceptions.HTTPError as e:
            body = ""
            try:
                body = response.text if response is not None else ""
            except Exception:
                body = ""
            if body:
                logger.error("Z.AI API error body: %s", body[:2000])
            logger.error(f"Z.AI API request failed: {e}", exc_info=True)
            return None
        except requests.exceptions.Timeout as e:
            logger.error(f"Z.AI API timeout: {e}", exc_info=True)
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Z.AI API request failed: {e}", exc_info=True)
            return None
        except KeyError as e:
            logger.error(f"Unexpected Z.AI API response format: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Z.AI generation failed: {e}", exc_info=True)
            return None

    def _clean_sql(self, sql: str) -> str:
        """
        Clean up generated SQL.
        """
        sql = re.sub(r'<think>.*?</think>', '', sql, flags=re.DOTALL | re.IGNORECASE)
        sql = re.sub(r'<reasoning>.*?</reasoning>', '', sql, flags=re.DOTALL | re.IGNORECASE)

        sql = re.sub(r'```sql\n?', '', sql)
        sql = re.sub(r'```\n?', '', sql)

        sql = sql.strip()

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

        if ';' in sql:
            sql = sql.split(';')[0] + ';'

        return sql.strip()
