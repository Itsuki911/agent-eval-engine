
# ORM基底を定義する
from sqlalchemy.orm import DeclarativeBase


# 全モデルの共通基底
class Base(DeclarativeBase):
    pass
