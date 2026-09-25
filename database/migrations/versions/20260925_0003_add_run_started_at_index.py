"""実行一覧の並び替えを高速化する。"""

from alembic import op


revision = "20260925_0003"
down_revision = "20260924_0002"
branch_labels = None
depends_on = None


# 実行日時の索引を追加する
def upgrade() -> None:
    op.create_index("ix_runs_started_at", "runs", ["started_at"])


# 実行日時の索引を削除する
def downgrade() -> None:
    op.drop_index("ix_runs_started_at", table_name="runs")
