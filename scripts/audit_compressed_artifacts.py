#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import zstandard as zstd

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from compressed_io import append_target_path, read_candidates, zstd_path


ALLOWED_BASE_SUFFIXES = (".csv", ".jsonl")
COMPRESSED_SUFFIXES = (".zst", ".zstd")
DEFAULT_EXCLUDE_DIRS = {".git", ".venv", "__pycache__", "node_modules"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit and optionally compress .csv/.jsonl artifacts with .zst sidecars.")
    parser.add_argument("--root", action="append", default=None, help="Root(s) to scan. May be passed multiple times.")
    parser.add_argument("--exclude-dir", action="append", default=None, help="Directory name to skip. May be passed multiple times.")
    parser.add_argument("--write-compressed-missing", action="store_true")
    parser.add_argument("--compression-level", type=int, default=6)
    parser.add_argument("--output-json", default=None)
    parser.add_argument("--print-summary", action="store_true")
    args = parser.parse_args()

    roots = [Path(value).resolve() for value in (args.root or ["."])]
    exclude_dirs = set(DEFAULT_EXCLUDE_DIRS)
    if args.exclude_dir:
        exclude_dirs.update(args.exclude_dir)

    groups = _collect_groups(roots, exclude_dirs=exclude_dirs)
    rows: list[dict[str, Any]] = []
    candidates_for_deletion: list[str] = []
    warnings: list[str] = []

    for base_path in sorted(groups):
        row, delete_candidates, row_warnings = _process_group(
            base_path,
            write_compressed_missing=args.write_compressed_missing,
            compression_level=args.compression_level,
        )
        rows.append(row)
        candidates_for_deletion.extend(delete_candidates)
        warnings.extend(row_warnings)

    payload = {
        "summary": {
            "roots": [str(root) for root in roots],
            "exclude_dirs": sorted(exclude_dirs),
            "n_groups": len(rows),
            "n_candidates_for_deletion": len(candidates_for_deletion),
            "n_warnings": len(warnings),
            "write_compressed_missing": bool(args.write_compressed_missing),
        },
        "candidates_for_deletion": sorted(set(candidates_for_deletion)),
        "warnings": warnings,
        "rows": rows,
    }
    if args.output_json:
        out_path = Path(args.output_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if args.print_summary:
        print(json.dumps(payload, indent=2))
    else:
        print(json.dumps(payload))


def _collect_groups(roots: list[Path], *, exclude_dirs: set[str]) -> set[Path]:
    groups: set[Path] = set()
    for root in roots:
        for current_root, dirnames, filenames in os.walk(root):
            dirnames[:] = [dirname for dirname in dirnames if dirname not in exclude_dirs]
            current_root_path = Path(current_root)
            for filename in filenames:
                path = current_root_path / filename
                suffix = path.suffix.lower()
                if suffix in COMPRESSED_SUFFIXES:
                    base = append_target_path(path)
                    if base.suffix.lower() in ALLOWED_BASE_SUFFIXES:
                        groups.add(base)
                    continue
                if suffix in ALLOWED_BASE_SUFFIXES:
                    groups.add(path)
    return groups


def _process_group(base_path: Path, *, write_compressed_missing: bool, compression_level: int) -> tuple[dict[str, Any], list[str], list[str]]:
    compressed_candidates = [candidate for candidate in read_candidates(base_path, prefer_compressed=True) if candidate.suffix.lower() in COMPRESSED_SUFFIXES and candidate.exists()]
    compressed_path = compressed_candidates[0] if compressed_candidates else None
    plain_exists = base_path.exists()
    compressed_exists = compressed_path is not None
    delete_candidates: list[str] = []
    warnings: list[str] = []
    action = "noop"
    compressed_written = None

    row: dict[str, Any] = {
        "base_path": str(base_path),
        "plain_exists": plain_exists,
        "compressed_path": str(compressed_path) if compressed_path else None,
        "compressed_exists": compressed_exists,
        "plain": _stat(base_path) if plain_exists else None,
        "compressed": _stat(compressed_path) if compressed_path else None,
    }

    if plain_exists and not compressed_exists:
        if write_compressed_missing:
            compressed_path = zstd_path(base_path)
            _compress_to_zst(base_path, compressed_path, compression_level=compression_level)
            compressed_written = str(compressed_path)
            action = "compressed_missing_plain"
            delete_candidates.append(str(base_path))
            row["compressed"] = _stat(compressed_path)
            row["compressed_exists"] = True
            row["compressed_path"] = str(compressed_path)
        else:
            action = "missing_compressed_sidecar"
    elif compressed_exists and not plain_exists:
        action = "compressed_only_ok"
    elif plain_exists and compressed_exists:
        if base_path.suffix.lower() == ".jsonl" and base_path.stat().st_size == 0:
            action = "empty_live_jsonl_kept_sidecar_deletable"
            delete_candidates.append(str(compressed_path))
        else:
            plain_mtime = base_path.stat().st_mtime
            compressed_mtime = compressed_path.stat().st_mtime
            if abs(plain_mtime - compressed_mtime) < 1e-6:
                if _plain_matches_compressed(base_path, compressed_path):
                    action = "same_mtime_identical_plain_deletable"
                    delete_candidates.append(str(base_path))
                else:
                    action = "same_mtime_but_different_warning"
                    warnings.append(_warning_line(base_path, compressed_path, "same mtime but content differs"))
            elif plain_mtime < compressed_mtime:
                action = "compressed_newer_plain_deletable"
                delete_candidates.append(str(base_path))
            else:
                action = "plain_newer_compressed_stale"
                delete_candidates.append(str(compressed_path))
                warnings.append(_warning_line(base_path, compressed_path, "plain file is newer; compressed sidecar is stale"))

    row["action"] = action
    row["compressed_written"] = compressed_written
    row["delete_candidates"] = delete_candidates
    row["warnings"] = row_warnings = warnings
    return row, delete_candidates, row_warnings


def _compress_to_zst(source: Path, dest: Path, *, compression_level: int) -> None:
    if dest.exists():
        raise FileExistsError(dest)
    compressor = zstd.ZstdCompressor(level=compression_level)
    with source.open("rb") as fin, dest.open("wb") as fout:
        compressor.copy_stream(fin, fout)


def _plain_matches_compressed(plain_path: Path, compressed_path: Path) -> bool:
    plain_bytes = plain_path.read_bytes()
    with compressed_path.open("rb") as compressed:
        dctx = zstd.ZstdDecompressor()
        with dctx.stream_reader(compressed) as reader:
            decompressed_bytes = reader.read()
    return plain_bytes == decompressed_bytes


def _stat(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    stat = path.stat()
    return {
        "path": str(path),
        "size_bytes": stat.st_size,
        "size_mb": round(stat.st_size / (1024 * 1024), 3),
        "mtime_epoch": stat.st_mtime,
    }


def _warning_line(plain_path: Path, compressed_path: Path, reason: str) -> str:
    return (
        f"{reason}: plain={plain_path} size={plain_path.stat().st_size}B "
        f"compressed={compressed_path} size={compressed_path.stat().st_size}B"
    )


if __name__ == "__main__":
    main()
