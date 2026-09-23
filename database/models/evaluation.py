"""評価器の判定結果を保存する。"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


# 評価結果を保存する
class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    evaluator_name: Mapped[str] = mapped_column(String(128))
    evaluator_version: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), index=True)
    score: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    findings: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)

    run: Mapped["Run"] = relationship(back_populates="evaluations")
