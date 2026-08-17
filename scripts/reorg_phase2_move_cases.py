#!/usr/bin/env python3
"""Phase 2 of the data re-org: move manifests + fixtures into the cases/ layout.

Target per case:
    cases/v5.1010/cases/<case_id>/manifest.json
    cases/v5.1010/cases/<case_id>/provenance/original/   (whole fixture dir, byte-for-byte)
    cases/v5.1010/cases/<case_id>/tasks/                 (canonical aliases, optional)

Every source path is symlink-bridged from its old location (symlink bridge mode).

DEFAULT IS DRY-RUN. Pass --execute to perform the moves.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MANIFEST_ROOT = REPO / "tests" / "v5_manifests_1010" / "web_scrape_hq"
DEST_ROOT = REPO / "cases" / "v5.1010" / "cases"

# task artifacts: canonical name -> possible source filenames in the fixture dir
TASK_MAP = {
    "uq_surface.txt": ["uq.txt"],
    "up_exec.txt": ["up_exec.txt"],
    "sql_gold.sql": ["sqlite.sql"],
    "res_gold.csv.zst": ["ground-truth.csv.zst"],
    "benchmark_spec_uq.txt": ["benchmark_spec_uq.txt"],
    "source_sql.sql": ["source.sql"],
    "documentation.txt": ["documentation.txt"],
    "metadata.json": ["metadata.json"],
}


def iter_manifests() -> list[Path]:
    """All manifest JSONs under MANIFEST_ROOT, including nested (case IDs with /)."""
    return sorted(p for p in MANIFEST_ROOT.rglob("*.json"))


def plan_case(manifest: Path, dry_run: bool) -> dict:
    data = json.loads(manifest.read_text())
    case_id = data["case_id"]
    safe_id = case_id.replace("/", "__")
    dest = DEST_ROOT / safe_id
    artifacts = data.get("artifacts", {})

    # collect unique fixture dirs referenced by this manifest
    fixture_dirs: set[Path] = set()
    for v in artifacts.values():
        if not isinstance(v, str) or not v.startswith("tests/fixtures/"):
            continue
        parts = v.split("/")
        # tests/fixtures/<wave>/<case>/<file>
        if len(parts) >= 4:
            fixture_dirs.add(REPO / "/".join(parts[:4]))

    return {
        "manifest": manifest,
        "case_id": case_id,
        "safe_id": safe_id,
        "dest": dest,
        "fixture_dirs": sorted(fixture_dirs),
        "n_artifact_refs": sum(1 for v in artifacts.values() if isinstance(v, str) and v.startswith("tests/fixtures/")),
    }


def move_and_bridge(src: Path, dst: Path) -> None:
    """Move src to dst (byte-for-byte) and leave a relative symlink at src."""
    if dst.exists():
        raise FileExistsError(f"{dst} already exists")
    dst.parent.mkdir(parents=True, exist_ok=True)
    os.rename(src, dst)
    rel = os.path.relpath(dst, src.parent)
    src.symlink_to(rel)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true", help="perform the moves (default: dry run)")
    ap.add_argument("--with-task-aliases", action="store_true", help="also create tasks/ aliases")
    args = ap.parse_args()

    manifests = iter_manifests()
    print(f"manifests: {len(manifests)}")

    if not args.execute:
        # dry-run: summarize the plan
        n_fix = 0
        for m in manifests:
            plan = plan_case(m, dry_run=True)
            print(f"  {plan['case_id'][:60]:60s} fixtures={len(plan['fixture_dirs'])} refs={plan['n_artifact_refs']}")
            n_fix += len(plan["fixture_dirs"])
        print(f"\nTOTAL fixture dirs to move: {n_fix}")
        print("RUN WITH --execute TO PERFORM")
        return

    # execute
    for m in manifests:
        plan = plan_case(m, dry_run=False)
        dest = plan["dest"]
        # 1. manifest
        move_and_bridge(plan["manifest"], dest / "manifest.json")
        # 2. fixture dirs -> provenance/original/<wave>-<case>
        for fd in plan["fixture_dirs"]:
            wave = fd.parent.name
            case = fd.name
            orig_dst = dest / "provenance" / "original" / f"{wave}--{case}"
            move_and_bridge(fd, orig_dst)
            if args.with_task_aliases:
                task_dir = dest / "tasks"
                for canon, sources in TASK_MAP.items():
                    for s in sources:
                        src = orig_dst / s
                        if src.exists():
                            if not (task_dir / canon).exists():
                                task_dir.mkdir(parents=True, exist_ok=True)
                                os.symlink(os.path.relpath(src, task_dir), task_dir / canon)
                            break
        # 3. rewrite manifest artifact paths
        #    old: tests/fixtures/<wave>/<case>/<file> -> cases/v5.1010/cases/<safe_id>/provenance/original/<wave>--<case>/<file>
        #    old: tests/fixtures_1010_overrides/<case>/<file> -> cases/v5.1010/cases/<safe_id>/provenance/original/overrides--<case>/<file>
        new_manifest = dest / "manifest.json"
        data = json.loads(new_manifest.read_text())
        changed = 0
        for k, v in list(data.get("artifacts", {}).items()):
            if not isinstance(v, str):
                continue
            if v.startswith("tests/fixtures/"):
                parts = v.split("/")
                wave, case, file = parts[2], parts[3], "/".join(parts[4:])
                new = f"cases/v5.1010/cases/{plan['safe_id']}/provenance/original/{wave}--{case}/{file}"
                data["artifacts"][k] = new
                changed += 1
            elif v.startswith("tests/fixtures_1010_overrides/"):
                parts = v.split("/")
                case, file = parts[2], "/".join(parts[3:])
                # overrides fixture dir may not exist under provenance; find it
                ov_src = REPO / "tests" / "fixtures_1010_overrides" / case
                new = f"cases/v5.1010/cases/{plan['safe_id']}/provenance/original/overrides--{case}/{file}"
                if ov_src.exists() and not (dest / "provenance" / "original" / f"overrides--{case}").exists():
                    move_and_bridge(ov_src, dest / "provenance" / "original" / f"overrides--{case}")
                data["artifacts"][k] = new
                changed += 1
        if changed:
            new_manifest.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        print(f"  {plan['case_id'][:60]:60s} -> {dest.relative_to(REPO)}  (rewrote {changed} paths)")

    print("DONE")


if __name__ == "__main__":
    main()
