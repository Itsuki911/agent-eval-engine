"""評価指標を独立して保存する。"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


# 指標値を保存する
class Metric(Base):
    __tablename__ = "metrics"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    value: Mapped[float] = mapped_column(Numeric(20, 8))
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    dimensions: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    run: Mapped["Run"] = relationship(back_populates="metrics")
