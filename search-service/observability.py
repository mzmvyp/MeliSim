import logging
import os
import time
import uuid

from fastapi import Request
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

log = logging.getLogger("observability")

REQUESTS = Counter("http_requests_total", "Total HTTP requests", ["method", "path", "status"])
LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "path"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
EVENTS_PUB = Counter("melisim_events_published_total", "Kafka events published", ["event_type"])
EVENTS_CON = Counter("melisim_events_consumed_total", "Kafka events consumed", ["event_type"])


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["x-request-id"] = rid
        return response


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        route = request.scope.get("route")
        path = route.path if route else request.url.path
        LATENCY.labels(method=request.method, path=path).observe(elapsed)
        REQUESTS.labels(method=request.method, path=path, status=str(response.status_code)).inc()
        return response


def metrics_endpoint() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def setup_tracing(app) -> None:
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        log.info("OTEL disabled")
        return
    service = os.getenv("OTEL_SERVICE_NAME", "unknown")
    try:
        provider = TracerProvider(resource=Resource.create({SERVICE_NAME: service}))
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint.rstrip('/')}/v1/traces"))
        )
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)
        log.info("OTEL enabled: service=%s", service)
    except Exception as e:
        log.warning("OTEL setup failed: %s", e)


def install(app) -> None:
    app.add_middleware(PrometheusMiddleware)
    app.add_middleware(CorrelationIdMiddleware)
    setup_tracing(app)

    @app.get("/metrics")
    def _metrics():
        return metrics_endpoint()
