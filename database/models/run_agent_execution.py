"""Agent実行の再現情報を保存する。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


# Agent実行単位を表す
class RunAgentExecution(Base):
    __tablename__ = "run_agent_executions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    target_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("agent_targets.id", ondelete="SET NULL"), nullable=True, index=True)
    adapter_type: Mapped[str] = mapped_column(String(32))
    target_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="prepared", index=True)
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    run: Mapped["Run"] = relationship(back_populates="agent_executions")
    target: Mapped["AgentTarget | None"] = relationship(back_populates="executions")
    artifacts: Mapped[list["Artifact"]] = relationship(back_populates="execution", cascade="all, delete-orphan")
