from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from compressed_io import read_candidates


ArtifactKind = Literal[
    "uq_surface",
    "up_exec",
    "sql_gold",
    "res_gold",
    "uq_benchmark_spec",
    "res_gold_presentation",
]
RealismLevel = Literal[
    "realistic_surface",
    "templated_surface",
    "benchmark_spec_only",
]
AmbiguityLevel = Literal[
    "unambiguous",
    "mildly_ambiguous",
    "requires_domain_assumption",
]
CaseRole = Literal["train", "val", "test"]


@dataclass(slots=True)
class V5ArtifactPaths:
    uq_surface: str
    up_exec: str | None = None
    sql_gold: str | None = None
    res_gold: str | None = None
    uq_benchmark_spec: str | None = None
    res_gold_presentation: str | None = None
    source_sql: str | None = None
    sqlite_sql: str | None = None
    documentation: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "V5ArtifactPaths":
        return cls(
            uq_surface=str(data["uq_surface"]),
            up_exec=_optional_str(data.get("up_exec")),
            sql_gold=_optional_str(data.get("sql_gold")),
            res_gold=_optional_str(data.get("res_gold")),
            uq_benchmark_spec=_optional_str(data.get("uq_benchmark_spec")),
            res_gold_presentation=_optional_str(data.get("res_gold_presentation")),
            source_sql=_optional_str(data.get("source_sql")),
            sqlite_sql=_optional_str(data.get("sqlite_sql")),
            documentation=_optional_str(data.get("documentation")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "uq_surface": self.uq_surface,
            "up_exec": self.up_exec,
            "sql_gold": self.sql_gold,
            "res_gold": self.res_gold,
            "uq_benchmark_spec": self.uq_benchmark_spec,
            "res_gold_presentation": self.res_gold_presentation,
            "source_sql": self.source_sql,
            "sqlite_sql": self.sqlite_sql,
            "documentation": self.documentation,
        }


@dataclass(slots=True)
class V5CaseMetadata:
    family: str
    origin: str
    source_title: str | None = None
    source_url: str | None = None
    realism_level: RealismLevel = "realistic_surface"
    ambiguity_level: AmbiguityLevel = "unambiguous"
    size_class: str | None = None
    expected_output_columns: list[str] = field(default_factory=list)
    sort_keys: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    allows_multiple_sql_forms: bool = True
    requires_schema_alias_fidelity: bool = False
    normalize: dict[str, Any] = field(default_factory=dict)
    column_rename_map: dict[str, str] = field(default_factory=dict)
    float_cols: list[str] = field(default_factory=list)
    int_cols: list[str] = field(default_factory=list)
    string_cols: list[str] = field(default_factory=list)
    float_tol: float = 1e-6
    notes: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "V5CaseMetadata":
        return cls(
            family=str(data["family"]),
            origin=str(data["origin"]),
            source_title=_optional_str(data.get("source_title")),
            source_url=_optional_str(data.get("source_url")),
            realism_level=str(data.get("realism_level", "realistic_surface")),  # type: ignore[arg-type]
            ambiguity_level=str(data.get("ambiguity_level", "unambiguous")),  # type: ignore[arg-type]
            size_class=_optional_str(data.get("size_class")),
            expected_output_columns=_string_list(data.get("expected_output_columns", [])),
            sort_keys=_string_list(data.get("sort_keys", [])),
            tags=_string_list(data.get("tags", [])),
            allows_multiple_sql_forms=bool(data.get("allows_multiple_sql_forms", True)),
            requires_schema_alias_fidelity=bool(data.get("requires_schema_alias_fidelity", False)),
            normalize=_string_dict(data.get("normalize", {})),
            column_rename_map=_string_dict(data.get("column_rename_map", {})),
            float_cols=_string_list(data.get("float_cols", [])),
            int_cols=_string_list(data.get("int_cols", [])),
            string_cols=_string_list(data.get("string_cols", [])),
            float_tol=float(data.get("float_tol", 1e-6)),
            notes=_optional_str(data.get("notes")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "family": self.family,
            "origin": self.origin,
            "source_title": self.source_title,
            "source_url": self.source_url,
            "realism_level": self.realism_level,
            "ambiguity_level": self.ambiguity_level,
            "size_class": self.size_class,
            "expected_output_columns": self.expected_output_columns,
            "sort_keys": self.sort_keys,
            "tags": self.tags,
            "allows_multiple_sql_forms": self.allows_multiple_sql_forms,
            "requires_schema_alias_fidelity": self.requires_schema_alias_fidelity,
            "normalize": self.normalize,
            "column_rename_map": self.column_rename_map,
            "float_cols": self.float_cols,
            "int_cols": self.int_cols,
            "string_cols": self.string_cols,
            "float_tol": self.float_tol,
            "notes": self.notes,
        }


@dataclass(slots=True)
class V5CaseManifest:
    case_id: str
    corpus: str
    split: CaseRole | None
    db_path: str
    artifacts: V5ArtifactPaths
    metadata: V5CaseMetadata

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "V5CaseManifest":
        return cls(
            case_id=str(data["case_id"]),
            corpus=str(data["corpus"]),
            split=_optional_split(data.get("split")),
            db_path=str(data["db_path"]),
            artifacts=V5ArtifactPaths.from_dict(dict(data["artifacts"])),
            metadata=V5CaseMetadata.from_dict(dict(data["metadata"])),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "corpus": self.corpus,
            "split": self.split,
            "db_path": self.db_path,
            "artifacts": self.artifacts.to_dict(),
            "metadata": self.metadata.to_dict(),
        }

    def validate(self, root: Path) -> list[str]:
        errors: list[str] = []
        if not self.case_id:
            errors.append("case_id must not be empty")
        if not self.corpus:
            errors.append("corpus must not be empty")
        if not self.db_path:
            errors.append("db_path must not be empty")
        for name, path_value in self.artifacts.to_dict().items():
            if not path_value:
                continue
            artifact_path = root / path_value
            if not any(candidate.exists() for candidate in read_candidates(artifact_path)):
                errors.append(f"artifact path missing: {name} -> {path_value}")
        if not (root / self.db_path).exists():
            errors.append(f"db_path missing: {self.db_path}")
        return errors


@dataclass(slots=True)
class V5SystemBlock:
    about_block: str
    schema_block_path: str | None = None
    hint_block_path: str | None = None
    examples_block: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "V5SystemBlock":
        return cls(
            about_block=str(data["about_block"]),
            schema_block_path=_optional_str(data.get("schema_block_path")),
            hint_block_path=_optional_str(data.get("hint_block_path")),
            examples_block=_optional_str(data.get("examples_block")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "about_block": self.about_block,
            "schema_block_path": self.schema_block_path,
            "hint_block_path": self.hint_block_path,
            "examples_block": self.examples_block,
        }


@dataclass(slots=True)
class V5ForwardPrompts:
    up: str
    sql: str
    judge: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "V5ForwardPrompts":
        return cls(
            up=str(data["up"]),
            sql=str(data["sql"]),
            judge=str(data["judge"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {"up": self.up, "sql": self.sql, "judge": self.judge}


@dataclass(slots=True)
class V5BackwardPrompts:
    sql_to_up: str
    up_to_uq: str
    res_sql_to_intent: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "V5BackwardPrompts":
        return cls(
            sql_to_up=str(data["sql_to_up"]),
            up_to_uq=str(data["up_to_uq"]),
            res_sql_to_intent=_optional_str(data.get("res_sql_to_intent")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "sql_to_up": self.sql_to_up,
            "up_to_uq": self.up_to_uq,
            "res_sql_to_intent": self.res_sql_to_intent,
        }


@dataclass(slots=True)
class V5ScoringConfig:
    judge_threshold: float = 0.9
    uq_up_echo_penalty_threshold: float = 0.95
    uq_up_echo_penalty_weight: float = 0.15

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "V5ScoringConfig":
        return cls(
            judge_threshold=float(data.get("judge_threshold", 0.9)),
            uq_up_echo_penalty_threshold=float(data.get("uq_up_echo_penalty_threshold", 0.95)),
            uq_up_echo_penalty_weight=float(data.get("uq_up_echo_penalty_weight", 0.15)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "judge_threshold": self.judge_threshold,
            "uq_up_echo_penalty_threshold": self.uq_up_echo_penalty_threshold,
            "uq_up_echo_penalty_weight": self.uq_up_echo_penalty_weight,
        }


@dataclass(slots=True)
class V5PromptPack:
    version: str
    system: V5SystemBlock
    pf: V5ForwardPrompts
    pb: V5BackwardPrompts
    scoring: V5ScoringConfig = field(default_factory=V5ScoringConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "V5PromptPack":
        return cls(
            version=str(data["version"]),
            system=V5SystemBlock.from_dict(dict(data["system"])),
            pf=V5ForwardPrompts.from_dict(dict(data["pf"])),
            pb=V5BackwardPrompts.from_dict(dict(data["pb"])),
            scoring=V5ScoringConfig.from_dict(dict(data.get("scoring", {}))),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "system": self.system.to_dict(),
            "pf": self.pf.to_dict(),
            "pb": self.pb.to_dict(),
            "scoring": self.scoring.to_dict(),
        }

    def validate(self, root: Path) -> list[str]:
        errors: list[str] = []
        if not self.version.startswith("v5"):
            errors.append("version must start with 'v5'")
        if not self.system.about_block.strip():
            errors.append("system.about_block must not be empty")
        if not self.pf.up.strip():
            errors.append("pf.up must not be empty")
        if not self.pf.sql.strip():
            errors.append("pf.sql must not be empty")
        if not self.pf.judge.strip():
            errors.append("pf.judge must not be empty")
        if not self.pb.sql_to_up.strip():
            errors.append("pb.sql_to_up must not be empty")
        if not self.pb.up_to_uq.strip():
            errors.append("pb.up_to_uq must not be empty")
        for attr_name in ("schema_block_path", "hint_block_path"):
            path_value = getattr(self.system, attr_name)
            if path_value and not (root / path_value).exists():
                errors.append(f"system.{attr_name} missing: {path_value}")
        return errors


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise TypeError(f"expected list[str], got {type(value).__name__}")
    return [str(item) for item in value]


def _string_dict(value: Any) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise TypeError(f"expected dict[str, str], got {type(value).__name__}")
    return {str(k): str(v) for k, v in value.items()}


def _optional_split(value: Any) -> CaseRole | None:
    if value is None or value == "":
        return None
    split = str(value)
    if split not in {"train", "val", "test"}:
        raise ValueError(f"invalid split: {split}")
    return split  # type: ignore[return-value]
