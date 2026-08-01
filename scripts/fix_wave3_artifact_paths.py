#!/usr/bin/env python3
"""Fix remaining artifact paths with commas/brackets in wave3 manifests."""
import json
from pathlib import Path

MANIFEST_DIR = Path("tests/v5_manifests/web_scrape_hq")
BAD_CHARS = ["[", "]", ","]


def clean(name: str) -> str:
    for ch in BAD_CHARS:
        name = name.replace(ch, "_")
    return name


def main() -> None:
    fixed = 0
    for mf_path in sorted(MANIFEST_DIR.glob("*.json")):
        data = json.load(open(mf_path))
        arts = data.get("artifacts", {})
        needs_fix = False

        for key, val in list(arts.items()):
            if val and isinstance(val, str) and any(ch in val for ch in BAD_CHARS):
                arts[key] = clean(val)
                needs_fix = True

        if needs_fix:
            data["case_id"] = clean(data.get("case_id", ""))
            json.dump(data, open(mf_path, "w"), indent=2)
            fixed += 1
            print(f"  Fixed: {mf_path.name}")

    print(f"\nFixed {fixed} manifests")


if __name__ == "__main__":
    main()
