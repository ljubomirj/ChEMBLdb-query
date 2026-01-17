#!/usr/bin/env python3
"""
OpenAI API direct provider for Text-to-SQL using the Responses API.
"""

import os
import re
import logging
from typing import Optional

import requests

from .base import Text2SQLProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(Text2SQLProvider):
    """
    Text-to-SQL provider using OpenAI Responses API directly.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = 'gpt-5.1-codex',
        timeout: int = 180,
        verbose: bool = False,
        base_url: Optional[str] = None,
        temperature: float = 1.0,
    ) -> None:
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = model
        self.timeout = timeout
        self.verbose = verbose
        self.base_url = base_url or os.getenv('OPENAI_BASE_URL') or 'https://api.openai.com/v1'
        self.temperature = float(temperature)

        if not self.api_key:
            logger.warning("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")

    def is_available(self) -> bool:
        return bool(self.api_key)

    @property
    def name(self) -> str:
        return f"OpenAI ({self.model})"

    def generate_sql(
        self,
        question: str,
        schema_docs: str,
        conversation_history: Optional[list] = None,
    ) -> Optional[str]:
        if not self.is_available():
            logger.error("OpenAI API key not available", exc_info=True)
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
        return self._chat(messages, temperature=float(temperature), max_tokens=int(max_tokens))

    def _chat(self, messages: list[dict], *, temperature: float, max_tokens: int) -> Optional[str]:
        if not self.is_available():
            logger.error("OpenAI API key not available", exc_info=True)
            return None

        input_items = [self._message_to_input_item(m) for m in messages]
        request_payload = {
            'model': self.model,
            'input': input_items,
            'temperature': float(temperature),
            'max_output_tokens': int(max_tokens),
        }

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "OpenAI request: endpoint=%s/responses model=%s messages=%s temperature=%s max_output_tokens=%s",
                self.base_url,
                self.model,
                len(input_items),
                request_payload["temperature"],
                request_payload["max_output_tokens"],
            )

        if self.verbose:
            lines = [
                "",
                "=" * 20,
                "VERBOSE: OpenAI API Request",
                "=" * 20,
                f"Endpoint: {self.base_url}/responses",
                f"Model: {self.model}",
                f"CONVERSATION ({len(input_items)} messages):",
                "-" * 20,
            ]
            for i, msg in enumerate(input_items):
                role = str(msg.get('role', '')).upper()
                content = msg.get('content', [])
                preview = ''
                if content:
                    text = content[0].get('text', '') if isinstance(content, list) else str(content)
                    preview = text[:200] + '...' if len(text) > 200 else text
                lines.append(f"{i+1}. {role}: {preview}")
            lines.extend(
                [
                    "-" * 20,
                    "API Parameters:",
                    f"   temperature: {request_payload['temperature']}",
                    f"   max_output_tokens: {request_payload['max_output_tokens']}",
                    f"   timeout: {self.timeout}s",
                    "=" * 20,
                    "",
                ]
            )
            self._log_lines(logging.INFO, "\n".join(lines))

        response = None
        try:
            response = requests.post(
                f"{self.base_url}/responses",
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                },
                json=request_payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            if self.verbose:
                lines = [
                    "=" * 20,
                    "VERBOSE: OpenAI API Response",
                    "=" * 20,
                    f"Response Status: {response.status_code}",
                ]
                usage = data.get('usage') or {}
                if usage:
                    lines.extend(
                        [
                            "Token Usage:",
                            f"   Input tokens: {usage.get('input_tokens', 0)}",
                            f"   Output tokens: {usage.get('output_tokens', 0)}",
                        ]
                    )
                text_preview = (self._extract_output_text(data) or '')
                if text_preview:
                    preview = text_preview[:500] + ('...' if len(text_preview) > 500 else '')
                    lines.extend(
                        [
                            "RAW RESPONSE (text):",
                            "-" * 20,
                            preview,
                            "-" * 20,
                        ]
                    )
                lines.extend(
                    [
                        "=" * 20,
                        "",
                    ]
                )
                self._log_lines(logging.INFO, "\n".join(lines))

            if logger.isEnabledFor(logging.DEBUG):
                usage = data.get('usage') or {}
                text_preview = (self._extract_output_text(data) or '')
                preview = text_preview[:300] + ('...' if len(text_preview) > 300 else '')
                logger.debug(
                    "OpenAI response: status=%s input_tokens=%s output_tokens=%s text_preview=%s",
                    response.status_code,
                    usage.get('input_tokens', 0),
                    usage.get('output_tokens', 0),
                    preview,
                )

            usage = data.get('usage') or {}
            if usage:
                logger.info(
                    "OpenAI API call: %s input + %s output = %s total tokens",
                    usage.get('input_tokens', 0),
                    usage.get('output_tokens', 0),
                    usage.get('total_tokens', usage.get('input_tokens', 0) + usage.get('output_tokens', 0)),
                )

            return self._extract_output_text(data)

        except requests.exceptions.HTTPError as e:
            body = ""
            try:
                body = response.text if response is not None else ""
            except Exception:
                body = ""
            if body:
                logger.error("OpenAI API error body: %s", self._sanitize_text(body[:2000]))
            logger.error("OpenAI API request failed: %s", e, exc_info=True)
            return None
        except requests.exceptions.Timeout as e:
            logger.error("OpenAI API timeout: %s", e, exc_info=True)
            return None
        except requests.exceptions.RequestException as e:
            logger.error("OpenAI API request failed: %s", e, exc_info=True)
            return None
        except KeyError as e:
            logger.error("Unexpected OpenAI API response format: %s", e, exc_info=True)
            return None
        except Exception as e:
            logger.error("OpenAI generation failed: %s", e, exc_info=True)
            return None

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

    def _sanitize_text(self, text: str) -> str:
        if not isinstance(text, str):
            text = str(text)
        # Replace invalid surrogate code points to keep UTF-8 logging safe.
        return text.encode('utf-8', 'replace').decode('utf-8')

    def _clean_sql(self, sql: str) -> str:
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
