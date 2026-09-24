"""手動確認用のJSON出力を提供する。"""

from __future__ import annotations

import json
from typing import Any


# テスト結果を1行JSONで表示する
def print_test_result(test: str, result: str, **values: Any) -> None:
    print(json.dumps({"test": test, "result": result, **values}, ensure_ascii=False, default=str))
