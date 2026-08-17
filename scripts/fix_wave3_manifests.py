#!/usr/bin/env python3
"""Fix wave3 manifests and registry entries that contain brackets or commas in paths."""
import json
from pathlib import Path

MANIFEST_DIR = Path("tests/v5_manifests/web_scrape_hq")
REGISTRY_PATH = Path("cases/registries/archive/web_scrape_hq_cases.json")

BAD_CHARS = ["[", "]", ","]


def clean_name(name: str) -> str:
    for ch in BAD_CHARS:
        name = name.replace(ch, "_")
    return name


def main() -> None:
    # Fix manifests
    fixed_count = 0
    to_rename = []

    for mf_path in sorted(MANIFEST_DIR.glob("*.json")):
        data = json.load(open(mf_path))
        arts = data.get("artifacts", {})
        case_id = data.get("case_id", "")

        needs_fix = False
        for key in ["uq_surface", "up_exec", "sql_gold", "res_gold", "source_sql", "documentation", "uq_benchmark_spec"]:
            val = arts.get(key) or ""
            if val and any(ch in val for ch in BAD_CHARS):
                arts[key] = clean_name(val)
                needs_fix = True

        if not needs_fix:
            continue

        # Fix case_id
        new_id = clean_name(case_id)
        data["case_id"] = new_id

        json.dump(data, open(mf_path, "w"), indent=2)

        fixed_count += 1

        if new_id != case_id:
            new_path = MANIFEST_DIR / f"{new_id}.json"
            mf_path.rename(new_path)
            to_rename.append((case_id, new_id))
            print(f"  Renamed manifest: {case_id} -> {new_id}")

        else:
            print(f"  Fixed in-place: {case_id}")

    # Fix registry
    registry = json.load(open(REGISTRY_PATH))
    reg_fixed = 0
    for entry in registry:
        eid = entry["id"]
        new_id = clean_name(eid)
        if new_id != eid:
            entry["id"] = new_id
            for path_key in ["source_sql_path", "sqlite_sql_path", "result_csv_path", "log_path", "benchmark_spec_uq_path"]:
                old_val = entry.get(path_key, "")
                if old_val and any(ch in old_val for ch in BAD_CHARS):
                    entry[path_key] = clean_name(old_val)
            reg_fixed += 1
    if reg_fixed:
        json.dump(registry, open(REGISTRY_PATH, "w"), indent=2)
        print(f"Fixed {reg_fixed} registry entries")

    else:
        print("No registry fixes needed")

    print(f"\nFixed {fixed_count} manifests, {len(to_rename)} renamed")


    if to_rename:
        print(f"Renamed manifests: {to_rename[:5]}")


if __name__ == "__main__":
    main()
