"""OpenTelemetryで実行を観測する。"""

from __future__ import annotations

from dataclasses import dataclass

from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from opentelemetry.trace import Tracer

from agent_eval.config import TelemetrySettings


# 観測に使うトレーサーを表す
@dataclass(frozen=True)
class Telemetry:
    tracer: Tracer
    provider: TracerProvider


# OpenTelemetryを初期化する
def create_telemetry(settings: TelemetrySettings) -> Telemetry:
    resource = Resource.create({SERVICE_NAME: settings.service_name})
    provider = TracerProvider(resource=resource)
    if settings.exporter == "console":
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    return Telemetry(tracer=provider.get_tracer("agent_eval"), provider=provider)
