#!/usr/bin/env python3
"""
LLM Text-to-SQL Query Interface (v5 runtime backbone, DSPy) for ChEMBL (SQLite)

Flow:
1) System prompt SP contains:
   - Database schema docs: tables, columns, and sampled rows per table (for the data semantics).
2) User question UQ initial question is provided by the user, once only at start.
3) A prompt-writer LLM produces UP_1 from (SP, UQ).
4) For iterations n=1..N:
   - SQL-writer LLM produces SQL_n from (SP, UQ, UP_n, and prior M iterations of history).
   - We run SQL_n locally against the ChEMBL SQLite DB producing result table RES_n; the summary is (plan, row count, columns, samples, errors).
   - Judge LLM produces judgement J_n from (SP, UQ, UP_n, SQL_n, PLAN_n, RES_n summary, last M iterations history), including qualitative evaluation + improvement advice + score [0,1] + YES/NO.
   - If YES (or score >= threshold), stop.
   - Else: new cycle starts with new {UP_n,SQL_n,PLAN_n,RES_n summary,J_n eval+improv+score+NO} added to the M-length hsotory.
   - Itreration (n+1): prompt-writer produces UP_(n+1) from (SP, UQ, prior M iteration of history)

TODO
1) Turn the current sequence into a tree (search); then
2) Prune the tree back into a lattice (search) to keep it manageable.
"""

"""
LJ flow design spec:

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

16. To a judge LLM we provide {SP}{UQ}{UP_1}{SQL_1}{PLAN_1}{RES_1}, and ask the judge for a judgement J_1.
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
    PLAN_1
    RES_1
    J_1 { how good or bad RES_1, how to improve, quantitavie [0,1], decision YES or NO }
    ===
    UP_2

19. Now the LLM returns UP_2, we have UP_2, and we cycle bacl to step 14, only we have UP_2 instead of UP_1, so now we will continue with 24 next for iteration 2.

Iteration 2.

24. An LLM is given {SP}{UQ}{UP_1}{SQL_1}{PLAN_1}{RES_1}{J_1}{UP_2}, and is asked to provide SQL_2
    SP
    UQ
    UP_1
    SQL_1
    PLAN_1
    RES_1
    J_1 { how good or bad RES_1, how to improve, quantitative [0,1], decision YES or NO }
    UP_2
    ===
    SQL_2

25. We run the SQL_2 returned against the ChEMBL SQLite DB (chembl_36.db), and get back a result table RES_2.

26. To a judge LLM we provide {SP}{UQ}{UP_1}{SQL_1}{PLAN_1}{RES_1}{J_1}{UP_2}{SQL_2}{PLAN_2}{RES_2}, and ask the judge for a judgement J_2.
    SP
    UQ
    UP_1
    SQL_1
    PLAN_1
    RES_1
    J_1 { how good or bad RES_1, how to inmprove, quantitative [0,1], decision YES or NO }
    UP_2
    SQL_2
    PLAN_2
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
    PLAN_1
    RES_1
    J_1 { how good or bad RES_1 is, how to improve, quantitative [0,1], decision YES or NO }
    UP_2
    SQL_2
    PLAN_2
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
    PLAN_1
    RES_1
    J_1 { how good or bad RES_1 is, how to improve, quantitative [0,1], decision YES or NO }
Iteration 2
    UP_2
    SQL_2
    PLAN_2
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
    PLAN_n
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
    PLAN_(n-M)
    RES_(n-M)
    J_(n-M) { how good or bad RES_(n-M) is, how to improve, quantitative [0,1], decision YES or NO }
    ...
    ... the last M steps
    ...
Iteration (n-1)
    UP_(n-1)
    SQL_(n-1)
    PLAN_(n-1)
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

  Here’s a concrete implementation plan for tools/db_llm_query_v3.py (starting from the previous version):

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
      - <ITERATION 1> <UP_1>...</UP_1> <SQL_1>...</SQL_1> <PLAN_1>...</PLAN_1> <RES_1>...</RES_1> <J_1>...</J_1> </ITERATION 1>
      - …
  - Only include the last M iterations (new CLI flag like --history-window with a sane default, e.g. 2 or 3).
  - RES_n is not the full table; it’s a summary: row_count, columns, sampled rows (head/mid/tail), plus error if any.

  4. Implement the v1 loop

  - Step “3”: call UP-writer LLM with SP + <UQ> to produce UP_1 (JSON only; required key "up").
  - For iteration n = 1..max_iters:
      - SQL step (14 / 24 / 34 …): call SQL LLM with SP + history + <UP_n> and request JSON only (required key "sql").
      - Execute SQL → produce RES_n summary.
      - Judge step (16 / 26 / …): call judge LLM with SP + history + <SQL_n> + <PLAN_n> + <RES_n> and request:
          - qualitative judgement
          - improvement advice
          - penultimate line: float in [0,1]
          - last line: YES or NO
      - Parse judge output strictly.
      - If YES, stop and return/save result.
      - Else UP refinement step (18 / 28 / …): call UP-writer with SP + history (including J_n) and ask for the next UP_(n+1) (JSON only; required key "up").
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

import argparse
import contextlib
import contextvars
import datetime
import hashlib
import json
import logging
import os
import random
import re
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Sequence, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import sqlite3
import polars as pl
import requests
import io
import yaml
from compressed_io import append_target_path, read_candidates, read_text_maybe_compressed

# Ensure the script directory is on sys.path so `import text2sql` works both when executed
# as a script (`python src/db_llm_query_v3.py`) and when imported as a module
# (e.g., via a console_script entry point).
_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from text2sql.env import load_dotenv_once
import dspy

LOCAL_OPENAI_COMPAT_PROVIDERS = {"llamacpp", "mlxlm", "local"}
LOCAL_ENDPOINT_PROBE_TIMEOUT_SECONDS = 3.0
SHARED_FALLBACK_RETRY_SECONDS = 3600.0

DEFAULT_PROMPT_PACK_PATH = str(
    (Path(__file__).resolve().parent.parent / "experiments" / "prompt_pack_v4.0.yaml").resolve()
)

DEFAULT_PROMPT_PACK: Dict[str, str] = {
    "version": "v4.0",
    "prompt_hints_path": "doc/chembl_prompt_hints.md",
    "about_block": "You will be used in different roles. Follow the task instructions in the user message under <TASK>.",
    "examples_block": """<EXAMPLES>
### Example 1 - Potency ranking

```text
User question:
"Top 10 most potent compounds against EGFR by IC50"

SQL:
SELECT
  md.pref_name,
  MIN(a.standard_value) AS ic50_nM
FROM activities a
JOIN assays ass ON a.assay_id = ass.assay_id
JOIN target_dictionary td ON ass.tid = td.tid
JOIN molecule_dictionary md ON a.molecule_chembl_id = md.molecule_chembl_id
WHERE
  td.pref_name = 'Epidermal Growth Factor Receptor'
  AND a.standard_type = 'IC50'
  AND a.standard_units = 'nM'
GROUP BY md.molecule_chembl_id
ORDER BY ic50_nM ASC
LIMIT 10;
```

---

### Example 2 - SMILES for active compounds

```text
User question:
"Give SMILES for compounds active against JAK2"

SQL:
SELECT DISTINCT
  cs.canonical_smiles
FROM activities a
JOIN assays ass ON a.assay_id = ass.assay_id
JOIN target_dictionary td ON ass.tid = td.tid
JOIN compound_structures cs ON a.molecule_chembl_id = cs.molecule_chembl_id
WHERE
  td.pref_name = 'Janus kinase 2'
  AND a.pchembl_value IS NOT NULL
LIMIT 50;
```

---

### Example 3 - Approved drugs for a target

```text
User question:
"Approved drugs targeting VEGFA"

SQL:
SELECT DISTINCT
  md.pref_name,
  md.max_phase
FROM activities a
JOIN assays ass ON a.assay_id = ass.assay_id
JOIN target_dictionary td ON ass.tid = td.tid
JOIN molecule_dictionary md ON a.molecule_chembl_id = md.molecule_chembl_id
WHERE
  td.pref_name = 'Vascular endothelial growth factor A'
  AND md.max_phase = 4
LIMIT 50;
```

---

### Example 4 - Counting molecules

```text
User question:
"How many molecules have activity data for KRAS?"

SQL:
SELECT
  COUNT(DISTINCT a.molecule_chembl_id) AS n_molecules
FROM activities a
JOIN assays ass ON a.assay_id = ass.assay_id
JOIN target_dictionary td ON ass.tid = td.tid
WHERE
  td.pref_name = 'KRAS';
```
</EXAMPLES>
""",
    "up_task_template": """<TASK>
You are a prompt writer that crafts a single improved User Prompt (UP) for a Text-to-SQL model.
The user gave you a User Question UQ thas is listed below. For that user question UQ, we are to retrieve data from the ChEMBLdb chemistry database.
We will do it in two steps.
Step 1 (this one): Write a User Prompt (UP), given the User Question (UQ) passed below, and the database schema and other relevant information passed in the System Prompt (SP).
Step 2 (next one): Write an Sql Query (SQL), given the User Prompt (UP) from step 1, the User Question (UQ), and the System Prompt (SP) with the database schema etc.
Now in this turn we are doing step 1. It's best if we do it in this iteration. But if we fail, we will retry. Currently we are starting iteration {next_n}.
Rules:
- Output ONLY a single JSON object on one line (no markdown, no code fences).
- Required key: "up" (string). This is the UP_{next_n} that will be passed to the SQL-writer.
- Optional keys (use when helpful): "targets", "output_columns", "filters", "ranking", "notes".
- The "up" string must be explicit about:
  + target definitions (e.g., target types, organism, protein family constraints)
  + required output columns
  + filters, units, and date ranges
  + whether results should be ranked and any top-N; but do not add limits to the number of rows yourself, if the UQ does not request itself; do not mistake any number in the UQ as a number of rows to be returned
- Do NOT ask for SQL or mention SQL output; describe the desired data/results only.
- Follow FILTER_PROFILE guidance when provided.
- Use prior judge advice ({prev_judge}) to improve UP_{next_n}.
</TASK>""",
    "sql_task_template": """<TASK>
You are a SQL-writer for SQLite chemistry database ChEMBL. Generate SQL statement as a SINGLE SQLite SELECT query.
The user gave us a question UQ that is listed below. For that question, we are to retreive data from the ChEMBLdb chemistry database.
We are doing it in two steps. This turn is step 2.
Step 1 (done previously): We wrote a User Prompt (UP), given the User Question (UQ), and the System Prompt (SP) descriing the database schema and other relevant information. The User Prompt (UP) is embedded below.
Step 2 (this one, doing it now): Write an Sql Query (SQL), given the User Prompt (UP) from step 1, the User Question (UQ), and the System Prompt (SP).
You job is to generate SQL statement as a SINGLE SQLite SELECT query.
It's best if we do it now in one shot, the sql works and th user gets his data. But if we fail, we will retry and have another shot. Currently we are starting iteration {n}.
Rules:
- Output ONLY a single JSON object on one line (no markdown, no code fences).
- Required key: "sql" (string) containing the SQLite SELECT query.
- Optional key: "notes" (string) for brief assumptions if needed.
- Use explicit JOIN clauses; avoid implicit joins.
- Do NOT add LIMIT clauses unless the user explicitly requests a row cap or top-N.
- If neither UQ nor UP explicitly requests a row cap/top-N, any LIMIT is incorrect.
- If the user asks for ranking/top-N, use ORDER BY ... DESC then LIMIT N.
- If you need multiple steps, use CTEs (WITH ...).
</TASK>""",
    "judge_task_template": """<TASK>
You are a strict judge evaluating whether the RES-ult table RES_{n} returned from the sql query answers user's question truthfully and completely.
The user gave us a question UQ thas is listed below. For that question, we were to retrieve data from the ChEMBLdb chemistry database.
We dit it in two steps. 
Step 1: We wrote a User Prompt (UP) not shown in this message, a specification for what the sql should look like, given the User Question (UQ - passed below), and the database schema and other relevant information (passed in the System Prompt - SP).
Step 2: We wrote an Sql Query (SQL - below) given the User Prompt UP (not shown) from step 1, the User Question (UQ - below), and the System Prompt (SP) with the database schema etc.
Then we run the SQL on the ChEMBLdb database, and the query returned a table with results - RES. We can re-try multiple times, iterating, and the current iteration is iteration {n}.
In this turn, you are to judge that result RES_{n} answers the user question truthfully and completely.
You MUST output a single JSON object on one line with keys:
- "analysis": string containing qualitative judgement + concrete improvement advice
- "score": float in [0,1]
- "decision": "YES" or "NO"
Constraints:
- If decision is YES then score SHOULD be >= {judge_yes_score_threshold}.
- If decision is NO then score SHOULD be <= {judge_no_override_threshold}; a NO above that score is treated as an effective YES by the runner.
- Output JSON ONLY (no markdown, no extra text, no code fences).
- Evaluate whether RES_{n} answers the user's question (UQ). Do NOT require SQL text in RES; SQL_{n} is provided separately.
- UP_{n} is an internal prompt for the SQL-writer; it may contain meta-instructions. Do NOT treat UP_{n} as the user's request.
IMPORTANT:
- RES_{n} may be a summary with samples only, or it may include full rows.
- The RES_{n} block will include a line `res_mode: sample` or `res_mode: full`.
- Do NOT assume missing rows are absent if `res_mode: sample`.
- When `res_mode: sample`, the full result exists locally but cannot fit in context; a subsample is shown by design.
- When `res_mode: sample`, focus on correctness and completeness of the query intent based on the sample and schema/SQL.
- Sample rows may truncate long fields for context; do NOT penalize truncation in the sample.
- If SQL_{n} includes a LIMIT but neither UQ nor UP explicitly requests a row cap/top-N, decision MUST be NO.
- Special case: if RES_{n} shows zero rows (row_count: 0), treat as failure and include BOTH of these statements verbatim in analysis:
  1) The SQL returned no rows; there are zero rows in the result.
  2) There is small probability that the user instructions are wrong resulting in no rows found - but far more likely: the LLM returned bad SQL, and it's almost certain that the SQL writing LLM got it very wrong, and we should retry, 99.9% probability.
