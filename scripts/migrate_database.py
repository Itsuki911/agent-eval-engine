"""DBを最新マイグレーションへ更新する。"""

from __future__ import annotations

import json
import sys

from database.migration import upgrade_database


# マイグレーション結果をJSONで出力する
def main() -> None:
    try:
        revision = upgrade_database()
    except Exception as error:
        print(
            json.dumps({"status": "failed", "error_type": type(error).__name__}),
            file=sys.stderr,
        )
        raise
    print(json.dumps({"status": "upgraded", "revision": revision}))


if __name__ == "__main__":
    main()
