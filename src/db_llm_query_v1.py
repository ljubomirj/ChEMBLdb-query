#!/usr/bin/env python3
"""
LLM Text-to-SQL Query Interface (v1) for ChEMBL (SQLite)

Flow:
1) System prompt SP contains:
   - Database schema docs: tables, columns, and sampled rows per table (for the data semantics).
2) User question UQ initial question is provided by the user, once only at start.
3) A prompt-writer LLM produces UP_1 from (SP, UQ).
4) For iterations n=1..N:
   - SQL-writer LLM produces SQL_n from (SP, UQ, UP_n, and prior M iterations of history).
   - We run SQL_n locally against the ChEMBL SQLite DB producing result table RES_n; the summary is (row count, columns, samples, errors).
   - Judge LLM produces judgement J_n from (SP, UQ, UP_n, SQL_n, RES_n summary, last M iterations history), including qualitative evaluation + improvement advice + score [0,1] + YES/NO.
   - If YES (or score >= threshold), stop.
   - Else: new cycle starts with new {UP_n,SQL_n,RES_n summary,J_n eval+improv+score+NO} added to the M-length hsotory.
   - Itreration (n+1): prompt-writer produces UP_(n+1) from (SP, UQ, prior M iteration of history)
The specification in more detail is laid down at the end of this file.

TODO
1) Turn the current sequence into a tree (search); then
2) Prune the tree back into a lattice (search) to keep it manageable.
"""

import argparse
import contextlib
import contextvars
import hashlib
import json
import logging
import os
import random
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple

import sqlite3
import polars as pl
import requests
import io

# Ensure the script directory is on sys.path so `import text2sql` works both when executed
# as a script (`python src/db_llm_query_v1.py`) and when imported as a module
# (e.g., via a console_script entry point).
_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from text2sql import create_provider
from text2sql.env import load_dotenv_once

_LOG_STAGE_STACK: contextvars.ContextVar[Tuple[str, ...]] = contextvars.ContextVar(
    "log_stage_stack",
    default=(),
)
_LOG_RECORD_FACTORY = logging.getLogRecordFactory()


def _format_log_stage() -> str:
    stack = _LOG_STAGE_STACK.get()
    return " > ".join(stack) if stack else "INIT"


def _stage_record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
    record = _LOG_RECORD_FACTORY(*args, **kwargs)
    record.stage = _format_log_stage()
    return record


@contextlib.contextmanager
def log_stage(stage: str) -> Iterator[None]:
    stack = _LOG_STAGE_STACK.get()
    token = _LOG_STAGE_STACK.set(stack + (stage,))
    try:
        yield
    finally:
        _LOG_STAGE_STACK.reset(token)


LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(stage)s - %(message)s'

logging.setLogRecordFactory(_stage_record_factory)
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
)
logger = logging.getLogger(__name__)


STAGE_LABELS = (
    ("SP", "SystemPrompt"),
    ("UQ", "UserQuestion"),
    ("ITER_n", "Iteration_n"),
    ("UP_n", "UserPrompt_n"),
    ("SQL_n", "SqlWrite_n"),
    ("RES_n", "Result_n"),
    ("J_n", "Judge_n"),
    ("INIT", "ProviderModelSelection"),
)


def _format_param_value(value: Any) -> str:
    return repr(value)


def log_stage_labels() -> None:
    logger.info("Stage labels (short -> long):")
    for short, long_name in STAGE_LABELS:
        logger.info("  %s = %s", short, long_name)


def log_effective_params(
    args: argparse.Namespace,
    *,
    provider: str,
    run_id: Optional[str],
    query: Optional[str],
    save_file: Optional[str],
) -> None:
    logger.info("Effective parameters:")
    derived_params = [
        ("query", query),
        ("provider", provider),
        ("run_id", run_id),
        ("save_file", save_file),
    ]
    for key, value in derived_params:
        logger.info("  %s = %s", key, _format_param_value(value))
    logger.info("CLI arguments (post-defaults):")
    for key, value in sorted(vars(args).items()):
        logger.info("  %s = %s", key, _format_param_value(value))


CHEAP_MODELS = [
    'z-ai/glm-4.7',
    'z-ai/glm-4.6v',
    'z-ai/glm-4.6:exacto',
    'z-ai/glm-4.5-air:free',
    'minimax/minimax-m2.1',
    'anthropic/claude-4.5-haiku',
    'deepseek/deepseek-v3.2-speciale',
    'deepseek/deepseek-v3.2',
    'minimax/minimax-m2.1',
    'openai/gpt-5.1-codex-mini',
    'openai/gpt-5-nano',
    'x-ai/grok-4.1-fast',
    'x-ai/grok-code-fast-1',
    'google/gemini-3-flash-preview',
    'qwen/qwen3-coder-flash',
]

EXPENSIVE_MODELS = [
    'openai/gpt-5.2',
    'openai/gpt-5.2-chat',
    'openai/gpt-5.1-codex-max',
    'openai/gpt-5.1-codex',
    'anthropic/claude-opus-4.5',
    'anthropic/claude-sonnet-4.5',
    'anthropic/claude-haiku-4.5',
    'x-ai/grok-4',
    'google/gemini-3-pro-preview',
    'qwen/qwen3-coder-plus',
    'qwen/qwen3-coder:exacto',
]

SUPER_MODELS = [
    'openai/gpt-5.2-pro',
]

ALL_MODELS = CHEAP_MODELS + EXPENSIVE_MODELS + SUPER_MODELS

# Provider-specific model lists (non-OpenRouter)
CEREBRAS_MODELS = [
    'zai-glm-4.7',
]

DEEPSEEK_MODELS = [
    'deepseek-reasoner',
    'deepseek-chat',
]

ANTHROPIC_MODELS = [
    'claude-haiku-4.5',
    'claude-sonnet-4.5',
    'claude-opus-4.5',
]


def cic_find_primes(limit: int) -> List[int]:
    sieve = [True] * (limit + 1)
    sieve[0] = sieve[1] = False
    for i in range(2, int(limit**0.5) + 1):
        if sieve[i]:
            sieve[i * i :: i] = [False] * len(sieve[i * i :: i])
    return [i for i, is_prime in enumerate(sieve) if is_prime]


def cic_schedule(n: int) -> List[int]:
    schedule: List[int] = []
    primes = cic_find_primes(100)
    for i in range(n):
        prime = primes[i % len(primes)]
        schedule.append((i * prime) % 233)
    return schedule


def get_model_list(category: str, provider: str = 'openrouter') -> List[str]:
    provider_lower = (provider or 'openrouter').lower()
    if provider_lower == 'cerebras':
        return CEREBRAS_MODELS
    if provider_lower == 'deepseek':
        return DEEPSEEK_MODELS
    if provider_lower == 'anthropic':
        return ANTHROPIC_MODELS
    if provider_lower == 'local':
        return []

    if category == 'cheap':
        return CHEAP_MODELS
    if category == 'expensive':
        return EXPENSIVE_MODELS
    if category == 'super':
        return SUPER_MODELS
    if category == 'all':
        return ALL_MODELS
    raise ValueError(f"Invalid model category: {category}")


_OPENROUTER_CONTEXT_CACHE: Optional[Dict[str, int]] = None


def filter_models_by_context(models: List[str], min_context: int) -> List[str]:
    if min_context <= 0:
        return models

    global _OPENROUTER_CONTEXT_CACHE
    try:
        if _OPENROUTER_CONTEXT_CACHE is None:
            _OPENROUTER_CONTEXT_CACHE = get_openrouter_context_map()
        context_map = _OPENROUTER_CONTEXT_CACHE
    except Exception:
        logger.warning("Failed to fetch OpenRouter models for context filtering; using unfiltered list.", exc_info=True)
        return models

    filtered = [m for m in models if context_map.get(m, 0) >= min_context]
    if not filtered:
        logger.error("No OpenRouter models meet min_context=%s.", min_context)
        return []

    if len(filtered) != len(models):
        logger.info("Filtered OpenRouter models by context >= %s: %s -> %s", min_context, len(models), len(filtered))
    return filtered


