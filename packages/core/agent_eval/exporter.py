"""評価データをExcel/Google Sheets向けCSV形式でエクスポートする。"""

from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from database.models import Run


# 利用者のローカルダウンロード先ディレクトリを取得する
def get_default_download_directory() -> Path:
    override = os.environ.get("AGENT_EVAL_DOWNLOAD_DIR")
    if override:
        path = Path(override).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    userprofile = os.environ.get("USERPROFILE")
    if userprofile:
        path = Path(userprofile) / "Downloads"
        if path.exists():
            return path

    home_downloads = Path.home() / "Downloads"
    if home_downloads.exists():
        return home_downloads

    try:
        home_downloads.mkdir(parents=True, exist_ok=True)
        return home_downloads
    except OSError:
        pass

    fallback = Path("./downloads").resolve()
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


# 利用者向け保存先表示を作る
def get_display_download_path(path: Path) -> str:
    display_dir = os.environ.get("AGENT_EVAL_DOWNLOAD_DISPLAY_DIR")
    if display_dir:
        return str(Path(display_dir) / path.name)
    return str(path)


# 実行履歴からファミリー名を推定する
def _infer_family(benchmark_id: str) -> str:
    if benchmark_id.startswith("GEN-"):
        return "generic"
    if benchmark_id.startswith("COD-"):
        return "coding"
    if benchmark_id.startswith("TERM-"):
        return "terminal"
    if benchmark_id.startswith("WEB-"):
        return "web"
    if benchmark_id.startswith("GUI-"):
        return "gui"
    return "unknown"


# 保存済み評価データをCSV形式で出力する
def export_runs_to_csv(
    session: Session,
    output_path: Path | None = None,
    run_id: UUID | str | None = None,
) -> Path:
    statement = (
        select(Run)
        .options(selectinload(Run.metrics), selectinload(Run.evaluations))
        .order_by(desc(Run.started_at))
    )
    if run_id:
        target_uuid = UUID(str(run_id))
        statement = statement.where(Run.id == target_uuid)

    runs = list(session.scalars(statement))

    # 動的なメトリクス列名を収集する
    common_metric_names = [
        "task_success",
        "step_count",
        "tool_call_count",
        "retry_count",
        "latency",
        "estimated_cost",
        "safety_violation_count",
    ]
    all_metric_keys: set[str] = set()
    for run in runs:
        for metric in run.metrics:
            all_metric_keys.add(f"{metric.category}.{metric.name}")

    ordered_metric_keys: list[str] = []
    for c in common_metric_names:
        for k in sorted(all_metric_keys):
            if k.endswith(f".{c}") and k not in ordered_metric_keys:
                ordered_metric_keys.append(k)
    for k in sorted(all_metric_keys):
        if k not in ordered_metric_keys:
            ordered_metric_keys.append(k)

    header = [
        "run_id",
        "started_at",
        "finished_at",
        "duration_seconds",
        "benchmark_id",
        "family",
        "agent_name",
        "provider",
        "model",
        "status",
        "llm_cost_usd",
        "eval_status",
        "eval_score",
    ] + [f"metric_{k}" for k in ordered_metric_keys]

    if output_path is None:
        download_dir = get_default_download_directory()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        if run_id:
            filename = f"agent_eval_run_{str(run_id)[:8]}_{timestamp}.csv"
        else:
            filename = f"agent_eval_runs_{timestamp}.csv"
        output_path = download_dir / filename
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)

    # Excel/Google Sheets向けに UTF-8 with BOM で書き込む
    with output_path.open("w", newline="", encoding="utf-8-sig") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(header)

        for run in runs:
            duration = None
            if run.finished_at and run.started_at:
                duration = round((run.finished_at - run.started_at).total_seconds(), 3)

            eval_status = run.evaluations[0].status if run.evaluations else ""
            eval_score = (
                f"{run.evaluations[0].score:.4f}"
                if run.evaluations and run.evaluations[0].score is not None
                else ""
            )

            metrics_map: dict[str, Any] = {
                f"{m.category}.{m.name}": m.value for m in run.metrics
            }

            row = [
                str(run.id),
                run.started_at.isoformat() if run.started_at else "",
                run.finished_at.isoformat() if run.finished_at else "",
                duration if duration is not None else "",
                run.benchmark_id,
                _infer_family(run.benchmark_id),
                run.agent_name,
                run.provider or "",
                run.model or "",
                run.status,
                f"{run.llm_cost_usd:.8f}" if run.llm_cost_usd is not None else "",
                eval_status,
                eval_score,
            ]
            for k in ordered_metric_keys:
                val = metrics_map.get(k)
                row.append(f"{val:.4f}" if isinstance(val, (int, float)) else (val or ""))

            writer.writerow(row)

    return output_path
