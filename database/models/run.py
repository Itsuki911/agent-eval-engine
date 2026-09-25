"""評価実行の開始と終了を保存する。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


# 実行単位を保存する
class Run(Base):
    __tablename__ = "runs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    benchmark_id: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(32), default="running", index=True)
    agent_name: Mapped[str] = mapped_column(String(128))
    provider: Mapped[str | None] = mapped_column(String(128), nullable=True)
    model: Mapped[str | None] = mapped_column(String(256), nullable=True)
    architecture: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    run_config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    final_state: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    failure_category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    llm_cost_usd: Mapped[float | None] = mapped_column(Numeric(20, 8), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    events: Mapped[list["Event"]] = relationship(back_populates="run", cascade="all, delete-orphan", order_by="Event.sequence")
    metrics: Mapped[list["Metric"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    evaluations: Mapped[list["Evaluation"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    agent_executions: Mapped[list["RunAgentExecution"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    artifacts: Mapped[list["Artifact"]] = relationship(back_populates="run", cascade="all, delete-orphan")