Do NOT write SQL.
</TASK>""",
}


class QuotaFallbackTriggered(RuntimeError):
    def __init__(self, *, provider: str, code: Optional[str], message: str) -> None:
        super().__init__(message)
        self.provider = provider
        self.code = code
        self.message = message


@dataclass
class FallbackEndpointConfig:
    provider: str
    model: Optional[str]
    base_url: Optional[str]


class SharedQuotaFallbackState:
    def __init__(
        self,
        config: FallbackEndpointConfig | list[FallbackEndpointConfig],
        *,
        primary_config: Optional[FallbackEndpointConfig] = None,
        refresh_callback: Optional[Callable[[], list[FallbackEndpointConfig]]] = None,
        refresh_interval_seconds: Optional[float] = None,
        quota_retry_seconds: Optional[float] = None,
        time_fn: Optional[Callable[[], float]] = None,
    ) -> None:
        if isinstance(config, list):
            self.configs = list(config)
        else:
            self.configs = [config]
        self.primary_config = primary_config
        self.current_index = -1
        self.reason: Optional[str] = None
        self.quota_retry_seconds = float(quota_retry_seconds) if quota_retry_seconds else None
        self._quota_retry_at: Optional[float] = None
        self._refresh_callback = refresh_callback
        self._refresh_interval_seconds = (
            float(refresh_interval_seconds) if refresh_interval_seconds else None
        )
        self._time_fn = time_fn or time.time
        self._next_refresh_at: Optional[float] = None
        if self._refresh_callback and self._refresh_interval_seconds:
            self._next_refresh_at = self._time_fn() + self._refresh_interval_seconds
        self._refresh_in_progress = False
        self._lock = threading.Lock()

    @property
    def active(self) -> bool:
        with self._lock:
            return self.current_index >= 0

    @property
    def config(self) -> FallbackEndpointConfig:
        with self._lock:
            if self.current_index < 0 or self.current_index >= len(self.configs):
                raise IndexError("no active fallback config")
            return self.configs[self.current_index]

    def activate(self, *, reason: str) -> bool:
        reason_lower = reason.lower()
        with self._lock:
            if self.current_index >= 0 and self.primary_config is not None:
                primary_quota_prefix = f"{self.primary_config.provider.lower()} quota"
                if reason_lower.startswith(primary_quota_prefix):
                    # Parallel in-flight primary requests can all observe the same
                    # quota error. Keep the already-selected fallback instead of
                    # advancing through the chain once per racing request.
                    self.reason = reason
                    return False
            if self.current_index + 1 >= len(self.configs):
                return False
            self.current_index += 1
            self.reason = reason
            if (
                self.quota_retry_seconds
                and self.primary_config is not None
                and ("quota" in reason_lower or "rate" in reason_lower)
            ):
                self._quota_retry_at = self._time_fn() + self.quota_retry_seconds
            return True

    def maybe_restore_primary(self) -> Optional[FallbackEndpointConfig]:
        with self._lock:
            if (
                self.primary_config is None
                or self._quota_retry_at is None
                or self._time_fn() < self._quota_retry_at
            ):
                return None
            self.current_index = -1
            self.reason = "quota cooldown elapsed; retrying primary endpoint"
            self._quota_retry_at = None
            return self.primary_config

    def force_restore_primary(self, *, reason: str) -> Optional[FallbackEndpointConfig]:
        with self._lock:
            if self.primary_config is None:
                return None
            self.current_index = -1
            self.reason = reason
            self._quota_retry_at = None
            return self.primary_config

    def maybe_refresh_configs(self) -> bool:
        if not self._refresh_callback or not self._refresh_interval_seconds:
            return False
        now = self._time_fn()
        with self._lock:
            if self._next_refresh_at is None:
                self._next_refresh_at = now + self._refresh_interval_seconds
            if now < self._next_refresh_at or self._refresh_in_progress:
                return False
            self._refresh_in_progress = True
            self._next_refresh_at = now + self._refresh_interval_seconds
            previous_configs = list(self.configs)
            previous_index = self.current_index
        refreshed = self._refresh_callback()
        with self._lock:
            self._refresh_in_progress = False
            if not refreshed:
                return False
            self.configs = list(refreshed)
            if previous_index < 0:
                self.current_index = -1
                return previous_configs != self.configs
            previous_active = (
                previous_configs[previous_index]
                if 0 <= previous_index < len(previous_configs)
                else None
            )
            if previous_active is None:
                self.current_index = min(previous_index, len(self.configs) - 1)
                return True
            for idx, config in enumerate(self.configs):
                if (
                    config.provider == previous_active.provider
                    and config.model == previous_active.model
                    and config.base_url == previous_active.base_url
                ):
                    self.current_index = idx
                    return previous_configs != self.configs
            self.current_index = 0
            return True


def _should_probe_fallback_endpoint(config: FallbackEndpointConfig) -> bool:
    return (
        config.provider in LOCAL_OPENAI_COMPAT_PROVIDERS
        and bool(config.base_url)
        and str(config.base_url).startswith("http://")
    )


def _probe_fallback_models(config: FallbackEndpointConfig) -> list[str]:
    if not config.base_url:
        return []
    base_url = str(config.base_url).rstrip("/")
    if not base_url.endswith("/v1"):
        base_url = f"{base_url}/v1"
    try:
        response = requests.get(
            f"{base_url}/models",
            timeout=LOCAL_ENDPOINT_PROBE_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        LOGGER.warning("Endpoint probe failed for %s: %s", config.base_url, exc)
        return []

    models: list[str] = []
    payload = data.get("data")
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict) and item.get("id"):
                models.append(str(item["id"]))
    if not models:
        payload = data.get("models")
        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict):
                    model_id = item.get("id") or item.get("model") or item.get("name")
                    if model_id:
                        models.append(str(model_id))
    if models:
        LOGGER.info("Endpoint probe %s -> models=%s", config.base_url, models)
    else:
        LOGGER.warning("Endpoint probe %s returned no model ids.", config.base_url)
    return models


def _prepare_shared_fallback_chain(
    fallback_chain: Sequence[FallbackEndpointConfig],
) -> list[FallbackEndpointConfig]:
    prepared: list[FallbackEndpointConfig] = []
    for config in fallback_chain:
        if not _should_probe_fallback_endpoint(config):
            prepared.append(config)
            continue
        available_models = _probe_fallback_models(config)
        if not available_models:
            LOGGER.warning("Skipping unreachable fallback endpoint %s.", config.base_url)
            continue
        selected_model = config.model
        if selected_model not in available_models:
            selected_model = available_models[0]
            LOGGER.warning(
                "Fallback endpoint %s does not advertise %s; using %s.",
                config.base_url,
                config.model,
                selected_model,
            )
        prepared.append(
            FallbackEndpointConfig(
                provider=config.provider,
                model=selected_model,
                base_url=config.base_url,
            )
        )
    return prepared


def _build_shared_fallback_refresh_callback(
    fallback_chain: Sequence[FallbackEndpointConfig],
) -> Callable[[], list[FallbackEndpointConfig]]:
    original_chain = [
        FallbackEndpointConfig(
            provider=item.provider,
            model=item.model,
            base_url=item.base_url,
        )
        for item in fallback_chain
    ]

    def refresh() -> list[FallbackEndpointConfig]:
        return _prepare_shared_fallback_chain(original_chain)

    return refresh


def _load_prompt_pack(path: Optional[str]) -> Dict[str, str]:
    pack = dict(DEFAULT_PROMPT_PACK)
    if not path:
        return pack
    pack_path = Path(path)
    if not pack_path.exists() and not pack_path.is_absolute():
        alt = (Path(__file__).resolve().parent.parent / pack_path).resolve()
        if alt.exists():
            pack_path = alt
    if not pack_path.exists():
        return pack
    loaded = yaml.safe_load(pack_path.read_text(encoding="utf-8"))
    if loaded is None:
        return pack
    if not isinstance(loaded, dict):
        raise ValueError(f"Prompt pack at {pack_path} must be a mapping.")
    for key, value in loaded.items():
        if value is None:
            continue
        pack[str(key)] = str(value)
    return pack


def _resolve_relative_to_prompt_pack(prompt_pack_path: Optional[str], raw_path: Optional[str]) -> Optional[str]:
    if not raw_path:
        return raw_path
    candidate = Path(raw_path)
    if candidate.is_absolute() or prompt_pack_path is None:
        return str(candidate)
    pack_path = Path(prompt_pack_path)
    if not pack_path.exists():
        return str(candidate)
    return str((pack_path.parent / candidate).resolve())

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
        LOGGER.info("STAGE %s start", stage)
        yield
    finally:
        _LOG_STAGE_STACK.reset(token)


LOG_FORMAT = '%(asctime)s - %(levelname)s - %(stage)s - %(message)s'

logging.setLogRecordFactory(_stage_record_factory)
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
)
LOGGER = logging.getLogger(__name__)


STAGE_LABELS = (
    ("SP", "SystemPrompt"),
    ("UQ", "UserQuestion"),
    ("ITER_n", "Iteration_n"),
    ("UP_n", "UserPrompt_n"),
    ("SQL_n", "SqlWrite_n"),
    ("PLAN_n", "SqlPlan_n"),
    ("RES_n", "Result_n"),
    ("J_n", "Judge_n"),
    ("INIT", "ProviderModelSelection"),
)


def _log_lines(level: int, message: str) -> None:
    text = str(message)
    lines = text.splitlines()
    if text.endswith("\n"):
        lines.append("")
    if not lines:
        lines = [""]
    for line in lines:
        LOGGER.log(level, line)


def LOG_LINES(level: int, message: str) -> None:
    _log_lines(level, message)

DEFAULT_JUDGE_CONTEXT_LIMITS = {
    "zai": 32768,
    "zai-anthropic": 200000,
    "cerebras": 32768,
    "deepseek": 65536,
    "anthropic": 200000,
    "openai": 200000,
    "gemini": 1048576,
    "llamacpp": 65536,
    "mlxlm": 65536,
    "local": 65536,
}


def _provider_api_key(provider: str) -> Optional[str]:
    key_map = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "zai-anthropic": "ZAI_ANTHROPIC_AUTH_TOKEN",
        "openrouter": "OPENROUTER_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "cerebras": "CEREBRAS_API_KEY",
        "zai": "ZAI_API_KEY",
    }
    env_key = key_map.get(provider)
    if not env_key:
        return None
    api_key = os.getenv(env_key)
    if api_key:
        return api_key
    if provider in {"anthropic", "zai-anthropic"}:
        return os.getenv("ZAI_ANTHROPIC_AUTH_TOKEN")
    return None


def _normalize_openai_base_url(base_url: Optional[str], *, provider: str) -> Optional[str]:
    if base_url:
        cleaned = base_url.rstrip("/")
        if not cleaned.endswith("/v1"):
            cleaned = f"{cleaned}/v1"
        return cleaned
    if provider == "openai":
        return os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    if provider == "openrouter":
        return os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
    if provider == "llamacpp":
        return os.getenv("LLAMACPP_BASE_URL", "http://127.0.0.1:1234/v1").rstrip("/")
    if provider == "mlxlm":
        return os.getenv("MLXLM_BASE_URL", "http://127.0.0.1:1234/v1").rstrip("/")
    return None


def _normalize_provider_base_url_for_compare(provider: str, base_url: Optional[str]) -> Optional[str]:
    if provider in {"openai", "openrouter", "llamacpp", "mlxlm", "local"}:
        return _normalize_openai_base_url(base_url, provider=provider)
    return base_url.rstrip("/") if base_url else None


def _is_claude_model(model_name: Optional[str]) -> bool:
    if not model_name:
        return False
    lowered = model_name.lower()
    return "claude" in lowered or model_name.startswith("anthropic/")


def resolve_auto_provider(model: Optional[str]) -> str:
    load_dotenv_once()
    if _is_claude_model(model) and os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.getenv("OPENROUTER_API_KEY"):
        return "openrouter"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    if os.getenv("LLAMACPP_BASE_URL") or os.getenv("LLAMACPP_API_KEY"):
        return "llamacpp"
    if os.getenv("MLXLM_BASE_URL") or os.getenv("MLXLM_API_KEY"):
        return "mlxlm"
    if os.getenv("GEMINI_API_KEY"):
        return "gemini"
    if os.getenv("CEREBRAS_API_KEY"):
        return "cerebras"
    if os.getenv("ZAI_ANTHROPIC_AUTH_TOKEN") and os.getenv("ZAI_ANTHROPIC_BASE_URL"):
        return "zai-anthropic"
    if os.getenv("ZAI_API_KEY"):
        return "zai"
    return "local"


def _resolve_dspy_model(provider: str, model: Optional[str]) -> Optional[str]:
    if not model:
        return None
    if provider == "openrouter":
        if model.startswith("openrouter/"):
            return model
        return f"openrouter/{model}"
    if provider in {"llamacpp", "mlxlm", "local"}:
        if model.startswith("openai/"):
            return model
        return f"openai/{model}"
    if provider == "openai":
        return model if model.startswith("openai/") else f"openai/{model}"
    if provider in {"anthropic", "zai-anthropic"}:
        return model if model.startswith("anthropic/") else f"anthropic/{model}"
    if provider == "gemini":
        return model if model.startswith("gemini/") else f"gemini/{model}"
    if provider == "deepseek":
        return model if model.startswith("deepseek/") else f"deepseek/{model}"
    if provider == "cerebras":
        return model if model.startswith("cerebras/") else f"cerebras/{model}"
    if provider == "zai":
        if model.startswith(("zai/", "z.ai/")):
            return model
        return f"zai/{model}"
    return model if "/" in model else f"{provider}/{model}"


def _normalize_zai_model_name(model: Optional[str]) -> Optional[str]:
    if not model:
        return model
    normalized = str(model).strip()
    for prefix in ("z.ai/", "zai/", "z-ai/"):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
            break
    return normalized or model


def _messages_to_prompt(messages: Sequence[Dict[str, str]]) -> str:
    parts: List[str] = []
    for msg in messages:
        role = msg.get("role", "user").upper()
        content = msg.get("content", "")
        parts.append(f"[{role}]\n{content}")
    return "\n\n".join(parts)


def _extract_text_from_response(response: Any) -> Optional[str]:
    if response is None:
        return None
    if isinstance(response, str):
        return response
    if isinstance(response, list) and response:
        for item in response:
            if isinstance(item, str):
                return item
    if isinstance(response, dict):
        choices = response.get("choices")
        if isinstance(choices, list) and choices:
            message = choices[0].get("message", {})
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str):
                    return content
        content = response.get("content")
        if isinstance(content, str):
            return content
    text = getattr(response, "text", None)
    if isinstance(text, str):
        return text
    return str(response)


def _extract_anthropic_text(data: Any) -> Optional[str]:
    if not isinstance(data, dict):
        return None
    content = data.get("content")
    if isinstance(content, str):
        content = content.strip()
        return _sanitize_text(content) if content else None
    if not isinstance(content, list):
        return None
    text_parts: list[str] = []
    for part in content:
        if not isinstance(part, dict):
            continue
        if part.get("type") == "text" and "text" in part:
            text_parts.append(str(part.get("text", "")))
            continue
        if "text" in part and isinstance(part.get("text"), str):
            text_parts.append(str(part.get("text", "")))
            continue
        if "content" in part and isinstance(part.get("content"), str):
            text_parts.append(str(part.get("content", "")))
            continue
        if "input" in part:
            try:
                text_parts.append(json.dumps(part.get("input"), ensure_ascii=False))
            except Exception:
                text_parts.append(str(part.get("input")))
    text = "\n".join(s for s in text_parts if s)
    return _sanitize_text(text.strip()) if text else None


def _contains_sql_bind_parameters(sql: str) -> bool:
    if not sql:
        return False
    patterns = (
        r":([A-Za-z_][A-Za-z0-9_]*)",
        r"\$\d+",
        r"\?",
    )
    return any(re.search(pattern, sql) for pattern in patterns)


def _call_dspy_lm(
    lm: "dspy.LM",
    *,
    messages: Sequence[Dict[str, str]],
    max_tokens: int,
    temperature: float,
    response_format: Optional[Dict[str, object]] = None,
) -> Optional[str]:
    base_kwargs: Dict[str, object] = {"max_tokens": max_tokens, "temperature": temperature}
    if response_format:
        base_kwargs["response_format"] = response_format

    prompt = _messages_to_prompt(messages)
    attempts: list[tuple[str, Dict[str, object]]] = [("messages", dict(base_kwargs))]
    if response_format:
        fallback_kwargs = dict(base_kwargs)
        fallback_kwargs.pop("response_format", None)
        attempts.append(("messages", fallback_kwargs))
    attempts.append(("prompt", dict(base_kwargs)))
    if response_format:
        prompt_fallback_kwargs = dict(base_kwargs)
        prompt_fallback_kwargs.pop("response_format", None)
        attempts.append(("prompt", prompt_fallback_kwargs))

    warned_no_response_format = False
    last_exc: Optional[Exception] = None
    for mode, kwargs in attempts:
        try:
            if mode == "messages":
                response = lm(messages=messages, **kwargs)
            else:
                response = lm(prompt, **kwargs)
            return _extract_text_from_response(response)
        except TypeError as exc:
            last_exc = exc
            continue
        except Exception as exc:  # pragma: no cover - defensive
            last_exc = exc
            text = str(exc)
            if "response_format" in text and "UnsupportedParamsError" in text and "response_format" in kwargs:
                if not warned_no_response_format:
                    LOGGER.warning(
                        "DSPy LM rejected response_format; retrying without it: %s",
                        exc,
                    )
                    warned_no_response_format = True
                continue
            LOGGER.warning("DSPy LM call failed: %s", exc)
            return None

    if last_exc is not None:
        LOGGER.warning("DSPy LM call failed: %s", last_exc)
    return None


def _responses_message_to_input_item(msg: dict) -> dict:
    role = msg.get("role", "user")
    content = msg.get("content", "")
    parts: list[dict] = []
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and "text" in part:
                parts.append({"type": "input_text", "text": _sanitize_text(str(part.get("text", "")))})
            elif isinstance(part, str):
                parts.append({"type": "input_text", "text": _sanitize_text(part)})
            else:
                parts.append({"type": "input_text", "text": _sanitize_text(str(part))})
    elif isinstance(content, str):
        parts.append({"type": "input_text", "text": _sanitize_text(content)})
    else:
        parts.append({"type": "input_text", "text": _sanitize_text(str(content))})
    return {"role": role, "content": parts}


def _extract_responses_text(data: dict) -> Optional[str]:
    if not isinstance(data, dict):
        return None
    output_text = data.get("output_text")
    if isinstance(output_text, str) and output_text:
        return _sanitize_text(output_text.strip())
    outputs = data.get("output")
    if not isinstance(outputs, list):
        return None
    chunks: list[str] = []
    for item in outputs:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "message":
            content = item.get("content", [])
            if isinstance(content, list):
                for part in content:
                    if not isinstance(part, dict):
                        continue
                    if part.get("type") in {"output_text", "text"} and "text" in part:
                        chunks.append(_sanitize_text(str(part.get("text", ""))))
        elif item.get("type") == "output_text" and "text" in item:
            chunks.append(_sanitize_text(str(item.get("text", ""))))
    text = "\n".join(s for s in chunks if s)
    return text.strip() if text else None


def _extract_tagged_section(
    text: str,
    tag_name: str,
    *,
    start_at: int = 0,
) -> tuple[Optional[str], int]:
    open_pat = re.compile(rf"<{re.escape(tag_name)}(?:\s[^>]*)?>", flags=re.IGNORECASE)
    self_closing_pat = re.compile(rf"<{re.escape(tag_name)}\s*/>", flags=re.IGNORECASE)
    close_text = f"</{tag_name}>"

    self_match = self_closing_pat.search(text, start_at)
    open_match = open_pat.search(text, start_at)
    if self_match and (open_match is None or self_match.start() <= open_match.start()):
        return text[self_match.start():self_match.end()], self_match.end()
    if not open_match:
        return None, start_at
    close_idx = text.find(close_text, open_match.end())
    if close_idx == -1:
        return None, start_at
    end_idx = close_idx + len(close_text)
    return text[open_match.start():end_idx], end_idx


def _build_anthropic_user_blocks(content: Any) -> list[dict[str, Any]]:
    if isinstance(content, list):
        blocks: list[dict[str, Any]] = []
        for item in content:
            if isinstance(item, dict):
                blocks.append(dict(item))
            elif isinstance(item, str):
                blocks.append({"type": "text", "text": _sanitize_text(item)})
            else:
                blocks.append({"type": "text", "text": _sanitize_text(str(item))})
        return blocks

    text = _sanitize_text(content if isinstance(content, str) else str(content))
    cursor = 0
    task_block, cursor = _extract_tagged_section(text, "TASK", start_at=cursor)
    uq_block, cursor = _extract_tagged_section(text, "UQ", start_at=cursor)
    filter_block, cursor = _extract_tagged_section(text, "FILTER_PROFILE", start_at=cursor)
    history_block, history_end = _extract_tagged_section(text, "HISTORY", start_at=cursor)
    if history_block is not None:
        cursor = history_end

    prefix_parts = [part.strip() for part in (task_block, uq_block, filter_block) if part and part.strip()]
    tail = text[cursor:].strip()

    blocks: list[dict[str, Any]] = []
    if prefix_parts:
        blocks.append(
            {
                "type": "text",
                "text": "\n".join(prefix_parts),
                "cache_control": {"type": "ephemeral"},
            }
        )
    if history_block and history_block.strip() != "<HISTORY/>":
        blocks.append(
            {
                "type": "text",
                "text": history_block.strip(),
                "cache_control": {"type": "ephemeral"},
            }
        )
    elif history_block and not prefix_parts:
        blocks.append({"type": "text", "text": history_block.strip()})
    if tail:
        blocks.append({"type": "text", "text": tail})
    if not blocks:
        blocks.append({"type": "text", "text": text})
    return blocks


def _build_endpoint_label(spec: "EndpointSpec") -> str:
    parts = [spec.provider]
    if spec.model:
        parts.append(spec.model)
    if spec.base_url:
        parts.append(spec.base_url)
    return "|".join(parts)


def _parse_endpoint_spec(
    raw: str,
    *,
    role: str,
    default_provider: str,
    default_model: Optional[str],
    default_base_url: Optional[str],
    default_temperature: float,
    default_timeout: int,
) -> "EndpointSpec":
    data: Dict[str, str] = {}
    text = (raw or "").strip()
    if text:
        for part in text.split(","):
            part = part.strip()
            if not part:
                continue
            if "=" not in part:
                data["model"] = part
                continue
            key, value = part.split("=", 1)
            data[key.strip().lower()] = value.strip()

    provider = data.get("provider", default_provider)
    model = data.get("model", default_model)
    base_url = data.get("base_url", data.get("url", default_base_url))
    temperature = float(data.get("temperature", default_temperature))
    timeout = int(data.get("timeout", default_timeout))
    spec = EndpointSpec(
        role=role,
        provider=provider,
        model=model,
        base_url=base_url,
        temperature=temperature,
        timeout=timeout,
        label="",
    )
    return EndpointSpec(
        role=spec.role,
        provider=spec.provider,
        model=spec.model,
        base_url=spec.base_url,
        temperature=spec.temperature,
        timeout=spec.timeout,
        label=_build_endpoint_label(spec),
    )


class DspyProvider:
    def __init__(
        self,
        *,
        provider: str,
        model: Optional[str],
        base_url: Optional[str],
        temperature: float,
        timeout: int,
        local_enable_thinking: bool = True,
        local_reasoning_budget_tokens: Optional[int] = None,
        local_reasoning_budget_message: Optional[str] = None,
        shared_quota_fallback_state: Optional[SharedQuotaFallbackState] = None,
    ) -> None:
        self.temperature = float(temperature)
        self.timeout = int(timeout)
        self.local_enable_thinking = bool(local_enable_thinking)
        self.local_reasoning_budget_tokens = (
            None if local_reasoning_budget_tokens is None else int(local_reasoning_budget_tokens)
        )
        self.local_reasoning_budget_message = local_reasoning_budget_message
        self.shared_quota_fallback_state = shared_quota_fallback_state
        self._fallback_applied_index = -1
        self._apply_endpoint(provider=provider, model=model, base_url=base_url)

    def _apply_endpoint(
        self,
        *,
        provider: str,
        model: Optional[str],
        base_url: Optional[str],
    ) -> None:
        self.provider = provider
        if provider == "zai":
            model = _normalize_zai_model_name(model)
        self.model = model
        self.responses_model = model
        self.dspy_model = _resolve_dspy_model(provider, model)
        self.base_url = base_url
        self.api_key = _provider_api_key(provider)
        if provider in {"llamacpp", "mlxlm", "local"} and not self.api_key:
            self.api_key = "EMPTY"
        if provider in {"openai", "openrouter", "llamacpp", "mlxlm", "local"}:
            self.base_url = _normalize_openai_base_url(self.base_url, provider=provider)
            if provider in {"openai", "llamacpp", "mlxlm", "local"} and self.responses_model and "/" in self.responses_model:
                self.responses_model = self.responses_model.split("/", 1)[-1]
        if provider == "zai" and not self.base_url:
            self.base_url = os.getenv("ZAI_BASE_URL", "https://api.z.ai/api/paas/v4").rstrip("/")
        if provider == "zai-anthropic" and not self.base_url:
            self.base_url = os.getenv("ZAI_ANTHROPIC_BASE_URL", "https://api.z.ai/api/anthropic").rstrip("/")

    def _apply_shared_quota_fallback_if_active(self) -> None:
        if not self.shared_quota_fallback_state or not self.shared_quota_fallback_state.active:
            return
        if self._fallback_applied_index == self.shared_quota_fallback_state.current_index:
            return
        config = self.shared_quota_fallback_state.config
        LOGGER.warning(
            "Quota fallback active; switching provider from %s/%s to %s/%s (%s)",
            self.provider,
            self.model,
            config.provider,
            config.model,
            self.shared_quota_fallback_state.reason or "quota limit",
        )
        self._apply_endpoint(provider=config.provider, model=config.model, base_url=config.base_url)
        self._fallback_applied_index = self.shared_quota_fallback_state.current_index

    @staticmethod
    def _runtime_provider_label(provider_obj: "DspyProvider") -> str:
        provider = str(provider_obj.provider or "unknown-provider")
        model = str(provider_obj.model or "unknown-model")
        return f"{provider}/{model}"

    def _refresh_runtime_routing(self) -> None:
        if not self.shared_quota_fallback_state:
            return
        restored_primary = self.shared_quota_fallback_state.maybe_restore_primary()
        if restored_primary is not None:
            LOGGER.warning(
                "Quota cooldown elapsed; restoring primary provider to %s/%s (%s)",
                restored_primary.provider,
                restored_primary.model,
                restored_primary.base_url,
            )
            self._apply_endpoint(
                provider=restored_primary.provider,
                model=restored_primary.model,
                base_url=restored_primary.base_url,
            )
            self._fallback_applied_index = -1
        refreshed = self.shared_quota_fallback_state.maybe_refresh_configs()
        if refreshed:
            LOGGER.info("Refreshed fallback endpoint availability during long-running job.")

    def _advance_shared_fallback_on_request_failure(self, exc: Exception) -> bool:
        if not self.shared_quota_fallback_state or not self.shared_quota_fallback_state.active:
            return False
        config = self.shared_quota_fallback_state.config
        config_base_url = _normalize_provider_base_url_for_compare(config.provider, config.base_url)
        provider_base_url = _normalize_provider_base_url_for_compare(self.provider, self.base_url)
        if config.provider != self.provider or config_base_url != provider_base_url:
            return False
        activated = self.shared_quota_fallback_state.activate(
            reason=f"{self.provider} request failure: {type(exc).__name__}: {exc}"
        )
        if not activated:
            restored_primary = self.shared_quota_fallback_state.force_restore_primary(
                reason=f"active fallback failed; retrying primary after {type(exc).__name__}: {exc}"
            )
            if restored_primary is None:
                return False
            LOGGER.warning(
                "Active fallback %s/%s at %s failed and no additional fallbacks remain; retrying primary %s/%s at %s",
                config.provider,
                config.model,
                config.base_url,
                restored_primary.provider,
                restored_primary.model,
                restored_primary.base_url,
            )
            self._apply_endpoint(
                provider=restored_primary.provider,
                model=restored_primary.model,
                base_url=restored_primary.base_url,
            )
            self._fallback_applied_index = -1
            return True
        LOGGER.warning(
            "Advancing shared fallback after request failure to %s/%s at %s",
            self.shared_quota_fallback_state.config.provider,
            self.shared_quota_fallback_state.config.model,
            self.shared_quota_fallback_state.config.base_url,
        )
        self._apply_shared_quota_fallback_if_active()
        return True

    def is_available(self) -> bool:
        if self.provider == "zai":
            return bool(self.model and self.api_key and self.base_url)
        if self.provider == "zai-anthropic":
            return bool(self.model and self.api_key and self.base_url and self.dspy_model)
        return bool(self.dspy_model)

    def generate_text(
        self,
        messages: Sequence[Dict[str, str]],
        *,
        max_tokens: int,
        temperature: float,
        response_format: Optional[Dict[str, object]] = None,
    ) -> Optional[str]:
        self._refresh_runtime_routing()
        self._apply_shared_quota_fallback_if_active()
        try:
            if self.provider == "zai":
                return self._call_zai_chat_api(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
            if self.provider == "zai-anthropic":
                return self._call_zai_anthropic_messages_api(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    response_format=response_format,
                )
            if not self.dspy_model:
                return None
            if self.provider == "openrouter":
                return self._call_responses_api(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    response_format=response_format,
                )
            if self.provider in {"openai", "llamacpp", "mlxlm", "local"}:
                return self._call_openai_chat_api(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    response_format=response_format,
                )
            lm_kwargs: Dict[str, object] = {
                "model": self.dspy_model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "timeout": self.timeout,
            }
            if self.base_url:
                lm_kwargs["api_base"] = self.base_url
            if self.api_key:
                lm_kwargs["api_key"] = self.api_key
            lm = dspy.LM(**lm_kwargs)
            return _call_dspy_lm(
                lm,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                response_format=response_format,
            )
        except QuotaFallbackTriggered as exc:
            if not self.shared_quota_fallback_state:
                LOGGER.warning("Quota hit for %s without fallback configured: %s", exc.provider, exc.message)
                return None
            activated = self.shared_quota_fallback_state.activate(
                reason=f"{exc.provider} quota code {exc.code or 'unknown'}: {exc.message}"
            )
            if activated:
                LOGGER.warning(
                    "Activating shared quota fallback to %s/%s at %s",
                    self.shared_quota_fallback_state.config.provider,
                    self.shared_quota_fallback_state.config.model,
                    self.shared_quota_fallback_state.config.base_url,
                )
            self._apply_shared_quota_fallback_if_active()
            return self.generate_text(
                messages,
                max_tokens=max_tokens,
                temperature=temperature,
                response_format=response_format,
            )

    def _call_responses_api(
        self,
        *,
        messages: Sequence[Dict[str, str]],
        max_tokens: int,
        temperature: float,
        response_format: Optional[Dict[str, object]],
    ) -> Optional[str]:
        if not self.base_url:
            return None
        input_items = [_responses_message_to_input_item(m) for m in messages]
        payload: Dict[str, object] = {
            "model": self.responses_model,
            "input": input_items,
            "max_output_tokens": int(max_tokens),
        }
        if temperature is not None:
            payload["temperature"] = float(temperature)
        if response_format:
            payload["response_format"] = response_format
        if self.provider in {"llamacpp", "mlxlm", "local"}:
            # llama.cpp-local knob; remote providers such as Z.AI do not expose
            # this OpenAI-compatible chat-template flag.
            payload["chat_template_kwargs"] = {"enable_thinking": self.local_enable_thinking}
            if self.local_reasoning_budget_tokens is not None:
                payload["thinking_budget_tokens"] = self.local_reasoning_budget_tokens
                payload["reasoning_budget_tokens"] = self.local_reasoning_budget_tokens
                if self.local_reasoning_budget_message:
                    payload["reasoning_budget_message"] = self.local_reasoning_budget_message

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if self.provider == "openrouter":
            headers["HTTP-Referer"] = "https://github.com/ljubomirj"
            headers["X-Title"] = "ChEMBLdb Text2SQL"

        response = None
        try:
            LOGGER.warning("OPENCODEGO_DEBUG: model=%s base_url=%s api_key=%s", self.model, self.base_url, "***" if self.api_key else "none")
            LOGGER.warning("OPENCODEGO_DEBUG: payload size=%d chars payload_keys=%s", len(str(payload)), list(payload.keys()))
            retried_without_temperature = False
            while True:
                response = requests.post(
                    f"{self.base_url}/responses",
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )
                if response.status_code == 400 and payload.get("temperature") is not None:
                    try:
                        err_data = response.json()
                    except Exception:
                        err_data = {}
                    err = err_data.get("error") if isinstance(err_data, dict) else None
                    param = err.get("param") if isinstance(err, dict) else None
                    if param == "temperature" and not retried_without_temperature:
                        LOGGER.warning(
                            "Responses API rejected temperature; retrying without temperature (model=%s).",
                            self.model,
                        )
                        payload = dict(payload)
                        payload.pop("temperature", None)
                        retried_without_temperature = True
                        continue
                response.raise_for_status()
                data = response.json()
                text = _extract_responses_text(data)
                if text is None:
                    try:
                        preview = json.dumps(data, ensure_ascii=False)[:2000]
                    except Exception:
                        preview = str(data)[:2000]
                    LOGGER.warning(
                        "Responses API returned no textual output; provider=%s model=%s preview=%s",
                        self.provider,
                        self.model,
                        preview,
                    )
                return text
        except requests.exceptions.RequestException as exc:
            if self._advance_shared_fallback_on_request_failure(exc):
                return self.generate_text(
                    messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    response_format=response_format,
                )
            LOGGER.warning("Responses API request failed: %s", exc)
            return None

    def _call_zai_chat_api(
        self,
        *,
        messages: Sequence[Dict[str, str]],
        max_tokens: int,
        temperature: float,
    ) -> Optional[str]:
        if not self.base_url or not self.api_key or not self.model:
            return None
        payload: Dict[str, object] = {
            "model": self.model,
            "messages": list(messages),
            "max_tokens": int(max_tokens),
            "stream": False,
        }
        if temperature is not None:
            payload["temperature"] = float(temperature)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept-Language": "en-US,en",
        }
        response = None
        try:
            LOGGER.warning("OPENCODEGO_DEBUG: model=%s base_url=%s api_key=%s", self.model, self.base_url, "***" if self.api_key else "none")
            LOGGER.warning("OPENCODEGO_DEBUG: payload size=%d chars payload_keys=%s", len(str(payload)), list(payload.keys()))
            retried_without_temperature = False
            while True:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )
                if response.status_code == 429:
                    try:
                        err_data = response.json()
                    except Exception:
                        err_data = {}
                    err = err_data.get("error") if isinstance(err_data, dict) else None
                    code = None
                    message = ""
                    if isinstance(err, dict):
                        if err.get("code") is not None:
                            code = str(err.get("code"))
                        message = str(err.get("message", ""))
                    elif isinstance(err_data, dict):
                        if err_data.get("code") is not None:
                            code = str(err_data.get("code"))
                        message = str(err_data.get("message", err_data.get("msg", "")))
                    if code in {"1302", "1308"}:
                        raise QuotaFallbackTriggered(
                            provider="zai",
                            code=code,
                            message=message or "Z.AI chat endpoint rate or quota limit reached.",
                        )
                if response.status_code == 400 and payload.get("temperature") is not None:
                    try:
                        err_data = response.json()
                    except Exception:
                        err_data = {}
                    err = err_data.get("error") if isinstance(err_data, dict) else None
                    param = err.get("param") if isinstance(err, dict) else None
                    if param == "temperature" and not retried_without_temperature:
                        LOGGER.warning(
                            "Z.AI chat API rejected temperature; retrying without temperature (model=%s).",
                            self.model,
                        )
                        payload = dict(payload)
                        payload.pop("temperature", None)
                        retried_without_temperature = True
                        continue
                response.raise_for_status()
                data = response.json()
                choices = data.get("choices")
                if not isinstance(choices, list) or not choices:
                    LOGGER.warning("Z.AI chat API returned no choices.")
                    return None
                message = choices[0].get("message", {})
                content = message.get("content", "") if isinstance(message, dict) else ""
                if isinstance(content, list):
                    text_parts: list[str] = []
                    for part in content:
                        if isinstance(part, dict) and "text" in part:
                            text_parts.append(str(part.get("text", "")))
                        elif isinstance(part, str):
                            text_parts.append(part)
                    content = "\n".join(text_parts)
                if not isinstance(content, str):
                    content = str(content)
                return _sanitize_text(content.strip())
        except requests.exceptions.RequestException as exc:
            if response is not None:
                try:
                    LOGGER.warning("Z.AI chat API error body: %s", response.text[:2000])
                except Exception:
                    pass
            LOGGER.warning("Z.AI chat API request failed: %s", exc)
            return None

    def _call_openai_chat_api(
        self,
        *,
        messages: Sequence[Dict[str, str]],
        max_tokens: int,
        temperature: float,
        response_format: Optional[Dict[str, object]],
    ) -> Optional[str]:
        if not self.base_url or not self.api_key or not self.model:
            return None
        payload: Dict[str, object] = {
            "model": self.model,
            "messages": list(messages),
            "max_tokens": int(max_tokens),

        }
        if temperature is not None:
            payload["temperature"] = float(temperature)
        # response_format is intentionally skipped — OpenCode Go's API rejects it.
        if self.provider in {"llamacpp", "mlxlm", "local"}:
            # Local Qwen-style servers otherwise default to a reasoning-only
            # response.  Keep this request-level control aligned with the
            # Responses API path above, including any caller-selected budget.
            payload["chat_template_kwargs"] = {
                "enable_thinking": self.local_enable_thinking,
            }
            if self.local_reasoning_budget_tokens is not None:
                payload["thinking_budget_tokens"] = self.local_reasoning_budget_tokens
                payload["reasoning_budget_tokens"] = self.local_reasoning_budget_tokens
                if self.local_reasoning_budget_message:
                    payload["reasoning_budget_message"] = self.local_reasoning_budget_message

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept-Language": "en-US,en",
        }
        response = None
        try:
            LOGGER.warning("OPENCODEGO_DEBUG: model=%s base_url=%s api_key=%s", self.model, self.base_url, "***" if self.api_key else "none")
            LOGGER.warning("OPENCODEGO_DEBUG: payload size=%d chars payload_keys=%s", len(str(payload)), list(payload.keys()))
            retried_without_temperature = False
            while True:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )
                if response.status_code == 400 and payload.get("temperature") is not None:
                    try:
                        err_data = response.json()
                    except Exception:
                        err_data = {}
                    err = err_data.get("error") if isinstance(err_data, dict) else None
                    param = err.get("param") if isinstance(err, dict) else None
                    if param == "temperature" and not retried_without_temperature:
                        LOGGER.warning(
                            "OpenAI chat API rejected temperature; retrying without temperature (model=%s).",
                            self.model,
                        )
                        payload = dict(payload)
                        payload.pop("temperature", None)
                        retried_without_temperature = True
                        continue
                response.raise_for_status()
                data = response.json()
                choices = data.get("choices")
                if not isinstance(choices, list) or not choices:
                    LOGGER.warning("OpenAI chat API returned no choices.")
                    return None
                message = choices[0].get("message", {})
                content = message.get("content", "") if isinstance(message, dict) else ""
                if isinstance(content, list):
                    text_parts: list[str] = []
                    for part in content:
                        if isinstance(part, dict) and "text" in part:
                            text_parts.append(str(part.get("text", "")))
                        elif isinstance(part, str):
                            text_parts.append(part)
                    content = "\n".join(text_parts)
                if not isinstance(content, str):
                    content = str(content)
                return _sanitize_text(content.strip())
        except requests.exceptions.RequestException as exc:
            if response is not None:
                try:
                    LOGGER.warning("OpenAI chat API error body: %s", response.text[:2000])
                except Exception:
                    pass
            LOGGER.warning("OpenAI chat API request failed: %s", exc)
            return None

    def _call_zai_anthropic_messages_api(
        self,
        *,
        messages: Sequence[Dict[str, str]],
        max_tokens: int,
        temperature: float,
        response_format: Optional[Dict[str, object]],
    ) -> Optional[str]:
        if not self.base_url or not self.api_key or not self.model:
            return None

        system_blocks: list[dict[str, Any]] = []
        user_messages: list[dict[str, Any]] = []
        for msg in messages:
            role = str(msg.get("role", "user"))
            content = msg.get("content", "")
            if role == "system":
                if isinstance(content, list):
                    for item in content:
                        block = dict(item) if isinstance(item, dict) else {"type": "text", "text": _sanitize_text(str(item))}
                        if "cache_control" not in block:
                            block["cache_control"] = {"type": "ephemeral"}
                        system_blocks.append(block)
                else:
                    system_blocks.append(
                        {
                            "type": "text",
                            "text": _sanitize_text(content if isinstance(content, str) else str(content)),
                            "cache_control": {"type": "ephemeral"},
                        }
                    )
                continue
            anthropic_role = role if role in {"user", "assistant"} else "user"
            user_messages.append(
                {
                    "role": anthropic_role,
                    "content": _build_anthropic_user_blocks(content),
                }
            )

        if not system_blocks:
            system_blocks = [
                {
                    "type": "text",
                    "text": "You are a helpful assistant.",
                    "cache_control": {"type": "ephemeral"},
                }
            ]

        payload: Dict[str, object] = {
            "model": self.model,
            "max_tokens": int(max_tokens),
            "system": system_blocks,
            "messages": user_messages,
        }
        if temperature is not None:
            payload["temperature"] = float(temperature)
        _ = response_format

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        response = None
        try:
            LOGGER.warning("OPENCODEGO_DEBUG: model=%s base_url=%s api_key=%s", self.model, self.base_url, "***" if self.api_key else "none")
            LOGGER.warning("OPENCODEGO_DEBUG: payload size=%d chars payload_keys=%s", len(str(payload)), list(payload.keys()))
            retried_without_temperature = False
            while True:
                response = requests.post(
                    f"{self.base_url}/v1/messages",
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )
                if response.status_code == 429:
                    try:
                        err_data = response.json()
                    except Exception:
                        err_data = {}
                    err = err_data.get("error") if isinstance(err_data, dict) else None
                    code = None
                    message = ""
                    if isinstance(err, dict):
                        if err.get("code") is not None:
                            code = str(err.get("code"))
                        message = str(err.get("message", ""))
                    elif isinstance(err_data, dict):
                        if err_data.get("code") is not None:
                            code = str(err_data.get("code"))
                        message = str(err_data.get("message", err_data.get("msg", "")))
                    if code in {"1302", "1308"}:
                        raise QuotaFallbackTriggered(
                            provider="zai-anthropic",
                            code=code,
                            message=message or "Rate or quota limit reached for Z.AI Anthropic endpoint.",
                        )
                if response.status_code == 400 and payload.get("temperature") is not None:
                    try:
                        err_data = response.json()
                    except Exception:
                        err_data = {}
                    err = err_data.get("error") if isinstance(err_data, dict) else None
                    err_message = ""
                    if isinstance(err, dict):
                        err_message = str(err.get("message", ""))
                    elif isinstance(err_data, dict):
                        err_message = str(err_data.get("msg", ""))
                    if "temperature" in err_message.lower() and not retried_without_temperature:
                        LOGGER.warning(
                            "Z.AI Anthropic API rejected temperature; retrying without temperature (model=%s).",
                            self.model,
                        )
                        payload = dict(payload)
                        payload.pop("temperature", None)
                        retried_without_temperature = True
                        continue
                response.raise_for_status()
                data = response.json()
                usage = data.get("usage", {}) if isinstance(data, dict) else {}
                if isinstance(usage, dict):
                    cache_read = usage.get("cache_read_input_tokens")
                    if cache_read:
                        LOGGER.info(
                            "Z.AI Anthropic cache hit: cache_read_input_tokens=%s model=%s",
                            cache_read,
                            self.model,
                        )
                text = _extract_anthropic_text(data)
                if text:
                    return text
                stop_reason = data.get("stop_reason") if isinstance(data, dict) else None
                content = data.get("content") if isinstance(data, dict) else None
                content_types: list[str] = []
                if isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict):
                            content_types.append(str(part.get("type", "unknown")))
                        else:
                            content_types.append(type(part).__name__)
                preview = ""
                try:
                    preview = json.dumps(data, ensure_ascii=False)[:2000]
                except Exception:
                    preview = str(data)[:2000]
                LOGGER.warning(
                    "Z.AI Anthropic API returned no textual content; stop_reason=%s content_types=%s preview=%s",
                    stop_reason,
                    content_types,
                    preview,
                )
                return None
        except requests.exceptions.RequestException as exc:
            if response is not None:
                try:
                    LOGGER.warning("Z.AI Anthropic API error body: %s", response.text[:2000])
                except Exception:
                    pass
            LOGGER.warning("Z.AI Anthropic API request failed: %s", exc)
            return None


def create_dspy_provider(
    *,
    provider: str,
    model: Optional[str],
    verbose: bool,
    temperature: float,
    timeout: int,
    base_url: Optional[str] = None,
    local_enable_thinking: bool = True,
    local_reasoning_budget_tokens: Optional[int] = None,
    local_reasoning_budget_message: Optional[str] = None,
    shared_quota_fallback_state: Optional[SharedQuotaFallbackState] = None,
) -> DspyProvider:
    _ = verbose
    return DspyProvider(
        provider=provider,
        model=model,
        base_url=base_url,
        temperature=temperature,
        timeout=timeout,
        local_enable_thinking=local_enable_thinking,
        local_reasoning_budget_tokens=local_reasoning_budget_tokens,
        local_reasoning_budget_message=local_reasoning_budget_message,
        shared_quota_fallback_state=shared_quota_fallback_state,
    )


def _format_param_value(value: Any) -> str:
    return repr(value)


def _sanitize_text(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    return text.encode('utf-8', 'replace').decode('utf-8')


def _emit_raw_block(text: str) -> None:
    if text is None:
        return
    sanitized = _sanitize_text(text)
    if not sanitized.endswith("\n"):
        sanitized += "\n"
    root = logging.getLogger()
    stream = None
    for handler in root.handlers:
        stream = getattr(handler, "stream", None)
        if stream is not None:
            break
    if stream is None:
        stream = sys.stderr
    try:
        stream.write(sanitized)
        stream.flush()
    except Exception:
        sys.stderr.write(sanitized)
        sys.stderr.flush()


def LOG_BLOCK(text: str) -> None:
    _emit_raw_block(text)


def log_stage_labels() -> None:
    LOGGER.info("Stage labels (short -> long):")
    for short, long_name in STAGE_LABELS:
        LOGGER.info("  %s = %s", short, long_name)


def log_effective_params(
    args: argparse.Namespace,
    *,
    provider: str,
    run_id: Optional[str],
    query: Optional[str],
    save_file: Optional[str],
) -> None:
    LOGGER.info("Effective parameters:")
    effective_judge_context = args.judge_context_limit
    if effective_judge_context is None:
        effective_judge_context = DEFAULT_JUDGE_CONTEXT_LIMITS.get(provider)
    derived_params = [
        ("query", query),
        ("provider", provider),
        ("run_id", run_id),
        ("save_file", save_file),
        ("judge_context_limit_effective", effective_judge_context),
    ]
    for key, value in derived_params:
        LOGGER.info("  %s = %s", key, _format_param_value(value))
    LOGGER.info("CLI arguments (post-defaults):")
    for key, value in sorted(vars(args).items()):
        LOGGER.info("  %s = %s", key, _format_param_value(value))


OPENROUTER_CHEAP_MODELS = [
    'z-ai/glm-4.7',
    'z-ai/glm-4.6v',
    'z-ai/glm-4.6:exacto',
    'z-ai/glm-4.5-air:free',
    'minimax/minimax-m2.1',
    'anthropic/claude-haiku-4.5',
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

OPENROUTER_EXPENSIVE_MODELS = [
    'openai/gpt-5.2',
    'openai/gpt-5.2-chat',
    'openai/gpt-5.1-codex-max',
    'openai/gpt-5.1-codex',
    'anthropic/claude-sonnet-4.5',
    'x-ai/grok-4',
    'google/gemini-3-pro-preview',
    'qwen/qwen3-coder-plus',
    'qwen/qwen3-coder:exacto',
]

OPENROUTER_SUPER_MODELS = [
    'openai/gpt-5.2-pro',
    'anthropic/claude-opus-4.5',
]

OPENROUTER_ALL_MODELS = (
    OPENROUTER_CHEAP_MODELS + OPENROUTER_EXPENSIVE_MODELS + OPENROUTER_SUPER_MODELS
)

# Provider-specific model lists (explicit providers)
ZAI_MODELS = [
    'glm-4.7',
    'glm-4.5-air',
    'pony-alpha-2',
]

CEREBRAS_MODELS = [
    'zai-glm-4.7',
]

DEEPSEEK_MODELS = [
    'deepseek-reasoner',
    'deepseek-chat',
]

LLAMACPP_MODELS = [
    'minimax-m2.1',
    'qwen3-next-80b-a3b-thinking',
    'nvidia-nemotron-3-nano-30b-a3b-mlx',
    'nvidia-nemotron-3-nano-30b-a3b-mlx',
    'glm-4.7-flash',
]

MLXLM_MODELS = list(LLAMACPP_MODELS)

GEMINI_CHEAP_MODELS = [
    'gemini-2.5-flash-lite',
]

GEMINI_EXPENSIVE_MODELS = [
    'gemini-2.5-flash',
    'gemini-3-flash-preview',
]

GEMINI_SUPER_MODELS = [
    'gemini-2.5-pro',
]

GEMINI_ALL_MODELS = GEMINI_CHEAP_MODELS + GEMINI_EXPENSIVE_MODELS + GEMINI_SUPER_MODELS

OPENAI_CHEAP_MODELS = [
    'gpt-5.1-codex-mini',
    'gpt-5-mini',
    'gpt-5-nano',
    'o3-mini',
    'o3-mini-high',
]

OPENAI_EXPENSIVE_MODELS = [
    'gpt-5.1-codex',
    'gpt-5.2-codex',
    'gpt-5.1',
    'gpt-5.2',
    'gpt-5.1-chat',
    'gpt-5.2-chat',
    'gpt-5-image',
    'gpt-5-image-mini',
    'o3',
]

OPENAI_SUPER_MODELS = [
    'gpt-5.1-codex-max',
    'gpt-5.2-pro',
    'gpt-5-pro',
    'o3-pro',
    'o3-deep-research',
]

OPENAI_ALL_MODELS = OPENAI_CHEAP_MODELS + OPENAI_EXPENSIVE_MODELS + OPENAI_SUPER_MODELS

ANTHROPIC_CHEAP_MODELS = [
    'claude-haiku-4.5',
]

ANTHROPIC_EXPENSIVE_MODELS = [
    'claude-sonnet-4.5',
]

ANTHROPIC_SUPER_MODELS = [
    'claude-opus-4.5',
]

ANTHROPIC_ALL_MODELS = (
    ANTHROPIC_CHEAP_MODELS + ANTHROPIC_EXPENSIVE_MODELS + ANTHROPIC_SUPER_MODELS
)


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
    if provider_lower == 'zai':
        return ZAI_MODELS
    if provider_lower == 'cerebras':
        return CEREBRAS_MODELS
    if provider_lower == 'deepseek':
        return DEEPSEEK_MODELS
    if provider_lower == 'llamacpp':
        return LLAMACPP_MODELS
    if provider_lower == 'mlxlm':
        return MLXLM_MODELS
    if provider_lower == 'gemini':
        if category == 'cheap':
            return GEMINI_CHEAP_MODELS
        if category == 'expensive':
            return GEMINI_EXPENSIVE_MODELS
        if category == 'super':
            return GEMINI_SUPER_MODELS
        if category == 'all':
            return GEMINI_ALL_MODELS
        raise ValueError(f"Invalid model category: {category}")
    if provider_lower == 'openai':
        if category == 'cheap':
            return OPENAI_CHEAP_MODELS
        if category == 'expensive':
            return OPENAI_EXPENSIVE_MODELS
        if category == 'super':
            return OPENAI_SUPER_MODELS
        if category == 'all':
            return OPENAI_ALL_MODELS
        raise ValueError(f"Invalid model category: {category}")
    if provider_lower == 'anthropic':
        if category == 'cheap':
            return ANTHROPIC_CHEAP_MODELS
        if category == 'expensive':
            return ANTHROPIC_EXPENSIVE_MODELS
        if category == 'super':
            return ANTHROPIC_SUPER_MODELS
        if category == 'all':
            return ANTHROPIC_ALL_MODELS
        raise ValueError(f"Invalid model category: {category}")
    if provider_lower == 'local':
        return []

    if category == 'cheap':
        return OPENROUTER_CHEAP_MODELS
    if category == 'expensive':
        return OPENROUTER_EXPENSIVE_MODELS
    if category == 'super':
        return OPENROUTER_SUPER_MODELS
    if category == 'all':
        return OPENROUTER_ALL_MODELS
    raise ValueError(f"Invalid model category: {category}")


_OPENROUTER_CONTEXT_CACHE: Optional[Dict[str, int]] = None


def filter_openrouter_models_by_context(models: List[str], min_context: int) -> List[str]:
    if min_context <= 0:
        return models

    global _OPENROUTER_CONTEXT_CACHE
    try:
        if _OPENROUTER_CONTEXT_CACHE is None:
            _OPENROUTER_CONTEXT_CACHE = get_openrouter_context_map()
        context_map = _OPENROUTER_CONTEXT_CACHE
    except Exception:
        LOGGER.warning("Failed to fetch OpenRouter models for context filtering; using unfiltered list.", exc_info=True)
        return models

    filtered = [m for m in models if context_map.get(m, 0) >= min_context]
    if not filtered:
        LOGGER.error("No OpenRouter models meet min_context=%s.", min_context)
        return []

    if len(filtered) != len(models):
        LOGGER.info("Filtered OpenRouter models by context >= %s: %s -> %s", min_context, len(models), len(filtered))
    return filtered


def get_openrouter_context_map() -> Dict[str, int]:
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        LOGGER.warning("OPENROUTER_API_KEY not set; cannot fetch OpenRouter model context.")
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
    max_cell_len: int = 40,
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
    max_samples: int = 5,
    max_cell_len: int = 40,
) -> List[Dict[str, object]]:
    if result_df is None or result_df.height == 0:
        return []

    n = result_df.height
    max_samples = max(1, int(max_samples))
    if n <= max_samples:
        indices = list(range(n))
    else:
        indices_set = {0, n - 1}
        for p in (0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99):
            idx = int(round(p * (n - 1)))
            indices_set.add(idx)
        target = min(max_samples, n)
        attempts = 0
        while len(indices_set) < target and attempts < target * 20:
            attempts += 1
            pick = random.random()
            u = random.random()
            if pick < 0.3:
                pos = u ** 2.5  # head (L-shaped)
            elif pick < 0.7:
                pos = min(1.0, max(0.0, random.gauss(0.5, 0.18)))  # middle (gaussian)
            else:
                pos = 1.0 - (u ** 2.5)  # tail (flipped L)
            idx = int(round(pos * (n - 1)))
            indices_set.add(idx)

        if len(indices_set) < target:
            for idx in _evenly_spaced_indices(n, target):
                indices_set.add(idx)
                if len(indices_set) >= target:
                    break

        indices = sorted(indices_set)

    rows_with_idx: List[Tuple[int, Tuple[object, ...]]] = []
    for idx in indices:
        try:
            row = result_df.row(idx)
        except Exception:
            continue
        rows_with_idx.append((idx, row))

    out: List[Dict[str, object]] = []
    total = len(rows_with_idx)
    for local_i, (idx, row) in enumerate(rows_with_idx):
        position = f"{local_i + 1}/{total} #{idx + 1}"
        out.append(
            {
                'position': position,
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
    return sample_result_rows(result_df, max_samples=max_samples, max_cell_len=max_cell_len)


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
                LOGGER.warning(f"Judge output JSON parse failed; preview='{preview}'")
                obj = None
            if isinstance(obj, dict):
                decision_raw = str(obj.get("decision", "")).strip().upper()
                decision: Optional[bool]
                if decision_raw in {"YES", "Y", "TRUE", "STOP", "DONE", "ACCEPT", "PASS"}:
                    decision = True
                elif decision_raw in {"NO", "N", "FALSE", "CONTINUE", "RETRY", "REVISE", "FAIL"}:
                    decision = False
                else:
                    decision = None
                try:
                    score = float(obj.get("score"))
                except Exception:
                    score = None
                if score is not None:
                    if 0.0 <= score <= 1.0:
                        pass
                    elif 1.0 < score <= 5.0:
                        score = score / 5.0
                    elif 5.0 < score <= 10.0:
                        score = score / 10.0
                    else:
                        score = None
                if decision is None or score is None:
                    preview = cleaned.replace("\n", " ")[:200]
                    LOGGER.warning(f"Judge JSON missing/invalid fields; preview='{preview}'")
                    return None, None
                return decision, score

    preview = cleaned.replace("\n", " ")[:200]
    LOGGER.warning(f"Judge output missing JSON object; preview='{preview}'")
    return None, None


def parse_up_output(text: str) -> Optional[str]:
    """
    Preferred UP output (JSON):
      {"up": "...", "targets": "...", "output_columns": [...], "filters": [...], "ranking": {...}}
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return None
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
            LOGGER.warning(f"Prompt-writer JSON parse failed; preview='{preview}'")
            return None
        if isinstance(obj, dict):
            up = obj.get("up")
            if up is None:
                up = obj.get("prompt") or obj.get("user_prompt") or obj.get("up_text")
            if isinstance(up, str) and up.strip():
                return up.strip()
    preview = cleaned.replace("\n", " ")[:200]
    LOGGER.warning(f"Prompt-writer output missing JSON object; preview='{preview}'")
    return None


