"""外部Agent実行の永続化基盤を追加する。"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260925_0004"
down_revision = "20260925_0003"
branch_labels = None
depends_on = None


# Agent実行用テーブルを追加する
def upgrade() -> None:
    op.create_table(
        "agent_targets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("adapter_type", sa.String(length=32), nullable=False),
        sa.Column("version", sa.String(length=128), nullable=True),
        sa.Column("configuration", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("capabilities", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("name", name="uq_agent_targets_name"),
    )
    op.create_index("ix_agent_targets_name", "agent_targets", ["name"])
    op.create_index("ix_agent_targets_adapter_type", "agent_targets", ["adapter_type"])
    op.create_table(
        "run_agent_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("adapter_type", sa.String(length=32), nullable=False),
        sa.Column("target_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("error", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["agent_targets.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_run_agent_executions_run_id", "run_agent_executions", ["run_id"])
    op.create_index("ix_run_agent_executions_target_id", "run_agent_executions", ["target_id"])
    op.create_index("ix_run_agent_executions_status", "run_agent_executions", ["status"])
    op.create_table(
        "artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("execution_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("uri", sa.String(length=1024), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["execution_id"], ["run_agent_executions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_artifacts_run_id", "artifacts", ["run_id"])
    op.create_index("ix_artifacts_execution_id", "artifacts", ["execution_id"])
    op.create_index("ix_artifacts_kind", "artifacts", ["kind"])
    op.create_index("ix_artifacts_sha256", "artifacts", ["sha256"])


# Agent実行用テーブルを削除する
def downgrade() -> None:
    op.drop_index("ix_artifacts_sha256", table_name="artifacts")
    op.drop_index("ix_artifacts_kind", table_name="artifacts")
    op.drop_index("ix_artifacts_execution_id", table_name="artifacts")
    op.drop_index("ix_artifacts_run_id", table_name="artifacts")
    op.drop_table("artifacts")
    op.drop_index("ix_run_agent_executions_status", table_name="run_agent_executions")
    op.drop_index("ix_run_agent_executions_target_id", table_name="run_agent_executions")
    op.drop_index("ix_run_agent_executions_run_id", table_name="run_agent_executions")
    op.drop_table("run_agent_executions")
    op.drop_index("ix_agent_targets_adapter_type", table_name="agent_targets")
    op.drop_index("ix_agent_targets_name", table_name="agent_targets")
    op.drop_table("agent_targets")
