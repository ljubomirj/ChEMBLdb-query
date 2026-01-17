#!/usr/bin/env python3
"""
Cerebras API-based Text-to-SQL provider (OpenAI-compatible).
"""

import os
import re
import logging
from typing import Optional

import requests

from .base import Text2SQLProvider

logger = logging.getLogger(__name__)


class CerebrasProvider(Text2SQLProvider):
    """
    Text-to-SQL provider using Cerebras API.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = 'zai-glm-4.7',
        timeout: int = 180,
        verbose: bool = False,
        base_url: Optional[str] = None,
        temperature: float = 1.0,
    ):
        """
        Initialize Cerebras provider.

        Args:
            api_key: Cerebras API key (reads from CEREBRAS_API_KEY env if None)
            model: Cerebras model identifier (default: zai-glm-4.7)
            timeout: Request timeout in seconds
            verbose: If True, print full API request/response for debugging
            base_url: Override API base URL (defaults to CEREBRAS_BASE_URL or https://api.cerebras.ai/v1)
        """
        self.api_key = api_key or os.getenv('CEREBRAS_API_KEY')
        self.model = model
        self.timeout = timeout
        self.verbose = verbose
        self.base_url = base_url or os.getenv('CEREBRAS_BASE_URL') or 'https://api.cerebras.ai/v1'
        self.temperature = float(temperature)

        if not self.api_key:
            logger.warning("Cerebras API key not found. Set CEREBRAS_API_KEY environment variable.")

    def is_available(self) -> bool:
        """Check if Cerebras is available (API key present)."""
        return bool(self.api_key)

    @property
    def name(self) -> str:
        """Provider name."""
        return f"Cerebras ({self.model})"

    def generate_sql(
        self,
        question: str,
        schema_docs: str,
        conversation_history: Optional[list] = None
    ) -> Optional[str]:
        """
        Generate SQL using Cerebras API.
        """
        if not self.is_available():
            logger.error("Cerebras API key not available", exc_info=True)
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
        Generate free-form text using Cerebras chat completions.
        """
        if not self.is_available():
            logger.error("Cerebras API key not available", exc_info=True)
            return None

        request_payload = {
            'model': self.model,
            'messages': messages,
            'temperature': float(temperature),
            'max_tokens': int(max_tokens),
        }

        if self.verbose:
            self._log_lines(logging.INFO, "\n".join(["", "=" * 20, "VERBOSE: Cerebras API Request", "=" * 20]))
            body_lines = [
                f"Endpoint: {self.base_url}/chat/completions",
                f"Model: {self.model}",
                f"CONVERSATION ({len(messages)} messages):",
                "-" * 20,
            ]
            for i, msg in enumerate(messages):
                role = str(msg.get('role', '')).upper()
                content = msg.get('content', '')
                if isinstance(content, str):
                    preview = content[:200] + "..." if len(content) > 200 else content
                else:
                    preview = str(content)[:200] + "..."
                body_lines.append(f"{i+1}. {role}: {preview}")
            body_lines.extend(
                [
                    "-" * 20,
                    "API Parameters:",
                    f"   temperature: {request_payload['temperature']}",
                    f"   max_tokens: {request_payload['max_tokens']}",
                    f"   timeout: {self.timeout}s",
                ]
            )
            self._emit_raw_block("\n".join(body_lines))
            self._log_lines(logging.INFO, "\n".join(["=" * 20, ""]))

        response = None
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
                self._log_lines(logging.INFO, "\n".join(["=" * 20, "VERBOSE: Cerebras API Response", "=" * 20]))
                body_lines = [
                    f"Response Status: {response.status_code}",
                ]
                if 'usage' in data:
                    usage = data['usage']
                    body_lines.extend(
                        [
                            "Token Usage:",
                            f"   Prompt tokens: {usage.get('prompt_tokens', 0)}",
                            f"   Completion tokens: {usage.get('completion_tokens', 0)}",
                            f"   Total tokens: {usage.get('total_tokens', 0)}",
                        ]
                    )
                raw_content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
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

            if 'usage' in data:
                usage = data['usage']
                logger.info(
                    f"Cerebras API call: {usage.get('prompt_tokens', 0)} prompt + "
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
                logger.error("Cerebras API error body: %s", body[:2000])
            logger.error(f"Cerebras API request failed: {e}", exc_info=True)
            return None
        except requests.exceptions.Timeout as e:
            logger.error(f"Cerebras API timeout: {e}", exc_info=True)
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Cerebras API request failed: {e}", exc_info=True)
            return None
        except KeyError as e:
            logger.error(f"Unexpected Cerebras API response format: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Cerebras generation failed: {e}", exc_info=True)
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
