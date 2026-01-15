
# Repository Guidelines

This repo maintains contains a copy of the ChEMBLdb together with agentic scaffolding used to query the data using natural language.

## Global Safety & Workflow

- **Never delete files without explicit user permission.** No `rm -rf`, `git reset --hard`, `git clean -fd`, or any destructive DB commands unless the user confirms the exact command and scope in writing 
- When destructive action is ever approved: restate the exact command, await confirmation, then record user text + command + time in the session notes.
- **Learning loop (all repos):** see the copied global instructions below (from `~/.claude/CLAUDE.md`).
- Do not edit README.LJ, never change README.LJ never write into README.LJ. But feel free to read README.LJ at will.

## Global CLAUDE learning loop (copied from ~/.claude/CLAUDE.md)
* always create a .claude/LEARNINGS.md file if it's not there. It should be checked in and then in context for any claude code sessions.
* Log Every Friction Point: If a build fails, a test hangs, or a logic error occurs, document the root cause and the specific fix before proceeding.
* Mandatory Update on Intervention: If you stop to ask for guidance, or if I provide a correction, you must update LEARNINGS.md with the "Signpost" (the specific instruction or realization) that prevented you from succeeding independently.
* Iterate Toward Autonomy: Use the existing log to avoid repeating mistakes. Your goal is to reach a state where you can complete the objective without manual triggers.

## Project-Specific Guidance

- There are agentic dirs .codex and .claude where agent related info is kept; some of it is linked with soft links, where possible e.g. CLAUDE.md and AGENTS.md, or the skills/ directory ahared between .clayde and .codex.
- Dependencies: Python, `openai`. Use `uv` + venv; **only Python 3.13**; **never use pip** use only uv at all times.
- Permissions: repository writing and network fetches are pre-approved; don’t worry about damaging data (under git).
- Tooling choice: use `ast-grep` when structure matters; `rg` for fast text search.

## Coding Style & Naming Conventions
- Python 3; prefer standard library and small, single‑purpose scripts.
- 4‑space indentation; `snake_case` for files/functions; constants `ALL_CAPS`.
- Keep CLI pattern: `if __name__ == '__main__': main()`.
- Use `uv run python script.py` to auto-install dependencies and run scripts.
- Dependencies specified in `pyproject.toml` (core, api, data, dev groups).

## Testing Guidelines
- No formal suite yet—add smoke checks and keep outputs deterministic.
- If adding tests, use `pytest` under `tests/` and rely on files in `data/` (no live network).

## Commit & Pull Request Guidelines
- Commits: short, imperative, lowercase
- PRs include: purpose, commands run, affected files, before/after snippets (first 5 lines), and anything else new. 
- There will be files - backups, temporary files, saves for various reasons - that are not in git version control. Usuually they are unimportant can be safely ignored. If anything is important, it will be in version control in git.

## Quick Reminders
- Maintain `.claude/LEARNINGS.md` per repo and log friction/signposts.
- For data work: Polars + DuckDB + Arrow; no pandas, never use pandas, always prefer polars. 
- Never silent exceptions - either catch and handle, or do not catch, but never sink exceptions.
- Use `src/db_llm_query.py` as the version-independent CLI wrapper; prompt hints live in `doc/chembl_prompt_hints.md`.
- Default runs use the `expensive` SQL model list and enforce `--min-context=300000`; use `--run-label` to stamp a single ID across logs and outputs.

## Agent Skills

This project includes Agent (e.g. Codex, Claude Code) skills that provide project-specific knowledge:

### database-schema Skill
- **Location**: `.codex/skills/chembl-database/
- **Purpose**: Provides comprehensive ChEMBLdb schema knowledge, query patterns, and best practices
- **Auto-invokes**: When database, SQL, or query-related topics are mentioned
- **Benefits**:
  - Instant access to schema without looking up documentation
  - Best practices for querying 
  - Common query patterns and examples

### db-llm-query-chembl Skill
- **Location**: `.codex/skills/db-llm-query-chembl/`
- **Purpose**: Run and iterate ChEMBL natural-language queries via `src/db_llm_query.py`, including outer-loop refinement until results look correct
- **Auto-invokes**: When asked to run or refine `db_llm_query.py` loops, inspect outputs/logs, or orchestrate ChEMBL LLM query runs
- **Benefits**:
  - Repeatable run labeling with consistent outputs
  - Prompt refinement guidance and validation checklist
  - Command templates and troubleshooting tips
