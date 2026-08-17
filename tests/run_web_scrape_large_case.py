#!/usr/bin/env python3
"""Run one or more large promoted web-scrape cases."""

from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.run_web_scrape_case import main as shared_main


if __name__ == "__main__":
    sys.argv[1:1] = ["--cases", "cases/registries/archive/web_scrape_large_cases.json"]
    shared_main()
