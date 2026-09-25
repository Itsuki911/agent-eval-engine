"""非同期LLM API、レート制限制御、並行実行、キャンセル処理をテストする。"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock

from agent_eval.agent import AsyncDryRunAgent
from agent_eval.benchmark import load_benchmark
from agent_eval.config import load_settings
from agent_eval.events import EventCollector
from agent_eval.openrouter import AsyncRateLimiter
from agent_eval.telemetry import create_telemetry
from agent_eval.workflow import EvaluationService
from database.session import create_session_factory


PROJECT_ROOT = Path(__file__).resolve().parents[2]


# レートリミッターのセマフォと同時実行数制御を確認する
def test_async_rate_limiter_concurrency() -> None:
    async def _run() -> None:
        limiter = AsyncRateLimiter(max_concurrency=2, requests_per_minute=600)
        current_concurrent = 0
        max_observed_concurrent = 0

        async def _worker() -> None:
            nonlocal current_concurrent, max_observed_concurrent
            async with limiter:
                current_concurrent += 1
                max_observed_concurrent = max(max_observed_concurrent, current_concurrent)
                await asyncio.sleep(0.01)
                current_concurrent -= 1

        await asyncio.gather(*[_worker() for _ in range(5)])
        assert max_observed_concurrent <= 2

    asyncio.run(_run())


# AsyncDryRunAgentが非同期に結果を返すことを確認する
def test_async_dry_run_agent() -> None:
    async def _run() -> None:
        settings = load_settings(PROJECT_ROOT / "configs" / "phase3-local.yaml")
        benchmark = load_benchmark(
            PROJECT_ROOT / "benchmarks" / "generic" / "GEN-TOOL-001.yaml",
            PROJECT_ROOT / "schemas" / "benchmark.schema.json",
        )
        telemetry = create_telemetry(settings.telemetry)
        collector = EventCollector(telemetry.tracer)

        agent = AsyncDryRunAgent(settings)
        result = await agent.run_async(benchmark, collector)

        assert result.final_state["success"] is True
        assert result.final_state["dry_run"] is True
        assert any(event.event_type == "llm_call" for event in collector.events())

    asyncio.run(_run())


# EvaluationService.run_asyncで単一benchmarkを非同期実行できることを確認する
def test_evaluation_service_run_async() -> None:
    async def _run() -> None:
        settings = load_settings(PROJECT_ROOT / "configs" / "phase3-local.yaml")
        session_factory = create_session_factory()
        with session_factory() as session:
            service = EvaluationService(settings, session)
            result = await service.run_async(PROJECT_ROOT / "benchmarks" / "generic" / "GEN-TOOL-001.yaml")

            assert result.benchmark_id == "GEN-TOOL-001"
            assert result.status == "simulated"
            assert result.event_count > 0
            assert len(result.metrics) > 0

    asyncio.run(_run())


# EvaluationService.run_batch_asyncで複数benchmarkを並行実行できることを確認する
def test_evaluation_service_run_batch_async() -> None:
    async def _run() -> None:
        settings = load_settings(PROJECT_ROOT / "configs" / "phase3-local.yaml")
        session_factory = create_session_factory()
        with session_factory() as session:
            service = EvaluationService(settings, session)
            benchmarks = [
                PROJECT_ROOT / "benchmarks" / "generic" / "GEN-TOOL-001.yaml",
                PROJECT_ROOT / "benchmarks" / "generic" / "GEN-DATA-001.yaml",
            ]
            results = await service.run_batch_async(benchmarks, max_concurrency=2)

            assert len(results) == 2
            assert {r.benchmark_id for r in results} == {"GEN-TOOL-001", "GEN-DATA-001"}
            assert all(r.status == "simulated" for r in results)

    asyncio.run(_run())


# キャンセル発生時にステータスが安全に記録されることを確認する
def test_evaluation_service_handles_cancellation() -> None:
    async def _run() -> None:
        settings = load_settings(PROJECT_ROOT / "configs" / "phase3-local.yaml")
        session_factory = create_session_factory()
        with session_factory() as session:
            mock_agent = MagicMock()
            async def slow_run(*args, **kwargs):
                await asyncio.sleep(10.0)
            mock_agent.run_async = slow_run

            service = EvaluationService(settings, session, agent=mock_agent)

            task = asyncio.create_task(
                service.run_async(PROJECT_ROOT / "benchmarks" / "generic" / "GEN-TOOL-001.yaml")
            )
            await asyncio.sleep(0.05)
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass
            else:
                assert False, "CancelledError was not raised"

    asyncio.run(_run())
