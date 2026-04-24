import logging
import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

log = logging.getLogger("observability")


def setup_tracing(app, service_name: str | None = None) -> None:
    name = service_name or os.getenv("OTEL_SERVICE_NAME", "unknown-service")
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        log.info("OTEL disabled (no OTEL_EXPORTER_OTLP_ENDPOINT)")
        return
    resource = Resource.create({SERVICE_NAME: name})
    provider = TracerProvider(resource=resource)
    try:
        exporter = OTLPSpanExporter(endpoint=f"{endpoint.rstrip('/')}/v1/traces")
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)
        HTTPXClientInstrumentor().instrument()
        log.info("OTEL tracing enabled: service=%s endpoint=%s", name, endpoint)
    except Exception as e:
        log.warning("OTEL setup failed: %s", e)
