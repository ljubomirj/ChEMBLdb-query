#!/usr/bin/env python3
"""
Local transformer-based LLM Text-to-SQL provider.
"""

import re
import logging
from typing import Optional

from .base import Text2SQLProvider

logger = logging.getLogger(__name__)

# Try to import transformers
try:
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False


class LocalLLMProvider(Text2SQLProvider):
    """
    Text-to-SQL provider using local transformer models.

    Uses HuggingFace transformers to load and run models locally.
    Slow on CPU, fast on GPU, but completely free (no API costs).
    """

    def __init__(self, model_name: str = 'Qwen/Qwen2.5-3B-Instruct', temperature: float = 1.0):
        """
        Initialize local LLM provider.

        Args:
            model_name: HuggingFace model identifier
        """
        self.model_name = model_name
        self.temperature = float(temperature)
        self.model = None
        self.tokenizer = None
        self._load_model()

    def is_available(self) -> bool:
        """Check if local model loaded successfully."""
        return self.model is not None and self.tokenizer is not None

    @property
    def name(self) -> str:
        """Provider name."""
        return f"Local LLM ({self.model_name})"

    def _load_model(self):
        """Load the LLM model from HuggingFace."""
        if not HAS_TRANSFORMERS:
            logger.error("transformers not installed. Install with: pip install transformers torch tokenizers")
            return

        self._log_lines(logging.INFO, "\n".join(["", "=" * 20, "Local LLM Load", "=" * 20]))
        self._emit_raw_block(f"Loading {self.model_name}...\nThis may take a minute on first run (downloading model)...")
        self._log_lines(logging.INFO, "\n".join(["=" * 20, ""]))

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
                device_map='auto' if torch.cuda.is_available() else 'cpu',
                low_cpu_mem_usage=True
            )
            self._log_lines(logging.INFO, "\n".join(["", "=" * 20, "Local LLM Loaded", "=" * 20]))
            self._emit_raw_block(
                "Model loaded successfully!\n"
                f"Model: {self.model_name}\n"
                f"Device: {'CUDA' if torch.cuda.is_available() else 'CPU'}"
            )
            self._log_lines(logging.INFO, "\n".join(["=" * 20, ""]))

        except Exception as e:
            logger.error(f"Failed to load model {self.model_name}: {e}", exc_info=True)
            error_str = str(e)

            # Provide specific fixes for common errors
            if "TokenizersBackend" in error_str or "tokenizers" in error_str.lower():
                self._log_lines(logging.INFO, "\n".join(["", "=" * 20, "Local LLM Fixes", "=" * 20]))
                self._emit_raw_block(
                    "Common fixes:\n"
                    "1. Install tokenizers: uv pip install --no-cache-dir tokenizers\n"
                    "2. Reinstall transformers: uv pip install --no-cache-dir --upgrade transformers\n"
                    "3. Run fix script: bash tools/fix_tokenizers.sh\n"
                    "4. Clear cache: rm -rf ~/.cache/huggingface/hub/*"
                )
                self._log_lines(logging.INFO, "\n".join(["=" * 20, ""]))
            elif "out of memory" in error_str.lower() or "oom" in error_str.lower():
                self._log_lines(logging.INFO, "\n".join(["", "=" * 20, "Local LLM Memory", "=" * 20]))
                self._emit_raw_block(
                    "Memory issue detected. Try:\n"
                    "- Using a smaller model\n"
                    "- Closing other applications\n"
                    "- Setting PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0 (for Mac)"
                )
                self._log_lines(logging.INFO, "\n".join(["=" * 20, ""]))

            self._log_lines(logging.INFO, "\n".join(["", "=" * 20, "Local LLM Fallback", "=" * 20]))
            self._emit_raw_block("Falling back to manual SQL entry")
            self._log_lines(logging.INFO, "\n".join(["=" * 20, ""]))
            self.model = None

    def generate_sql(
        self,
        question: str,
        schema_docs: str,
        conversation_history: Optional[list] = None
    ) -> Optional[str]:
        """
        Generate SQL using local LLM.

        Args:
            question: Natural language question
            schema_docs: Database schema documentation
            conversation_history: Optional conversation history (not used for local LLM)

        Returns:
            Generated SQL query, or None if failed
        """
        if not self.is_available():
            logger.error("Local LLM not available")
            return None

        # Note: Local LLM doesn't use conversation_history - always generates fresh
        # This could be enhanced in the future to support context

        # Create prompt
        prompt = f"""You are a SQL expert for a chemistry database called ChEMBLdb.

DATABASE SCHEMA:
{schema_docs}

IMPORTANT RULES:
1. ALWAYS use the "latest data pattern" for temporal tables (shown in schema docs)
2. Start temporal queries with: WITH latest AS (SELECT MAX(asof_utc) as max_date FROM table_name)
3. Market cap is in USD - divide by 1e9 for billions, 1e12 for trillions
4. Join via labels: equities.company_label → companies.label
5. For company info + stock info, join: equity_attributes → equities → companies
6. Only generate SELECT queries (no INSERT/UPDATE/DELETE)
7. Return ONLY the SQL query, no explanation
8. The 'equities' table uses valid_from/valid_to, NOT asof_utc
9. Only *_attributes tables and index_members have asof_utc

USER QUESTION: {question}

SQL QUERY:"""

        try:
            # Generate
            inputs = self.tokenizer(prompt, return_tensors="pt")
            if torch.cuda.is_available():
                inputs = {k: v.cuda() for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=512,
                    temperature=self.temperature,
                    do_sample=True,
                    top_p=0.9,
                    pad_token_id=self.tokenizer.eos_token_id
                )

            # Decode
            generated = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            # Extract SQL (after the prompt)
            sql = generated.split("SQL QUERY:")[-1].strip()

            # Clean up
            sql = self._clean_sql(sql)

            return sql

        except Exception as e:
            logger.error(f"Local LLM generation failed: {e}", exc_info=True)
            return None

    def generate_text(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> Optional[str]:
        """
        Generate free-form text from a chat-style messages array.

        This is a lightweight implementation and may be lower quality than API providers.
        """
        if not self.is_available():
            logger.error("Local LLM not available")
            return None

        # Flatten messages into a single prompt.
        prompt_parts: list[str] = []
        for msg in messages:
            role = str(msg.get('role', 'user')).upper()
            content = msg.get('content', '')
            if not isinstance(content, str):
                content = str(content)
            prompt_parts.append(f"{role}:\n{content}\n")

        prompt = "\n".join(prompt_parts) + "\nASSISTANT:\n"

        try:
            inputs = self.tokenizer(prompt, return_tensors="pt")
            if torch.cuda.is_available():
                inputs = {k: v.cuda() for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=int(max_tokens),
                    temperature=float(temperature),
                    do_sample=True,
                    top_p=0.9,
                    pad_token_id=self.tokenizer.eos_token_id
                )

            generated = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            # Return everything after the final assistant marker.
            return generated.split("ASSISTANT:")[-1].strip()

        except Exception as e:
            logger.error(f"Local LLM text generation failed: {e}", exc_info=True)
            return None

    def _clean_sql(self, sql: str) -> str:
        """
        Clean up generated SQL.

        Args:
            sql: Raw SQL from LLM

        Returns:
            Cleaned SQL query
        """
        # Remove markdown code blocks
        sql = re.sub(r'```sql\n?', '', sql)
        sql = re.sub(r'```\n?', '', sql)

        # Remove leading/trailing whitespace
        sql = sql.strip()

        # Remove explanatory text after query
        if '\n\n' in sql:
            sql = sql.split('\n\n')[0]

        # Take only up to first semicolon
        if ';' in sql:
            sql = sql.split(';')[0] + ';'

        return sql.strip()

    def close(self):
        """Clean up model resources."""
        if self.model is not None:
            del self.model
            self.model = None
        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None

        # Clear CUDA cache if available
        if HAS_TRANSFORMERS and torch.cuda.is_available():
            torch.cuda.empty_cache()

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
