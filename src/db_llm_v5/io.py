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
