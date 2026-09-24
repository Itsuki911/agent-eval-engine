"""実行ごとのLLM料金を保存する。"""

from alembic import op
import sqlalchemy as sa


revision = "20260924_0002"
down_revision = "20260923_0001"
branch_labels = None
depends_on = None


# LLM料金列を追加する
def upgrade() -> None:
    op.add_column("runs", sa.Column("llm_cost_usd", sa.Numeric(20, 8), nullable=True))


# LLM料金列を削除する
def downgrade() -> None:
    op.drop_column("runs", "llm_cost_usd")
