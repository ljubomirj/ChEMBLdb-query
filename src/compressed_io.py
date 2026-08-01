from __future__ import annotations

import io
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Sequence

import polars as pl
import zstandard as zstd


ZSTD_SUFFIXES: tuple[str, ...] = (".zst", ".zstd")
READ_CHUNK_SIZE = 1024 * 1024


def zstd_path(path: Path, *, suffix: str = ".zst") -> Path:
    return path.with_name(path.name + suffix)


def strip_compression_suffix(path: Path) -> Path:
    if path.suffix.lower() not in ZSTD_SUFFIXES:
        return path
    return path.with_name(path.name[: -len(path.suffix)])


def append_target_path(path: Path) -> Path:
    return strip_compression_suffix(path)


def read_candidates(path: Path, *, prefer_compressed: bool = True) -> list[Path]:
    if path.suffix.lower() in ZSTD_SUFFIXES:
        candidates = [path, strip_compression_suffix(path)]
    else:
        compressed = [zstd_path(path, suffix=".zst"), zstd_path(path, suffix=".zstd")]
        candidates = [*compressed, path] if prefer_compressed else [path, *compressed]
    seen: set[Path] = set()
    ordered: list[Path] = []
    for candidate in candidates:
        if candidate not in seen:
            seen.add(candidate)
            ordered.append(candidate)
    return ordered


def resolve_read_path(path: Path, *, prefer_compressed: bool = True) -> Path:
    for candidate in read_candidates(path, prefer_compressed=prefer_compressed):
        if candidate.exists():
            return candidate
    return path


def read_text_maybe_compressed(path: Path, *, encoding: str = "utf-8", errors: str = "replace", prefer_compressed: bool = True) -> str:
    resolved = resolve_read_path(path, prefer_compressed=prefer_compressed)
    if resolved.suffix.lower() in ZSTD_SUFFIXES:
        with resolved.open("rb") as compressed:
            dctx = zstd.ZstdDecompressor()
            with dctx.stream_reader(compressed) as reader:
                text_reader = io.TextIOWrapper(reader, encoding=encoding, errors=errors)
                try:
                    return text_reader.read()
                finally:
                    text_reader.detach()
    return resolved.read_text(encoding=encoding, errors=errors)


@contextmanager
def open_text_maybe_compressed(path: Path, *, encoding: str = "utf-8", errors: str = "replace") -> Iterator[io.TextIOBase]:
    resolved = resolve_read_path(path)
    if resolved.suffix.lower() in ZSTD_SUFFIXES:
        with resolved.open("rb") as compressed:
            dctx = zstd.ZstdDecompressor()
            with dctx.stream_reader(compressed) as reader:
                text_reader = io.TextIOWrapper(reader, encoding=encoding, errors=errors)
                try:
                    yield text_reader
                finally:
                    text_reader.detach()
        return
    with resolved.open("r", encoding=encoding, errors=errors) as handle:
        yield handle


def read_json_maybe_compressed(path: Path, *, prefer_compressed: bool = True) -> Any:
    return json.loads(read_text_maybe_compressed(path, prefer_compressed=prefer_compressed))


def read_csv_maybe_compressed(path: Path, *, infer_schema_length: int = 10_000, schema_overrides: dict[str, pl.DataType] | None = None, prefer_compressed: bool = True) -> pl.DataFrame:
    resolved = resolve_read_path(path, prefer_compressed=prefer_compressed)
    if resolved.suffix.lower() in ZSTD_SUFFIXES:
        with resolved.open("rb") as compressed:
            dctx = zstd.ZstdDecompressor()
            with dctx.stream_reader(compressed) as reader:
                return pl.read_csv(reader, infer_schema_length=infer_schema_length, schema_overrides=schema_overrides)
    return pl.read_csv(resolved, infer_schema_length=infer_schema_length, schema_overrides=schema_overrides)


def count_csv_rows_maybe_compressed(path: Path, *, prefer_compressed: bool = True) -> int:
    resolved = resolve_read_path(path, prefer_compressed=prefer_compressed)
    newline_count = 0
    if resolved.suffix.lower() in ZSTD_SUFFIXES:
        with resolved.open("rb") as compressed:
            dctx = zstd.ZstdDecompressor()
            with dctx.stream_reader(compressed) as reader:
                while True:
                    chunk = reader.read(READ_CHUNK_SIZE)
                    if not chunk:
                        break
                    newline_count += chunk.count(b"\n")
        return max(0, newline_count - 1)

    with resolved.open("rb") as handle:
        while True:
            chunk = handle.read(READ_CHUNK_SIZE)
            if not chunk:
                break
            newline_count += chunk.count(b"\n")
    return max(0, newline_count - 1)


def rotated_jsonl_archives(path: Path) -> list[Path]:
    plain = append_target_path(path)
    if plain.suffix.lower() != ".jsonl":
        return []
    base_name = plain.name[: -len(".jsonl")]
    candidates: list[Path] = []
    for suffix in ZSTD_SUFFIXES:
        candidates.extend(sorted(plain.parent.glob(f"{base_name}.*.jsonl{suffix}")))
    return candidates


def iter_jsonl_records(path: Path, *, include_rotated: bool = False, prefer_compressed: bool = False) -> Iterator[dict[str, Any]]:
    paths: list[Path] = []
    if include_rotated:
        paths.extend(rotated_jsonl_archives(path))
    resolved = resolve_read_path(path, prefer_compressed=prefer_compressed)
    if resolved.exists():
        paths.append(resolved)
    for record_path in paths:
        with open_text_maybe_compressed(record_path) as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                parsed = json.loads(line)
                if isinstance(parsed, dict):
                    yield parsed


def summarize_read_targets(path: Path, *, include_rotated: bool = False, prefer_compressed: bool = True) -> dict[str, Sequence[str]]:
    payload: dict[str, Sequence[str]] = {"candidates": [str(candidate) for candidate in read_candidates(path, prefer_compressed=prefer_compressed)]}
    payload["resolved"] = [str(resolve_read_path(path, prefer_compressed=prefer_compressed))]
    if include_rotated:
        payload["rotated_archives"] = [str(candidate) for candidate in rotated_jsonl_archives(path)]
    return payload
