"""外部Agentの接続先を保存する。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


# Agent接続先を表す
class AgentTarget(Base):
    __tablename__ = "agent_targets"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    adapter_type: Mapped[str] = mapped_column(String(32), index=True)
    version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    capabilities: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    executions: Mapped[list["RunAgentExecution"]] = relationship(back_populates="target")
