#!/usr/bin/env python3
"""
Update the master web_scrape_cases.json registry with rounds 10-13 cases.

This script combines all the individual round registries into the master registry.
"""

import json
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
CASES_DIR = BASE_DIR / "tests" / "cases"

# Round registries to merge into master
ROUND_REGISTRIES = [
    "web_scrape_cases.json",      # Original cases
    "web_scrape2_cases.json",     # Round 2
    "web_scrape3_cases.json",     # Round 3
    "web_scrape4_cases.json",     # Round 4
    "web_scrape5_cases.json",     # Round 5
    "web_scrape6_cases.json",     # Round 6
    "web_scrape7_cases.json",     # Round 7
    "web_scrape8_cases.json",     # Round 8
    "web_scrape9_cases.json",     # Round 9
    "web_scrape10_cases.json",    # Round 10 (NEW)
    "web_scrape11_cases.json",    # Round 11 (NEW)
    "web_scrape12_cases.json",    # Round 12 (NEW)
    "web_scrape13_cases.json",    # Round 13 (NEW)
]

def load_registry(filename):
    """Load a case registry file."""
    path = CASES_DIR / filename
    with open(path) as f:
        return json.load(f)

def save_registry(filename, cases):
    """Save a case registry file."""
    path = CASES_DIR / filename
    with open(path, 'w') as f:
        json.dump(cases, f, indent=2)

def main():
    """Update the master registry."""
    print("=" * 80)
    print("Updating master web_scrape_cases.json registry")
    print("=" * 80)

    # Load all round registries
    all_cases = []
    for registry_file in ROUND_REGISTRIES:
        cases = load_registry(registry_file)
        print(f"  Loaded {len(cases)} cases from {registry_file}")
        all_cases.extend(cases)

    # Deduplicate by case ID (keep first occurrence)
    seen_ids = set()
    unique_cases = []
    for case in all_cases:
        if case['id'] not in seen_ids:
            seen_ids.add(case['id'])
            unique_cases.append(case)

    if len(unique_cases) < len(all_cases):
        print(f"\n  Deduplicated: {len(all_cases)} -> {len(unique_cases)} cases")

    # Save master registry
    save_registry("web_scrape_cases.json", unique_cases)

    print(f"\n" + "=" * 80)
    print(f"Master registry updated!")
    print(f"  - Total cases: {len(unique_cases)}")
    print(f"  - Saved to: cases/registries/archive/web_scrape_cases.json")
    print("=" * 80)

    # Print breakdown by round
    print("\nBreakdown by round:")
    for registry_file in ROUND_REGISTRIES:
        cases = load_registry(registry_file)
        print(f"  {registry_file}: {len(cases)} cases")

if __name__ == "__main__":
    main()