def parse_sql_output(text: str) -> Optional[str]:
    """
    Preferred SQL output (JSON):
      {"sql": "SELECT ..."}
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return None
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
            LOGGER.warning(f"SQL-writer JSON parse failed; preview='{preview}'")
            return None
        if isinstance(obj, dict):
            sql = obj.get("sql")
            if sql is None:
                sql = obj.get("query") or obj.get("sql_text")
            if isinstance(sql, str) and sql.strip():
                return sql.strip()
    preview = cleaned.replace("\n", " ")[:200]
    LOGGER.warning(f"SQL-writer output missing JSON object; preview='{preview}'")
    return None


def _response_format_schema(name: str, schema: Dict[str, object]) -> Dict[str, object]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": name,
            "schema": schema,
            "strict": True,
        },
    }


def response_format_up() -> Dict[str, object]:
    schema = {
        "type": "object",
        "properties": {
            "up": {"type": "string"},
        },
        "required": ["up"],
        "additionalProperties": True,
    }
    return _response_format_schema("up_output", schema)


def response_format_sql() -> Dict[str, object]:
    schema = {
        "type": "object",
        "properties": {
            "sql": {"type": "string"},
        },
        "required": ["sql"],
        "additionalProperties": True,
    }
    return _response_format_schema("sql_output", schema)


def response_format_judge() -> Dict[str, object]:
    schema = {
        "type": "object",
        "properties": {
            "analysis": {"type": "string"},
            "score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "decision": {"type": "string", "enum": ["YES", "NO"]},
        },
        "required": ["analysis", "score", "decision"],
        "additionalProperties": True,
    }
    return _response_format_schema("judge_output", schema)


@dataclass(frozen=True, slots=True)
class Iteration:
    n: int
    up: str
    sql: str
    sql_model: Optional[str]
    plan_summary: str
    res_row_count: int
    res_columns: Tuple[str, ...]
    res_samples: Tuple[Tuple[str, Tuple[str, ...]], ...]  # (position, tuple(data_str))
    res_error: Optional[str]
    judge_text: str
    judge_model: Optional[str]
    judge_score: Optional[float]
    judge_decision: Optional[bool]


@dataclass(frozen=True, slots=True)
class EndpointSpec:
    role: str
    provider: str
    model: Optional[str]
    base_url: Optional[str]
    temperature: float
    timeout: int
    label: str


@dataclass(frozen=True, slots=True)
class SqlCandidate:
    sql: str
    model: Optional[str]
    provider: str
    base_url: Optional[str]
    label: str
    sql_index: int


@dataclass(frozen=True, slots=True)
class JudgeResult:
    decision: Optional[bool]
    score: Optional[float]
    text: str
    judge_model: Optional[str]
    judge_provider: str
    label: str


class ChEMBLLLMQuery:
    @staticmethod
    def _runtime_provider_label(provider_obj: DspyProvider) -> str:
        return DspyProvider._runtime_provider_label(provider_obj)

    def __init__(
        self,
        db_path: str = 'database/latest/chembl_36/chembl_36_sqlite/chembl_36.db',
        provider: str = 'auto',
        up_provider: Optional[str] = None,
        up_model: Optional[str] = None,
        up_base_url: Optional[str] = None,
        sql_model: Optional[str] = None,
        sql_model_list: Optional[str] = None,
        sql_model_cycle: str = 'cicada',
        judge_model: Optional[str] = None,
        judge_model_list: Optional[str] = 'expensive',
        judge_model_cycle: Optional[str] = None,
        judge_provider: Optional[str] = None,
        judge_base_url: Optional[str] = None,
        sql_samplers: Optional[Sequence[str]] = None,
        judge_samplers: Optional[Sequence[str]] = None,
        sql_parallelism: Optional[int] = None,
        judge_parallelism: Optional[int] = None,
        provider_base_url: Optional[str] = None,
        verbose: int | bool = False,
        max_retries: int = 20,
        timeout: int = 600,
        writer_timeout: int = 1800,
        judge_timeout: int = 900,
        history_window_up_sql: Optional[int] = None,
        judge_history_window: int = 1,
        judge_score_threshold: float = 0.5,
        judge_yes_score_threshold: Optional[float] = None,
        judge_no_override_threshold: float = 0.99,
        judge_call_retries: int = 3,
        up_max_tokens: int = 4096,
        sql_max_tokens: int = 4096,
        judge_max_tokens: int = 4096,
        schema_docs_path: str = 'doc/chembl_database_schema.md',
        schema_sample_rows: int = 3,
        schema_max_cell_len: int = 40,
        prompt_pack_path: str = DEFAULT_PROMPT_PACK_PATH,
        prompt_hints_path: Optional[str] = None,
        min_context: int = 100000,
        save_intermediate: bool = True,
        intermediate_dir: str = 'logs/intermediate',
        output_base: str = 'query_results',
        run_id: Optional[str] = None,
        filter_profile: str = 'none',
        strip_unrequested_limit: bool = True,
        judge_context_limit: Optional[int] = None,
        sql_temperature: float = 1.0,
        prompt_writer_temperature: float = 1.0,
        judge_temperature: float = 0.5,
        up_temperature: Optional[float] = None,
        up_timeout: Optional[int] = None,
        provider_sleep: float = 0.0,
        provider_retry_backoff: float = 0.0,
        local_enable_thinking: bool = True,
        local_reasoning_budget_tokens: Optional[int] = None,
        local_reasoning_budget_message: Optional[str] = None,
        memory_json_path: Optional[str] = 'MEMORY-ChEMBLdb-query.jsonl',
        quota_fallback_provider: Optional[str] = None,
        quota_fallback_base_url: Optional[str] = None,
        quota_fallback_model: Optional[str] = None,
        quota_fallback_provider_2: Optional[str] = None,
        quota_fallback_base_url_2: Optional[str] = None,
        quota_fallback_model_2: Optional[str] = None,
        case_context: Optional[Dict[str, object]] = None,
    ):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = None
        self.case_context = dict(case_context or {})

        load_dotenv_once()
        if not provider:
            provider = "auto"
        if provider == "auto":
            provider = resolve_auto_provider(sql_model or judge_model)
        if judge_provider is None:
            judge_provider = provider
        if up_provider is None:
            up_provider = judge_provider
        if judge_provider == "auto":
            judge_provider = resolve_auto_provider(judge_model or sql_model)
        if up_provider == "auto":
            up_provider = resolve_auto_provider(up_model or judge_model or sql_model)

        if isinstance(verbose, bool):
            self.verbosity = 1 if verbose else 0
        else:
            self.verbosity = int(verbose)
        self.verbose = self.verbosity >= 1

        self.max_retries = int(max_retries)
        self.timeout = int(timeout)
        self.writer_timeout = int(writer_timeout)
        self.judge_timeout = int(judge_timeout)
        self.history_window_up_sql = None if history_window_up_sql is None else int(history_window_up_sql)
        self.judge_history_window = max(1, int(judge_history_window))
        self.judge_yes_score_threshold = float(
            judge_score_threshold if judge_yes_score_threshold is None else judge_yes_score_threshold
        )
        # Backward-compatible alias used by older prompt packs and logs.
        self.judge_score_threshold = self.judge_yes_score_threshold
        self.judge_no_override_threshold = float(judge_no_override_threshold)
        self.judge_call_retries = int(judge_call_retries)
        self.up_max_tokens = int(up_max_tokens)
        self.sql_max_tokens = int(sql_max_tokens)
        self.judge_max_tokens = int(judge_max_tokens)
        self.schema_docs_path = schema_docs_path
        self.schema_sample_rows = int(schema_sample_rows)
        self.schema_max_cell_len = int(schema_max_cell_len)
        self.prompt_pack_path = prompt_pack_path
        self.prompt_pack = _load_prompt_pack(prompt_pack_path)
        effective_prompt_hints_path = prompt_hints_path or self.prompt_pack.get("prompt_hints_path")
        self.prompt_hints_path = _resolve_relative_to_prompt_pack(prompt_pack_path, effective_prompt_hints_path)
        self.min_context = int(min_context)
        self.save_intermediate = bool(save_intermediate)
        self.intermediate_dir = intermediate_dir
        self.output_base = output_base
        self.run_id = run_id
        self.latest_iterations: List[Iteration] = []
        self.latest_sql: Optional[str] = None
        self.latest_up: Optional[str] = None
        self.latest_judge_decision: Optional[bool] = None
        self.latest_judge_score: Optional[float] = None
        self.latest_result_df: Optional[pl.DataFrame] = None
        self.latest_returned_iteration_n: Optional[int] = None
        self.latest_exhausted: bool = False
        self.filter_profile = (filter_profile or 'none').strip().lower()
        if self.filter_profile not in {'none', 'strict', 'relaxed'}:
            raise ValueError(
                f"Invalid filter_profile={filter_profile!r}; expected 'none', 'strict' or 'relaxed'"
            )
        self.strip_unrequested_limit = bool(strip_unrequested_limit)
        if judge_context_limit is None:
            self.judge_context_limit = DEFAULT_JUDGE_CONTEXT_LIMITS.get(provider)
        else:
            self.judge_context_limit = int(judge_context_limit)
        self.sql_temperature = float(sql_temperature)
        self.prompt_writer_temperature = float(prompt_writer_temperature)
        self.judge_temperature = float(judge_temperature)
        self.up_temperature = float(up_temperature) if up_temperature is not None else self.prompt_writer_temperature
        self.up_timeout = int(up_timeout) if up_timeout is not None else self.writer_timeout
        self.provider_sleep = max(0.0, float(provider_sleep))
        self.provider_retry_backoff = max(0.0, float(provider_retry_backoff))
        self.local_enable_thinking = bool(local_enable_thinking)
        self.local_reasoning_budget_tokens = (
            None if local_reasoning_budget_tokens is None else int(local_reasoning_budget_tokens)
        )
        self.local_reasoning_budget_message = local_reasoning_budget_message
        self.memory_json_path = memory_json_path.strip() if isinstance(memory_json_path, str) else None
        self.shared_quota_fallback_state: Optional[SharedQuotaFallbackState] = None
        if quota_fallback_provider:
            fallback_chain = [
                FallbackEndpointConfig(
                    provider=quota_fallback_provider,
                    model=quota_fallback_model,
                    base_url=quota_fallback_base_url,
                )
            ]
            if quota_fallback_provider_2:
                fallback_chain.append(
                    FallbackEndpointConfig(
                        provider=quota_fallback_provider_2,
                        model=quota_fallback_model_2,
                        base_url=quota_fallback_base_url_2,
                    )
                )
            prepared_fallback_chain = _prepare_shared_fallback_chain(fallback_chain)
            if prepared_fallback_chain:
                shared_primary_config: Optional[FallbackEndpointConfig] = None
                judge_primary_base_url = judge_base_url or provider_base_url
                up_primary_base_url = up_base_url or judge_primary_base_url or provider_base_url
                primary_models = {sql_model, judge_model, up_model}
                primary_providers = {provider, judge_provider, up_provider}
                primary_base_urls = {provider_base_url, judge_primary_base_url, up_primary_base_url}
                if len(primary_models) == 1 and len(primary_providers) == 1 and len(primary_base_urls) == 1:
                    shared_primary_config = FallbackEndpointConfig(
                        provider=provider,
                        model=sql_model,
                        base_url=provider_base_url,
                    )
                self.shared_quota_fallback_state = SharedQuotaFallbackState(
                    prepared_fallback_chain,
                    primary_config=shared_primary_config,
                    refresh_callback=_build_shared_fallback_refresh_callback(fallback_chain),
                    refresh_interval_seconds=SHARED_FALLBACK_RETRY_SECONDS,
                    quota_retry_seconds=(
                        SHARED_FALLBACK_RETRY_SECONDS if shared_primary_config is not None else None
                    ),
                )
                LOGGER.info(
                    "Shared fallback configured: primary=%s/%s at %s; fallbacks=%s; primary_retry_seconds=%s; refresh_interval_seconds=%s",
                    shared_primary_config.provider if shared_primary_config else None,
                    shared_primary_config.model if shared_primary_config else None,
                    shared_primary_config.base_url if shared_primary_config else None,
                    [
                        (item.provider, item.model, item.base_url)
                        for item in prepared_fallback_chain
                    ],
                    SHARED_FALLBACK_RETRY_SECONDS if shared_primary_config is not None else None,
                    SHARED_FALLBACK_RETRY_SECONDS,
                )
            else:
                LOGGER.warning(
                    "No reachable fallback endpoints remain for primary %s/%s.",
                    provider,
                    sql_model,
                )
        self._last_provider_call_ts: Optional[float] = None
        self.openrouter_context_map: Dict[str, int] = {}
        if provider == 'openrouter':
            try:
                self.openrouter_context_map = get_openrouter_context_map()
            except Exception:
                LOGGER.warning("Failed to fetch OpenRouter model context map.", exc_info=True)

        self.base_provider = provider
        self.provider_base_url = provider_base_url
        self.up_provider_name = up_provider
        self.up_base_url = up_base_url
        self.judge_provider_name = judge_provider
        self.judge_base_url = judge_base_url
        self.sql_samplers_raw = list(sql_samplers) if sql_samplers else []
        self.judge_samplers_raw = list(judge_samplers) if judge_samplers else []
        self.sql_parallelism = sql_parallelism
        self.judge_parallelism = judge_parallelism

        # SQL models
        self.sql_model_list: Optional[List[str]] = None
        if sql_model:
            if sql_model_list:
                LOGGER.info(
                    "SQL model list (%s) ignored because --sql-model was provided: %s",
                    sql_model_list,
                    sql_model,
                )
        elif sql_model_list:
            base_list = get_model_list(sql_model_list, provider)
            if provider == 'openrouter':
                if self.openrouter_context_map:
                    base_list = [m for m in base_list if self.openrouter_context_map.get(m, 0) >= self.min_context]
                else:
                    base_list = filter_openrouter_models_by_context(base_list, self.min_context)
                if self.min_context > 0 and not base_list:
                    raise RuntimeError("No SQL models meet the minimum context requirement.")
            self.sql_model_list = base_list
            if self.sql_model_list:
                sql_model = self.sql_model_list[0]
                LOGGER.info(f"Using default SQL model from {sql_model_list} list: {sql_model}")
            if self.sql_model_list is not None:
                LOGGER.info("SQL model list (%s): %s", len(self.sql_model_list), self.sql_model_list)
        self.sql_model = sql_model
        self.sql_model_cycle = sql_model_cycle

        # Judge models (also used for prompt-writer)
        if judge_model_cycle is None:
            judge_model_cycle = sql_model_cycle
        self.judge_model_cycle = judge_model_cycle

        self.judge_model_list: Optional[List[str]] = None
        if judge_model:
            if judge_model_list:
                LOGGER.info(
                    "Judge model list (%s) ignored because --judge-model was provided: %s",
                    judge_model_list,
                    judge_model,
                )
        elif judge_model_list:
            base_list = get_model_list(judge_model_list, provider)
            if provider == 'openrouter':
                if self.openrouter_context_map:
                    base_list = [m for m in base_list if self.openrouter_context_map.get(m, 0) >= self.min_context]
                else:
                    base_list = filter_openrouter_models_by_context(base_list, self.min_context)
                if self.min_context > 0 and not base_list:
                    raise RuntimeError("No judge models meet the minimum context requirement.")
            self.judge_model_list = base_list
            if self.judge_model_list:
                judge_model = self.judge_model_list[0]
                LOGGER.info(f"Using default judge model from {judge_model_list} list: {judge_model}")
            if self.judge_model_list is not None:
                LOGGER.info("Judge model list (%s): %s", len(self.judge_model_list), self.judge_model_list)
        self.judge_model = judge_model
        if up_model is None:
            up_model = self.judge_model

        # Load schema docs with table samples.
        with log_stage("SP"):
            schema_path = Path(self.schema_docs_path)
            db_file = Path(self.db_path)
            should_regenerate = False

            if not db_file.exists():
                if schema_path.exists():
                    LOGGER.warning("DB file missing; using existing schema docs at %s", schema_path)
                    self.schema_docs = schema_path.read_text()
                else:
                    raise FileNotFoundError(f"ChEMBL SQLite DB not found: {self.db_path}")
            else:
                should_regenerate = not schema_path.exists()
                try:
                    if schema_path.exists():
                        should_regenerate = schema_path.stat().st_mtime < db_file.stat().st_mtime
                except Exception:
                    LOGGER.warning("Could not compare schema docs mtime to DB mtime", exc_info=True)

                if should_regenerate:
                    LOGGER.warning("Schema docs missing or stale; generating...")
                    self.schema_docs = generate_schema_docs_sqlite(
                        db_path=self.db_path,
                        output_path=str(schema_path),
                        sample_rows=self.schema_sample_rows,
                        max_cell_len=self.schema_max_cell_len,
                    )
                else:
                    self.schema_docs = schema_path.read_text()

            prompt_hints_path = Path(self.prompt_hints_path) if self.prompt_hints_path else None
            if prompt_hints_path is not None and prompt_hints_path.exists():
                self.prompt_hints = prompt_hints_path.read_text()
            else:
                self.prompt_hints = ""

            self.system_prompt = self._build_system_prompt()
            sp_hash = hashlib.sha256(self.system_prompt.encode("utf-8")).hexdigest()
            self.system_prompt_hash = sp_hash
            if self.case_context:
                LOGGER.info("CASE_CONTEXT:")
                for key in sorted(self.case_context):
                    LOGGER.info("  %s: %s", key, self.case_context[key])
            LOGGER.info("SP_SHA256: %s", sp_hash)
            LOGGER.info("SP_FULL:")
            self.LOG_BLOCK(self.system_prompt)

        # Providers (DSPy)
        LOGGER.info("Initializing SQL provider (DSPy)...")
        sql_provider_kwargs: Dict[str, object] = {}
        if self.provider_base_url:
            sql_provider_kwargs["base_url"] = self.provider_base_url
        self.sql_provider = create_dspy_provider(
            provider=provider,
            model=self.sql_model,
            verbose=self.verbose,
            temperature=self.sql_temperature,
            timeout=self.writer_timeout,
            local_enable_thinking=self.local_enable_thinking,
            local_reasoning_budget_tokens=self.local_reasoning_budget_tokens,
            local_reasoning_budget_message=self.local_reasoning_budget_message,
            shared_quota_fallback_state=self.shared_quota_fallback_state,
            **sql_provider_kwargs,
        )
        self.current_sql_model = self.sql_model

        judge_base_url = self.judge_base_url or self.provider_base_url
        LOGGER.info("Initializing judge provider (DSPy)...")
        judge_provider_kwargs: Dict[str, object] = {}
        if judge_base_url:
            judge_provider_kwargs["base_url"] = judge_base_url
        self.judge_provider = create_dspy_provider(
            provider=self.judge_provider_name,
            model=self.judge_model,
            verbose=self.verbose,
            temperature=self.judge_temperature,
            timeout=self.judge_timeout,
            local_enable_thinking=self.local_enable_thinking,
            local_reasoning_budget_tokens=self.local_reasoning_budget_tokens,
            local_reasoning_budget_message=self.local_reasoning_budget_message,
            shared_quota_fallback_state=self.shared_quota_fallback_state,
            **judge_provider_kwargs,
        )
        self.current_judge_model = self.judge_model

        up_base_url = self.up_base_url or judge_base_url or self.provider_base_url
        LOGGER.info("Initializing UP provider (DSPy)...")
        up_provider_kwargs: Dict[str, object] = {}
        if up_base_url:
            up_provider_kwargs["base_url"] = up_base_url
        self.up_provider = create_dspy_provider(
            provider=self.up_provider_name,
            model=up_model,
            verbose=self.verbose,
            temperature=self.up_temperature,
            timeout=self.up_timeout,
            local_enable_thinking=self.local_enable_thinking,
            local_reasoning_budget_tokens=self.local_reasoning_budget_tokens,
            local_reasoning_budget_message=self.local_reasoning_budget_message,
            shared_quota_fallback_state=self.shared_quota_fallback_state,
            **up_provider_kwargs,
        )
        self.up_model = up_model

        self.sql_model_schedule: List[str] = []
        if self.sql_model_list and len(self.sql_model_list) > 1:
            self.sql_model_schedule = generate_model_schedule(self.max_retries, self.sql_model_list, self.sql_model_cycle)
            LOGGER.info(f"SQL model schedule (method: {self.sql_model_cycle}, {len(self.sql_model_schedule)} retries):")
            for i, m in enumerate(self.sql_model_schedule[:10]):
                LOGGER.info(f"  Retry {i+1}: {m}")
            if len(self.sql_model_schedule) > 10:
                LOGGER.info(f"  ... and {len(self.sql_model_schedule)-10} more")
        elif self.sql_model:
            LOGGER.info("SQL model fixed: %s", self.sql_model)

        self.judge_model_schedule: List[str] = []
        if self.judge_model_list and len(self.judge_model_list) > 1:
            self.judge_model_schedule = generate_model_schedule(self.max_retries, self.judge_model_list, self.judge_model_cycle)
            LOGGER.info(f"Judge model schedule (method: {self.judge_model_cycle}, {len(self.judge_model_schedule)} retries):")
            for i, m in enumerate(self.judge_model_schedule[:10]):
                LOGGER.info(f"  Retry {i+1}: {m}")
            if len(self.judge_model_schedule) > 10:
                LOGGER.info(f"  ... and {len(self.judge_model_schedule)-10} more")
        elif self.judge_model:
            LOGGER.info("Judge model fixed: %s", self.judge_model)

        self.sql_sampler_specs: List[EndpointSpec] = []
        self.sql_sampler_providers: List[Tuple[EndpointSpec, DspyProvider]] = []
        if self.sql_samplers_raw:
            for raw in self.sql_samplers_raw:
                spec = _parse_endpoint_spec(
                    raw,
                    role="sql",
                    default_provider=self.base_provider,
                    default_model=self.sql_model,
                    default_base_url=self.provider_base_url,
                    default_temperature=self.sql_temperature,
                    default_timeout=self.writer_timeout,
                )
                provider_obj = create_dspy_provider(
                    provider=spec.provider,
                    model=spec.model,
                    verbose=self.verbose,
                    temperature=spec.temperature,
                    timeout=spec.timeout,
                    base_url=spec.base_url,
                    local_enable_thinking=self.local_enable_thinking,
                    local_reasoning_budget_tokens=self.local_reasoning_budget_tokens,
                    local_reasoning_budget_message=self.local_reasoning_budget_message,
                    shared_quota_fallback_state=self.shared_quota_fallback_state,
                )
                self.sql_sampler_specs.append(spec)
                self.sql_sampler_providers.append((spec, provider_obj))
            LOGGER.info("SQL samplers: %s", [spec.label for spec in self.sql_sampler_specs])
        self.sql_sampler_label_map = {
            spec.label: idx + 1 for idx, spec in enumerate(self.sql_sampler_specs)
        }

        self.judge_sampler_specs: List[EndpointSpec] = []
        self.judge_sampler_providers: List[Tuple[EndpointSpec, DspyProvider]] = []
        if self.judge_samplers_raw:
            for raw in self.judge_samplers_raw:
                spec = _parse_endpoint_spec(
                    raw,
                    role="judge",
                    default_provider=self.judge_provider_name,
                    default_model=self.judge_model,
                    default_base_url=judge_base_url,
                    default_temperature=self.judge_temperature,
                    default_timeout=self.judge_timeout,
                )
                provider_obj = create_dspy_provider(
                    provider=spec.provider,
                    model=spec.model,
                    verbose=self.verbose,
                    temperature=spec.temperature,
                    timeout=spec.timeout,
                    base_url=spec.base_url,
                    local_enable_thinking=self.local_enable_thinking,
                    local_reasoning_budget_tokens=self.local_reasoning_budget_tokens,
                    local_reasoning_budget_message=self.local_reasoning_budget_message,
                    shared_quota_fallback_state=self.shared_quota_fallback_state,
                )
                self.judge_sampler_specs.append(spec)
                self.judge_sampler_providers.append((spec, provider_obj))
            LOGGER.info("Judge samplers: %s", [spec.label for spec in self.judge_sampler_specs])
        self.judge_sampler_label_map = {
            spec.label: idx + 1 for idx, spec in enumerate(self.judge_sampler_specs)
        }
        if self.judge_sampler_specs and self.judge_parallelism is None:
            self.judge_parallelism = 1

        # Effective model usage summary
        if self.sql_sampler_specs:
            LOGGER.info("SQL model schedule ignored (SQL samplers configured).")
        if self.judge_sampler_specs:
            LOGGER.info("Judge model schedule ignored (judge samplers configured).")
        if self.sql_sampler_specs:
            sql_map = [f"C{idx + 1}={spec.label}" for idx, spec in enumerate(self.sql_sampler_specs)]
            LOGGER.info("SQL endpoint map: %s", sql_map)
        if self.judge_sampler_specs:
            judge_map = [f"J{idx + 1}={spec.label}" for idx, spec in enumerate(self.judge_sampler_specs)]
            LOGGER.info("Judge endpoint map: %s", judge_map)
        LOGGER.info(
            "Effective UP model: provider=%s model=%s base_url=%s",
            self.up_provider_name,
            self.up_model,
            self.up_base_url or self.provider_base_url or self.judge_base_url,
        )
        if self.sql_sampler_specs:
            LOGGER.info("Effective SQL models: %s", [spec.label for spec in self.sql_sampler_specs])
        elif self.sql_model_schedule:
            LOGGER.info("Effective SQL schedule: %s", self.sql_model_schedule[:10])
        else:
            LOGGER.info("Effective SQL model: %s", self.sql_model)
        if self.judge_sampler_specs:
            LOGGER.info("Effective judge models: %s", [spec.label for spec in self.judge_sampler_specs])
        elif self.judge_model_schedule:
            LOGGER.info("Effective judge schedule: %s", self.judge_model_schedule[:10])
        else:
            LOGGER.info("Effective judge model: %s", self.judge_model)

    def _vprint(self, level: int, *args: object) -> None:
        if self.verbosity >= level:
            message = " ".join(str(a) for a in args)
            log_level = logging.DEBUG if level >= 2 else logging.INFO
            _log_lines(log_level, message)

    def LOG(self, level: int, *args: object) -> None:
        self._vprint(level, *args)

    def _emit_raw_block(self, text: str) -> None:
        if text is None:
            return
        sanitized = _sanitize_text(text)
        if not sanitized.endswith("\n"):
            sanitized += "\n"
        root = logging.getLogger()
        stream = None
        for handler in root.handlers:
            stream = getattr(handler, "stream", None)
            if stream is not None:
                break
        if stream is None:
            stream = sys.stderr
        try:
            stream.write(sanitized)
            stream.flush()
        except Exception:
            sys.stderr.write(sanitized)
            sys.stderr.flush()

    def LOG_BLOCK(self, text: str) -> None:
        self._emit_raw_block(text)

    def _throttle_before_call(self, *, stage: str) -> None:
        now = time.time()
        if self._last_provider_call_ts is not None and self.provider_sleep > 0:
            elapsed = now - self._last_provider_call_ts
            if elapsed < self.provider_sleep:
                delay = self.provider_sleep - elapsed
                LOGGER.info("Throttling %s call: sleeping %.2fs", stage, delay)
                time.sleep(delay)
                now = time.time()
        self._last_provider_call_ts = now

    def _set_provider_timeout(self, provider: object, timeout: int) -> None:
        if provider is None:
            return
        if hasattr(provider, "timeout"):
            try:
                setattr(provider, "timeout", int(timeout))
            except Exception:
                LOGGER.warning("Failed to set provider timeout to %s", timeout, exc_info=True)

    def _backoff_after_failure(self, *, stage: str, retry_idx: int) -> None:
        if self.provider_retry_backoff <= 0:
            return
        delay = self.provider_retry_backoff * (2 ** max(0, int(retry_idx)))
        if delay <= 0:
            return
        LOGGER.info("Backoff after %s failure: sleeping %.2fs", stage, delay)
        time.sleep(delay)

    def _build_system_prompt(self) -> str:
        prompt_hints_block = ""
        if self.prompt_hints.strip():
            prompt_hints_block = f"""\n<PROMPT_HINTS>\n{self.prompt_hints}\n</PROMPT_HINTS>\n"""
        about_block = self.prompt_pack.get("about_block", DEFAULT_PROMPT_PACK["about_block"])
        examples_block = self.prompt_pack.get("examples_block", DEFAULT_PROMPT_PACK["examples_block"])
        return f"""<SP>
