from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class V5Paths:
    repo_root: Path

    @property
    def prompt_pack_default(self) -> Path:
        return self.repo_root / "experiments" / "prompt_pack_v5.0.yaml"

    @property
    def schema_prompt_pack(self) -> Path:
        return self.repo_root / "schemas" / "v5_prompt_pack.schema.json"

    @property
    def schema_case_manifest(self) -> Path:
        return self.repo_root / "schemas" / "v5_case_manifest.schema.json"

    @property
    def example_case_manifest(self) -> Path:
        return self.repo_root / "doc" / "examples" / "v5_case_example" / "case_manifest.json"
