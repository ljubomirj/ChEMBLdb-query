from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from compressed_io import read_json_maybe_compressed, read_text_maybe_compressed

from .artifacts import V5CaseManifest, V5PromptPack


def load_prompt_pack(path: str | Path) -> V5PromptPack:
    path = Path(path)
    data = yaml.safe_load(read_text_maybe_compressed(path)) or {}
    prompt_pack = V5PromptPack.from_dict(_require_dict(data, "prompt pack"))
    errors = prompt_pack.validate(_project_root(path))
    if errors:
        raise ValueError(f"invalid v5 prompt pack at {path}: " + "; ".join(errors))
    return prompt_pack


def save_prompt_pack(prompt_pack: V5PromptPack, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(prompt_pack.to_dict(), sort_keys=False))


def load_case_manifest(path: str | Path) -> V5CaseManifest:
    path = Path(path)
    data = read_json_maybe_compressed(path)
    manifest = V5CaseManifest.from_dict(_require_dict(data, "case manifest"))
    errors = manifest.validate(_project_root(path))
    if errors:
        raise ValueError(f"invalid v5 case manifest at {path}: " + "; ".join(errors))
    return manifest


def save_case_manifest(manifest: V5CaseManifest, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest.to_dict(), indent=2) + "\n")


def resolve_case_manifest_path(
    manifest_root: str | Path, corpus: str, case_id: str
) -> Path:
    """Resolve a (corpus, case_id) pair to a manifest file path.

    Supports the post-reorg layout (cases/v5.1010/cases/<safe_id>/manifest.json,
    where safe_id replaces '/' with '__') and the legacy layout
    (<manifest_root>/<corpus>/<case_id>.json) as fallback. The legacy layout
    may exist transiently as symlink bridges during migration.
    """
    root = Path(manifest_root)
    safe_id = case_id.replace("/", "__")
    new_style = root / safe_id / "manifest.json"
    if new_style.exists():
        return new_style
    legacy = root / corpus / f"{case_id}.json"
    if legacy.exists():
        return legacy
    # prefer the canonical (new) path even when only the legacy path exists,
    # so writers/readers converge on the new layout after migration completes
    return new_style if (root / safe_id).exists() else legacy


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be a mapping")
    return value


def _project_root(path: Path) -> Path:
    path = path.resolve()
    for candidate in [path.parent, *path.parents]:
        if (candidate / "pyproject.toml").exists():
            return candidate
    return path.parent
