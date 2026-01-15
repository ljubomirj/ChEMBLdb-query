#!/usr/bin/env python3
"""
Minimal .env loader (no external dependencies).
"""

import os
import logging
from pathlib import Path
from typing import Iterable, Optional

logger = logging.getLogger(__name__)

_ENV_LOADED = False


def _parse_env_line(line: str) -> Optional[tuple[str, str]]:
    stripped = line.strip()
    if not stripped or stripped.startswith('#'):
        return None
    if stripped.startswith('export '):
        stripped = stripped[len('export '):].lstrip()
    if '=' not in stripped:
        return None
    key, value = stripped.split('=', 1)
    key = key.strip()
    if not key:
        return None
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        value = value[1:-1]
    return key, value


def _iter_env_paths(paths: Optional[Iterable[Path]]) -> list[Path]:
    if paths is not None:
        return [Path(p) for p in paths]

    cwd = Path.cwd()
    repo_root = Path(__file__).resolve().parents[2]
    candidates = [cwd / '.env']
    if repo_root != cwd:
        candidates.append(repo_root / '.env')
    return candidates


def load_dotenv_once(paths: Optional[Iterable[Path]] = None, *, override: bool = False) -> None:
    """
    Load key/value pairs from .env files into os.environ (once).

    The loader is intentionally minimal: KEY=VALUE lines, optional quotes, and
    'export KEY=VALUE' are supported. Existing environment variables are not
    overwritten unless override=True.
    """
    global _ENV_LOADED
    if _ENV_LOADED:
        return

    for path in _iter_env_paths(paths):
        try:
            if not path.is_file():
                continue
            for line in path.read_text(encoding='utf-8').splitlines():
                parsed = _parse_env_line(line)
                if not parsed:
                    continue
                key, value = parsed
                if not override and key in os.environ:
                    continue
                os.environ[key] = value
        except Exception:
            logger.warning(f"Failed to load env file: {path}", exc_info=True)

    _ENV_LOADED = True
