import contextvars
import logging
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

HEADER = "x-request-id"
_request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


def current_request_id() -> str:
    return _request_id_ctx.get()


class RequestIdLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = current_request_id()
        return True


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Accepts inbound X-Request-ID or mints a fresh UUID4. Forwards the value to
    downstream services via request.state so the proxy can inject it in upstream
    headers. Adds the same header on the response.
    """

    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get(HEADER)
        rid = incoming if incoming else uuid.uuid4().hex
        token = _request_id_ctx.set(rid)
        request.state.request_id = rid
        try:
            response = await call_next(request)
        finally:
            _request_id_ctx.reset(token)
        response.headers[HEADER] = rid
        return response
