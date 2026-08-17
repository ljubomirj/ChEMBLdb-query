#!/usr/bin/env python3
"""Phases 3-5 of the data re-org: splits, configs, runs — symlink-bridged moves.

Phase 3: experiments/case_splits_v5.1010*.json  -> cases/v5.1010/splits/
Phase 4: experiments/prompt_pack_v*.yaml        -> configs/prompt_packs/
Phase 5: experiments/evals/v5_forward_eval      -> runs/  (whole tree, one rename)

Every moved path keeps a relative symlink at its old location (symlink bridge)
so nothing breaks until the code path-fix pass is verified.

DEFAULT IS DRY-RUN. Pass --execute to perform the moves.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PHASES = {
    "splits": ("experiments/case_splits_v5.1010*.json", "cases/v5.1010/splits", False, False),
    "configs": ("experiments/prompt_pack_v*.yaml", "configs/prompt_packs", False, False),
    "runs": ("experiments/evals/v5_forward_eval", "runs", False, True),  # hoist children
}


def move_and_bridge(src: Path, dst: Path) -> None:
    if dst.exists():
        raise FileExistsError(f"{dst} already exists")
    dst.parent.mkdir(parents=True, exist_ok=True)
    os.rename(src, dst)
    rel = os.path.relpath(dst, src.parent)
    src.symlink_to(rel)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=list(PHASES), required=True)
    ap.add_argument("--execute", action="store_true", help="perform moves (default: dry run)")
    args = ap.parse_args()

    glob_pat, dest_str, whole_dir, hoist_children = PHASES[args.phase]
    dest = REPO / dest_str

    if hoist_children:
        src_root = REPO / glob_pat
        if not src_root.is_dir():
            print(f"source missing: {src_root}")
            sys.exit(1)
        items = sorted(p for p in src_root.iterdir())
    elif whole_dir:
        src = REPO / glob_pat
        if not src.exists():
            print(f"source missing: {src}")
            sys.exit(1)
        items = [src]
    else:
        items = sorted(REPO.glob(glob_pat))

    print(f"phase {args.phase}: {len(items)} items -> {dest_str}")
    if not args.execute:
        for it in items:
            print(f"  {it.relative_to(REPO)} -> {dest / it.name}")
        print("RUN WITH --execute TO PERFORM")
        return

    for it in items:
        dst = dest / it.name
        move_and_bridge(it, dst)
        print(f"  moved {it.relative_to(REPO)} -> {dst.relative_to(REPO)} (bridged)")
    print("DONE")

if __name__ == "__main__":
    main()
