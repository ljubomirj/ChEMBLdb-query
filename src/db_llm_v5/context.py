from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class IterationHistoryItem:
    iteration: int
    uq: str | None = None
    up: str | None = None
    sql: str | None = None
    res_summary: str | None = None
    judge_analysis: str | None = None
    judge_score: float | None = None


@dataclass(slots=True)
class ForwardContext:
    system_prompt: str
    uq: str
    filter_profile: str | None = None
    history: list[IterationHistoryItem] = field(default_factory=list)


@dataclass(slots=True)
class BackwardContext:
    system_prompt: str
    sql: str | None = None
    res_summary: str | None = None
    history: list[IterationHistoryItem] = field(default_factory=list)