def get_openrouter_context_map() -> Dict[str, int]:
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        logger.warning("OPENROUTER_API_KEY not set; cannot fetch OpenRouter model context.")
        return {}

    response = requests.get(
        'https://openrouter.ai/api/v1/models',
        headers={'Authorization': f'Bearer {api_key}'},
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    model_data = data.get('data', [])
    return {
        m.get('id'): int(m.get('context_length', 0) or 0)
        for m in model_data
        if isinstance(m, dict)
    }


def generate_model_schedule(num_retries: int, models: List[str], cycle_method: str) -> List[str]:
    schedule: List[str] = []
    num_models = len(models)
    if num_models == 0:
        return schedule

    if cycle_method == 'random':
        last_idx = -1
        for _ in range(num_retries):
            idx = random.randint(0, num_models - 1)
            if idx == last_idx and num_models > 1:
                idx = (idx + 1) % num_models
            schedule.append(models[idx])
            last_idx = idx
        return schedule

    if cycle_method == 'orderly':
        for i in range(num_retries):
            schedule.append(models[i % num_models])
        return schedule

    if cycle_method == 'cicada':
        positions = cic_schedule(num_retries)
        for pos in positions:
            schedule.append(models[pos % num_models])
        return schedule

    raise ValueError(f"Invalid cycle method: {cycle_method}")


def _truncate_cell(v: object, max_len: int) -> str:
    s = "NULL" if v is None else str(v)
    s = s.replace("\n", "\\n")
    if len(s) > max_len:
        return s[: max_len - 3] + "..."
    return s


def _quote_ident(name: str) -> str:
    safe = name.replace('"', '""')
    return f'"{safe}"'


def _list_sqlite_tables(conn: sqlite3.Connection) -> List[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def generate_schema_docs_sqlite(
    *,
    db_path: str,
    output_path: Optional[str],
    sample_rows: int = 3,
    max_cell_len: int = 80,
) -> str:
    conn = sqlite3.connect(db_path)
    try:
        tables = _list_sqlite_tables(conn)
        lines: List[str] = []
        lines.append("# ChEMBL SQLite schema (auto-generated)")
        lines.append(f"Database: {db_path}")
        lines.append(f"Tables: {len(tables)}")
        lines.append("")

        for table in tables:
            lines.append(f"## Table: {table}")
            try:
                col_rows = conn.execute(f"PRAGMA table_info({_quote_ident(table)})").fetchall()
            except Exception as e:
                lines.append(f"ERROR: failed to read columns: {e}")
                lines.append("")
                continue

            if col_rows:
                lines.append("Columns:")
                for r in col_rows:
                    # PRAGMA table_info: cid, name, type, notnull, dflt_value, pk
                    col_name = str(r[1])
                    col_type = str(r[2]) if r[2] is not None else ""
                    notnull = "NOT NULL" if r[3] else "NULL"
                    pk = "PK" if r[5] else ""
                    extras = " ".join(x for x in [notnull, pk] if x)
                    lines.append(f"- {col_name} {col_type} {extras}".strip())
            else:
                lines.append("Columns: (none)")

            if sample_rows > 0:
                try:
                    cur = conn.execute(f"SELECT * FROM {_quote_ident(table)} LIMIT {int(sample_rows)}")
                    rows = cur.fetchall()
                    cols = [d[0] for d in (cur.description or [])]
                    if rows:
                        lines.append("")
                        lines.append("Sample rows:")
                        lines.append("| " + " | ".join(cols) + " |")
                        lines.append("|" + "|".join(["---"] * len(cols)) + "|")
                        for row in rows:
                            cells = [_truncate_cell(v, max_cell_len) for v in row]
                            lines.append("| " + " | ".join(cells) + " |")
                    else:
                        lines.append("")
                        lines.append("Sample rows: (none)")
                except Exception as e:
                    lines.append("")
                    lines.append(f"Sample rows ERROR: {e}")

            lines.append("")

        docs = "\n".join(lines)
        if output_path:
            out_path = Path(output_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(docs)
        return docs
    finally:
        conn.close()


def sample_result_rows(
    result_df: pl.DataFrame,
    max_samples: int = 9,
    max_cell_len: int = 60,
) -> List[Dict[str, object]]:
    if result_df is None or result_df.height == 0:
        return []

    n = result_df.height
    if n <= max_samples:
        indices = list(range(n))
    elif max_samples <= 9:
        indices: List[int] = []
        indices.extend(list(range(min(3, n))))
        if n > 6:
            mid_start = max(0, n // 2 - 1)
            indices.extend([mid_start + i for i in range(min(3, n - mid_start))])
        if n > 9:
            indices.extend(list(range(max(0, n - 3), n)))
        indices = sorted(set(indices))[:max_samples]
    else:
        if max_samples >= n:
            indices = list(range(n))
        else:
            step = (n - 1) / (max_samples - 1)
            indices = [int(round(i * step)) for i in range(max_samples)]
            indices = sorted(set(indices))
            if len(indices) < max_samples:
                for i in range(n):
                    if i not in indices:
                        indices.append(i)
                        if len(indices) >= max_samples:
                            break
                indices = sorted(indices[:max_samples])

    try:
        sampled = result_df.take(pl.Series(indices))
    except Exception:
        sampled = result_df.head(min(max_samples, n))
        indices = list(range(sampled.height))

    rows = sampled.rows()
    out: List[Dict[str, object]] = []
    for local_i, row in enumerate(rows):
        idx = indices[local_i] if local_i < len(indices) else local_i
        position = 'head' if idx < 3 else ('tail' if idx >= n - 3 else 'middle')
        out.append(
            {
                'position': f'{position} (row {idx + 1})',
                'data': tuple(_truncate_cell(v, max_cell_len) for v in row),
            }
        )
    return out


def _evenly_spaced_indices(count: int, max_items: int) -> List[int]:
    if count <= 0 or max_items <= 0:
        return []
    if max_items >= count:
        return list(range(count))
    if max_items == 1:
        return [0]
    step = (count - 1) / (max_items - 1)
    indices = [int(round(i * step)) for i in range(max_items)]
    return sorted(set(indices))


def sample_result_rows_stratified(
    result_df: pl.DataFrame,
    *,
    strata_cols: Sequence[str],
    max_samples: int,
    max_cell_len: int,
) -> List[Dict[str, object]]:
    if result_df is None or result_df.height == 0:
        return []
    if not strata_cols or any(c not in result_df.columns for c in strata_cols):
        return sample_result_rows(result_df, max_samples=max_samples, max_cell_len=max_cell_len)

    df = result_df.with_row_index(name="_row_idx")
    groups = (
        df.group_by(list(strata_cols))
        .agg(
            pl.col("_row_idx").alias("_row_idx"),
            pl.len().alias("_group_size"),
        )
        .sort(list(strata_cols))
    )
    if groups.height == 0:
        return sample_result_rows(result_df, max_samples=max_samples, max_cell_len=max_cell_len)

    group_indices = list(range(groups.height))
    if groups.height > max_samples:
        group_indices = _evenly_spaced_indices(groups.height, max_samples)
        groups = groups.take(pl.Series(group_indices))

    sizes = groups.get_column("_group_size").to_list()
    row_lists = groups.get_column("_row_idx").to_list()
    group_count = len(sizes)
    if group_count == 0:
        return sample_result_rows(result_df, max_samples=max_samples, max_cell_len=max_cell_len)

    target_total = min(max_samples, int(result_df.height))
    per_group = [1] * group_count
    remaining = max(0, target_total - group_count)
    if remaining > 0:
        total_size = sum(sizes) or 1
        extras = [int(round(remaining * (s / total_size))) for s in sizes]
        diff = remaining - sum(extras)
        if diff != 0:
            order = sorted(range(group_count), key=lambda i: sizes[i], reverse=True)
            step = 1 if diff > 0 else -1
            for i in range(abs(diff)):
                idx = order[i % group_count]
                if step < 0 and extras[idx] == 0:
                    continue
                extras[idx] += step
        per_group = [base + extra for base, extra in zip(per_group, extras)]

    sample_indices: List[int] = []
    for i in range(group_count):
        row_list = row_lists[i] if i < len(row_lists) else []
        if not row_list:
            continue
        want = min(int(per_group[i]), len(row_list))
        if want <= 0:
            continue
        chosen_pos = _evenly_spaced_indices(len(row_list), want)
        for pos in chosen_pos:
            sample_indices.append(int(row_list[pos]))

    if not sample_indices:
        return sample_result_rows(result_df, max_samples=max_samples, max_cell_len=max_cell_len)

    sample_indices = sorted(set(sample_indices))
    try:
        sampled = result_df.take(pl.Series(sample_indices))
    except Exception:
        sampled = result_df.head(min(max_samples, result_df.height))

    rows = sampled.rows()
    out: List[Dict[str, object]] = []
    for local_i, row in enumerate(rows):
        idx = sample_indices[local_i] if local_i < len(sample_indices) else local_i
        position = 'head' if idx < 3 else ('tail' if idx >= result_df.height - 3 else 'middle')
        out.append(
            {
                'position': f'{position} (row {idx + 1})',
                'data': tuple(_truncate_cell(v, max_cell_len) for v in row),
            }
        )
    return out


def _nonempty_lines(text: str) -> List[str]:
    return [ln.strip() for ln in (text or "").splitlines() if ln.strip()]


def parse_judge_output(text: str) -> Tuple[Optional[bool], Optional[float]]:
    """
    Preferred judge output (JSON):
      {"analysis": "...", "score": 0.93, "decision": "YES"}
    """
    cleaned = (text or "").strip()
    if cleaned:
        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned, flags=re.IGNORECASE | re.MULTILINE)
        cleaned = re.sub(r'\s*```\s*$', '', cleaned, flags=re.MULTILINE)
        start = cleaned.find('{')
        end = cleaned.rfind('}')
        if start != -1 and end != -1 and end > start:
            candidate = cleaned[start:end + 1]
            try:
                obj = json.loads(candidate)
            except Exception:
                preview = cleaned.replace("\n", " ")[:200]
                logger.warning(f"Judge output JSON parse failed; preview='{preview}'")
                obj = None
            if isinstance(obj, dict):
                decision_raw = str(obj.get("decision", "")).strip().upper()
                decision: Optional[bool]
                if decision_raw == "YES":
                    decision = True
                elif decision_raw == "NO":
                    decision = False
                else:
                    decision = None
                try:
                    score = float(obj.get("score"))
                except Exception:
                    score = None
                if score is not None and not (0.0 <= score <= 1.0):
                    score = None
                if decision is None or score is None:
                    preview = cleaned.replace("\n", " ")[:200]
                    logger.warning(f"Judge JSON missing/invalid fields; preview='{preview}'")
                    return None, None
                return decision, score

    preview = cleaned.replace("\n", " ")[:200]
    logger.warning(f"Judge output missing JSON object; preview='{preview}'")
    return None, None


@dataclass(frozen=True, slots=True)
class Iteration:
    n: int
    up: str
    sql: str
    sql_model: Optional[str]
    res_row_count: int
    res_columns: Tuple[str, ...]
    res_samples: Tuple[Tuple[str, Tuple[str, ...]], ...]  # (position, tuple(data_str))
    res_error: Optional[str]
    judge_text: str
    judge_model: Optional[str]
    judge_score: Optional[float]
    judge_decision: Optional[bool]


class ChEMBLLLMQuery:
    def __init__(
        self,
        db_path: str = 'database/latest/chembl_36/chembl_36_sqlite/chembl_36.db',
        provider: str = 'auto',
        sql_model: Optional[str] = None,
        sql_model_list: Optional[str] = None,
        sql_model_cycle: str = 'cicada',
        judge_model: Optional[str] = None,
        judge_model_list: Optional[str] = 'expensive',
        judge_model_cycle: Optional[str] = None,
        verbose: int | bool = False,
        max_retries: int = 20,
        timeout: int = 600,
        history_window: int = 11,
        judge_score_threshold: float = 0.9,
        judge_call_retries: int = 3,
        schema_docs_path: str = 'doc/chembl_database_schema.md',
        schema_sample_rows: int = 3,
        schema_max_cell_len: int = 80,
        prompt_hints_path: str = 'doc/chembl_prompt_hints.md',
        min_context: int = 100000,
        save_intermediate: bool = True,
        intermediate_dir: str = 'logs/intermediate',
        output_base: str = 'query_results',
        run_id: Optional[str] = None,
        filter_profile: str = 'strict',
        strip_unrequested_limit: bool = True,
        sql_temperature: float = 1.0,
        prompt_writer_temperature: float = 1.0,
        judge_temperature: float = 0.1,
    ):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = None

        if isinstance(verbose, bool):
            self.verbosity = 1 if verbose else 0
        else:
            self.verbosity = int(verbose)
        self.verbose = self.verbosity >= 1

        self.max_retries = int(max_retries)
        self.timeout = int(timeout)
        self.history_window = int(history_window)
        self.judge_score_threshold = float(judge_score_threshold)
        self.judge_call_retries = int(judge_call_retries)
        self.schema_docs_path = schema_docs_path
        self.schema_sample_rows = int(schema_sample_rows)
        self.schema_max_cell_len = int(schema_max_cell_len)
        self.prompt_hints_path = prompt_hints_path
        self.min_context = int(min_context)
        self.save_intermediate = bool(save_intermediate)
        self.intermediate_dir = intermediate_dir
        self.output_base = output_base
        self.run_id = run_id
        self.filter_profile = (filter_profile or 'strict').strip().lower()
        if self.filter_profile not in {'strict', 'relaxed'}:
            raise ValueError(f"Invalid filter_profile={filter_profile!r}; expected 'strict' or 'relaxed'")
        self.strip_unrequested_limit = bool(strip_unrequested_limit)
        self.sql_temperature = float(sql_temperature)
        self.prompt_writer_temperature = float(prompt_writer_temperature)
        self.judge_temperature = float(judge_temperature)
        self.openrouter_context_map: Dict[str, int] = {}
        if provider == 'openrouter':
            try:
                self.openrouter_context_map = get_openrouter_context_map()
            except Exception:
                logger.warning("Failed to fetch OpenRouter model context map.", exc_info=True)

        self.base_provider = provider

        # SQL models
        self.sql_model_list: Optional[List[str]] = None
        if sql_model_list:
            base_list = get_model_list(sql_model_list, provider)
            if provider == 'openrouter':
                if self.openrouter_context_map:
                    base_list = [m for m in base_list if self.openrouter_context_map.get(m, 0) >= self.min_context]
                else:
                    base_list = filter_models_by_context(base_list, self.min_context)
                if self.min_context > 0 and not base_list:
                    raise RuntimeError("No SQL models meet the minimum context requirement.")
            if sql_model:
                self.sql_model_list = [sql_model] + [m for m in base_list if m != sql_model]
            else:
                self.sql_model_list = base_list
                if self.sql_model_list:
                    sql_model = self.sql_model_list[0]
                    logger.info(f"Using default SQL model from {sql_model_list} list: {sql_model}")
            if self.sql_model_list is not None:
                logger.info("SQL model list (%s): %s", len(self.sql_model_list), self.sql_model_list)
        self.sql_model = sql_model
        self.sql_model_cycle = sql_model_cycle

        # Judge models (also used for prompt-writer)
        if judge_model_cycle is None:
            judge_model_cycle = sql_model_cycle
        self.judge_model_cycle = judge_model_cycle

        self.judge_model_list: Optional[List[str]] = None
        if judge_model_list:
            base_list = get_model_list(judge_model_list, provider)
            if provider == 'openrouter':
                if self.openrouter_context_map:
                    base_list = [m for m in base_list if self.openrouter_context_map.get(m, 0) >= self.min_context]
                else:
                    base_list = filter_models_by_context(base_list, self.min_context)
                if self.min_context > 0 and not base_list:
                    raise RuntimeError("No judge models meet the minimum context requirement.")
            if judge_model:
                self.judge_model_list = [judge_model] + [m for m in base_list if m != judge_model]
            else:
                self.judge_model_list = base_list
                if self.judge_model_list:
                    judge_model = self.judge_model_list[0]
                    logger.info(f"Using default judge model from {judge_model_list} list: {judge_model}")
            if self.judge_model_list is not None:
                logger.info("Judge model list (%s): %s", len(self.judge_model_list), self.judge_model_list)
        self.judge_model = judge_model

        # Load schema docs with table samples.
        with log_stage("SP"):
            schema_path = Path(self.schema_docs_path)
            db_file = Path(self.db_path)
            should_regenerate = False

            if not db_file.exists():
                if schema_path.exists():
                    logger.warning("DB file missing; using existing schema docs at %s", schema_path)
                    self.schema_docs = schema_path.read_text()
                else:
                    raise FileNotFoundError(f"ChEMBL SQLite DB not found: {self.db_path}")
            else:
                should_regenerate = not schema_path.exists()
                try:
                    if schema_path.exists():
                        should_regenerate = schema_path.stat().st_mtime < db_file.stat().st_mtime
                except Exception:
                    logger.warning("Could not compare schema docs mtime to DB mtime", exc_info=True)

                if should_regenerate:
                    print("⚠️  Schema docs missing or stale; generating...")
                    self.schema_docs = generate_schema_docs_sqlite(
                        db_path=self.db_path,
                        output_path=str(schema_path),
                        sample_rows=self.schema_sample_rows,
                        max_cell_len=self.schema_max_cell_len,
                    )
                else:
                    self.schema_docs = schema_path.read_text()

            prompt_hints_path = Path(self.prompt_hints_path)
            if prompt_hints_path.exists():
                self.prompt_hints = prompt_hints_path.read_text()
            else:
                self.prompt_hints = ""

            self.system_prompt = self._build_system_prompt()
            sp_hash = hashlib.sha256(self.system_prompt.encode("utf-8")).hexdigest()
            self.system_prompt_hash = sp_hash
            logger.info("SP_SHA256: %s", sp_hash)
            logger.info("SP_FULL:\n%s", self.system_prompt)

        # Providers
        print("🧪 Initializing SQL provider...")
        self.sql_provider = create_provider(provider=provider, model=self.sql_model, verbose=self.verbose, temperature=self.sql_temperature)
        self.current_sql_model = self.sql_model

        print("🧪 Initializing judge provider...")
        self.judge_provider = create_provider(provider=provider, model=self.judge_model, verbose=self.verbose, temperature=self.judge_temperature)
        self.current_judge_model = self.judge_model

        self.sql_model_schedule: List[str] = []
        if self.sql_model_list and len(self.sql_model_list) > 1:
            self.sql_model_schedule = generate_model_schedule(self.max_retries, self.sql_model_list, self.sql_model_cycle)
            logger.info(f"SQL model schedule (method: {self.sql_model_cycle}, {len(self.sql_model_schedule)} retries):")
            for i, m in enumerate(self.sql_model_schedule[:10]):
                logger.info(f"  Retry {i+1}: {m}")
            if len(self.sql_model_schedule) > 10:
                logger.info(f"  ... and {len(self.sql_model_schedule)-10} more")

        self.judge_model_schedule: List[str] = []
        if self.judge_model_list and len(self.judge_model_list) > 1:
            self.judge_model_schedule = generate_model_schedule(self.max_retries, self.judge_model_list, self.judge_model_cycle)
            logger.info(f"Judge model schedule (method: {self.judge_model_cycle}, {len(self.judge_model_schedule)} retries):")
            for i, m in enumerate(self.judge_model_schedule[:10]):
                logger.info(f"  Retry {i+1}: {m}")
            if len(self.judge_model_schedule) > 10:
                logger.info(f"  ... and {len(self.judge_model_schedule)-10} more")

    def _vprint(self, level: int, *args: object) -> None:
        if self.verbosity >= level:
            print(*args)

    def _build_system_prompt(self) -> str:
        prompt_hints_block = ""
        if self.prompt_hints.strip():
            prompt_hints_block = f"""\n<PROMPT_HINTS>\n{self.prompt_hints}\n</PROMPT_HINTS>\n"""
        return f"""<SP>
<ABOUT>
You will be used in different roles. Follow the task instructions in the user message under <TASK>.
</ABOUT>

<DATABASE_SCHEMA_DOCS>
{self.schema_docs}
</DATABASE_SCHEMA_DOCS>
{prompt_hints_block}</SP>"""

    def _ensure_sql_provider_for_attempt(self, attempt_idx: int) -> None:
        if attempt_idx < len(self.sql_model_schedule):
            model = self.sql_model_schedule[attempt_idx]
            if model != self.current_sql_model:
                self.sql_provider = create_provider(provider=self.base_provider, model=model, verbose=self.verbose)
                self.current_sql_model = model

    def _ensure_judge_provider_for_attempt_with_offset(self, *, attempt_idx: int, offset: int) -> None:
        if self.judge_model_schedule:
            idx = (attempt_idx + offset) % len(self.judge_model_schedule)
            model = self.judge_model_schedule[idx]
        else:
            model = self.judge_model

        if model != self.current_judge_model:
            self.judge_provider = create_provider(provider=self.base_provider, model=model, verbose=self.verbose)
            self.current_judge_model = model

    def execute_query_with_timeout(self, sql: str) -> Tuple[bool, Optional[pl.DataFrame], Optional[str]]:
        try:
            logger.info(f"Executing query (timeout: {self.timeout}s)...")
            start_time = time.time()
            timed_out = False

            def _progress_handler() -> int:
                nonlocal timed_out
                if self.timeout and (time.time() - start_time) > self.timeout:
                    timed_out = True
                    return 1
                return 0

            if self.timeout:
                self.conn.set_progress_handler(_progress_handler, 10000)

            cur = self.conn.execute(sql)
            rows = cur.fetchall()
            cols = [d[0] for d in (cur.description or [])]
            df = pl.DataFrame(rows, schema=cols)

            elapsed = time.time() - start_time
            logger.info(f"Query completed in {elapsed:.2f}s")
            return True, df, None
        except Exception as e:
            msg = str(e)
            if "interrupted" in msg.lower():
                msg = f"Query timed out after {self.timeout}s"
            logger.error(f"Query failed: {msg}", exc_info=True)
            return False, None, msg
        finally:
            self.conn.set_progress_handler(None, 0)

    def _iteration_to_block(self, it: Iteration) -> str:
        samples_lines: List[str] = []
        for pos, data in it.res_samples:
            samples_lines.append(f"{pos}: {data}")

        res_body = []
        if it.res_error:
            res_body.append(f"ERROR: {it.res_error}")
        res_body.append(f"row_count: {it.res_row_count}")
        res_body.append(f"columns: {list(it.res_columns)}")
        if samples_lines:
            res_body.append("samples:")
            res_body.extend(samples_lines)

        return (
            f"<ITERATION {it.n}>\n"
            f"<UP_{it.n}>\n{it.up}\n</UP_{it.n}>\n"
            f"<SQL_{it.n}>\n{it.sql}\n</SQL_{it.n}>\n"
            f"<RES_{it.n}>\n" + "\n".join(res_body) + f"\n</RES_{it.n}>\n"
            f"<J_{it.n}>\n{it.judge_text}\n</J_{it.n}>\n"
            f"</ITERATION {it.n}>"
        )

    def _history_blocks(self, iterations: List[Iteration]) -> str:
        if not iterations:
            return "<HISTORY/>\n"
        start_n = iterations[0].n
        end_n = iterations[-1].n
        blocks = "\n".join(self._iteration_to_block(it) for it in iterations)
        return f"<HISTORY from=\"{start_n}\" to=\"{end_n}\">\n{blocks}\n</HISTORY>"

    def _filter_profile_guidance(self) -> str:
        if self.filter_profile == 'strict':
            return "\n".join(
                [
                    "- Use docs.doc_type = 'PUBLICATION' when applying publication-year filters.",
                    "- Use assays.confidence_score = 9.",
                    "- Use target_dictionary.target_type = 'SINGLE PROTEIN'.",
                    "- Do NOT add extra filters unless explicitly requested (no DOI-not-null, no unit restrictions, no relation restrictions).",
                    "- If units are not requested, include all IC50 units (do not force nM).",
                ]
            )
        if self.filter_profile == 'relaxed':
            return "\n".join(
                [
                    "- Do NOT require docs.doc_type or DOI unless explicitly requested; only use year filters.",
                    "- Prefer assays.confidence_score >= 8; if unavailable, skip the confidence filter.",
                    "- Do NOT restrict target_type unless explicitly requested.",
                    "- Do NOT add extra filters unless explicitly requested (no unit restrictions, no relation restrictions).",
                ]
            )
        return ""

    def _assert_system_prompt_unchanged(self) -> None:
        current_hash = hashlib.sha256(self.system_prompt.encode("utf-8")).hexdigest()
        if current_hash != self.system_prompt_hash:
            logger.error(
                "System prompt changed during run: expected %s, got %s",
                self.system_prompt_hash,
                current_hash,
            )
            raise RuntimeError("System prompt changed during run; caching assumptions violated.")

    def _user_requested_limit(self, text: str) -> bool:
        lowered = text.lower()
        patterns = [
            r"\blimit\s+\d+\b",
            r"\btop\s+\d+\b",
            r"\bfirst\s+\d+\b",
            r"\blast\s+\d+\b",
            r"\bat\s+most\s+\d+\b",
            r"\bno\s+more\s+than\s+\d+\b",
            r"\bmaximum\s+\d+\b",
            r"\bminimum\s+\d+\b",
            r"\bonly\s+\d+\b",
            r"\breturn\s+\d+\b",
            r"\bshow\s+\d+\b",
            r"\brows?\s+\d+\b",
            r"\bsample\s+\d+\b",
        ]
        return any(re.search(pat, lowered) for pat in patterns)

    def _strip_unrequested_limit(self, *, sql: str, uq: str, up: str) -> str:
        if not self.strip_unrequested_limit:
            return sql
        if self._user_requested_limit(f"{uq}\n{up}"):
            return sql
        if not re.search(r"\blimit\b", sql, flags=re.IGNORECASE):
            return sql
        clause_re = re.compile(r"\s+limit\s+\d+(?:\s+offset\s+\d+)?", flags=re.IGNORECASE)
        cleaned, count = clause_re.subn("", sql)
        if count:
            logger.warning("Removed %s unrequested LIMIT clause(s) from SQL.", count)
        cleaned = re.sub(r"\s+;", ";", cleaned).strip()
        return cleaned

    def _build_messages_for_up(self, *, uq: str, iterations: List[Iteration], next_n: int) -> List[Dict[str, str]]:
        self._assert_system_prompt_unchanged()
        task = f"""<TASK>
You are a prompt-writer that crafts a single improved user prompt UP_{next_n} for a Text-to-SQL model.

Rules:
- Output ONLY the text of UP_{next_n} (no tags, no markdown, no bullets).
- UP must be explicit about:
  - target definitions (e.g., target types, organism, protein family constraints)
  - required output columns
  - filters, units, and date ranges
  - whether results should be ranked and any top-N
- Follow FILTER_PROFILE guidance when provided.
- Use prior judge advice (J_k) to improve UP_{next_n}.
</TASK>"""

        profile_guidance = self._filter_profile_guidance()
        user = "\n".join(
            [
                task,
                f"<UQ>\n{uq}\n</UQ>",
                f"<FILTER_PROFILE name=\"{self.filter_profile}\">\n{profile_guidance}\n</FILTER_PROFILE>" if profile_guidance else "",
                self._history_blocks(iterations[-self.history_window :]),
            ]
        )
        return [{"role": "system", "content": self.system_prompt}, {"role": "user", "content": user}]

    def _build_messages_for_sql(self, *, uq: str, up: str, iterations: List[Iteration], n: int) -> List[Dict[str, str]]:
        self._assert_system_prompt_unchanged()
        task = f"""<TASK>
You are a SQL-writer for SQLite (ChEMBL).
Generate SQL_{n} as a SINGLE SQLite SELECT query.

Rules:
- Output ONLY the SQL text (no tags, no markdown, no explanation).
- Use explicit JOIN clauses; avoid implicit joins.
- Do NOT add LIMIT clauses unless the user explicitly requests a row cap or top-N.
- If neither UQ nor UP explicitly requests a row cap/top-N, any LIMIT is incorrect.
- If the user asks for ranking/top-N, use ORDER BY ... DESC then LIMIT N.
- If you need multiple steps, use CTEs (WITH ...).
</TASK>"""

        user = "\n".join(
            [
                task,
                f"<UQ>\n{uq}\n</UQ>",
                self._history_blocks(iterations[-self.history_window :]),
                f"<UP_{n}>\n{up}\n</UP_{n}>",
            ]
        )
        return [{"role": "system", "content": self.system_prompt}, {"role": "user", "content": user}]

    def _build_messages_for_judge(self, *, uq: str, up: str, sql: str, res_summary: str, iterations: List[Iteration], n: int) -> List[Dict[str, str]]:
        self._assert_system_prompt_unchanged()
        task = f"""<TASK>
You are a strict judge evaluating whether RES_{n} answers the user's question.

You MUST output a single JSON object on one line with keys:
- "analysis": string containing qualitative judgement + concrete improvement advice
- "score": float in [0,1]
- "decision": "YES" or "NO"

Constraints:
- If decision is YES then score MUST be >= {self.judge_score_threshold}
- If decision is NO then score MUST be < {self.judge_score_threshold}
- Output JSON ONLY (no markdown, no extra text, no code fences).

IMPORTANT:
- RES_{n} may be a summary with samples only, or it may include full rows.
- The RES_{n} block will include a line `res_mode: sample` or `res_mode: full`.
- Do NOT assume missing rows are absent if `res_mode: sample`.
- When `res_mode: sample`, the full result exists locally but cannot fit in context; a subsample is shown by design.
- When `res_mode: sample`, focus on correctness and completeness of the query intent based on the sample and schema/SQL.
- Sample rows may truncate long fields for context; do NOT penalize truncation in the sample.
- If `sample_strata` is provided, samples are stratified by those columns; do NOT penalize missing strata not shown.
- If SQL_{n} includes a LIMIT but neither UQ nor UP explicitly requests a row cap/top-N, decision MUST be NO and score MUST be < {self.judge_score_threshold}.

Do NOT write SQL.
</TASK>"""

        user = self._build_judge_user_content(
            task=task,
            uq=uq,
            up=up,
            sql=sql,
            res_summary=res_summary,
            iterations=iterations,
            n=n,
        )
        return [{"role": "system", "content": self.system_prompt}, {"role": "user", "content": user}]

    def _build_judge_user_content(
        self,
        *,
        task: str,
        uq: str,
        up: str,
        sql: str,
        res_summary: str,
        iterations: List[Iteration],
        n: int,
    ) -> str:
        return "\n".join(
            [
                task,
                f"<UQ>\n{uq}\n</UQ>",
                self._history_blocks(iterations[-self.history_window :]),
                f"<UP_{n}>\n{up}\n</UP_{n}>",
                f"<SQL_{n}>\n{sql}\n</SQL_{n}>",
                f"<RES_{n}>\n{res_summary}\n</RES_{n}>",
            ]
        )

    def _summarize_result(
        self,
        *,
        df: Optional[pl.DataFrame],
        error: Optional[str],
        min_rows: int,
        res_mode: str,
        sample_rows: Optional[int],
        sample_cell_len: int,
        strata_cols: Sequence[str],
    ) -> Tuple[int, Tuple[str, ...], Tuple[Tuple[str, Tuple[str, ...]], ...], str]:
        if error:
            return 0, tuple(), tuple(), f"ERROR: {error}"
        if df is None:
            return 0, tuple(), tuple(), "ERROR: no result"

        row_count = int(df.height)
        cols = tuple(df.columns)
        max_samples = int(sample_rows) if sample_rows is not None else 9
        if res_mode == "sample" and strata_cols:
            samples = sample_result_rows_stratified(
                df,
                strata_cols=strata_cols,
                max_samples=max_samples,
                max_cell_len=sample_cell_len,
            )
        else:
            samples = sample_result_rows(df, max_samples=max_samples, max_cell_len=sample_cell_len)
        samples_t = tuple((s["position"], tuple(str(x) for x in s["data"])) for s in samples)

        lines: List[str] = []
        lines.append("OK")
        lines.append(f"res_mode: {res_mode}")
        lines.append(f"row_count: {row_count}")
        if min_rows > 0 and row_count < min_rows:
            lines.append(f"warning: below min_rows hint ({min_rows})")
        lines.append(f"columns: {list(cols)}")
        if res_mode == "full":
            buf = io.StringIO()
            df.write_csv(buf)
            csv_text = buf.getvalue().strip()
            if csv_text:
                lines.append("rows_csv:")
                lines.extend(csv_text.splitlines())
        else:
            lines.append(f"sample_rows: {len(samples)}")
            if strata_cols:
                lines.append(f"sample_strata: {list(strata_cols)}")
            lines.append(
                f"sample_note: There are {row_count} rows; they do not fit in judge context. "
                f"Subsampling {len(samples)} rows for judging."
            )
            lines.append(
                "sample_note: Full result exists locally; do NOT penalize missing rows in the sample."
            )
            lines.append(
                f"sample_note: Sample cells truncated to {sample_cell_len} chars for context; "
                "do NOT penalize truncation."
            )
            if samples:
                lines.append("samples:")
                for s in samples:
                    lines.append(f"- {s['position']}: {s['data']}")

        return row_count, cols, samples_t, "\n".join(lines)

    def _print_full_result_rows(self, *, df: Optional[pl.DataFrame], n: int) -> None:
        if df is None:
            return
        self._vprint(2, "\n" + "=" * 20)
        self._vprint(2, f"RES_{n} FULL ROWS (CSV):")
        self._vprint(2, "=" * 20)
        try:
            df.write_csv(sys.stdout)
        except BrokenPipeError:
            logger.warning("Broken pipe while printing full result rows; continuing.")
        self._vprint(2, "=" * 20 + "\n")

    def _call_prompt_writer(self, *, uq: str, iterations: List[Iteration], next_n: int, attempt_idx: int) -> Optional[str]:
        if not self.judge_provider.is_available():
            logger.error("Judge/provider not available for prompt writing")
            return None

        messages = self._build_messages_for_up(uq=uq, iterations=iterations, next_n=next_n)
        if self.verbosity >= 2:
            user_prompt = messages[1]["content"] if len(messages) > 1 else ""
            logger.info("SP here; SHA256=%s", self.system_prompt_hash)
            logger.info("UP_PROMPT_USER:\n%s", user_prompt)

        last_text: Optional[str] = None
        for offset in range(max(1, self.judge_call_retries)):
            self._ensure_judge_provider_for_attempt_with_offset(attempt_idx=attempt_idx, offset=offset)
            text = self.judge_provider.generate_text(messages, max_tokens=4096, temperature=self.prompt_writer_temperature)
            if text is None:
                logger.warning("Prompt-writer call failed; trying next judge model")
                continue
            last_text = text.strip()
            if last_text:
                return last_text
        logger.error("Prompt-writer failed after retries")
        return last_text

    def _estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        return max(1, int(len(text) / 4))

    def _estimate_sample_row_tokens(self, df: pl.DataFrame, *, max_cell_len: int = 60, sample_rows: int = 200) -> int:
        if df is None or df.height == 0:
            return 0
        sample = df.head(min(sample_rows, df.height))
        total_chars = 0
        for row in sample.iter_rows():
            truncated = tuple(_truncate_cell(v, max_cell_len) for v in row)
            total_chars += len(str(truncated)) + 20
        avg = total_chars / sample.height if sample.height else 0
        return self._estimate_tokens("X" * int(avg))

    def _choose_strata_cols(self, df: pl.DataFrame) -> Tuple[str, ...]:
        if df is None:
            return tuple()
        cols = set(df.columns)
        year_candidates = ("publication_year", "year", "pub_year", "doc_year")
        class_candidates = (
            "target_class",
            "target_classification",
            "protein_class",
            "protein_classification",
            "protein_class_name",
        )
        year_col = next((c for c in year_candidates if c in cols), None)
        class_col = next((c for c in class_candidates if c in cols), None)
        if year_col and class_col:
            return (year_col, class_col)
        if year_col:
            return (year_col,)
        if class_col:
            return (class_col,)
        return tuple()

    def _choose_sample_params(
        self,
        df: pl.DataFrame,
        *,
        available_tokens: Optional[int],
        min_samples: int = 200,
        max_samples: int = 1000,
        max_cell_len: int = 60,
    ) -> Tuple[int, int]:
        if df is None or df.height == 0:
            return 0, max_cell_len

        cap = min(df.height, max_samples)
        if available_tokens is None or available_tokens <= 0:
            return max(1, min(cap, max(min_samples, cap))), max_cell_len

        budget = int(available_tokens * 0.6)
        tokens_per_row = self._estimate_sample_row_tokens(df, max_cell_len=max_cell_len)
        if tokens_per_row <= 0:
            return max(1, min(cap, max(min_samples, cap))), max_cell_len

        max_by_budget = max(1, int(budget / tokens_per_row))
        target = min(cap, max(min_samples, min(max_samples, max_by_budget)))
        if target < min_samples and df.height >= min_samples:
            for alt_len in (50, 40, 30):
                tokens_per_row = self._estimate_sample_row_tokens(df, max_cell_len=alt_len)
                if tokens_per_row <= 0:
                    continue
                max_by_budget = max(1, int(budget / tokens_per_row))
                if max_by_budget >= min_samples:
                    return min_samples, alt_len
        return target, max_cell_len

    def _estimate_full_result_tokens(self, df: pl.DataFrame, sample_rows: int = 200) -> int:
        if df.height == 0:
            return 0
        sample = df.head(min(sample_rows, df.height))
        total = 0
        for row in sample.iter_rows():
            total += sum(len(str(cell)) for cell in row) + max(0, len(row) - 1)
        avg = total / sample.height if sample.height else 0
        header = sum(len(c) for c in df.columns) + max(0, len(df.columns) - 1)
        approx_chars = int(header + (avg + 1) * df.height)
        return self._estimate_tokens("X" * approx_chars)

    def _judge_context_limit(self) -> Optional[int]:
        if self.base_provider != 'openrouter':
            return None
        if not self.openrouter_context_map:
            return None
        if not self.current_judge_model:
            return None
        return self.openrouter_context_map.get(self.current_judge_model)

    def _call_sql_writer(self, *, uq: str, up: str, iterations: List[Iteration], n: int, attempt_idx: int) -> Optional[str]:
        if not self.sql_provider.is_available():
            logger.error("SQL provider not available")
            return None

        self._ensure_sql_provider_for_attempt(attempt_idx)
        messages = self._build_messages_for_sql(uq=uq, up=up, iterations=iterations, n=n)
        start_time = time.time()
        sql = self.sql_provider.generate_sql(question=up, schema_docs=self.schema_docs, conversation_history=messages)
        elapsed = time.time() - start_time
        logger.info(f"SQL generated in {elapsed:.2f}s")
        if sql is None:
            return None

        cleaned = sql.strip()
        cleaned = re.sub(r'^```sql\s*', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'^```\s*$', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'\s*```\s*$', '', cleaned, flags=re.MULTILINE)
        cleaned = self._strip_unrequested_limit(sql=cleaned, uq=uq, up=up)
        return cleaned

    def _call_judge(self, *, uq: str, up: str, sql: str, res_summary: str, iterations: List[Iteration], n: int, attempt_idx: int) -> Tuple[Optional[bool], Optional[float], str]:
        if not self.judge_provider.is_available():
            return None, None, "Judge disabled\n0\nNO"

        messages = self._build_messages_for_judge(uq=uq, up=up, sql=sql, res_summary=res_summary, iterations=iterations, n=n)
        if self.verbosity >= 3:
            user_chars = sum(len(m.get('content', '')) for m in messages if m.get('role') == 'user')
            self._vprint(3, "\n" + "=" * 20)
            self._vprint(3, f"🔍 VERBOSE: Judge Prompt (Iteration {n})")
            self._vprint(3, "=" * 20)
            self._vprint(3, f"(system chars: {len(messages[0]['content']):,})")
            self._vprint(3, f"(user chars total: {user_chars:,})")
            self._vprint(3, "=" * 20 + "\n")

        last_text: Optional[str] = None
        for offset in range(max(1, self.judge_call_retries)):
            self._ensure_judge_provider_for_attempt_with_offset(attempt_idx=attempt_idx, offset=offset)
            text = self.judge_provider.generate_text(messages, max_tokens=4096, temperature=self.judge_temperature)
            if text is None:
                logger.warning("Judge call failed; trying next judge model")
                continue
            last_text = text.strip()
            decision, score = parse_judge_output(last_text)
            if decision is None or score is None:
                logger.warning("Judge output malformed; model=%s; trying next judge model", self.current_judge_model)
                self._save_malformed_judge_output(
                    text=last_text,
                    n=n,
                    attempt_idx=attempt_idx,
                    offset=offset,
                )
                continue

            # Enforce requested invariants.
            if decision is True and score < self.judge_score_threshold:
                logger.warning("Judge said YES but score < threshold; treating as malformed and retrying")
                continue
            if decision is False and score >= self.judge_score_threshold:
                logger.warning("Judge said NO but score >= threshold; treating as malformed and retrying")
                continue

            return decision, score, last_text

        if last_text is None:
            return None, None, "Judge failed\n0\nNO"
        return parse_judge_output(last_text)[0], parse_judge_output(last_text)[1], last_text

    def _save_malformed_judge_output(
        self,
        *,
        text: str,
        n: int,
        attempt_idx: int,
        offset: int,
    ) -> None:
        run_id = self.run_id or "run"
        model = self.current_judge_model or "unknown_model"
        safe_model = re.sub(r'[^A-Za-z0-9._-]+', '-', model).strip('-')
        out_dir = Path("logs") / "judge_malformed"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"judge_malformed_{run_id}_iter{n}_attempt{attempt_idx}_offset{offset}_{safe_model}.txt"
        try:
            out_path.write_text(text, encoding="utf-8")
            logger.warning("Saved malformed judge output to %s", out_path)
        except Exception as exc:
            logger.warning("Failed to save malformed judge output: %s", exc)

    def query(
        self,
        question: str,
        *,
        save_to_file: Optional[str] = None,
        min_rows: int = 0,
        dry_run: bool = False,
    ) -> Optional[pl.DataFrame]:
        uq = (question or "").strip()
        if not uq:
            return None

        with log_stage("UQ"):
            logger.info("User question received (%s chars)", len(uq))

        iterations: List[Iteration] = []
        up: Optional[str] = None

        for attempt_idx in range(self.max_retries):
            n = attempt_idx + 1
            with log_stage(f"ITER_{n}"):
                logger.info("Iteration %s/%s using SQL model: %s", n, self.max_retries, self.current_sql_model)

                window_iters = iterations[-self.history_window :]

                self._vprint(2, "\n" + "=" * 20, f"\nPROMPT-WRITER: generating UP_{n}\n" + "=" * 20)
                with log_stage(f"UP_{n}"):
                    logger.info("Generating UP_%s...", n)
                    up_next = self._call_prompt_writer(
                        uq=uq,
                        iterations=window_iters,
                        next_n=n,
                        attempt_idx=attempt_idx,
                    )
                if up_next is None or not up_next.strip():
                    if up is None:
                        raise RuntimeError("Failed to generate UP_1")
                    logger.warning("Failed to generate UP_%s; reusing previous UP", n)
                else:
                    up = up_next.strip()
                if up is None:
                    raise RuntimeError(f"Failed to generate UP_{n}")

                self._vprint(2, f"\nUP_{n}:\n{up}\n")
                with log_stage(f"SQL_{n}"):
                    logger.info("Generating SQL...")
                    sql = self._call_sql_writer(uq=uq, up=up, iterations=window_iters, n=n, attempt_idx=attempt_idx)
                if sql is None:
                    raise RuntimeError("SQL generation returned None")

                if self.verbose:
                    print("\n" + "=" * 20)
                    print(f"Generated SQL_{n} ({self.current_sql_model}):")
                    print("=" * 20)
                    print(sql)
                    print("=" * 20 + "\n")

                if dry_run:
                    print("DRY RUN: not executing SQL")
                    return None

                with log_stage(f"RES_{n}"):
                    success, df, err = self.execute_query_with_timeout(sql)

                    res_mode = "sample"
                    sample_rows: Optional[int] = None
                    sample_cell_len = 60
                    strata_cols: Tuple[str, ...] = tuple()
                    available_tokens: Optional[int] = None
                    if success and df is not None:
                        if self.verbosity >= 2:
                            self._print_full_result_rows(df=df, n=n)
                        context_limit = self._judge_context_limit()
                        if context_limit:
                            task = f"""<TASK>
You are a strict judge evaluating whether RES_{n} answers the user's question.
</TASK>"""
                            base_user = self._build_judge_user_content(
                                task=task,
                                uq=uq,
                                up=up,
                                sql=sql,
                                res_summary="",
                                iterations=window_iters,
                                n=n,
                            )
                            base_tokens = self._estimate_tokens(self.system_prompt) + self._estimate_tokens(base_user)
                            available = int(context_limit * 0.9) - base_tokens
                            available_tokens = max(0, available)
                            est_full = self._estimate_full_result_tokens(df)
                            if available > 0 and est_full <= available:
                                res_mode = "full"
                            if self.verbosity >= 2:
                                self._vprint(
                                    2,
                                    f"\nRES_{n} sizing: context={context_limit} tokens, base≈{base_tokens}, "
                                    f"full≈{est_full}, available≈{max(0, available)} -> {res_mode}",
                                )
                    if success and df is not None and res_mode == "sample":
                        sample_rows, sample_cell_len = self._choose_sample_params(df, available_tokens=available_tokens)
                        strata_cols = self._choose_strata_cols(df)

                    row_count, cols, samples_t, res_summary = self._summarize_result(
                        df=df,
                        error=err if not success else None,
                        min_rows=min_rows,
                        res_mode=res_mode,
                        sample_rows=sample_rows,
                        sample_cell_len=sample_cell_len,
                        strata_cols=strata_cols,
                    )

                    if self.verbosity >= 2:
                        sampled_for_judge = row_count if res_mode == "full" else len(samples_t)
                        self._vprint(2, "\n" + "=" * 20)
                        self._vprint(2, f"RES_{n} STATS:")
                        self._vprint(2, "=" * 20)
                        self._vprint(2, f"row_count: {row_count}")
                        self._vprint(2, f"res_mode: {res_mode}")
                        self._vprint(2, f"rows_passed_to_judge: {sampled_for_judge}")
                        self._vprint(2, "=" * 20)
                        self._vprint(2, "\n" + "=" * 20)
                        self._vprint(2, f"RES_{n}:")
                        self._vprint(2, "=" * 20)
                        self._vprint(2, res_summary)
                        self._vprint(2, "=" * 20 + "\n")

                with log_stage(f"J_{n}"):
                    logger.info("Judging RES_%s...", n)
                    judge_decision, judge_score, judge_text = self._call_judge(
                        uq=uq,
                        up=up,
                        sql=sql,
                        res_summary=res_summary,
                        iterations=window_iters,
                        n=n,
                        attempt_idx=attempt_idx,
                    )

                it = Iteration(
                    n=n,
                    up=up,
                    sql=sql,
                    sql_model=self.current_sql_model,
                    res_row_count=row_count,
                    res_columns=cols,
                    res_samples=samples_t,
                    res_error=err if not success else None,
                    judge_text=judge_text,
                    judge_model=self.current_judge_model,
                    judge_score=judge_score,
                    judge_decision=judge_decision,
                )
                iterations.append(it)

                if self.save_intermediate and df is not None:
                    run_id = self.run_id or "run"
                    out_dir = Path(self.intermediate_dir)
                    out_dir.mkdir(parents=True, exist_ok=True)
                    out_path = out_dir / f"{self.output_base}_{run_id}_iter{n}.csv"
                    df.write_csv(out_path)
                    self._vprint(2, f"\n📄 Intermediate saved to: {out_path}")

                if self.verbosity >= 2:
                    self._vprint(2, "\n" + "-" * 20)
                    self._vprint(2, f"J_{n}:\n{judge_text}\n")
                    self._vprint(2, "-" * 20 + "\n")

                stop_by_threshold = judge_score is not None and judge_score >= self.judge_score_threshold
                stop_by_yes = judge_decision is True and (judge_score is None or judge_score >= self.judge_score_threshold)

                if stop_by_yes or stop_by_threshold:
                    logger.info(f"Stopping: judge_decision={judge_decision} judge_score={judge_score}")
                    if df is None:
                        return None
                    if save_to_file:
                        df.write_csv(save_to_file)
                        print(f"\n📄 Saved to: {save_to_file}")
                    return df

        logger.error(f"All {self.max_retries} iterations exhausted")
        return None


def main() -> None:
    load_dotenv_once()
    def configure_logging(verbosity: int) -> None:
        level = logging.INFO if verbosity < 2 else logging.DEBUG
        root = logging.getLogger()
        root.setLevel(level)
        for handler in root.handlers:
            handler.setLevel(level)
            handler.setFormatter(logging.Formatter(LOG_FORMAT))

    parser = argparse.ArgumentParser(
        description='Natural language to SQL with UP/SQL/J loop (v1) for ChEMBL',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('query', nargs='?', help='Natural language query (can be provided via pipe)')
    parser.add_argument('-q', '--query', dest='query_text', help='Natural language query')
    provider_choices = ['auto', 'anthropic', 'openrouter', 'cerebras', 'deepseek', 'local']
    parser.add_argument(
        '--provider',
        choices=provider_choices,
        default=None,
        help='LLM provider (default: OPENROUTER; can also set TEXT2SQL_PROVIDER)',
    )
    parser.add_argument(
        '--no-provider',
        action='store_true',
        help='Disable remote providers (force local LLM)',
    )
    parser.add_argument('--db-path', default='database/latest/chembl_36/chembl_36_sqlite/chembl_36.db', help='Path to ChEMBL SQLite DB')

    # SQL model controls (aliases keep v4/v5 compatibility)
    parser.add_argument('--sql-model', '-m', '--model', dest='sql_model', help='SQL model')
    parser.add_argument('--sql-model-list', '--model-list', dest='sql_model_list', choices=['cheap', 'expensive', 'super', 'all'])
    parser.add_argument(
        '--sql-model-cycle',
        '--model-cycle',
        dest='sql_model_cycle',
        choices=['random', 'orderly', 'cicada'],
        default='cicada',
    )

    # Judge/prompt-writer controls
    parser.add_argument('--judge-model', dest='judge_model', help='Judge/prompt-writer model')
    parser.add_argument(
        '--judge-model-list',
        dest='judge_model_list',
        choices=['cheap', 'expensive', 'super', 'all'],
        default='expensive',
        help='Judge/prompt-writer model list (default: expensive)',
    )
    parser.add_argument(
        '--judge-model-cycle',
        dest='judge_model_cycle',
        choices=['random', 'orderly', 'cicada'],
        default=None,
        help='Judge model cycling method (default: same as SQL cycle)',
    )

    parser.add_argument('--max-retries', type=int, default=20, help='Max iterations (default: 20)')
    parser.add_argument('-t', '--timeout', type=int, default=600, help='Query timeout in seconds (default: 600)')
    parser.add_argument('-a', '--auto', action='store_true', help='Auto-save results to timestamped CSV')
    parser.add_argument('-f', '--format', choices=['json', 'csv', 'table'], default='table', help='Output format')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Verbose output; repeat for more (-vv, -vvv)')
    parser.add_argument('--dry-run', action='store_true', help='Show query only, do not execute')
    parser.add_argument('--min-rows', type=int, default=1, help='Min rows hint for retries (default: 1)')

    parser.add_argument('--history-window', type=int, default=11, help='How many last iterations to include (default: 11)')
    parser.add_argument('--judge-score-threshold', type=float, default=0.9, help='Stop if judge score >= threshold (default: 0.9)')
    parser.add_argument('--judge-call-retries', type=int, default=3, help='Retries per judge/prompt-writer call (offset models) (default: 3)')
    parser.add_argument('--schema-docs-path', default='doc/chembl_database_schema.md', help='Cached schema docs path')
    parser.add_argument('--schema-sample-rows', type=int, default=3, help='Sample rows per table in schema docs (default: 3)')
    parser.add_argument('--schema-max-cell-len', type=int, default=80, help='Max cell length in schema docs (default: 80)')
    parser.add_argument('--prompt-hints-path', default='doc/chembl_prompt_hints.md', help='Prompt hints path (full small lookup tables)')
    parser.add_argument(
        '--filter-profile',
        choices=['strict', 'relaxed'],
        default='strict',
        help='Preset filters for prompt-writer (strict: publication+confidence=9+single protein; relaxed: no doc/doi, confidence>=8)',
    )
    parser.add_argument('--output-base', default='query_results', help='Base filename for CSV outputs (default: query_results)')
    parser.add_argument('--output-file', default=None, help='Exact filename for CSV outputs (overrides --output-base)')
    parser.add_argument('--min-context', type=int, default=100000, help='Minimum OpenRouter model context length (default: 100000)')
    parser.add_argument('--strip-unrequested-limit', dest='strip_unrequested_limit', action='store_true', help='Strip LIMIT unless user explicitly requested a row cap/top-N')
    parser.add_argument('--no-strip-unrequested-limit', dest='strip_unrequested_limit', action='store_false', help='Disable heuristic LIMIT stripping')
    parser.add_argument('--intermediate-dir', default='logs/intermediate', help='Directory for intermediate CSV results (default: logs/intermediate)')
    parser.add_argument('--save-intermediate', dest='save_intermediate', action='store_true', help='Save intermediate CSV results per iteration')
    parser.add_argument('--no-save-intermediate', dest='save_intermediate', action='store_false', help='Disable intermediate CSV results')
    parser.set_defaults(save_intermediate=True, strip_unrequested_limit=True)
    parser.add_argument('--run-label', default=None, help='Label used in all run-derived filenames (default: timestamp)')
    parser.add_argument('--temperature', type=float, default=1.0, help='Temperature for SQL generation and prompt-writer (default: 1.0)')
    parser.add_argument('--judge-temperature', type=float, default=0.1, help='Temperature for judge model (default: 0.1)')

    args = parser.parse_args()
    configure_logging(int(args.verbose))

    query = args.query or args.query_text
    if not query:
        if not sys.stdin.isatty():
            query = sys.stdin.read().strip()
        else:
            parser.print_help()
            return

    provider = args.provider
    if provider is None:
        provider = (os.getenv('TEXT2SQL_PROVIDER') or '').strip().lower() or 'openrouter'
        if provider not in provider_choices:
            logger.warning(f"Invalid TEXT2SQL_PROVIDER={provider!r}; falling back to openrouter")
            provider = 'openrouter'
    if args.no_provider:
        provider = 'local'

    if args.sql_model_list is None and args.sql_model is None:
        args.sql_model_list = 'expensive'

    try:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    except Exception:
        timestamp = None

    run_id = None
    if args.run_label:
        cleaned = re.sub(r'[^A-Za-z0-9._-]+', '_', str(args.run_label)).strip('_')
        run_id = cleaned or None
    if run_id is None:
        run_id = timestamp

    if run_id:
        logger.info("Run label: %s", run_id)

    save_file = None
    if args.auto:
        save_stamp = run_id or "run"
        save_file = args.output_file or f"{args.output_base}_{save_stamp}.csv"

    log_stage_labels()
    log_effective_params(
        args,
        provider=provider,
        run_id=run_id,
        query=query,
        save_file=save_file,
    )

    llm = ChEMBLLLMQuery(
        db_path=args.db_path,
        provider=provider,
        sql_model=args.sql_model,
        sql_model_list=args.sql_model_list,
        sql_model_cycle=args.sql_model_cycle,
        judge_model=args.judge_model,
        judge_model_list=args.judge_model_list,
        judge_model_cycle=args.judge_model_cycle,
        verbose=args.verbose,
        max_retries=args.max_retries,
        timeout=args.timeout,
        history_window=args.history_window,
        judge_score_threshold=args.judge_score_threshold,
        judge_call_retries=args.judge_call_retries,
        schema_docs_path=args.schema_docs_path,
        schema_sample_rows=args.schema_sample_rows,
        schema_max_cell_len=args.schema_max_cell_len,
        prompt_hints_path=args.prompt_hints_path,
        min_context=args.min_context,
        save_intermediate=args.save_intermediate,
        intermediate_dir=args.intermediate_dir,
        output_base=args.output_base,
        run_id=run_id,
        filter_profile=args.filter_profile,
        strip_unrequested_limit=args.strip_unrequested_limit,
        sql_temperature=args.temperature,
        prompt_writer_temperature=args.temperature,
        judge_temperature=args.judge_temperature,
    )

    try:
        result = llm.query(
            question=query,
            save_to_file=save_file,
            min_rows=args.min_rows,
            dry_run=args.dry_run,
        )

        if result is not None and not args.dry_run:
            if args.format == 'json':
                print(json.dumps(result.to_dicts(), indent=2))
            elif args.format == 'csv':
                if not args.auto:
                    if args.output_file:
                        output_file = args.output_file
                    elif run_id:
                        output_file = f"{args.output_base}_{run_id}.csv"
                    else:
                        output_file = f"{args.output_base}.csv"
                    result.write_csv(output_file)
                    print(f"\n📄 Saved to: {output_file}")
            else:
                print("\n" + "=" * 20)
                print("Results:")
                print("=" * 20)
                print(result)
                print("=" * 20)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)

V1_FLOW_SPEC = r"""

LJ flow desgin spec:

1. System prompt SP with the database schema and the sampled rows of every table (at head, middle, tail)

2. The user question UQ

3. An LLM gets 1+2, and the LLM is asked to provide a good initial user prompt (UP) - UP_1

Skipped numbers in the numbering, going here from 3 to 14, as this is iteration 1. Furher down in iteration 2 we will start with 24 and so on.

Iteration 1.

14. An LLM is given {SP}{UQ}{UP_1}, and is asked to provide SQL_1
  SP
  UQ
  UP_1
  ===
  SQL_1

15. We run the SQL_1 returned against the ChEMBL SQLite DB (chembl_36.db), and get back a result table RES_1.

16. To a judge LLM we provide {SP}{UQ}{UP_1}{SQL_1}{RES_1}, and ask the judge for a judgement J_1.
  SP
  UQ
  UP_1
  SQL_1
  RES_1
  ===
  J_1

17. The judge LLM returns judgement J_1.
  17a. A judgement of how good or bad the result table is qualitativelly, as judged by the judge.
  17b. Advice from the judge how to improve the query in the next turn in order to get a better result (as per judge-s opinion).
  17c. The penultimate line of the judge answer provides a quantitative measure between 0 and 1 so the interval [0,1] where 0=max distant, continue trying, and 1=done, stop trying.
  17d. The last line has only YES or NO. A decision by the judge if we are done (if YES), or we should continue trying (if NO).
  So J_1 is J_1 = { how good or bad RES_1, how to improve, quantitavie [0,1], decision YES or NO }

18. We give the LLM the history so far, and ask it to come up with a better user prompt, UP_2. The history is laid out as:
  SP
  UQ
  UP_1
  SQL_1
  RES_1
  J_1 { how good or bad RES_1, how to improve, quantitavie [0,1], decision YES or NO }
  ===
  UP_2

19. Now the LLM returns UP_2, we have UP_2, and we cycle bacl to step 14, only we have UP_2 instead of UP_1, so now we will continue with 24 next for iteration 2.

Iteration 2.

24. An LLM is given {SP}{UQ}{UP_1}{SQL_1}{RES_1}{J_1}{UP_2}, and is asked to provide SQL_2
  SP
  UQ
  UP_1
  SQL_1
  RES_1
  J_1 { how good or bad RES_1, how to improve, quantitative [0,1], decision YES or NO }
  UP_2
  ===
  SQL_2

25. We run the SQL_2 returned against the ChEMBL SQLite DB (chembl_36.db), and get back a result table RES_2.

26. To a judge LLM we provide {SP}{UQ}{UP_1}{SQL_1}{RES_1}{J_1}{UP_2}{SQL_2}{RES_2}, and ask the judge for a judgement J_2.
  SP
  UQ
  UP_1
  SQL_1
  RES_1
  J_1 { how good or bad RES_1, how to inmprove, quantitative [0,1], decision YES or NO }
  UP_2
  SQL_2
  RES_2
  ===
  J_2

27. The judge LLM returns judgement J_2.
  27a. A judgement of how good or bad the result table is qualitativelly, as judged by the judge.
  27b. Advice from the judge how to improve the query in the next turn in order to get a better result (as per judge-s opinion).
  27c. The penultimate line of the judge answer provides a quantitative measure between 0 and 1 so the interval [0,1] where 0=max distant, continue trying, and 1=done, stop trying.
  27d. The last one has only YES or NO. A decision by the judge if we are done (if YES), or we should continue trying (if NO).
  So J_2 is J_2 = { how good or bad RES_2, how to improve, quantitavie [0,1], decision YES or NO }

28. We give the LLM the history so far, and ask it to come up with a better user prompt, UP_3. The history is layed as:
  SP
  UQ
  UP_1
  SQL_1
  RES_1
  J_1 { how good or bad RES_1 is, how to improve, quantitative [0,1], decision YES or NO }
  UP_2
  SQL_2
  RES_2
  J_2 { how good or bad RES_2 is, how to improve, quantitative [0,1], decision YES or NO }
  ===
  UP_3

29. Now the LLM returns UP_3, we have UP_3, and we cycle onto step 34: a copy of 24, only we have UP_3 instead of UP_2. And then we continue with 34 next, for iteration 3.

Iteration 3

34. ...like 24 only we have finished full iteration 2 and starting with iteration 3.

So we will have

Unchanged at head
  SP
  UQ
Iteration 1
  UP_1
  SQL_1
  RES_1
  J_1 { how good or bad RES_1 is, how to improve, quantitative [0,1], decision YES or NO }
Iteration 2
  UP_2
  SQL_2
  RES_2
  J_2 { how good or bad RES_2 is, how to improve, quantitative [0,1], decision YES or NO }
Iteration 3
  UP_3
  ...
  ...
  ...
Iteration n
  UP_n
  SQL_n
  RES_n
  J_n { how good or bad RES_n is, how to improve, quantitative [0,1], decision YES or NO }

We stop at iteration n: either b/c n is the max iteration, or the judge said YES b/c the result RES_n is good enough.
Note that the entire history is passed along, but we can envision it becoming too long, so implement with only the last M iteration being passed.

Unchanged at head
  SP
  UQ
Iteration (n-M)
  UP_(n-M)
  SQL_(n-M)
  RES_(n-M)
  J_(n-M) { how good or bad RES_(n-M) is, how to improve, quantitative [0,1], decision YES or NO }
...
... the last M steps
...
Iteration (n-1)
  UP_(n-1)
  SQL_(n-1)
  RES_(n-1)
  J_(n-1) { how good or bad RES_(n-1) is, how to improve, quantitative [0,1], decision YES or NO }
Iteration n
  ... UP_n etc

Separate the section with nice html-like tags

<tag n>
</tag n>

so it is very clear what is hapenning.

Codex:
• This design is solid: it cleanly separates (a) “prompt engineering” (UP), (b) SQL generation, and (c) evaluation, and it makes the feedback loop explicit and
  auditable.

  Here’s a concrete implementation plan for tools/db_llm_query_v1.py (starting from the previous version):

  1. Define the three LLM roles + model cycling

  - Keep the existing SQL model schedule (cheap/all/etc) exactly like v5 (per iteration n).
  - Keep the judge model schedule exactly like v5 (per iteration n, with optional “offset retries” on failures).
  - Reuse the judge provider + judge model schedule for UP generation (the “prompt writer”), unless you want separate flags later (e.g. --up-model-list).

  2. Build a single cached System Prompt block SP

  - SP lives entirely in the system message (so Anthropic caching works).
  - Contents:
      - Schema docs that already include “sampled rows for every table” (from doc/chembl_database_schema.md).
      - Only schema docs + sampled rows; TBD if there exist a small but important table in ChEMBL schema, the whole content can be added verbatim.
  - Wrap in tags for clarity, e.g.
      - <SP> ... <SCHEMA>...</SCHEMA> <LISTS_TABLE>...</LISTS_TABLE> </SP>

  3. Represent the rolling history with tagged blocks (last M iterations)

  - Create a renderer that produces a single string like:
      - <UQ>...</UQ>
      - <ITERATION 1> <UP_1>...</UP_1> <SQL_1>...</SQL_1> <RES_1>...</RES_1> <J_1>...</J_1> </ITERATION 1>
      - …
  - Only include the last M iterations (new CLI flag like --history-window with a sane default, e.g. 2 or 3).
  - RES_n is not the full table; it’s a summary: row_count, columns, sampled rows (head/mid/tail), plus error if any.

  4. Implement the v1 loop

  - Step “3”: call UP-writer LLM with SP + <UQ> to produce UP_1 (plain text only).
  - For iteration n = 1..max_iters:
      - SQL step (14 / 24 / 34 …): call SQL LLM with SP + history + <UP_n> and request SQL only.
      - Execute SQL → produce RES_n summary.
      - Judge step (16 / 26 / …): call judge LLM with SP + history + <SQL_n> + <RES_n> and request:
          - qualitative judgement
          - improvement advice
          - penultimate line: float in [0,1]
          - last line: YES or NO
      - Parse judge output strictly.
      - If YES, stop and return/save result.
      - Else UP refinement step (18 / 28 / …): call UP-writer with SP + history (including J_n) and ask for the next UP_(n+1) (plain text only).
      - Append everything to internal history list; trim to last M.

  5. Parsing + robustness

  - Add parsers:
      - judge_decision = YES/NO from last non-empty line.
      - judge_score from penultimate non-empty line (validate 0<=x<=1, else treat as malformed).
  - On malformed judge output or API failure: retry judge using the “offset” cycling (next judge model), similar to v5.
  - Keep -v/-vv/-vvv behavior: print full SP once at -v; print UP/SQL/RES/J blocks at -vv; print full judge/user messages sizes at -vvv.

  6. CLI additions (minimal)

  - Keep exiting flags, add:
      - --history-window M
      - --judge-call-retries K (offset retries)
      - (optional) --judge-score-threshold if you want an additional stop criterion besides YES/NO.

"""

if __name__ == '__main__':
    main()
