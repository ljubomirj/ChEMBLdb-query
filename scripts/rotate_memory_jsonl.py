#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

import zstandard as zstd

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from compressed_io import append_target_path, rotated_jsonl_archives, summarize_read_targets


def main() -> None:
    parser = argparse.ArgumentParser(description="Create explicit .jsonl.zst archives for the accepted-run memory log.")
    parser.add_argument(
        "--memory-path",
        default="MEMORY-ChEMBLdb-query.jsonl",
        help="Live JSONL memory file. If a .zst path is passed, the plain .jsonl append target is used.",
    )
    parser.add_argument(
        "--stamp",
        default=None,
        help="Archive stamp. Defaults to current UTC time as YYYYmmdd_HHMMSS.",
    )
    parser.add_argument("--compression-level", type=int, default=6, help="Zstandard compression level.")
    parser.add_argument(
        "--min-size-mb",
        type=float,
        default=1.0,
        help="Skip archive creation if the live file is smaller than this many MiB unless --force is set.",
    )
    parser.add_argument("--force", action="store_true", help="Archive even if the live file is smaller than --min-size-mb.")
    parser.add_argument(
        "--replace-with-empty-current",
        action="store_true",
        help="Move the live file to a stamped plain archive and create a new empty current file. This does not delete the stamped plain archive or the compressed archive.",
    )
    parser.add_argument("--print-summary", action="store_true", help="Pretty-print the JSON summary.")
    args = parser.parse_args()

    memory_path = append_target_path(Path(args.memory_path))
    if memory_path.suffix.lower() != ".jsonl":
        raise ValueError(f"--memory-path must resolve to a .jsonl file, got {memory_path}")
    if not memory_path.exists():
        raise FileNotFoundError(memory_path)

    size_bytes = memory_path.stat().st_size
    min_size_bytes = int(args.min_size_mb * 1024 * 1024)
    stamp = args.stamp or time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    archive_plain = memory_path.with_name(f"{memory_path.name[:-len('.jsonl')]}.{stamp}.jsonl")
    archive_zst = archive_plain.with_name(archive_plain.name + ".zst")

    summary: dict[str, object] = {
        "memory_path": str(memory_path.resolve()),
        "size_bytes": size_bytes,
        "size_mb": round(size_bytes / (1024 * 1024), 3),
        "archive_plain": str(archive_plain.resolve()),
        "archive_zst": str(archive_zst.resolve()),
        "created_archive": False,
        "replaced_with_empty_current": False,
        "existing_rotated_archives": [str(path.resolve()) for path in rotated_jsonl_archives(memory_path)],
        "read_targets_after": None,
    }

    if not args.force and size_bytes < min_size_bytes:
        summary["skipped"] = f"live file is smaller than --min-size-mb ({args.min_size_mb})"
        _emit(summary, args.print_summary)
        return

    if archive_zst.exists():
        raise FileExistsError(f"archive already exists: {archive_zst}")

    compressor = zstd.ZstdCompressor(level=args.compression_level)
    with memory_path.open("rb") as source, archive_zst.open("wb") as dest:
        compressor.copy_stream(source, dest)
    summary["created_archive"] = True

    if args.replace_with_empty_current:
        if archive_plain.exists():
            raise FileExistsError(f"plain archive already exists: {archive_plain}")
        shutil.move(str(memory_path), str(archive_plain))
        memory_path.write_text("", encoding="utf-8")
        summary["replaced_with_empty_current"] = True

    summary["read_targets_after"] = summarize_read_targets(memory_path, include_rotated=True, prefer_compressed=False)
    _emit(summary, args.print_summary)


def _emit(summary: dict[str, object], pretty: bool) -> None:
    if pretty:
        print(json.dumps(summary, indent=2))
    else:
        print(json.dumps(summary))


if __name__ == "__main__":
    main()
