#!/usr/bin/env python3
"""
DeepSeek API-based Text-to-SQL provider (OpenAI-compatible).
"""

import os
import re
import logging
from typing import Optional

import requests

from .base import Text2SQLProvider

logger = logging.getLogger(__name__)


class DeepSeekProvider(Text2SQLProvider):
    """
    Text-to-SQL provider using DeepSeek API.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = 'deepseek-reasoner',
        timeout: int = 30,
        verbose: bool = False,
        base_url: Optional[str] = None,
        temperature: float = 1.0,
    ):
        """
        Initialize DeepSeek provider.

        Args:
            api_key: DeepSeek API key (reads from DEEPSEEK_API_KEY env if None)
            model: DeepSeek model identifier (default: deepseek-reasoner)
            timeout: Request timeout in seconds
            verbose: If True, print full API request/response for debugging
            base_url: Override API base URL (defaults to DEEPSEEK_BASE_URL or https://api.deepseek.com)
        """
        self.api_key = api_key or os.getenv('DEEPSEEK_API_KEY')
        self.model = model
        self.timeout = timeout
        self.verbose = verbose
        self.base_url = base_url or os.getenv('DEEPSEEK_BASE_URL') or 'https://api.deepseek.com'
        self.temperature = float(temperature)

        if not self.api_key:
            logger.warning("DeepSeek API key not found. Set DEEPSEEK_API_KEY environment variable.")

    def is_available(self) -> bool:
        """Check if DeepSeek is available (API key present)."""
        return bool(self.api_key)

    @property
    def name(self) -> str:
        """Provider name."""
        return f"DeepSeek ({self.model})"

    def generate_sql(
        self,
        question: str,
        schema_docs: str,
        conversation_history: Optional[list] = None
    ) -> Optional[str]:
        """
        Generate SQL using DeepSeek API.
        """
        if not self.is_available():
            logger.error("DeepSeek API key not available", exc_info=True)
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
5. Join via labels: equities.company_label → companies.label
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
        Generate free-form text using DeepSeek chat completions.
        """
        if not self.is_available():
            logger.error("DeepSeek API key not available", exc_info=True)
            return None

        request_payload = {
            'model': self.model,
            'messages': messages,
            'temperature': float(temperature),
            'max_tokens': int(max_tokens),
        }

        if self.verbose:
            print("\n" + "="*20)
            print("🔍 VERBOSE: DeepSeek API Request")
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
                },
                json=request_payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            if self.verbose:
                print("="*20)
                print("🔍 VERBOSE: DeepSeek API Response")
                print("="*20)
                print(f"\n📊 Response Status: {response.status_code}")
                if 'usage' in data:
                    usage = data['usage']
                    print(f"📈 Token Usage:")
                    print(f"   Prompt tokens: {usage.get('prompt_tokens', 0)}")
                    print(f"   Completion tokens: {usage.get('completion_tokens', 0)}")
                    print(f"   Total tokens: {usage.get('total_tokens', 0)}")
                raw_content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                print(f"\n💬 RAW RESPONSE:\n{'-'*20}\n{raw_content}\n{'-'*20}")
                print("="*20 + "\n")

            if 'usage' in data:
                usage = data['usage']
                logger.info(
                    f"DeepSeek API call: {usage.get('prompt_tokens', 0)} prompt + "
                    f"{usage.get('completion_tokens', 0)} completion = "
                    f"{usage.get('total_tokens', 0)} total tokens"
                )

            message = data['choices'][0]['message']
            content = message.get('content')
            if content is None:
                content = message.get('reasoning_content', '')
            return str(content).strip()

        except requests.exceptions.Timeout as e:
            logger.error(f"DeepSeek API timeout: {e}", exc_info=True)
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"DeepSeek API request failed: {e}", exc_info=True)
            return None
        except KeyError as e:
            logger.error(f"Unexpected DeepSeek API response format: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"DeepSeek generation failed: {e}", exc_info=True)
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
