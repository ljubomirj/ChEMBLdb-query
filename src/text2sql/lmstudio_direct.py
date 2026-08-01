#!/usr/bin/env python3
"""
Local OpenAI-compatible provider (llama.cpp / mlx-lm) for Text-to-SQL.
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


class LlamaCppProvider(Text2SQLProvider):
    """
    Text-to-SQL provider using a local OpenAI-compatible endpoint (llama.cpp).
    """
    ENV_PREFIX = "LLAMACPP"
    PROVIDER_LABEL = "LlamaCpp"
    DEFAULT_BASE_URL = "http://127.0.0.1:1234/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = 'minimax-m2.1',
        timeout: int = 600,
        verbose: bool = False,
        base_url: Optional[str] = None,
        temperature: float = 1.0,
    ) -> None:
        env_prefix = self.ENV_PREFIX
        self.api_key = api_key or os.getenv(f'{env_prefix}_API_KEY') or os.getenv('OPENAI_API_KEY')
        self.model = model
        self.timeout = timeout
        self.verbose = verbose
        self.base_url = base_url or os.getenv(f'{env_prefix}_BASE_URL') or self.DEFAULT_BASE_URL
        if self.base_url:
            cleaned = self.base_url.rstrip('/')
            if not cleaned.endswith('/v1'):
                cleaned = f"{cleaned}/v1"
            self.base_url = cleaned
        self.temperature = float(temperature)

    def is_available(self) -> bool:
        # Local endpoint may not require an API key.
        return True

    @property
    def name(self) -> str:
        return f"{self.PROVIDER_LABEL} ({self.model})"

    def generate_sql(
        self,
        question: str,
        schema_docs: str,
        conversation_history: Optional[list] = None,
    ) -> Optional[str]:
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
                {'role': 'user', 'content': user_prompt},
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
        response_format: Optional[dict] = None,
    ) -> Optional[str]:
        return self._chat(
            messages,
            temperature=float(temperature),
            max_tokens=int(max_tokens),
            response_format=response_format,
        )

    def _chat(
        self,
        messages: list[dict],
        *,
        temperature: float,
        max_tokens: int,
        response_format: Optional[dict],
    ) -> Optional[str]:
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

            self._log_lines(
                logging.INFO,
                "\n".join(["", "=" * 20, f"VERBOSE: {self.PROVIDER_LABEL} API Request", "=" * 20]),
            )
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

        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'

        response = None
        try:
            response = requests.post(
                f"{self.base_url}/responses",
                headers=headers,
                json=request_payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            if self.verbose:
                self._log_lines(
                    logging.INFO,
                    "\n".join(["=" * 20, f"VERBOSE: {self.PROVIDER_LABEL} API Response", "=" * 20]),
                )
                body_lines = [
                    f"Response Status: {response.status_code}",
                ]
                if 'usage' in data:
                    usage = data['usage']
                    body_lines.extend(
                        [
                            "Token Usage:",
                            f"   Input tokens: {usage.get('input_tokens', 0)}",
                            f"   Output tokens: {usage.get('output_tokens', 0)}",
                        ]
                    )
                raw_content = self._extract_output_text(data) or ''
                reasoning_content = ''
                body_lines.extend(
                    [
                        "RAW RESPONSE:",
                        "-" * 20,
                        raw_content,
                        "-" * 20,
                    ]
                )
                if reasoning_content:
                    body_lines.extend(
                        [
                            "RAW REASONING:",
                            "-" * 20,
                            reasoning_content,
                            "-" * 20,
                        ]
                    )
                self._emit_raw_block("\n".join(body_lines))
                self._log_lines(logging.INFO, "\n".join(["=" * 20, ""]))

            if 'usage' in data:
                usage = data['usage']
                logger.info(
                    "%s API call: %s input + %s output = %s total tokens",
                    self.PROVIDER_LABEL,
                    usage.get('input_tokens', 0),
                    usage.get('output_tokens', 0),
                    usage.get('total_tokens', usage.get('input_tokens', 0) + usage.get('output_tokens', 0)),
                )

            content = self._extract_output_text(data)
            return content.strip() if content else ""

        except requests.exceptions.HTTPError as e:
            body = ""
            try:
                body = response.text if response is not None else ""
            except Exception:
                body = ""
            if body:
                logger.error("%s API error body: %s", self.PROVIDER_LABEL, self._sanitize_text(body[:2000]))
            logger.error("%s API request failed: %s", self.PROVIDER_LABEL, e, exc_info=True)
            return None
        except requests.exceptions.Timeout as e:
            logger.error("%s API timeout: %s", self.PROVIDER_LABEL, e, exc_info=True)
            return None
        except requests.exceptions.RequestException as e:
            logger.error("%s API request failed: %s", self.PROVIDER_LABEL, e, exc_info=True)
            return None
        except KeyError as e:
            logger.error("Unexpected %s API response format: %s", self.PROVIDER_LABEL, e, exc_info=True)
            return None
        except Exception as e:
            logger.error("%s generation failed: %s", self.PROVIDER_LABEL, e, exc_info=True)
            return None

    def _sanitize_text(self, text: str) -> str:
        if not isinstance(text, str):
            text = str(text)
        return text.encode('utf-8', 'replace').decode('utf-8')

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
        sql = re.sub(r'<think>.*?</think>', '', sql, flags=re.DOTALL | re.IGNORECASE)
        sql = re.sub(r'<reasoning>.*?</reasoning>', '', sql, flags=re.DOTALL | re.IGNORECASE)

        sql = re.sub(r'```sql\n?', '', sql)
        sql = re.sub(r'```\n?', '', sql)

        keyword_match = re.search(r'\b(SELECT|WITH|INSERT|UPDATE|DELETE|CREATE)\b', sql, flags=re.IGNORECASE)
        if keyword_match:
            sql = sql[keyword_match.start():]

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


class MlxLMProvider(LlamaCppProvider):
    """
    Text-to-SQL provider using a local OpenAI-compatible endpoint (mlx-lm).
    """
    ENV_PREFIX = "MLXLM"
    PROVIDER_LABEL = "MLXLM"
    DEFAULT_BASE_URL = "http://127.0.0.1:1234/v1"
