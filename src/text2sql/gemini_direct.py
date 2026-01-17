#!/usr/bin/env python3
"""
Gemini API direct provider for Text-to-SQL using the generateContent API.
"""

import os
import re
import logging
from typing import Optional, Iterable

import requests

from .base import Text2SQLProvider

logger = logging.getLogger(__name__)


class GeminiProvider(Text2SQLProvider):
    """
    Text-to-SQL provider using the Gemini API directly.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = 'gemini-3-flash-preview',
        timeout: int = 180,
        verbose: bool = False,
        base_url: Optional[str] = None,
        temperature: float = 1.0,
    ) -> None:
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        self.model = model
        self.timeout = timeout
        self.verbose = verbose
        self.base_url = base_url or os.getenv('GEMINI_BASE_URL') or 'https://generativelanguage.googleapis.com/v1beta'
        self.temperature = float(temperature)

        if not self.api_key:
            logger.warning("Gemini API key not found. Set GEMINI_API_KEY environment variable.")

    def is_available(self) -> bool:
        return bool(self.api_key)

    @property
    def name(self) -> str:
        return f"Gemini ({self.model})"

    def generate_sql(
        self,
        question: str,
        schema_docs: str,
        conversation_history: Optional[list] = None,
    ) -> Optional[str]:
        if not self.is_available():
            logger.error("Gemini API key not available", exc_info=True)
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
    ) -> Optional[str]:
        return self._chat(messages, temperature=float(temperature), max_tokens=int(max_tokens))

    def _chat(self, messages: list[dict], *, temperature: float, max_tokens: int) -> Optional[str]:
        if not self.is_available():
            logger.error("Gemini API key not available", exc_info=True)
            return None

        system_instruction, contents = self._messages_to_contents(messages)
        request_payload = {
            'contents': contents,
            'generationConfig': {
                'temperature': float(temperature),
                'maxOutputTokens': int(max_tokens),
            },
        }
        if system_instruction:
            request_payload['system_instruction'] = {
                'parts': [{'text': system_instruction}],
            }

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "Gemini request: endpoint=%s/models/%s:generateContent messages=%s temperature=%s max_output_tokens=%s",
                self.base_url,
                self.model,
                len(contents),
                request_payload['generationConfig']['temperature'],
                request_payload['generationConfig']['maxOutputTokens'],
            )

        if self.verbose:
            self._log_lines(logging.INFO, "\n".join(["", "=" * 20, "VERBOSE: Gemini API Request", "=" * 20]))
            body_lines = [
                f"Endpoint: {self.base_url}/models/{self.model}:generateContent",
                f"Model: {self.model}",
                f"CONVERSATION ({len(contents)} messages):",
                "-" * 20,
            ]
            for i, msg in enumerate(contents):
                role = str(msg.get('role', '')).upper()
                parts = msg.get('parts', [])
                text = ''
                if parts:
                    text = str(parts[0].get('text', ''))
                preview = text[:200] + '...' if len(text) > 200 else text
                body_lines.append(f"{i+1}. {role}: {preview}")
            body_lines.extend(
                [
                    "-" * 20,
                    "API Parameters:",
                    f"   temperature: {request_payload['generationConfig']['temperature']}",
                    f"   maxOutputTokens: {request_payload['generationConfig']['maxOutputTokens']}",
                    f"   timeout: {self.timeout}s",
                ]
            )
            self._emit_raw_block("\n".join(body_lines))
            self._log_lines(logging.INFO, "\n".join(["=" * 20, ""]))

        response = None
        try:
            response = requests.post(
                f"{self.base_url}/models/{self.model}:generateContent",
                headers={
                    'x-goog-api-key': self.api_key,
                    'Content-Type': 'application/json',
                },
                json=request_payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            if self.verbose:
                self._log_lines(logging.INFO, "\n".join(["=" * 20, "VERBOSE: Gemini API Response", "=" * 20]))
                body_lines = [
                    f"Response Status: {response.status_code}",
                ]
                usage = data.get('usageMetadata') or {}
                if usage:
                    body_lines.extend(
                        [
                            "Token Usage:",
                            f"   Prompt tokens: {usage.get('promptTokenCount', 0)}",
                            f"   Output tokens: {usage.get('candidatesTokenCount', 0)}",
                            f"   Total tokens: {usage.get('totalTokenCount', 0)}",
                        ]
                    )
                text_preview = (self._extract_output_text(data) or '')
                if text_preview:
                    preview = text_preview[:500] + ('...' if len(text_preview) > 500 else '')
                    body_lines.extend(
                        [
                            "RAW RESPONSE (text):",
                            "-" * 20,
                            preview,
                            "-" * 20,
                        ]
                    )
                self._emit_raw_block("\n".join(body_lines))
                self._log_lines(logging.INFO, "\n".join(["=" * 20, ""]))

            usage = data.get('usageMetadata') or {}
            if usage:
                logger.info(
                    "Gemini API call: %s input + %s output = %s total tokens",
                    usage.get('promptTokenCount', 0),
                    usage.get('candidatesTokenCount', 0),
                    usage.get('totalTokenCount', 0),
                )

            if logger.isEnabledFor(logging.DEBUG):
                text_preview = (self._extract_output_text(data) or '')
                preview = text_preview[:300] + ('...' if len(text_preview) > 300 else '')
                logger.debug(
                    "Gemini response: status=%s text_preview=%s",
                    response.status_code,
                    preview,
                )

            return self._extract_output_text(data)

        except requests.exceptions.HTTPError as e:
            body = ""
            try:
                body = response.text if response is not None else ""
            except Exception:
                body = ""
            if body:
                logger.error("Gemini API error body: %s", self._sanitize_text(body[:2000]))
            logger.error("Gemini API request failed: %s", e, exc_info=True)
            return None
        except requests.exceptions.Timeout as e:
            logger.error("Gemini API timeout: %s", e, exc_info=True)
            return None
        except requests.exceptions.RequestException as e:
            logger.error("Gemini API request failed: %s", e, exc_info=True)
            return None
        except KeyError as e:
            logger.error("Unexpected Gemini API response format: %s", e, exc_info=True)
            return None
        except Exception as e:
            logger.error("Gemini generation failed: %s", e, exc_info=True)
            return None

    def _messages_to_contents(self, messages: Iterable[dict]) -> tuple[str, list[dict]]:
        system_parts: list[str] = []
        contents: list[dict] = []
        for msg in messages:
            role = str(msg.get('role', 'user'))
            content = msg.get('content', '')
            text = self._coerce_text(content)
            if role == 'system':
                if text:
                    system_parts.append(text)
                continue
            out_role = 'model' if role == 'assistant' else 'user'
            if text:
                contents.append({'role': out_role, 'parts': [{'text': self._sanitize_text(text)}]})
        system_instruction = "\n\n".join(system_parts).strip()
        return system_instruction, contents

    def _coerce_text(self, content: object) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for part in content:
                if isinstance(part, dict) and 'text' in part:
                    parts.append(str(part.get('text', '')))
                elif isinstance(part, str):
                    parts.append(part)
                else:
                    parts.append(str(part))
            return "\n".join(parts)
        return str(content)

    def _extract_output_text(self, data: dict) -> Optional[str]:
        if not isinstance(data, dict):
            return None
        candidates = data.get('candidates')
        if not isinstance(candidates, list) or not candidates:
            return None
        content = candidates[0].get('content', {})
        parts = content.get('parts', []) if isinstance(content, dict) else []
        chunks: list[str] = []
        if isinstance(parts, list):
            for part in parts:
                if isinstance(part, dict) and 'text' in part:
                    chunks.append(self._sanitize_text(str(part.get('text', ''))))
        text = "\n".join(s for s in chunks if s)
        return text.strip() if text else None

    def _sanitize_text(self, text: str) -> str:
        if not isinstance(text, str):
            text = str(text)
        return text.encode('utf-8', 'replace').decode('utf-8')

    def _clean_sql(self, sql: str) -> str:
        sql = re.sub(r'<think>.*?</think>', '', sql, flags=re.DOTALL | re.IGNORECASE)
        sql = re.sub(r'<reasoning>.*?</reasoning>', '', sql, flags=re.DOTALL | re.IGNORECASE)

        sql = re.sub(r'```sql\n?', '', sql)
        sql = re.sub(r'```\n?', '', sql)

        # Strip any leading non-SQL artifacts (e.g., stray citation text) before the first SQL keyword.
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
