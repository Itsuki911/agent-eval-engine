"""外部Agent Adapterの共通契約を定義する。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


# Agent実行要求を表す
@dataclass(frozen=True)
class AgentExecutionRequest:
    benchmark_id: str
    prompt: str
    workspace: Path
    limits: dict[str, Any] = field(default_factory=dict)


# Agent実行結果を表す
@dataclass(frozen=True)
class AgentExecutionResult:
    status: str
    exit_code: int | None
    summary: dict[str, Any] = field(default_factory=dict)
    artifacts: list[dict[str, Any]] = field(default_factory=list)


# 外部Agent接続の共通契約を表す
class AgentAdapter(Protocol):
    adapter_type: str

    # 接続先の能力を返す
    def capabilities(self) -> dict[str, Any]: ...

    # 隔離済みworkspaceで評価する
    def run(self, request: AgentExecutionRequest) -> AgentExecutionResult: ...
