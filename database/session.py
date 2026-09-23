
# 接続設定を生成する
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


# DB接続URLを取得する
def database_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://agent_eval:local-development-password@localhost:5432/agent_eval",
    )


# ORMエンジンを作成する
def create_db_engine(url: str | None = None):
    return create_engine(url or database_url(), pool_pre_ping=True)


# セッション生成器を作る
def create_session_factory(url: str | None = None) -> sessionmaker[Session]:
    return sessionmaker(bind=create_db_engine(url), expire_on_commit=False)
