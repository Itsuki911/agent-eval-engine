"""外部Coding Agentの実行記録を取り込む。"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_eval.agent_adapter import AgentExecutionRequest, AgentExecutionResult
from database.repositories import RunRepository
from database.repositories.run_repository import reject_secret_configuration


SUPPORTED_AGENT_TYPES = frozenset({"codex", "opencode", "antigravity", "generic"})
MAX_TRANSCRIPT_BYTES = 5 * 1024 * 1024
MAX_TRANSCRIPT_EVENTS = 10_000


# 読み込めない記録形式を表す
class TranscriptError(ValueError):
    pass


# 外部Agentイベントを表す
@dataclass(frozen=True)
class TranscriptEvent:
    sequence: int
    event_type: str
    payload: dict[str, Any]
    actor: str = "agent"
    previous_state: dict[str, Any] | None = None
    next_state: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    trace_id: str | None = None
    span_id: str | None = None


# 外部Agent実行記録を表す
@dataclass(frozen=True)
class AgentTranscript:
    adapter_type: str
    benchmark_id: str
    agent_name: str
    model: str | None
    agent_version: str | None
    events: list[TranscriptEvent]
    status: str
    task_success: bool
    exit_code: int | None
    final_state: dict[str, Any]
    failure_category: str | None


# JSONL記録を安全に読み込む
def load_agent_transcript(path: Path) -> AgentTranscript:
    if path.suffix != ".jsonl":
        raise TranscriptError("記録ファイルは .jsonl を指定してください")
    if not path.is_file():
        raise TranscriptError("記録ファイルが見つかりません")
    if path.stat().st_size > MAX_TRANSCRIPT_BYTES:
        raise TranscriptError("記録ファイルが上限を超えています")

    records = _read_records(path)
    if len(records) < 2 or records[0].get("record_type") != "run":
        raise TranscriptError("先頭に run レコードが必要です")
    if records[-1].get("record_type") != "result":
        raise TranscriptError("末尾に result レコードが必要です")

    header = records[0]
    adapter_type = _required_text(header, "adapter_type")
    if adapter_type not in SUPPORTED_AGENT_TYPES:
        raise TranscriptError("未対応の adapter_type です")
    benchmark_id = _required_text(header, "benchmark_id")
    agent_name = _required_text(header, "agent_name")
    events = [_event_from_record(record, index) for index, record in enumerate(records[1:-1])]
    if len(events) > MAX_TRANSCRIPT_EVENTS:
        raise TranscriptError("イベント数が上限を超えています")
    if [event.sequence for event in events] != list(range(len(events))):
        raise TranscriptError("event の sequence は 0 から連番にしてください")

    result = records[-1]
    status = _required_text(result, "status")
    if status not in {"completed", "failed", "cancelled"}:
        raise TranscriptError("result の status が不正です")
    task_success = result.get("task_success")
    if not isinstance(task_success, bool):
        raise TranscriptError("result の task_success は boolean にしてください")
    final_state = result.get("final_state", {})
    if not isinstance(final_state, dict):
        raise TranscriptError("result の final_state は object にしてください")
    exit_code = result.get("exit_code")
    if exit_code is not None and (not isinstance(exit_code, int) or isinstance(exit_code, bool)):
        raise TranscriptError("result の exit_code は整数か null にしてください")
    failure_category = result.get("failure_category")
    if failure_category is not None and not isinstance(failure_category, str):
        raise TranscriptError("result の failure_category は文字列か null にしてください")
    return AgentTranscript(
        adapter_type=adapter_type,
        benchmark_id=benchmark_id,
        agent_name=agent_name,
        model=_optional_text(header, "model"),
        agent_version=_optional_text(header, "agent_version"),
        events=events,
        status=status,
        task_success=task_success,
        exit_code=exit_code,
        final_state=final_state,
        failure_category=failure_category,
    )


# 許可root内の記録パスを解決する
def resolve_agent_transcript_path(root: Path, transcript_file: str) -> Path:
    supplied = Path(transcript_file)
    if supplied.is_absolute():
        raise TranscriptError("絶対パスは指定できません")
    resolved_root = root.resolve()
    candidate = (resolved_root / supplied).resolve()
    if not candidate.is_relative_to(resolved_root):
        raise TranscriptError("記録ファイルは許可フォルダ内を指定してください")
    return candidate


# JSONL記録をDBへ保存する
def import_agent_transcript(
    repository: RunRepository,
    transcript_path: Path,
) -> dict[str, Any]:
    transcript = load_agent_transcript(transcript_path)
    target = repository.get_or_create_agent_target(
        name=f"{transcript.adapter_type}:{transcript.agent_name}"[:128],
        adapter_type=transcript.adapter_type,
        configuration={"transcript_format": "agent-eval.trace.v1"},
        capabilities={"trace_import": True},
        version=transcript.agent_version,
    )
    run = repository.create_run(
        benchmark_id=transcript.benchmark_id,
        agent_name=transcript.agent_name,
        provider="external-agent",
        model=transcript.model,
        architecture={"framework": "external-agent", "adapter_type": transcript.adapter_type},
        run_config={"transcript_format": "agent-eval.trace.v1"},
    )
    execution = repository.create_agent_execution(
        run.id,
        transcript.adapter_type,
        target.id,
        {"name": target.name, "version": target.version, "adapter_type": transcript.adapter_type},
    )
    for event in transcript.events:
        repository.add_event(
            run.id,
            event.sequence,
            event.event_type,
            event.payload,
            event.previous_state,
            event.next_state,
            event.error,
            event.actor,
            event.trace_id,
            event.span_id,
        )
    final_state = {**transcript.final_state, "success": transcript.task_success}
    repository.finish_agent_execution(execution.id, transcript.status, transcript.exit_code)
    repository.add_artifact(
        run.id,
        "agent_transcript",
        f"local://agent-traces/{transcript_path.name}",
        execution.id,
        _file_sha256(transcript_path),
        transcript_path.stat().st_size,
        {"format": "agent-eval.trace.v1", "event_count": len(transcript.events)},
    )
    repository.add_metric(run.id, "success", "task_success", float(transcript.task_success), "ratio")
    repository.add_metric(run.id, "trajectory", "step_count", float(len(transcript.events)), "count")
    repository.add_metric(
        run.id,
        "tool_usage",
        "tool_call_count",
        float(sum(event.event_type == "tool_call" for event in transcript.events)),
        "count",
    )
    repository.add_evaluation(
        run.id,
        "transcript-import",
        "1",
        "passed" if transcript.task_success else "failed",
        1.0 if transcript.task_success else 0.0,
        {"source": "external-agent", "event_count": len(transcript.events)},
    )
    repository.finish_run(run.id, transcript.status, final_state, transcript.failure_category)
    repository.session.commit()
    return {
        "run_id": str(run.id),
        "execution_id": str(execution.id),
        "adapter_type": transcript.adapter_type,
        "status": transcript.status,
        "task_success": transcript.task_success,
        "event_count": len(transcript.events),
    }


# 標準記録をAgent Adapterとして扱う
class JsonlAgentAdapter:
    adapter_type = "jsonl"

    # JSONL記録の対応機能を返す
    def capabilities(self) -> dict[str, Any]:
        return {"trace_import": True, "agent_types": sorted(SUPPORTED_AGENT_TYPES)}

    # 要求と記録の対象一致を確認する
    def run(self, request: AgentExecutionRequest) -> AgentExecutionResult:
        transcript = load_agent_transcript(request.workspace)
        if transcript.benchmark_id != request.benchmark_id:
            raise TranscriptError("benchmark_id が実行要求と一致しません")
        return AgentExecutionResult(
            status=transcript.status,
            exit_code=transcript.exit_code,
            summary={"task_success": transcript.task_success, "event_count": len(transcript.events)},
        )


# JSONL各行を読み取る
def _read_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise TranscriptError(f"{line_number}行目のJSONが不正です") from error
        if not isinstance(value, dict):
            raise TranscriptError(f"{line_number}行目はobjectにしてください")
        try:
            reject_secret_configuration(value)
        except ValueError as error:
            raise TranscriptError("秘密情報を含む記録は取り込めません") from error
        records.append(value)
    return records


# event行を検証して変換する
def _event_from_record(record: dict[str, Any], index: int) -> TranscriptEvent:
    if record.get("record_type") != "event":
        raise TranscriptError(f"{index + 2}行目は event レコードにしてください")
    sequence = record.get("sequence")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 0:
        raise TranscriptError("event の sequence は0以上の整数にしてください")
    payload = record.get("payload", {})
    if not isinstance(payload, dict):
        raise TranscriptError("event の payload は object にしてください")
    return TranscriptEvent(
        sequence=sequence,
        event_type=_required_text(record, "event_type"),
        payload=payload,
        actor=_optional_text(record, "actor") or "agent",
        previous_state=_optional_object(record, "previous_state"),
        next_state=_optional_object(record, "next_state"),
        error=_optional_object(record, "error"),
        trace_id=_optional_text(record, "trace_id"),
        span_id=_optional_text(record, "span_id"),
    )


# 必須文字列を検証する
def _required_text(record: dict[str, Any], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise TranscriptError(f"{key} は空でない文字列にしてください")
    return value


# 任意文字列を検証する
def _optional_text(record: dict[str, Any], key: str) -> str | None:
    value = record.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise TranscriptError(f"{key} は文字列か null にしてください")
    return value


# 任意objectを検証する
def _optional_object(record: dict[str, Any], key: str) -> dict[str, Any] | None:
    value = record.get(key)
    if value is None:
        return None
    if not isinstance(value, dict):
        raise TranscriptError(f"{key} は object か null にしてください")
    return value


# 記録ファイルのハッシュを計算する
def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
