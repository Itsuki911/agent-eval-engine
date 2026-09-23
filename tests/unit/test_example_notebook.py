"""外部実行Notebookの構成を確認する。"""

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK_PATH = PROJECT_ROOT / "examples" / "evaluation_engine_python_walkthrough.ipynb"


# Notebookが自己完結することを確認する
def test_evaluation_engine_notebook_is_self_contained() -> None:
    notebook = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
    source = "\n".join(
        "".join(cell["source"])
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    )

    assert notebook["nbformat"] == 4
    compile(source, str(NOTEBOOK_PATH), "exec")
    assert "DATABASE_URL" in source
    assert "CREATE TABLE IF NOT EXISTS runs" in source
    assert "GEN-TOOL-001" in source
    assert "tool-selection-v1" in source
    assert "run_evaluation" in source
    assert "reconstruct_history" in source