<ABOUT>
{about_block}
</ABOUT>

<DATABASE_SCHEMA_DOCS>
{self.schema_docs}
</DATABASE_SCHEMA_DOCS>
{prompt_hints_block}{examples_block}</SP>"""

    def _ensure_sql_provider_for_attempt(self, attempt_idx: int) -> None:
        if attempt_idx < len(self.sql_model_schedule):
            model = self.sql_model_schedule[attempt_idx]
            if model != self.current_sql_model:
                sql_provider_kwargs: Dict[str, object] = {}
                if self.provider_base_url:
                    sql_provider_kwargs["base_url"] = self.provider_base_url
                self.sql_provider = create_dspy_provider(
                    provider=self.base_provider,
                    model=model,
                    verbose=self.verbose,
                    temperature=self.sql_temperature,
                    timeout=self.writer_timeout,
                    shared_quota_fallback_state=self.shared_quota_fallback_state,
                    **sql_provider_kwargs,
                )
                self.current_sql_model = model

    def _ensure_judge_provider_for_attempt_with_offset(self, *, attempt_idx: int, offset: int) -> None:
        if self.judge_model_schedule:
            idx = (attempt_idx + offset) % len(self.judge_model_schedule)
            model = self.judge_model_schedule[idx]
        else:
            model = self.judge_model

        if model != self.current_judge_model:
            judge_provider_kwargs: Dict[str, object] = {}
            if self.judge_base_url or self.provider_base_url:
                judge_provider_kwargs["base_url"] = self.judge_base_url or self.provider_base_url
            self.judge_provider = create_dspy_provider(
                provider=self.judge_provider_name,
                model=model,
                verbose=self.verbose,
                temperature=self.judge_temperature,
                timeout=self.judge_timeout,
                shared_quota_fallback_state=self.shared_quota_fallback_state,
                **judge_provider_kwargs,
            )
            self.current_judge_model = model

    def execute_query_with_timeout(self, sql: str) -> Tuple[bool, Optional[pl.DataFrame], Optional[str]]:
        try:
            LOGGER.info(f"Executing query (timeout: {self.timeout}s)...")
            start_time = time.time()
            timed_out = False

            if _contains_sql_bind_parameters(sql):
                msg = "Query contains unsupported bind parameters/placeholders; generate fully executable SQLite with literal values."
                LOGGER.error("Query failed: %s", msg)
                return False, None, msg

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
            df = self._rows_to_dataframe(rows, cols)

            elapsed = time.time() - start_time
            LOGGER.info(f"Query completed in {elapsed:.2f}s")
            return True, df, None
        except Exception as e:
            msg = str(e)
            if "interrupted" in msg.lower():
                msg = f"Query timed out after {self.timeout}s"
            LOGGER.error(f"Query failed: {msg}", exc_info=True)
            return False, None, msg
        finally:
            self.conn.set_progress_handler(None, 0)

    @staticmethod
    def _rows_to_dataframe(rows: List[tuple], cols: List[str]) -> pl.DataFrame:
        if not cols:
            return pl.DataFrame()

        # Polars row-construction can fail on duplicate column names even when
        # the SQLite query itself executed correctly. Keep the rows, but make
        # duplicate names explicit so downstream evaluation can score the schema
        # mismatch instead of losing the entire result table.
        col_counts: Dict[str, int] = {}
        unique_cols: List[str] = []
        for col in cols:
            count = col_counts.get(col, 0) + 1
            col_counts[col] = count
            if count == 1:
                unique_cols.append(col)
            else:
                unique_cols.append(f"{col}__dup{count}")

        observed_types: List[set[str]] = [set() for _ in cols]
        for row in rows:
            for idx, value in enumerate(row):
                if value is None:
                    continue
                if isinstance(value, bool):
                    observed_types[idx].add("bool")
                elif isinstance(value, int):
                    observed_types[idx].add("int")
                elif isinstance(value, float):
                    observed_types[idx].add("float")
                elif isinstance(value, (bytes, bytearray, memoryview)):
                    observed_types[idx].add("binary")
                elif isinstance(value, str):
                    observed_types[idx].add("string")
                else:
                    observed_types[idx].add("other")

        schema: List[tuple[str, pl.DataType]] = []
        for col, types_seen in zip(unique_cols, observed_types):
            if not types_seen:
                dtype = pl.String
            elif types_seen <= {"bool"}:
                dtype = pl.Boolean
            elif types_seen <= {"int"}:
                dtype = pl.Int64
            elif types_seen <= {"int", "float"}:
                dtype = pl.Float64 if "float" in types_seen else pl.Int64
            elif types_seen <= {"string"}:
                dtype = pl.String
            elif types_seen <= {"binary"}:
                dtype = pl.Binary
            else:
                dtype = pl.String
            schema.append((col, dtype))

        return pl.DataFrame(rows, schema=schema, orient="row")

    def explain_query_plan(self, sql: str) -> Tuple[bool, str]:
        try:
            if _contains_sql_bind_parameters(sql):
                return False, "ERROR: Query contains unsupported bind parameters/placeholders; generate fully executable SQLite with literal values."
            plan_sql = f"EXPLAIN QUERY PLAN {sql.strip().rstrip(';')}"
            cur = self.conn.execute(plan_sql)
            rows = cur.fetchall()
            lines = ["OK", f"plan_rows: {len(rows)}"]
            for row in rows:
                lines.append(" | ".join(str(v) for v in row))
            return True, "\n".join(lines)
        except Exception as exc:
            msg = str(exc)
            LOGGER.error("EXPLAIN QUERY PLAN failed: %s", msg, exc_info=True)
            return False, f"ERROR: {msg}"

    def _iteration_to_block(
        self,
        it: Iteration,
        *,
        include_res: bool = True,
        include_plan: bool = True,
        include_judge: bool = True,
    ) -> str:
        samples_lines: List[str] = []
        for pos, data in it.res_samples:
            samples_lines.append(f"{pos}: {data}")

        blocks: List[str] = [
            f"<ITERATION {it.n}>",
            f"<UP_{it.n}>\n{it.up}\n</UP_{it.n}>",
            f"<SQL_{it.n}>\n{it.sql}\n</SQL_{it.n}>",
        ]
        if include_plan:
            blocks.append(f"<PLAN_{it.n}>\n{it.plan_summary}\n</PLAN_{it.n}>")
        if include_res:
            res_body: List[str] = []
            if it.res_error:
                res_body.append(f"ERROR: {it.res_error}")
                res_body.append(f"sqlite_error: {it.res_error}")
            res_body.append(f"n_rows: {it.res_row_count}")
            res_body.append(f"n_cols: {len(it.res_columns)}")
            res_body.append(f"colnames: {list(it.res_columns)}")
            res_body.append(f"row_count: {it.res_row_count}")
            res_body.append(f"columns: {list(it.res_columns)}")
            if samples_lines:
                res_body.append("samples:")
                res_body.extend(samples_lines)
            blocks.append(f"<RES_{it.n}>\n" + "\n".join(res_body) + f"\n</RES_{it.n}>")
        if include_judge:
            blocks.append(f"<J_{it.n}>\n{it.judge_text}\n</J_{it.n}>")
        blocks.append(f"</ITERATION {it.n}>")
        return "\n".join(blocks)

    def _history_blocks(
        self,
        iterations: List[Iteration],
        *,
        include_res: bool = True,
        include_plan: bool = True,
        include_judge: bool = True,
    ) -> str:
        if not iterations:
            return "<HISTORY/>\n"
        start_n = iterations[0].n
        end_n = iterations[-1].n
        blocks = "\n".join(
            self._iteration_to_block(
                it,
                include_res=include_res,
                include_plan=include_plan,
                include_judge=include_judge,
            )
            for it in iterations
        )
        return f"<HISTORY from=\"{start_n}\" to=\"{end_n}\">\n{blocks}\n</HISTORY>"

    def _slice_history(self, iterations: List[Iteration], window: Optional[int]) -> List[Iteration]:
        if window is None:
            return list(iterations)
        if window <= 0:
            return []
        return iterations[-window:]

    def _filter_profile_guidance(self) -> str:
        if self.filter_profile == 'none':
            return "\n".join(
                [
                    "- Do NOT require docs.doc_type or DOI unless explicitly requested; only use year filters.",
                    "- Do NOT filter on assays.confidence_score unless explicitly requested.",
                    "- Do NOT restrict target_type unless explicitly requested.",
                    "- Do NOT add extra filters unless explicitly requested (no unit restrictions, no relation restrictions).",
                ]
            )
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
            LOGGER.error(
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
            LOGGER.warning("Removed %s unrequested LIMIT clause(s) from SQL.", count)
        cleaned = re.sub(r"\s+;", ";", cleaned).strip()
        return cleaned

    def _build_messages_for_up(self, *, uq: str, iterations: List[Iteration], next_n: int) -> List[Dict[str, str]]:
        self._assert_system_prompt_unchanged()
        prev_judge = f"J_{next_n - 1}" if next_n > 1 else "N/A"
        task = self.prompt_pack.get("up_task_template", DEFAULT_PROMPT_PACK["up_task_template"]).format(
            next_n=next_n,
            prev_judge=prev_judge,
        )

        profile_guidance = self._filter_profile_guidance()
        user = "\n".join(
            [
                task,
                f"<UQ>\n{uq}\n</UQ>",
                f"<FILTER_PROFILE name=\"{self.filter_profile}\">\n{profile_guidance}\n</FILTER_PROFILE>" if profile_guidance else "",
                self._history_blocks(iterations, include_res=False),
            ]
        )
        return [{"role": "system", "content": self.system_prompt}, {"role": "user", "content": user}]

    def _build_messages_for_sql(self, *, uq: str, up: str, iterations: List[Iteration], n: int) -> List[Dict[str, str]]:
        self._assert_system_prompt_unchanged()
        task = self.prompt_pack.get("sql_task_template", DEFAULT_PROMPT_PACK["sql_task_template"]).format(
            n=n,
        )

        user = "\n".join(
            [
                task,
                f"<UQ>\n{uq}\n</UQ>",
                self._history_blocks(iterations, include_res=True),
                f"<UP_{n}>\n{up}\n</UP_{n}>",
            ]
        )
        return [{"role": "system", "content": self.system_prompt}, {"role": "user", "content": user}]

    def _build_messages_for_judge(
        self,
        *,
        uq: str,
        up: str,
        sql: str,
        plan_summary: str,
        res_summary: str,
        iterations: List[Iteration],
        n: int,
    ) -> List[Dict[str, str]]:
        self._assert_system_prompt_unchanged()
        task = self.prompt_pack.get("judge_task_template", DEFAULT_PROMPT_PACK["judge_task_template"]).format(
            n=n,
            judge_score_threshold=self.judge_score_threshold,
            judge_yes_score_threshold=self.judge_yes_score_threshold,
            judge_no_override_threshold=self.judge_no_override_threshold,
        )

        user = self._build_judge_user_content(
            task=task,
            uq=uq,
            up=up,
            sql=sql,
            plan_summary=plan_summary,
            res_summary=res_summary,
            iterations=iterations,
            n=n,
        )
        return [{"role": "system", "content": self.system_prompt}, {"role": "user", "content": user}]

    def _apply_judge_score_policy(
        self,
        *,
        decision: bool,
        score: float,
        text: str,
        model_label: str,
    ) -> Tuple[Optional[bool], str]:
        if decision is True:
            if score < self.judge_yes_score_threshold:
                LOGGER.warning(
                    "Judge said YES but score %.3f < YES threshold %.3f (%s); retrying",
                    score,
                    self.judge_yes_score_threshold,
                    model_label,
                )
                return None, text
            return True, text

        if score > self.judge_no_override_threshold:
            LOGGER.warning(
                "Judge said NO but score %.3f > NO override threshold %.3f (%s); treating as effective YES",
                score,
                self.judge_no_override_threshold,
                model_label,
            )
            return True, text
        return False, text

    def _build_judge_user_content(
        self,
        *,
        task: str,
        uq: str,
        up: str,
        sql: str,
        plan_summary: str,
        res_summary: str,
        iterations: List[Iteration],
        n: int,
    ) -> str:
        return "\n".join(
            [
                task,
                f"<UQ>\n{uq}\n</UQ>",
                self._history_blocks(iterations),
                f"<UP_{n}>\n{up}\n</UP_{n}>",
                f"<SQL_{n}>\n{sql}\n</SQL_{n}>",
                f"<PLAN_{n}>\n{plan_summary}\n</PLAN_{n}>",
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
    ) -> Tuple[int, Tuple[str, ...], Tuple[Tuple[str, Tuple[str, ...]], ...], str]:
        row_count = int(df.height) if df is not None else 0
        cols = tuple(df.columns) if df is not None else tuple()
        max_samples = int(sample_rows) if sample_rows is not None else 9
        lines: List[str] = []
        full_chars = self._estimate_full_result_chars(df) if df is not None else 0

        if error:
            lines.append(f"ERROR: {error}")
            lines.append(f"sqlite_error: {error}")
        elif df is None:
            lines.append("ERROR: no result")

        lines.append(f"n_rows: {row_count}")
        lines.append(f"n_cols: {len(cols)}")
        lines.append(f"colnames: {list(cols)}")
        lines.append(f"full_response: {row_count} rows : {full_chars} chars")

        if error or df is None:
            lines.append(f"row_count: {row_count}")
            lines.append(f"columns: {list(cols)}")
            return row_count, cols, tuple(), "\n".join(lines)
        samples = sample_result_rows(df, max_samples=max_samples, max_cell_len=sample_cell_len)
        samples_t = tuple((s["position"], tuple(str(x) for x in s["data"])) for s in samples)

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
            sample_rows_count = len(samples)
            sample_lines: List[str] = []
            if samples:
                for s in samples:
                    sample_lines.append(f"- {s['position']}: {s['data']}")
            sample_chars = sum(len(line) + 1 for line in sample_lines) if sample_lines else 0

            lines.append(f"sample_rows: {sample_rows_count}")
            lines.append(f"sample_response: {sample_rows_count} rows : {sample_chars} chars")
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
            lines.append(
                "sample_note: Sample rows selected probabilistically across head/middle/tail; "
                "first/last rows always included."
            )
            lines.append(
                "sample_note: Sample always includes rows near 1%, 5%, 25%, 50%, 75%, 95%, and 99% positions."
            )
            if sample_lines:
                lines.append("samples:")
                lines.extend(sample_lines)

        return row_count, cols, samples_t, "\n".join(lines)

    def _print_full_result_rows(self, *, df: Optional[pl.DataFrame], n: int, label: Optional[str] = None) -> None:
        if df is None:
            return
        self.LOG(2, "\n" + "=" * 20)
        label_suffix = f" ({label})" if label else ""
        self.LOG(2, f"RES_{n} FULL ROWS (CSV){label_suffix} [{df.height} rows x {df.width} cols]:")
        self.LOG(2, "=" * 20)
        try:
            buf = io.StringIO()
            df.write_csv(buf)
            csv_text = buf.getvalue().strip()
            if csv_text:
                self.LOG_BLOCK(csv_text)
        except BrokenPipeError:
            LOGGER.warning("Broken pipe while printing full result rows; continuing.")
        self.LOG(2, "=" * 20 + "\n")

    def _call_prompt_writer(self, *, uq: str, iterations: List[Iteration], next_n: int, attempt_idx: int) -> Optional[str]:
        if not self.up_provider.is_available():
            LOGGER.error("UP provider not available for prompt writing")
            return None

        messages = self._build_messages_for_up(uq=uq, iterations=iterations, next_n=next_n)
        if self.verbosity >= 2:
            user_prompt = messages[1]["content"] if len(messages) > 1 else ""
            LOGGER.debug("SP here; SHA256=%s", self.system_prompt_hash)
            self.LOG(2, "UP_USER_PROMPT:")
            self.LOG_BLOCK(user_prompt)

        last_text: Optional[str] = None
        rf = response_format_up()
        for offset in range(max(1, self.judge_call_retries)):
            self._set_provider_timeout(self.up_provider, self.up_timeout)
            self._throttle_before_call(stage="prompt-writer")
            text = self.up_provider.generate_text(
                messages,
                max_tokens=self.up_max_tokens,
                temperature=self.up_temperature,
                response_format=rf,
            )
            if text is None:
                LOGGER.warning("Prompt-writer call failed; retrying")
                self._backoff_after_failure(stage="prompt-writer", retry_idx=offset)
                continue
            last_text = text.strip()
            if not last_text:
                LOGGER.warning("Prompt-writer returned empty output; retrying")
                self._backoff_after_failure(stage="prompt-writer", retry_idx=offset)
                continue
            if self.verbosity >= 3:
                self.LOG(3, "UP_JSON_RAW:")
                self.LOG_BLOCK(last_text)
            up_text = parse_up_output(last_text)
            if up_text:
                return up_text
            LOGGER.warning("Prompt-writer output invalid JSON; retrying")
            self._backoff_after_failure(stage="prompt-writer", retry_idx=offset)
            continue
        LOGGER.error("Prompt-writer failed after retries")
        return None

    def _estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        return max(1, int(len(text) / 4))

    def _estimate_sample_row_tokens(self, df: pl.DataFrame, *, max_cell_len: int = 40, sample_rows: int = 200) -> int:
        if df is None or df.height == 0:
            return 0
        sample = df.head(min(sample_rows, df.height))
        total_chars = 0
        for row in sample.iter_rows():
            truncated = tuple(_truncate_cell(v, max_cell_len) for v in row)
            total_chars += len(str(truncated)) + 6
        avg = total_chars / sample.height if sample.height else 0
        return self._estimate_tokens("X" * int(avg))

    def _render_info_result_sample_table(
        self,
        *,
        df: pl.DataFrame,
        max_rows: int = 7,
        max_cell_len: int = 40,
    ) -> str:
        headers = ["row", *list(df.columns)]
        table_lines = [
            "| " + " | ".join(headers) + " |",
            "|" + "|".join("---" for _ in headers) + "|",
        ]
        if df.height == 0:
            table_lines.append("| (no rows) |" + " |" * len(df.columns))
            return "\n".join(table_lines)

        target = max(1, int(max_rows))
        if df.height <= target:
            indices = list(range(df.height))
        else:
            preferred = [
                0,
                int(round(0.01 * (df.height - 1))),
                int(round(0.25 * (df.height - 1))),
                int(round(0.50 * (df.height - 1))),
                int(round(0.75 * (df.height - 1))),
                int(round(0.99 * (df.height - 1))),
                df.height - 1,
            ]
            indices: List[int] = []
            for idx in preferred:
                idx = max(0, min(df.height - 1, idx))
                if idx not in indices:
                    indices.append(idx)
            if len(indices) < target:
                for idx in _evenly_spaced_indices(df.height, target):
                    if idx not in indices:
                        indices.append(idx)
                    if len(indices) >= target:
                        break
            indices = indices[:target]

        for idx in indices:
            row = list(df.row(idx))
            rendered = [str(idx + 1), *[_truncate_cell(value, max_cell_len) for value in row]]
            table_lines.append("| " + " | ".join(rendered) + " |")
        return "\n".join(table_lines)

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
        min_samples: int = 100,
        max_samples: int = 200,
        max_cell_len: int = 40,
    ) -> Tuple[int, int]:
        if df is None or df.height == 0:
            return 0, max_cell_len

        min_samples = min(min_samples, df.height)
        scale = min(1.0, 6 / max(6, df.width))
        max_samples = max(min_samples, min(max_samples, int(round(max_samples * scale))))
        cap = min(df.height, max_samples)
        if available_tokens is None:
            return max(1, min(cap, max(min_samples, cap))), max_cell_len
        if available_tokens <= 0:
            return max(1, min(cap, min_samples)), max_cell_len

        budget = int(available_tokens * 0.5)
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

    def _estimate_full_result_chars(self, df: pl.DataFrame, sample_rows: int = 200) -> int:
        if df.height == 0:
            return 0
        sample = df.head(min(sample_rows, df.height))
        total = 0
        for row in sample.iter_rows():
            total += sum(len(str(cell)) for cell in row) + max(0, len(row) - 1)
        avg = total / sample.height if sample.height else 0
        header = sum(len(c) for c in df.columns) + max(0, len(df.columns) - 1)
        approx_chars = int(header + (avg + 1) * df.height)
        return approx_chars

    def _estimate_full_result_tokens(self, df: pl.DataFrame, sample_rows: int = 200) -> int:
        approx_chars = self._estimate_full_result_chars(df, sample_rows=sample_rows)
        if approx_chars <= 0:
            return 0
        return max(1, int(approx_chars / 4))

    def _judge_context_limit(self) -> Optional[int]:
        if self.base_provider == 'openrouter':
            if not self.openrouter_context_map:
                return None
            if not self.current_judge_model:
                return None
            return self.openrouter_context_map.get(self.current_judge_model)
        return self.judge_context_limit

    def _call_sql_writer_with_provider(
        self,
        *,
        provider: DspyProvider,
        model_label: str,
        temperature: float,
        uq: str,
        up: str,
        iterations: List[Iteration],
        n: int,
    ) -> Optional[str]:
        if not provider.is_available():
            LOGGER.error("SQL provider not available: %s", model_label)
            return None

        messages = self._build_messages_for_sql(uq=uq, up=up, iterations=iterations, n=n)
        if self.verbosity >= 3:
            self.LOG(3, "SQL_SYSTEM_PROMPT:")
            self.LOG(3, "[[[ SP here; SHA256=", self.system_prompt_hash, " ]]]")
            user_prompt = messages[1]["content"] if len(messages) > 1 else ""
            self.LOG(3, f"SQL_USER_PROMPT ({model_label}):")
            self.LOG_BLOCK(user_prompt)
        start_time = time.time()
        self._throttle_before_call(stage="sql-writer")
        sql = provider.generate_text(
            messages,
            max_tokens=self.sql_max_tokens,
            temperature=temperature,
            response_format=response_format_sql(),
        )
        elapsed = time.time() - start_time
        actual_label = self._runtime_provider_label(provider)
        LOGGER.info("SQL generated in %.2fs (%s)", elapsed, actual_label)
        if sql is None:
            return None

        cleaned = sql.strip()
        if self.verbosity >= 3:
            self.LOG(3, f"SQL_JSON_RAW ({model_label}):")
            self.LOG_BLOCK(cleaned)
        parsed = parse_sql_output(cleaned)
        if not parsed:
            return None
        parsed = re.sub(r'^```sql\s*', '', parsed, flags=re.MULTILINE)
        parsed = re.sub(r'^```\s*$', '', parsed, flags=re.MULTILINE)
        parsed = re.sub(r'\s*```\s*$', '', parsed, flags=re.MULTILINE)
        parsed = self._strip_unrequested_limit(sql=parsed, uq=uq, up=up)
        return parsed

    def _call_sql_writer(self, *, uq: str, up: str, iterations: List[Iteration], n: int, attempt_idx: int) -> Optional[str]:
        if not self.sql_provider.is_available():
            LOGGER.error("SQL provider not available")
            return None

        self._ensure_sql_provider_for_attempt(attempt_idx)
        return self._call_sql_writer_with_provider(
            provider=self.sql_provider,
            model_label=str(self.current_sql_model),
            temperature=self.sql_temperature,
            uq=uq,
            up=up,
            iterations=iterations,
            n=n,
        )

    def _call_sql_candidates(
        self,
        *,
        uq: str,
        up: str,
        iterations: List[Iteration],
        n: int,
        attempt_idx: int,
    ) -> List[SqlCandidate]:
        if self.sql_sampler_providers:
            max_workers = self.sql_parallelism or len(self.sql_sampler_providers)
            results: List[SqlCandidate] = []
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {}
                for spec, provider_obj in self.sql_sampler_providers:
                    label = spec.label
                    futures[executor.submit(
                        self._call_sql_writer_with_provider,
                        provider=provider_obj,
                        model_label=label,
                        temperature=spec.temperature,
                        uq=uq,
                        up=up,
                        iterations=iterations,
                        n=n,
                    )] = spec
                for future in as_completed(futures):
                    spec = futures[future]
                    try:
                        sql = future.result()
                    except Exception as exc:
                        LOGGER.warning("SQL sampler failed (%s): %s", spec.label, exc)
                        continue
                    if not sql:
                        continue
                    results.append(
                        SqlCandidate(
                            sql=sql,
                            model=spec.model,
                            provider=spec.provider,
                            base_url=spec.base_url,
                            label=spec.label,
                            sql_index=self.sql_sampler_label_map.get(spec.label, 1),
                        )
                    )
            return results

        sql = self._call_sql_writer(uq=uq, up=up, iterations=iterations, n=n, attempt_idx=attempt_idx)
        if not sql:
            return []
        return [
            SqlCandidate(
                sql=sql,
                model=self.sql_provider.model,
                provider=self.sql_provider.provider,
                base_url=self.sql_provider.base_url,
                label=self._runtime_provider_label(self.sql_provider),
                sql_index=1,
            )
        ]

    def _call_judge(
        self,
        *,
        uq: str,
        up: str,
        sql: str,
        plan_summary: str,
        res_summary: str,
        iterations: List[Iteration],
        n: int,
        attempt_idx: int,
        stage_label: Optional[str] = None,
    ) -> Tuple[Optional[bool], Optional[float], str]:
        stage_ctx = log_stage(stage_label) if stage_label else contextlib.nullcontext()
        with stage_ctx:
            if not self.judge_provider.is_available():
                fallback = {"analysis": "Judge disabled.", "score": 0.0, "decision": "NO"}
                return False, 0.0, json.dumps(fallback)

            messages = self._build_messages_for_judge(
                uq=uq,
                up=up,
                sql=sql,
                plan_summary=plan_summary,
                res_summary=res_summary,
                iterations=iterations,
                n=n,
            )
            if self.verbosity >= 3:
                user_chars = sum(len(m.get('content', '')) for m in messages if m.get('role') == 'user')
                self.LOG(3, "\n" + "=" * 20)
                self.LOG(3, f"VERBOSE: Judge Prompt (Iteration {n})")
                self.LOG(3, "=" * 20)
                self.LOG(3, f"(system chars: {len(messages[0]['content']):,})")
                self.LOG(3, f"(user chars total: {user_chars:,})")
                self.LOG(3, "=" * 20 + "\n")
                system_text = ""
                user_text = ""
                for msg in messages:
                    role = str(msg.get("role", ""))
                    content = msg.get("content", "")
                    if isinstance(content, list):
                        content = "\n".join(str(c) for c in content)
                    else:
                        content = str(content)
                    if role == "system":
                        system_text += content
                    elif role == "user":
                        user_text += content
                self.LOG(3, "Judge system prompt:")
                self.LOG_BLOCK(system_text)
                self.LOG(3, "Judge user prompt:")
                self.LOG_BLOCK(user_text)
                self.LOG(3, "SQL passed to judge:")
                self.LOG_BLOCK(sql)
                self.LOG(3, "PLAN passed to judge:")
                self.LOG_BLOCK(plan_summary)
                self.LOG(3, "RES summary passed to judge:")
                self.LOG_BLOCK(res_summary)

            last_text: Optional[str] = None
            rf = response_format_judge()
            for offset in range(max(1, self.judge_call_retries)):
                self._ensure_judge_provider_for_attempt_with_offset(attempt_idx=attempt_idx, offset=offset)
                self._set_provider_timeout(self.judge_provider, self.judge_timeout)
                self._throttle_before_call(stage="judge")
                text = self.judge_provider.generate_text(
                    messages,
                    max_tokens=self.judge_max_tokens,
                    temperature=self.judge_temperature,
                    response_format=rf,
                )
                if text is None:
                    LOGGER.warning("Judge call failed; trying next judge model")
                    self._backoff_after_failure(stage="judge", retry_idx=offset)
                    continue
                last_text = text.strip()
                decision, score = parse_judge_output(last_text)
                if decision is None or score is None:
                    LOGGER.warning("Judge output malformed; model=%s; trying next judge model", self.current_judge_model)
                    self._save_malformed_judge_output(
                        text=last_text,
                        n=n,
                        attempt_idx=attempt_idx,
                        offset=offset,
                    )
                    continue

                effective_decision, effective_text = self._apply_judge_score_policy(
                    decision=decision,
                    score=score,
                    text=last_text,
                    model_label=self._runtime_provider_label(self.judge_provider),
                )
                if effective_decision is None:
                    continue

                return effective_decision, score, effective_text

            if last_text is None:
                fallback = {"analysis": "Judge failed.", "score": 0.0, "decision": "NO"}
                return False, 0.0, json.dumps(fallback)
            decision, score = parse_judge_output(last_text)
            if decision is None or score is None:
                preview = last_text.replace("\n", " ")[:200]
                fallback = {
                    "analysis": f"Judge output malformed; treating as NO. preview='{preview}'",
                    "score": 0.0,
                    "decision": "NO",
                }
                return False, 0.0, json.dumps(fallback)
            effective_decision, effective_text = self._apply_judge_score_policy(
                decision=decision,
                score=score,
                text=last_text,
                model_label=self._runtime_provider_label(self.judge_provider),
            )
            if effective_decision is None:
                fallback = {
                    "analysis": "Judge said YES with too low a score after retries; treating as NO.",
                    "score": score,
                    "decision": "NO",
                }
                return False, score, json.dumps(fallback)
            return effective_decision, score, effective_text

    def _call_judge_with_provider(
        self,
        *,
        provider_obj: DspyProvider,
        model_label: str,
        temperature: float,
        uq: str,
        up: str,
        sql: str,
        plan_summary: str,
        res_summary: str,
        iterations: List[Iteration],
        n: int,
        stage_label: Optional[str] = None,
    ) -> JudgeResult:
        stage_ctx = log_stage(stage_label) if stage_label else contextlib.nullcontext()
        with stage_ctx:
            if not provider_obj.is_available():
                fallback = {"analysis": "Judge disabled.", "score": 0.0, "decision": "NO"}
                return JudgeResult(
                    decision=False,
                    score=0.0,
                    text=json.dumps(fallback),
                    judge_model=model_label,
                    judge_provider=model_label,
                    label=model_label,
                )

            messages = self._build_messages_for_judge(
                uq=uq,
                up=up,
                sql=sql,
                plan_summary=plan_summary,
                res_summary=res_summary,
                iterations=iterations,
                n=n,
            )
            if self.verbosity >= 3:
                user_chars = sum(len(m.get('content', '')) for m in messages if m.get('role') == 'user')
                self.LOG(3, "\n" + "=" * 20)
                self.LOG(3, f"VERBOSE: Judge Prompt (Iteration {n}, {model_label})")
                self.LOG(3, "=" * 20)
                self.LOG(3, f"(system chars: {len(messages[0]['content']):,})")
                self.LOG(3, f"(user chars total: {user_chars:,})")
                self.LOG(3, "=" * 20 + "\n")

            last_text: Optional[str] = None
            rf = response_format_judge()
            for offset in range(max(1, self.judge_call_retries)):
                self._set_provider_timeout(provider_obj, self.judge_timeout)
                self._throttle_before_call(stage="judge")
                text = provider_obj.generate_text(
                    messages,
                    max_tokens=self.judge_max_tokens,
                    temperature=temperature,
                    response_format=rf,
                )
                if text is None:
                    LOGGER.warning("Judge call failed (%s); retrying", model_label)
                    self._backoff_after_failure(stage="judge", retry_idx=offset)
                    continue
                last_text = text.strip()
                decision, score = parse_judge_output(last_text)
                if decision is None or score is None:
                    LOGGER.warning("Judge output malformed (%s); retrying", model_label)
                    continue
                effective_decision, effective_text = self._apply_judge_score_policy(
                    decision=decision,
                    score=score,
                    text=last_text,
                    model_label=model_label,
                )
                if effective_decision is None:
                    continue
                actual_judge_label = self._runtime_provider_label(provider_obj)
                return JudgeResult(
                    decision=effective_decision,
                    score=score,
                    text=effective_text,
                    judge_model=actual_judge_label,
                    judge_provider=provider_obj.provider,
                    label=actual_judge_label,
                )

            if last_text is None:
                fallback = {"analysis": "Judge failed.", "score": 0.0, "decision": "NO"}
                return JudgeResult(
                    decision=False,
                    score=0.0,
                    text=json.dumps(fallback),
                    judge_model=self._runtime_provider_label(provider_obj),
                    judge_provider=provider_obj.provider,
                    label=self._runtime_provider_label(provider_obj),
                )
            decision, score = parse_judge_output(last_text)
            if decision is None or score is None:
                preview = last_text.replace("\n", " ")[:200]
                fallback = {
                    "analysis": f"Judge output malformed; treating as NO. preview='{preview}'",
                    "score": 0.0,
                    "decision": "NO",
                }
                return JudgeResult(
                    decision=False,
                    score=0.0,
                    text=json.dumps(fallback),
                    judge_model=self._runtime_provider_label(provider_obj),
                    judge_provider=provider_obj.provider,
                    label=self._runtime_provider_label(provider_obj),
                )
            return JudgeResult(
                decision=decision,
                score=score,
                text=last_text,
                judge_model=self._runtime_provider_label(provider_obj),
                judge_provider=provider_obj.provider,
                label=self._runtime_provider_label(provider_obj),
            )

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
            LOGGER.warning("Saved malformed judge output to %s", out_path)
        except Exception as exc:
            LOGGER.warning("Failed to save malformed judge output: %s", exc)

    def _append_accepted_memory_json(
        self,
        *,
        uq: str,
        up: str,
        sql: str,
        res_summary: str,
        judge_text: str,
        iter_n: int,
        sql_label: Optional[str],
        judge_label: Optional[str],
        sql_stage: Optional[str],
        judge_stage: Optional[str],
        row_count: Optional[int],
    ) -> None:
        if not self.memory_json_path:
            return
        judge_obj: Optional[Dict[str, object]] = None
        try:
            parsed = json.loads(judge_text)
            if isinstance(parsed, dict):
                judge_obj = parsed
        except Exception:
            judge_obj = None

        entry = {
            "ts_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "run_label": self.run_id,
            "iteration": int(iter_n),
            "accepted": True,
            "UQ": uq,
            "UP": up,
            "SQL": sql,
            "RES": res_summary,
            "J": judge_obj if judge_obj is not None else {"raw": judge_text},
            "J_raw": judge_text,
            "row_count": int(row_count) if row_count is not None else None,
            "sql_label": sql_label,
            "judge_label": judge_label,
            "sql_stage": sql_stage,
            "judge_stage": judge_stage,
            "system_prompt_sha256": self.system_prompt_hash,
        }
        try:
            memory_path = append_target_path(Path(self.memory_json_path))
            memory_path.parent.mkdir(parents=True, exist_ok=True)
            if memory_path.suffix.lower() == ".json":
                payload: Dict[str, object]
                if any(candidate.exists() for candidate in read_candidates(memory_path, prefer_compressed=False)):
                    text = read_text_maybe_compressed(memory_path, encoding="utf-8", errors="replace", prefer_compressed=False).strip()
                    if text:
                        parsed = json.loads(text)
                        if isinstance(parsed, dict) and isinstance(parsed.get("entries"), list):
                            payload = parsed
                        elif isinstance(parsed, list):
                            payload = {"schema_version": 1, "entries": parsed}
                        else:
                            payload = {"schema_version": 1, "entries": []}
                    else:
                        payload = {"schema_version": 1, "entries": []}
                else:
                    payload = {"schema_version": 1, "entries": []}

                entries = payload.get("entries")
                if not isinstance(entries, list):
                    entries = []
                    payload["entries"] = entries
                entries.append(entry)
                payload["generated_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                memory_path.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
            else:
                with memory_path.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
            LOGGER.info("Accepted-memory appended: %s", memory_path)
        except Exception as exc:
            LOGGER.warning("Failed to append accepted-memory JSON entry: %s", exc)

    def query(
        self,
        question: str,
        *,
        save_to_file: Optional[str] = None,
        min_rows: int = 0,
        dry_run: bool = False,
        case_label: Optional[str] = None,
    ) -> Optional[pl.DataFrame]:
        uq = (question or "").strip()
        if not uq:
            return None

        with log_stage("UQ"):
            if case_label:
                LOGGER.info("Case: %s", case_label)
            LOGGER.info("User question received (%s chars)", len(uq))
            LOGGER.info("%s", uq)

        iterations: List[Iteration] = []
        up: Optional[str] = None
        self.latest_returned_iteration_n = None
        self.latest_exhausted = False
        exhausted_best_iteration: Optional[Iteration] = None
        exhausted_best_df: Optional[pl.DataFrame] = None
        exhausted_best_score = -1.0

        for attempt_idx in range(self.max_retries):
            n = attempt_idx + 1
            with log_stage(f"ITER_{n}"):
                if self.sql_sampler_specs:
                    labels = ", ".join(spec.label for spec in self.sql_sampler_specs)
                    LOGGER.info("Iteration %s/%s using SQL samplers: %s", n, self.max_retries, labels)
                else:
                    self._ensure_sql_provider_for_attempt(attempt_idx)
                    LOGGER.info(
                        "Iteration %s/%s using SQL target=%s active=%s",
                        n,
                        self.max_retries,
                        self.current_sql_model,
                        self._runtime_provider_label(self.sql_provider),
                    )

                history_up_sql = self._slice_history(iterations, self.history_window_up_sql)
                judge_history_len = max(0, self.judge_history_window - 1)
                history_for_judge = self._slice_history(iterations, judge_history_len)

                self.LOG(2, "\n" + "=" * 20, f"\nPROMPT-WRITER: generating UP_{n}\n" + "=" * 20)
                with log_stage(f"UP_{n}"):
                    LOGGER.info("Generating UP_%s with %s...", n, self._runtime_provider_label(self.up_provider))
                    up_next = self._call_prompt_writer(
                        uq=uq,
                        iterations=history_up_sql,
                        next_n=n,
                        attempt_idx=attempt_idx,
                    )
                if up_next is None or not up_next.strip():
                    if up is None:
                        LOGGER.error("Failed to generate UP_%s; skipping iteration", n)
                        continue
                    LOGGER.warning("Failed to generate UP_%s; reusing previous UP", n)
                else:
                    up = up_next.strip()
                if up is None:
                    LOGGER.error("No usable UP_%s; skipping iteration", n)
                    continue

                self.LOG(2, f"\nUP_{n}:")
                self.LOG_BLOCK(up)
                with log_stage(f"SQL_{n}"):
                    LOGGER.info("Generating SQL...")
                    candidates = self._call_sql_candidates(
                        uq=uq,
                        up=up,
                        iterations=history_up_sql,
                        n=n,
                        attempt_idx=attempt_idx,
                    )
                if not candidates:
                    LOGGER.error("Failed to generate SQL_%s; skipping iteration", n)
                    continue

                for cand in candidates:
                    LOGGER.info("Generated SQL_%s_%s (%s):", n, cand.sql_index, cand.label)
                    LOG_BLOCK(cand.sql)

                if self.verbose:
                    for cand in candidates:
                        self.LOG(1, "\n" + "=" * 20)
                        self.LOG(1, f"Generated SQL_{n} ({cand.label}):")
                        self.LOG(1, "=" * 20)
                        self.LOG_BLOCK(cand.sql)
                        self.LOG(1, "=" * 20 + "\n")

                if dry_run:
                    LOGGER.info("DRY RUN: not executing SQL")
                    return None

                candidate_runs: List[Dict[str, object]] = []
                for cand in candidates:
                    sql = cand.sql
                    with log_stage(f"RES_{n}_{cand.sql_index}"):
                        with log_stage(f"PLAN_{n}_{cand.sql_index}"):
                            _, plan_summary = self.explain_query_plan(sql)
                            if self.verbosity >= 2:
                                self.LOG(2, "\n" + "=" * 20)
                                self.LOG(2, f"PLAN_{n}_{cand.sql_index} ({cand.label}):")
                                self.LOG(2, "=" * 20)
                                self.LOG_BLOCK(plan_summary)
                                self.LOG(2, "=" * 20 + "\n")

                        success, df, err = self.execute_query_with_timeout(sql)

                        res_mode = "sample"
                        sample_rows: Optional[int] = None
                        sample_cell_len = 60
                        available_tokens: Optional[int] = None
                        if success and df is not None:
                            if self.verbosity >= 2:
                                self._print_full_result_rows(df=df, n=n, label=cand.label)
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
                                    plan_summary=plan_summary,
                                    res_summary="",
                                    iterations=history_for_judge,
                                    n=n,
                                )
                                base_tokens = self._estimate_tokens(self.system_prompt) + self._estimate_tokens(base_user)
                                available = int(context_limit * 0.9) - base_tokens
                                available_tokens = max(0, available)
                                est_full = self._estimate_full_result_tokens(df)
                                max_full_rows = 200
                                max_full_tokens = min(max(0, available), int(context_limit * 0.25))
                                if (
                                    available > 0
                                    and df.height <= max_full_rows
                                    and est_full <= max_full_tokens
                                ):
                                    res_mode = "full"
                                if self.verbosity >= 2:
                                    self.LOG(
                                        2,
                                        f"\nRES_{n} sizing: context={context_limit} tokens, base≈{base_tokens}, "
                                        f"full≈{est_full}, available≈{max(0, available)}, "
                                        f"max_full_rows={max_full_rows}, max_full_tokens≈{max_full_tokens} -> {res_mode}",
                                    )
                        if success and df is not None and res_mode == "sample":
                            sample_rows, sample_cell_len = self._choose_sample_params(df, available_tokens=available_tokens)

                        row_count, cols, samples_t, res_summary = self._summarize_result(
                            df=df,
                            error=err if not success else None,
                            min_rows=min_rows,
                            res_mode=res_mode,
                            sample_rows=sample_rows,
                            sample_cell_len=sample_cell_len,
                        )

                        if df is not None and success:
                            approx_chars = self._estimate_full_result_chars(df)
                            approx_tokens = max(1, int(approx_chars / 4)) if approx_chars > 0 else 0
                            LOGGER.info(
                                "RES_%s size: rows=%s cols=%s approx_bytes=%s approx_tokens=%s res_mode=%s",
                                n,
                                row_count,
                                len(cols),
                                approx_chars,
                                approx_tokens,
                                res_mode,
                            )
                            LOGGER.info(
                                "RES_%s sample:\n%s",
                                n,
                                self._render_info_result_sample_table(df=df, max_rows=7, max_cell_len=60),
                            )

                        if self.verbosity >= 2:
                            sampled_for_judge = row_count if res_mode == "full" else len(samples_t)
                            self.LOG(2, "\n" + "=" * 20)
                            self.LOG(2, f"RES_{n}_{cand.sql_index} STATS:")
                            self.LOG(2, "=" * 20)
                            self.LOG(2, f"row_count: {row_count}")
                            self.LOG(2, f"res_mode: {res_mode}")
                            self.LOG(2, f"rows_passed_to_judge: {sampled_for_judge}")
                            self.LOG(2, "=" * 20)
                            self.LOG(2, "\n" + "=" * 20)
                            self.LOG(2, f"RES_{n}_{cand.sql_index} ({cand.label}):")
                            self.LOG(2, "=" * 20)
                            self.LOG_BLOCK(res_summary)
                            self.LOG(2, "=" * 20 + "\n")

                    candidate_runs.append(
                        {
                            "candidate": cand,
                            "plan_summary": plan_summary,
                            "res_summary": res_summary,
                            "row_count": row_count,
                            "cols": cols,
                            "samples_t": samples_t,
                            "df": df,
                            "err": err if not success else None,
                        }
                    )

                judge_results_by_candidate: Dict[int, List[JudgeResult]] = {}
                with log_stage(f"J_{n}"):
                    LOGGER.info("Judging RES_%s...", n)
                    if self.judge_sampler_providers:
                        max_workers = self.judge_parallelism or len(self.judge_sampler_providers)
                        max_workers = min(max_workers, len(self.judge_sampler_providers))
                        selected_judges = self.judge_sampler_providers[:max_workers]
                        LOGGER.info(
                            "Judge dispatching to %s endpoints (parallel): %s",
                            len(selected_judges),
                            [spec.label for spec, _ in selected_judges],
                        )
                        with ThreadPoolExecutor(max_workers=max_workers) as executor:
                            futures = {}
                            for idx, payload in enumerate(candidate_runs):
                                cand = payload["candidate"]
                                for spec, provider_obj in selected_judges:
                                    label = spec.label
                                    judge_idx = self.judge_sampler_label_map.get(label, 1)
                                    stage_label = f"J_{n}_{judge_idx}_SQL_{n}_{cand.sql_index}"
                                    future = executor.submit(
                                        self._call_judge_with_provider,
                                        provider_obj=provider_obj,
                                        model_label=label,
                                        temperature=spec.temperature,
                                        uq=uq,
                                        up=up,
                                        sql=cand.sql,
                                        plan_summary=payload["plan_summary"],
                                        res_summary=payload["res_summary"],
                                        iterations=history_for_judge,
                                        n=n,
                                        stage_label=stage_label,
                                    )
                                    futures[future] = idx
                            for future in as_completed(futures):
                                idx = futures[future]
                                try:
                                    result = future.result()
                                except Exception as exc:
                                    LOGGER.warning("Judge sampler failed: %s", exc)
                                    continue
                                judge_results_by_candidate.setdefault(idx, []).append(result)
                    else:
                        LOGGER.info(
                            "Judge dispatching to single endpoint: %s",
                            self._runtime_provider_label(self.judge_provider),
                        )
                        for idx, payload in enumerate(candidate_runs):
                            cand = payload["candidate"]
                            stage_label = f"J_{n}_1_SQL_{n}_{cand.sql_index}"
                            decision, score, text = self._call_judge(
                                uq=uq,
                                up=up,
                                sql=cand.sql,
                                plan_summary=payload["plan_summary"],
                                res_summary=payload["res_summary"],
                                iterations=history_for_judge,
                                n=n,
                                attempt_idx=attempt_idx,
                                stage_label=stage_label,
                            )
                            actual_judge_label = self._runtime_provider_label(self.judge_provider)
                            judge_results_by_candidate[idx] = [
                                JudgeResult(
                                    decision=decision,
                                    score=score,
                                    text=text,
                                    judge_model=actual_judge_label,
                                    judge_provider=self.judge_provider.provider,
                                    label=actual_judge_label,
                                )
                            ]

                best_idx = None
                best_score = -1.0
                best_decision = False
                best_judge_text = ""
                best_judge_model = None
                for idx, payload in enumerate(candidate_runs):
                    results = judge_results_by_candidate.get(idx, [])
                    if not results:
                        continue
                    best_for_candidate = max(
                        results,
                        key=lambda r: ((r.decision is True), (r.score or -1.0)),
                    )
                    if self.verbosity >= 1:
                        judge_idx = self.judge_sampler_label_map.get(best_for_candidate.label, 1)
                        LOGGER.info(
                            "SQL_%s_%s (%s) judged by %s (J%s): decision=%s score=%s",
                            n,
                            payload["candidate"].sql_index,
                            payload["candidate"].label,
                            best_for_candidate.label,
                            judge_idx,
                            best_for_candidate.decision,
                            best_for_candidate.score,
                        )
                    decision = bool(best_for_candidate.decision)
                    score = best_for_candidate.score if best_for_candidate.score is not None else -1.0
                    if decision and score >= self.judge_yes_score_threshold:
                        if not best_decision or score > best_score:
                            best_decision = True
                            best_score = score
                            best_idx = idx
                            best_judge_text = best_for_candidate.text
                            best_judge_model = best_for_candidate.judge_model
                    else:
                        if not best_decision and score > best_score:
                            best_score = score
                            best_idx = idx
                            best_judge_text = best_for_candidate.text
                            best_judge_model = best_for_candidate.judge_model

                if best_idx is None:
                    LOGGER.error("No judge results; skipping iteration")
                    continue

                if self.sql_sampler_specs:
                    sql_map = [f"SQL_{n}_{idx + 1}={spec.label}" for idx, spec in enumerate(self.sql_sampler_specs)]
                    LOGGER.info("SQL map (ITER_%s): %s", n, sql_map)
                if self.judge_sampler_specs:
                    judge_map = [f"J{idx + 1}={spec.label}" for idx, spec in enumerate(self.judge_sampler_specs)]
                    LOGGER.info("Judge map (ITER_%s): %s", n, judge_map)
                LOGGER.info("SQL verdicts (ITER_%s):", n)
                candidate_best: Dict[int, JudgeResult] = {}
                for idx, payload in enumerate(candidate_runs):
                    cand = payload["candidate"]
                    results = judge_results_by_candidate.get(idx, [])
                    LOGGER.info("SQL_%s_%s: %s", n, cand.sql_index, cand.label)
                    LOGGER.info("SQL_%s_%s text:", n, cand.sql_index)
                    LOG_BLOCK(cand.sql)
                    if not results:
                        LOGGER.info("  (no judge results)")
                        continue
                    for res in results:
                        judge_idx = self.judge_sampler_label_map.get(res.label, 1)
                        LOGGER.info(
                            "  SQL_%s_%s Judge J%s (%s): decision=%s score=%s",
                            n,
                            cand.sql_index,
                            judge_idx,
                            res.label,
                            res.decision,
                            res.score,
                        )
                        LOGGER.info("  SQL_%s_%s Judge J%s text:", n, cand.sql_index, judge_idx)
                        LOG_BLOCK(res.text)
                    best_for_candidate = max(
                        results,
                        key=lambda r: ((r.decision is True), (r.score or -1.0)),
                    )
                    candidate_best[idx] = best_for_candidate

                chosen = candidate_runs[best_idx]
                chosen_candidate: SqlCandidate = chosen["candidate"]
                sql = chosen_candidate.sql
                self.current_sql_model = chosen_candidate.model or self.current_sql_model
                df = chosen["df"]
                err = chosen["err"]
                plan_summary = chosen["plan_summary"]
                res_summary = chosen["res_summary"]
                row_count = chosen["row_count"]
                cols = chosen["cols"]
                samples_t = chosen["samples_t"]
                judge_text = best_judge_text
                judge_score = best_score if best_score >= 0 else None
                judge_decision = best_decision
                if best_judge_model:
                    self.current_judge_model = best_judge_model
                winner_label: Optional[str] = None
                winner_judge_idx: Optional[int] = None
                if best_idx in candidate_best:
                    winner = candidate_best[best_idx]
                    winner_label = winner.label
                    winner_judge_idx = self.judge_sampler_label_map.get(winner.label, 1)
                    LOGGER.info(
                        "Winner (ITER_%s): SQL_%s_%s %s judged by %s (J%s) decision=%s score=%s",
                        n,
                        n,
                        chosen_candidate.sql_index,
                        chosen_candidate.label,
                        winner.label,
                        winner_judge_idx,
                        winner.decision,
                        winner.score,
                    )

                it = Iteration(
                    n=n,
                    up=up,
                    sql=sql,
                    sql_model=chosen_candidate.label,
                    plan_summary=plan_summary,
                    res_row_count=row_count,
                    res_columns=cols,
                    res_samples=samples_t,
                    res_error=err if err else None,
                    judge_text=judge_text,
                    judge_model=best_judge_model,
                    judge_score=judge_score,
                    judge_decision=judge_decision,
                )
                iterations.append(it)
                self.latest_iterations = list(iterations)
                self.latest_sql = sql
                self.latest_up = up
                self.latest_judge_decision = judge_decision
                self.latest_judge_score = judge_score
                self.latest_result_df = df
                score_for_exhaustion = judge_score if judge_score is not None else -1.0
                if df is not None and score_for_exhaustion >= exhausted_best_score:
                    exhausted_best_score = score_for_exhaustion
                    exhausted_best_iteration = it
                    exhausted_best_df = df
                    LOGGER.info(
                        "Current best judged result: ITER_%s decision=%s score=%s",
                        it.n,
                        it.judge_decision,
                        it.judge_score,
                    )

                if self.save_intermediate and df is not None:
                    run_id = self.run_id or "run"
                    out_dir = Path(self.intermediate_dir)
                    out_dir.mkdir(parents=True, exist_ok=True)
                    out_path = out_dir / f"{self.output_base}_{run_id}_iter{n}.csv"
                    df.write_csv(out_path)
                    self.LOG(2, f"\n📄 Intermediate saved to: {out_path}")

                if self.verbosity >= 2:
                    self.LOG(2, "\n" + "-" * 20)
                    self.LOG(2, f"J_{n}:")
                    self.LOG_BLOCK(judge_text)
                    self.LOG(2, "-" * 20 + "\n")

                stop_by_yes = judge_decision is True and (judge_score is None or judge_score >= self.judge_yes_score_threshold)

                if stop_by_yes:
                    LOGGER.info(f"Stopping: judge_decision={judge_decision} judge_score={judge_score}")
                    effective_judge_label = winner_label or (str(best_judge_model) if best_judge_model else None)
                    self._append_accepted_memory_json(
                        uq=uq,
                        up=up,
                        sql=sql,
                        res_summary=res_summary,
                        judge_text=judge_text,
                        iter_n=n,
                        sql_label=chosen_candidate.label,
                        judge_label=effective_judge_label,
                        sql_stage=f"SQL_{n}_{chosen_candidate.sql_index}",
                        judge_stage=f"J_{n}_{winner_judge_idx}_SQL_{n}_{chosen_candidate.sql_index}" if winner_judge_idx is not None else f"J_{n}",
                        row_count=row_count,
                    )
                    if df is None:
                        return None
                    self.latest_returned_iteration_n = n
                    if save_to_file:
                        df.write_csv(save_to_file)
                        LOGGER.info("Saved to: %s", save_to_file)
                    return df

        LOGGER.error(f"All {self.max_retries} iterations exhausted")
        self.latest_iterations = list(iterations)
        if exhausted_best_iteration is not None and exhausted_best_df is not None:
            LOGGER.warning(
                "Returning best judged result after exhaustion: ITER_%s decision=%s score=%s",
                exhausted_best_iteration.n,
                exhausted_best_iteration.judge_decision,
                exhausted_best_iteration.judge_score,
            )
            self.latest_result_df = exhausted_best_df
            self.latest_sql = exhausted_best_iteration.sql
            self.latest_up = exhausted_best_iteration.up
            self.latest_judge_decision = exhausted_best_iteration.judge_decision
            self.latest_judge_score = exhausted_best_iteration.judge_score
            self.latest_returned_iteration_n = exhausted_best_iteration.n
            self.latest_exhausted = True
            if save_to_file:
                exhausted_best_df.write_csv(save_to_file)
                LOGGER.info("Saved best exhausted result to: %s", save_to_file)
            return exhausted_best_df
        self.latest_result_df = None
        self.latest_sql = None
        self.latest_up = None
        self.latest_judge_decision = None
        self.latest_judge_score = None
        self.latest_returned_iteration_n = None
        self.latest_exhausted = True
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
        description='Natural language to SQL with UP/SQL/J loop (v4, DSPy) for ChEMBL',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('query', nargs='?', help='Natural language query (can be provided via pipe)')
    parser.add_argument('-q', '--query', dest='query_text', help='Natural language query')
    provider_choices = [
        'auto',
        'anthropic',
        'zai-anthropic',
        'openai',
        'gemini',
        'llamacpp',
        'mlxlm',
        'openrouter',
        'zai',
        'cerebras',
        'deepseek',
        'local',
    ]
    parser.add_argument(
        '--provider',
        choices=provider_choices,
        default=None,
        help='LLM provider (required; can also set TEXT2SQL_PROVIDER)',
    )
    parser.add_argument('--up-provider', default=None, help='Provider for prompt-writer (UP) stage')
    parser.add_argument('--up-model', default=None, help='Model for prompt-writer (UP) stage')
    parser.add_argument('--up-base-url', default=None, help='Base URL for prompt-writer (UP) stage')
    parser.add_argument('--up-temperature', type=float, default=None, help='Temperature for prompt-writer (UP) stage')
    parser.add_argument('--up-timeout', type=int, default=None, help='Timeout for prompt-writer (UP) stage')
    parser.add_argument(
        '--no-provider',
        action='store_true',
        help='Disable remote providers (force local LLM)',
    )
    parser.add_argument('--db-path', default='database/latest/chembl_36/chembl_36_sqlite/chembl_36.db', help='Path to ChEMBL SQLite DB')
    parser.add_argument(
        '--provider-base-url',
        default=None,
        help='Override provider base URL (e.g., http://127.0.0.1:8080/v1)',
    )
    parser.add_argument(
        '--sql-sampler',
        action='append',
        default=None,
        help='Extra SQL sampler endpoint (comma-separated key=value; repeatable)',
    )
    parser.add_argument(
        '--judge-sampler',
        action='append',
        default=None,
        help='Extra judge endpoint (comma-separated key=value; repeatable)',
    )
    parser.add_argument('--sql-parallelism', type=int, default=None, help='Max parallel SQL sampler calls')
    parser.add_argument('--judge-parallelism', type=int, default=None, help='Max parallel judge calls')

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
    parser.add_argument('--judge-provider', dest='judge_provider', default=None, help='Provider for judge stage')
    parser.add_argument('--judge-base-url', dest='judge_base_url', default=None, help='Base URL for judge stage')
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
    parser.add_argument('--writer-timeout', type=int, default=1800, help='LLM timeout for UP+SQL writers in seconds (default: 1800)')
    parser.add_argument('--judge-timeout', type=int, default=900, help='LLM timeout for judge in seconds (default: 900)')
    parser.add_argument('--provider-sleep', type=float, default=0.0, help='Min seconds between LLM API calls (default: 0)')
    parser.add_argument('--provider-retry-backoff', type=float, default=0.0, help='Base seconds for exponential backoff after failed provider calls (default: 0)')
    parser.add_argument(
        '--local-enable-thinking',
        action=argparse.BooleanOptionalAction,
        default=True,
        help='Enable llama.cpp-local chat-template thinking via chat_template_kwargs (default: enabled; use --no-local-enable-thinking to disable)',
    )
    parser.add_argument(
        '--local-reasoning-budget-tokens',
        type=int,
        default=None,
        help='Per-call llama.cpp local thinking budget; overrides server default when set',
    )
    parser.add_argument(
        '--local-reasoning-budget-message',
        default=None,
        help='Optional message injected when the local per-call reasoning budget is exhausted',
    )
    parser.add_argument('--quota-fallback-provider', default=None, help='First fallback provider to switch to when the primary Z.AI endpoint is rate- or quota-limited')
    parser.add_argument('--quota-fallback-base-url', default=None, help='Base URL for first fallback provider')
    parser.add_argument('--quota-fallback-model', default=None, help='Model for first fallback provider')
    parser.add_argument('--quota-fallback-provider-2', default=None, help='Second fallback provider to switch to when the first fallback is rate- or quota-limited')
    parser.add_argument('--quota-fallback-base-url-2', default=None, help='Base URL for second fallback provider')
    parser.add_argument('--quota-fallback-model-2', default=None, help='Model for second fallback provider')
    parser.add_argument('-a', '--auto', action='store_true', help='Auto-save results to timestamped CSV')
    parser.add_argument('-f', '--format', choices=['json', 'csv', 'table'], default='table', help='Output format')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Verbose output; repeat for more (-vv, -vvv)')
    parser.add_argument('--dry-run', action='store_true', help='Show query only, do not execute')
    parser.add_argument('--min-rows', type=int, default=1, help='Min rows hint for retries (default: 1)')
    parser.add_argument(
        '--multi-endpoint-profile',
        choices=[
            'local-mesh',
            'local-mesh2',
            'local-mesh3',
            'local-mesh1a',
            'local-mesh1b',
            'openrouter-free-mesh',
            'openrouter-free-one',
            'openrouter-free-local-mesha',
            'openrouter-free-local-meshb',
            'zai-pony-alpha-2',
            'zai-glm-4.7-anthropic',
            'zai-glm47-glm5-local',
            'zai-glm47-then-glm5-then-local',
        ],
        default=None,
        help='Apply a predefined multi-endpoint profile (local-mesh=local-mesh2, local-mesh3, openrouter-free-mesh, openrouter-free-one, local-mesh1a/1b, openrouter-free-local-mesh[a/b], zai-pony-alpha-2, zai-glm-4.7-anthropic, zai-glm47-glm5-local)',
    )

    parser.add_argument(
        '--history-window',
        type=str,
        default=None,
        help='(Deprecated) History window for both UP/SQL and judge. Use --history-window-up-sql and --judge-history-window.',
    )
    parser.add_argument(
        '--history-window-up-sql',
        type=str,
        default='all',
        help='How many prior iterations to include for UP+SQL writers (default: all)',
    )
    parser.add_argument(
        '--judge-history-window',
        type=int,
        default=1,
        help='How many iterations (including current) to include for judge context (default: 1)',
    )
    parser.add_argument(
        '--judge-score-threshold',
        type=float,
        default=0.5,
        help='Backward-compatible alias for --judge-yes-score-threshold (default: 0.5)',
    )
    parser.add_argument(
        '--judge-yes-score-threshold',
        type=float,
        default=None,
        help='Accept YES decisions at or above this score; defaults to --judge-score-threshold',
    )
    parser.add_argument(
        '--judge-no-override-threshold',
        type=float,
        default=0.99,
        help='Treat NO decisions above this score as effective YES (default: 0.99)',
    )
    parser.add_argument('--judge-call-retries', type=int, default=3, help='Retries per judge/prompt-writer call (offset models) (default: 3)')
    parser.add_argument('--judge-max-tokens', type=int, default=4096, help='Max output tokens for judge calls (default: 4096)')
    parser.add_argument('--schema-docs-path', default='doc/chembl_database_schema.md', help='Cached schema docs path')
    parser.add_argument('--schema-sample-rows', type=int, default=3, help='Sample rows per table in schema docs (default: 3)')
    parser.add_argument('--schema-max-cell-len', type=int, default=80, help='Max cell length in schema docs (default: 80)')
    parser.add_argument('--prompt-pack-path', default=DEFAULT_PROMPT_PACK_PATH, help='Prompt pack YAML path (default: experiments/prompt_pack_v4.0.yaml)')
    parser.add_argument('--prompt-hints-path', default=None, help='Override prompt hints path from prompt pack')
    parser.add_argument(
        '--filter-profile',
        choices=['none', 'strict', 'relaxed'],
        default='none',
        help='Preset filters for prompt-writer (none: no baseline filters; strict: publication+confidence=9+single protein; relaxed: no doc/doi, confidence>=8)',
    )
    parser.add_argument('--output-base', default='query_results', help='Base filename for CSV outputs (default: query_results)')
    parser.add_argument('--output-file', default=None, help='Exact filename for CSV outputs (overrides --output-base)')
    parser.add_argument(
        '--memory-json-path',
        default='MEMORY-ChEMBLdb-query.jsonl',
        help='Accepted-run memory path. Appends always target the plain .jsonl/.json path; reads transparently fall back to .zst/.zstd sidecars when present (default: MEMORY-ChEMBLdb-query.jsonl)',
    )
    parser.add_argument('--min-context', type=int, default=100000, help='Minimum OpenRouter model context length (default: 100000)')
    parser.add_argument('--judge-context-limit', type=int, default=None, help='Max judge context tokens for non-OpenRouter providers (default: provider preset)')
    parser.add_argument('--strip-unrequested-limit', dest='strip_unrequested_limit', action='store_true', help='Strip LIMIT unless user explicitly requested a row cap/top-N')
    parser.add_argument('--no-strip-unrequested-limit', dest='strip_unrequested_limit', action='store_false', help='Disable heuristic LIMIT stripping')
    parser.add_argument('--intermediate-dir', default='logs/intermediate', help='Directory for intermediate CSV results (default: logs/intermediate)')
    parser.add_argument('--save-intermediate', dest='save_intermediate', action='store_true', help='Save intermediate CSV results per iteration')
    parser.add_argument('--no-save-intermediate', dest='save_intermediate', action='store_false', help='Disable intermediate CSV results')
    parser.set_defaults(save_intermediate=True, strip_unrequested_limit=True)
    parser.add_argument('--run-label', default=None, help='Label used in all run-derived filenames (default: timestamp)')
    parser.add_argument('--temperature', type=float, default=1.0, help='Temperature for SQL generation and prompt-writer (default: 1.0)')
    parser.add_argument('--judge-temperature', type=float, default=0.5, help='Temperature for judge model (default: 0.5)')

    args = parser.parse_args()
    configure_logging(int(args.verbose))

    query = args.query or args.query_text
    if not query:
        if not sys.stdin.isatty():
            query = sys.stdin.read().strip()
        else:
            LOG_LINES(logging.INFO, "\n".join(["", "=" * 20, "Help", "=" * 20]))
            LOG_BLOCK(parser.format_help())
            LOG_LINES(logging.INFO, "\n".join(["=" * 20, ""]))
            return

    if args.multi_endpoint_profile in {'local-mesh', 'local-mesh2'}:
        def _set_if_empty(field: str, value: object) -> None:
            current = getattr(args, field)
            if current is None or current == [] or current == "":
                setattr(args, field, value)

        _set_if_empty('provider', 'llamacpp')
        _set_if_empty('provider_base_url', 'http://127.0.0.1:1234')
        _set_if_empty('up_provider', 'llamacpp')
        _set_if_empty('up_base_url', 'http://192.168.1.251:8081')
        _set_if_empty('up_model', 'glm-4.7-flash')
        _set_if_empty('judge_provider', 'llamacpp')
        _set_if_empty('judge_base_url', 'http://192.168.1.251:8081')
        _set_if_empty('temperature', 0.95)
        _set_if_empty('up_temperature', 0.95)
        _set_if_empty('judge_temperature', 0.95)
        _set_if_empty('writer_timeout', 1200)
        _set_if_empty('up_timeout', 1200)
        _set_if_empty('judge_timeout', 1200)
        _set_if_empty('sql_sampler', [
            'provider=llamacpp,base_url=http://127.0.0.1:1234,model=qwen3-coder-next-80b,temperature=0.95,timeout=1200',
            'provider=llamacpp,base_url=http://192.168.1.251:8081,model=glm-4.7-flash,temperature=0.95,timeout=1200',
        ])
        _set_if_empty('judge_sampler', [
            'provider=llamacpp,base_url=http://192.168.1.251:8081,model=glm-4.7-flash,temperature=0.95,timeout=1200',
            'provider=llamacpp,base_url=http://127.0.0.1:1234,model=qwen3-coder-next-80b,temperature=0.95,timeout=1200',
        ])
        if args.sql_parallelism is None and args.sql_sampler:
            args.sql_parallelism = len(args.sql_sampler)
        if args.judge_parallelism is None and args.judge_sampler:
            args.judge_parallelism = 1
    elif args.multi_endpoint_profile == 'local-mesh3':
        def _set_if_empty(field: str, value: object) -> None:
            current = getattr(args, field)
            if current is None or current == [] or current == "":
                setattr(args, field, value)

        _set_if_empty('provider', 'llamacpp')
        _set_if_empty('provider_base_url', 'http://127.0.0.1:1234')
        _set_if_empty('up_provider', 'llamacpp')
        _set_if_empty('up_base_url', 'http://192.168.1.251:8082')
        _set_if_empty('up_model', 'lfm2.5-small')
        _set_if_empty('judge_provider', 'llamacpp')
        _set_if_empty('judge_base_url', 'http://192.168.1.251:8081')
        _set_if_empty('temperature', 0.95)
        _set_if_empty('up_temperature', 0.95)
        _set_if_empty('judge_temperature', 0.95)
        _set_if_empty('writer_timeout', 1200)
        _set_if_empty('up_timeout', 1200)
        _set_if_empty('judge_timeout', 1200)
        _set_if_empty('sql_sampler', [
            'provider=llamacpp,base_url=http://127.0.0.1:1234,model=qwen3-coder-next-80b,temperature=0.95,timeout=1200',
            'provider=llamacpp,base_url=http://192.168.1.251:8081,model=glm-4.7-flash,temperature=0.95,timeout=1200',
        ])
        _set_if_empty('judge_sampler', [
            'provider=llamacpp,base_url=http://192.168.1.251:8081,model=glm-4.7-flash,temperature=0.95,timeout=1200',
            'provider=llamacpp,base_url=http://127.0.0.1:1234,model=qwen3-coder-next-80b,temperature=0.95,timeout=1200',
        ])
        if args.sql_parallelism is None and args.sql_sampler:
            args.sql_parallelism = len(args.sql_sampler)
        if args.judge_parallelism is None and args.judge_sampler:
            args.judge_parallelism = 1
    elif args.multi_endpoint_profile == 'openrouter-free-mesh':
        def _set_if_empty(field: str, value: object) -> None:
            current = getattr(args, field)
            if current is None or current == [] or current == "":
                setattr(args, field, value)

        _set_if_empty('provider', 'openrouter')
        _set_if_empty('provider_base_url', 'https://openrouter.ai/api/v1')
        _set_if_empty('up_provider', 'openrouter')
        _set_if_empty('up_model', 'openrouter/free')
        _set_if_empty('judge_provider', 'openrouter')
        _set_if_empty('judge_model', 'openrouter/free')
        _set_if_empty('temperature', 0.95)
        _set_if_empty('up_temperature', 0.95)
        _set_if_empty('judge_temperature', 0.95)
        _set_if_empty('writer_timeout', 1200)
        _set_if_empty('up_timeout', 1200)
        _set_if_empty('judge_timeout', 1200)
        _set_if_empty('sql_sampler', [
            'provider=openrouter,model=arcee-ai/trinity-large-preview:free,temperature=0.95,timeout=1200',
            'provider=openrouter,model=stepfun/step-3.5-flash:free,temperature=0.95,timeout=1200',
            'provider=openrouter,model=upstage/solar-pro-3:free,temperature=0.95,timeout=1200',
            'provider=openrouter,model=moonshotai/kimi-k2:free,temperature=0.95,timeout=1200',
            'provider=openrouter,model=tngtech/deepseek-r1t2-chimera:free,temperature=0.95,timeout=1200',
            'provider=openrouter,model=openrouter/free,temperature=0.95,timeout=1200',
        ])
        _set_if_empty('judge_sampler', [
            'provider=openrouter,model=moonshotai/kimi-k2:free,temperature=0.95,timeout=1200',
            'provider=openrouter,model=tngtech/deepseek-r1t2-chimera:free,temperature=0.95,timeout=1200',
            'provider=openrouter,model=openrouter/free,temperature=0.95,timeout=1200',
        ])
        if args.sql_parallelism is None and args.sql_sampler:
            args.sql_parallelism = len(args.sql_sampler)
        if args.judge_parallelism is None and args.judge_sampler:
            args.judge_parallelism = 1
    elif args.multi_endpoint_profile == 'openrouter-free-one':
        def _set_if_empty(field: str, value: object) -> None:
            current = getattr(args, field)
            if current is None or current == [] or current == "":
                setattr(args, field, value)

        _set_if_empty('provider', 'openrouter')
        _set_if_empty('provider_base_url', 'https://openrouter.ai/api/v1')
        _set_if_empty('up_provider', 'openrouter')
        _set_if_empty('up_model', 'openrouter/free')
        _set_if_empty('judge_provider', 'openrouter')
        _set_if_empty('judge_model', 'openrouter/free')
        _set_if_empty('temperature', 0.95)
        _set_if_empty('up_temperature', 0.95)
        _set_if_empty('judge_temperature', 0.95)
        _set_if_empty('writer_timeout', 1200)
        _set_if_empty('up_timeout', 1200)
        _set_if_empty('judge_timeout', 1200)
        _set_if_empty('sql_sampler', [
            'provider=openrouter,model=openrouter/free,temperature=0.95,timeout=1200',
        ])
        _set_if_empty('judge_sampler', [
            'provider=openrouter,model=openrouter/free,temperature=0.95,timeout=1200',
        ])
        if args.sql_parallelism is None and args.sql_sampler:
            args.sql_parallelism = len(args.sql_sampler)
        if args.judge_parallelism is None and args.judge_sampler:
            args.judge_parallelism = 1
    elif args.multi_endpoint_profile == 'local-mesh1a':
        def _set_if_empty(field: str, value: object) -> None:
            current = getattr(args, field)
            if current is None or current == [] or current == "":
                setattr(args, field, value)

        _set_if_empty('provider', 'llamacpp')
        _set_if_empty('provider_base_url', 'http://192.168.1.251:8081')
        _set_if_empty('up_provider', 'llamacpp')
        _set_if_empty('up_base_url', 'http://192.168.1.251:8081')
        _set_if_empty('up_model', 'glm-4.7-flash')
        _set_if_empty('judge_provider', 'llamacpp')
        _set_if_empty('judge_base_url', 'http://192.168.1.251:8081')
        _set_if_empty('judge_model', 'glm-4.7-flash')
        _set_if_empty('temperature', 0.95)
        _set_if_empty('up_temperature', 0.95)
        _set_if_empty('judge_temperature', 0.95)
        _set_if_empty('writer_timeout', 1200)
        _set_if_empty('up_timeout', 1200)
        _set_if_empty('judge_timeout', 1200)
        _set_if_empty('sql_sampler', [
            'provider=llamacpp,base_url=http://192.168.1.251:8081,model=glm-4.7-flash,temperature=0.95,timeout=1200',
        ])
        _set_if_empty('judge_sampler', [
            'provider=llamacpp,base_url=http://192.168.1.251:8081,model=glm-4.7-flash,temperature=0.95,timeout=1200',
        ])
        if args.sql_parallelism is None and args.sql_sampler:
            args.sql_parallelism = len(args.sql_sampler)
        if args.judge_parallelism is None and args.judge_sampler:
            args.judge_parallelism = 1
    elif args.multi_endpoint_profile == 'local-mesh1b':
        def _set_if_empty(field: str, value: object) -> None:
            current = getattr(args, field)
            if current is None or current == [] or current == "":
                setattr(args, field, value)

        _set_if_empty('provider', 'llamacpp')
        _set_if_empty('provider_base_url', 'http://127.0.0.1:1234')
        _set_if_empty('up_provider', 'llamacpp')
        _set_if_empty('up_base_url', 'http://127.0.0.1:1234')
        _set_if_empty('up_model', 'qwen3-coder-next-80b')
        _set_if_empty('judge_provider', 'llamacpp')
        _set_if_empty('judge_base_url', 'http://127.0.0.1:1234')
        _set_if_empty('judge_model', 'qwen3-coder-next-80b')
        _set_if_empty('temperature', 0.95)
        _set_if_empty('up_temperature', 0.95)
        _set_if_empty('judge_temperature', 0.95)
        _set_if_empty('writer_timeout', 1200)
        _set_if_empty('up_timeout', 1200)
        _set_if_empty('judge_timeout', 1200)
        _set_if_empty('sql_sampler', [
            'provider=llamacpp,base_url=http://127.0.0.1:1234,model=qwen3-coder-next-80b,temperature=0.95,timeout=1200',
        ])
        _set_if_empty('judge_sampler', [
            'provider=llamacpp,base_url=http://127.0.0.1:1234,model=qwen3-coder-next-80b,temperature=0.95,timeout=1200',
        ])
        if args.sql_parallelism is None and args.sql_sampler:
            args.sql_parallelism = len(args.sql_sampler)
        if args.judge_parallelism is None and args.judge_sampler:
            args.judge_parallelism = 1
    elif args.multi_endpoint_profile == 'openrouter-free-local-mesha':
        def _set_if_empty(field: str, value: object) -> None:
            current = getattr(args, field)
            if current is None or current == [] or current == "":
                setattr(args, field, value)

        _set_if_empty('provider', 'openrouter')
        _set_if_empty('provider_base_url', 'https://openrouter.ai/api/v1')
        _set_if_empty('up_provider', 'openrouter')
        _set_if_empty('up_model', 'openrouter/free')
        _set_if_empty('judge_provider', 'openrouter')
        _set_if_empty('judge_model', 'openrouter/free')
        _set_if_empty('temperature', 0.95)
        _set_if_empty('up_temperature', 0.95)
        _set_if_empty('judge_temperature', 0.95)
        _set_if_empty('writer_timeout', 1200)
        _set_if_empty('up_timeout', 1200)
        _set_if_empty('judge_timeout', 1200)
        _set_if_empty('sql_sampler', [
            'provider=openrouter,model=arcee-ai/trinity-large-preview:free,temperature=0.95,timeout=1200',
            'provider=openrouter,model=stepfun/step-3.5-flash:free,temperature=0.95,timeout=1200',
            'provider=openrouter,model=upstage/solar-pro-3:free,temperature=0.95,timeout=1200',
            'provider=openrouter,model=moonshotai/kimi-k2:free,temperature=0.95,timeout=1200',
            'provider=openrouter,model=tngtech/deepseek-r1t2-chimera:free,temperature=0.95,timeout=1200',
            'provider=openrouter,model=openrouter/free,temperature=0.95,timeout=1200',
            'provider=llamacpp,base_url=http://192.168.1.251:8081,model=glm-4.7-flash,temperature=0.95,timeout=1200',
        ])
        _set_if_empty('judge_sampler', [
            'provider=openrouter,model=moonshotai/kimi-k2:free,temperature=0.95,timeout=1200',
            'provider=openrouter,model=tngtech/deepseek-r1t2-chimera:free,temperature=0.95,timeout=1200',
            'provider=openrouter,model=openrouter/free,temperature=0.95,timeout=1200',
            'provider=llamacpp,base_url=http://192.168.1.251:8081,model=glm-4.7-flash,temperature=0.95,timeout=1200',
        ])
        if args.sql_parallelism is None and args.sql_sampler:
            args.sql_parallelism = len(args.sql_sampler)
        if args.judge_parallelism is None and args.judge_sampler:
            args.judge_parallelism = 1
    elif args.multi_endpoint_profile == 'openrouter-free-local-meshb':
        def _set_if_empty(field: str, value: object) -> None:
            current = getattr(args, field)
            if current is None or current == [] or current == "":
                setattr(args, field, value)

        _set_if_empty('provider', 'openrouter')
        _set_if_empty('provider_base_url', 'https://openrouter.ai/api/v1')
        _set_if_empty('up_provider', 'openrouter')
        _set_if_empty('up_model', 'openrouter/free')
        _set_if_empty('judge_provider', 'openrouter')
        _set_if_empty('judge_model', 'openrouter/free')
        _set_if_empty('temperature', 0.95)
        _set_if_empty('up_temperature', 0.95)
        _set_if_empty('judge_temperature', 0.95)
        _set_if_empty('writer_timeout', 1200)
        _set_if_empty('up_timeout', 1200)
        _set_if_empty('judge_timeout', 1200)
        _set_if_empty('sql_sampler', [
            'provider=openrouter,model=arcee-ai/trinity-large-preview:free,temperature=0.95,timeout=1200',
            'provider=openrouter,model=stepfun/step-3.5-flash:free,temperature=0.95,timeout=1200',
            'provider=openrouter,model=upstage/solar-pro-3:free,temperature=0.95,timeout=1200',
            'provider=openrouter,model=moonshotai/kimi-k2:free,temperature=0.95,timeout=1200',
            'provider=openrouter,model=tngtech/deepseek-r1t2-chimera:free,temperature=0.95,timeout=1200',
            'provider=openrouter,model=openrouter/free,temperature=0.95,timeout=1200',
            'provider=llamacpp,base_url=http://127.0.0.1:1234,model=qwen3-coder-next-80b,temperature=0.95,timeout=1200',
        ])
        _set_if_empty('judge_sampler', [
            'provider=openrouter,model=moonshotai/kimi-k2:free,temperature=0.95,timeout=1200',
            'provider=openrouter,model=tngtech/deepseek-r1t2-chimera:free,temperature=0.95,timeout=1200',
            'provider=openrouter,model=openrouter/free,temperature=0.95,timeout=1200',
            'provider=llamacpp,base_url=http://127.0.0.1:1234,model=qwen3-coder-next-80b,temperature=0.95,timeout=1200',
        ])
        if args.sql_parallelism is None and args.sql_sampler:
            args.sql_parallelism = len(args.sql_sampler)
        if args.judge_parallelism is None and args.judge_sampler:
            args.judge_parallelism = 1
    elif args.multi_endpoint_profile == 'zai-pony-alpha-2':
        def _set_if_empty(field: str, value: object) -> None:
            current = getattr(args, field)
            if current is None or current == [] or current == "":
                setattr(args, field, value)

        _set_if_empty('provider', 'zai')
        _set_if_empty('provider_base_url', 'https://api.z.ai/api/paas/v4')
        _set_if_empty('up_provider', 'zai')
        _set_if_empty('up_base_url', 'https://api.z.ai/api/paas/v4')
        _set_if_empty('up_model', 'pony-alpha-2')
        _set_if_empty('judge_provider', 'zai')
        _set_if_empty('judge_base_url', 'https://api.z.ai/api/paas/v4')
        _set_if_empty('judge_model', 'pony-alpha-2')
        _set_if_empty('sql_model', 'pony-alpha-2')
        _set_if_empty('temperature', 1.0)
        _set_if_empty('up_temperature', 1.0)
        _set_if_empty('judge_temperature', 0.5)
        _set_if_empty('writer_timeout', 1800)
        _set_if_empty('up_timeout', 1800)
        _set_if_empty('judge_timeout', 900)
    elif args.multi_endpoint_profile == 'zai-glm-4.7-anthropic':
        def _set_if_empty(field: str, value: object) -> None:
            current = getattr(args, field)
            if current is None or current == [] or current == "":
                setattr(args, field, value)

        anthropic_base_url = os.getenv('ZAI_ANTHROPIC_BASE_URL', 'https://api.z.ai/api/anthropic')
        _set_if_empty('provider', 'zai-anthropic')
        _set_if_empty('provider_base_url', anthropic_base_url)
        _set_if_empty('up_provider', 'zai-anthropic')
        _set_if_empty('up_base_url', anthropic_base_url)
        _set_if_empty('up_model', 'glm-4.7')
        _set_if_empty('judge_provider', 'zai-anthropic')
        _set_if_empty('judge_base_url', anthropic_base_url)
        _set_if_empty('judge_model', 'glm-4.7')
        _set_if_empty('sql_model', 'glm-4.7')
        _set_if_empty('temperature', 1.0)
        _set_if_empty('up_temperature', 1.0)
        _set_if_empty('judge_temperature', 0.5)
        _set_if_empty('writer_timeout', 1800)
        _set_if_empty('up_timeout', 1800)
        _set_if_empty('judge_timeout', 900)
        _set_if_empty('quota_fallback_provider', 'llamacpp')
        _set_if_empty('quota_fallback_base_url', 'http://192.168.1.251:8081')
        _set_if_empty('quota_fallback_model', 'Qwen3.5-35B-A3B')
    elif args.multi_endpoint_profile in {'zai-glm47-glm5-local', 'zai-glm47-then-glm5-then-local'}:
        def _set_if_empty(field: str, value: object) -> None:
            current = getattr(args, field)
            if current is None or current == [] or current == "":
                setattr(args, field, value)

        anthropic_base_url = os.getenv('ZAI_ANTHROPIC_BASE_URL', 'https://api.z.ai/api/anthropic')
        zai_chat_base_url = os.getenv('ZAI_BASE_URL', 'https://api.z.ai/api/paas/v4')
        _set_if_empty('provider', 'zai-anthropic')
        _set_if_empty('provider_base_url', anthropic_base_url)
        _set_if_empty('up_provider', 'zai-anthropic')
        _set_if_empty('up_base_url', anthropic_base_url)
        _set_if_empty('up_model', 'glm-4.7')
        _set_if_empty('judge_provider', 'zai-anthropic')
        _set_if_empty('judge_base_url', anthropic_base_url)
        _set_if_empty('judge_model', 'glm-4.7')
        _set_if_empty('sql_model', 'glm-4.7')
        _set_if_empty('temperature', 1.0)
        _set_if_empty('up_temperature', 1.0)
        _set_if_empty('judge_temperature', 0.5)
        _set_if_empty('writer_timeout', 1800)
        _set_if_empty('up_timeout', 1800)
        _set_if_empty('judge_timeout', 900)
        _set_if_empty('quota_fallback_provider', 'zai')
        _set_if_empty('quota_fallback_base_url', zai_chat_base_url)
        _set_if_empty('quota_fallback_model', 'glm-5-turbo')
        _set_if_empty('quota_fallback_provider_2', 'llamacpp')
        _set_if_empty('quota_fallback_base_url_2', 'http://192.168.1.251:8081')
        _set_if_empty('quota_fallback_model_2', 'Qwen3.5-35B-A3B')
    elif args.multi_endpoint_profile == 'opencode-go-dsv4-flash':
        def _set_if_empty(field: str, value: object) -> None:
            current = getattr(args, field)
            if current is None or current == [] or current == "":
                setattr(args, field, value)

        opencode_go_key = os.getenv('OPENCODE_GO_LJ_API_KEY', os.getenv('OPENCODE_GO_API_KEY', ''))
        opencode_go_base = os.getenv('OPENCODE_GO_BASE_URL', 'https://opencode.ai/zen/go/v1')
        _set_if_empty('provider', 'openai')
        _set_if_empty('provider_api_key', opencode_go_key)
        _set_if_empty('provider_base_url', opencode_go_base)
        _set_if_empty('up_provider', 'openai')
        _set_if_empty('up_api_key', opencode_go_key)
        _set_if_empty('up_base_url', opencode_go_base)
        _set_if_empty('up_model', 'deepseek-v4-flash')
        _set_if_empty('judge_provider', 'openai')
        _set_if_empty('judge_api_key', opencode_go_key)
        _set_if_empty('judge_base_url', opencode_go_base)
        _set_if_empty('judge_model', 'deepseek-v4-flash')
        _set_if_empty('sql_model', 'deepseek-v4-flash')
        _set_if_empty('temperature', 0.2)
        _set_if_empty('up_temperature', 0.2)
        _set_if_empty('judge_temperature', 0.5)
        _set_if_empty('writer_timeout', 1200)
        _set_if_empty('up_timeout', 1200)
        _set_if_empty('judge_timeout', 1200)
        _set_if_empty('sql_max_tokens', 4000)

    provider = args.provider
    if provider is None:
        env_provider = (os.getenv('TEXT2SQL_PROVIDER') or '').strip().lower()
        if env_provider:
            provider = env_provider
            if provider not in provider_choices:
                LOGGER.error("Invalid TEXT2SQL_PROVIDER=%r. Choose a provider explicitly.", provider)
                LOG_LINES(logging.INFO, "Example:")
                LOG_BLOCK(
                    'uv run python src/db_llm_query.py --provider llamacpp --sql-model minimax-m2.1 '
                    '-q \"get the smiles and chembl_id for kinase inhibitors\"'
                )
                LOG_BLOCK(parser.format_help())
                return
        else:
            if args.no_provider:
                provider = 'local'
            else:
                LOGGER.error("No provider specified. Use --provider to select one.")
                LOG_LINES(logging.INFO, "Example:")
                LOG_BLOCK(
                    'uv run python src/db_llm_query.py --provider llamacpp --sql-model minimax-m2.1 '
                    '-q \"get the smiles and chembl_id for kinase inhibitors\"'
                )
                LOG_BLOCK(parser.format_help())
                return
    if args.no_provider:
        provider = 'local'
    if provider == 'auto':
        provider = resolve_auto_provider(args.sql_model or args.judge_model)

    if args.sql_model_list is None and args.sql_model is None:
        args.sql_model_list = 'expensive'

    def _parse_history_window_arg(value: Optional[str]) -> Optional[int]:
        if value is None:
            return None
        text = str(value).strip().lower()
        if text in {"all", "*"}:
            return None
        try:
            parsed = int(text)
        except Exception as exc:
            raise ValueError(f"Invalid history window value: {value!r}") from exc
        if parsed < 0:
            raise ValueError(f"History window must be >= 0, got {parsed}")
        return parsed

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
        LOGGER.info("Run label: %s", run_id)

    if isinstance(args.memory_json_path, str):
        mem_path = args.memory_json_path.strip()
        if mem_path.lower() in {"", "none", "off", "false"}:
            args.memory_json_path = None
        else:
            args.memory_json_path = mem_path

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

    history_window_up_sql = _parse_history_window_arg(args.history_window_up_sql)
    judge_history_window = int(args.judge_history_window)
    if args.history_window is not None:
        legacy = _parse_history_window_arg(args.history_window)
        if legacy is None:
            history_window_up_sql = None
            judge_history_window = 10**9
        else:
            history_window_up_sql = legacy
            judge_history_window = max(1, legacy)
        LOGGER.warning(
            "Using deprecated --history-window=%s; set --history-window-up-sql and --judge-history-window instead.",
            args.history_window,
        )

    llm = ChEMBLLLMQuery(
        db_path=args.db_path,
        provider=provider,
        up_provider=args.up_provider,
        up_model=args.up_model,
        up_base_url=args.up_base_url,
        sql_model=args.sql_model,
        sql_model_list=args.sql_model_list,
        sql_model_cycle=args.sql_model_cycle,
        judge_model=args.judge_model,
        judge_model_list=args.judge_model_list,
        judge_model_cycle=args.judge_model_cycle,
        judge_provider=args.judge_provider,
        judge_base_url=args.judge_base_url,
        sql_samplers=args.sql_sampler,
        judge_samplers=args.judge_sampler,
        sql_parallelism=args.sql_parallelism,
        judge_parallelism=args.judge_parallelism,
        provider_base_url=args.provider_base_url,
        verbose=args.verbose,
        max_retries=args.max_retries,
        timeout=args.timeout,
        writer_timeout=args.writer_timeout,
        judge_timeout=args.judge_timeout,
        history_window_up_sql=history_window_up_sql,
        judge_history_window=judge_history_window,
        judge_score_threshold=args.judge_score_threshold,
        judge_yes_score_threshold=args.judge_yes_score_threshold,
        judge_no_override_threshold=args.judge_no_override_threshold,
        judge_call_retries=args.judge_call_retries,
        judge_max_tokens=args.judge_max_tokens,
        schema_docs_path=args.schema_docs_path,
        schema_sample_rows=args.schema_sample_rows,
        schema_max_cell_len=args.schema_max_cell_len,
        prompt_pack_path=args.prompt_pack_path,
        prompt_hints_path=args.prompt_hints_path,
        min_context=args.min_context,
        save_intermediate=args.save_intermediate,
        intermediate_dir=args.intermediate_dir,
        output_base=args.output_base,
        run_id=run_id,
        filter_profile=args.filter_profile,
        strip_unrequested_limit=args.strip_unrequested_limit,
        judge_context_limit=args.judge_context_limit,
        sql_temperature=args.temperature,
        prompt_writer_temperature=args.temperature,
        judge_temperature=args.judge_temperature,
        up_temperature=args.up_temperature,
        up_timeout=args.up_timeout,
        provider_sleep=args.provider_sleep,
        provider_retry_backoff=args.provider_retry_backoff,
        local_enable_thinking=args.local_enable_thinking,
        local_reasoning_budget_tokens=args.local_reasoning_budget_tokens,
        local_reasoning_budget_message=args.local_reasoning_budget_message,
        memory_json_path=args.memory_json_path,
        quota_fallback_provider=args.quota_fallback_provider,
        quota_fallback_base_url=args.quota_fallback_base_url,
        quota_fallback_model=args.quota_fallback_model,
        quota_fallback_provider_2=args.quota_fallback_provider_2,
        quota_fallback_base_url_2=args.quota_fallback_base_url_2,
        quota_fallback_model_2=args.quota_fallback_model_2,
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
                LOG_LINES(logging.INFO, "\n".join(["", "=" * 20, "Results (JSON)", "=" * 20]))
                LOG_BLOCK(json.dumps(result.to_dicts(), indent=2))
                LOG_LINES(logging.INFO, "\n".join(["=" * 20, ""]))
            elif args.format == 'csv':
                if not args.auto:
                    if args.output_file:
                        output_file = args.output_file
                    elif run_id:
                        output_file = f"{args.output_base}_{run_id}.csv"
                    else:
                        output_file = f"{args.output_base}.csv"
                    result.write_csv(output_file)
                    LOGGER.info("Saved to: %s", output_file)
            else:
                LOG_LINES(logging.INFO, "\n".join(["", "=" * 20, "Results", "=" * 20]))
                LOG_BLOCK(str(result))
                LOG_LINES(logging.INFO, "\n".join(["=" * 20, ""]))

    except KeyboardInterrupt:
        LOGGER.warning("Interrupted by user")
        sys.exit(1)
    except Exception as e:
        LOGGER.error("Error: %s", e)
        sys.exit(1)

if __name__ == '__main__':
    main()
