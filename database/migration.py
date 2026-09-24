"""DBマイグレーション操作を共通化する。"""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]


# Alembic設定を作成する
def create_alembic_config() -> Config:
    return Config(str(PROJECT_ROOT / "alembic.ini"))


# DBを最新リビジョンへ更新する
def upgrade_database() -> str:
    config = create_alembic_config()
    revision = ScriptDirectory.from_config(config).get_current_head()
    command.upgrade(config, revision)
    return revision
