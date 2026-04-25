"""
Distributed sliding-window rate limiter backed by Redis.

Why this and not the in-memory version?
  - Multiple gateway instances behind a load balancer share state, so the
    quota is genuinely "100/min per IP" across the fleet, not per-instance.
  - Survives restarts (in-memory limiter resets every deploy).

Algorithm: classic sorted-set sliding window.
  ZREMRANGEBYSCORE drops timestamps older than (now - window).
  ZADD records the new request.
  ZCARD returns how many requests fall inside the live window.
  EXPIRE garbage-collects buckets idle clients leave behind.
A Lua script wraps all four steps atomically so we never count between writes.
"""
from __future__ import annotations

import logging
import secrets
import time

import redis.asyncio as redis_async
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

log = logging.getLogger("rate_limiter_redis")

# KEYS[1] = user key, ARGV[1] = now (sec), ARGV[2] = window (sec),
# ARGV[3] = max_requests, ARGV[4] = unique member to insert
_LUA_SLIDING_WINDOW = """
redis.call('ZREMRANGEBYSCORE', KEYS[1], 0, ARGV[1] - ARGV[2])
local count = redis.call('ZCARD', KEYS[1])
if tonumber(count) >= tonumber(ARGV[3]) then
  return {0, count}
end
redis.call('ZADD', KEYS[1], ARGV[1], ARGV[4])
redis.call('EXPIRE', KEYS[1], math.ceil(ARGV[2]) + 1)
return {1, count + 1}
"""


class RedisRateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Falls back to a permissive no-op when Redis is unreachable so a Redis
    outage doesn't take down the gateway. The fallback path is logged and
    can be alerted on via the `melisim_rate_limiter_redis_errors_total`
    counter (added in Phase 2).
    """

    def __init__(
        self,
        app,
        redis_url: str,
        max_requests: int = 100,
        window_seconds: int = 60,
        key_prefix: str = "rl",
    ) -> None:
        super().__init__(app)
        self.max_requests = max_requests
        self.window = window_seconds
        self.key_prefix = key_prefix
        self.client: redis_async.Redis | None = None
        self._script_sha: str | None = None
        try:
            self.client = redis_async.from_url(
                f"redis://{redis_url}", decode_responses=True, socket_timeout=0.5
            )
        except Exception as e:
            log.warning("could not init Redis client; rate limiter disabled: %s", e)

    def _client_key(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def _check(self, ip: str) -> tuple[bool, int]:
        if self.client is None:
            return True, 0
        now = time.time()
        member = f"{now}:{secrets.token_hex(4)}"
        key = f"{self.key_prefix}:{ip}"
        try:
            if self._script_sha is None:
                self._script_sha = await self.client.script_load(_LUA_SLIDING_WINDOW)
            allowed, _ = await self.client.evalsha(
                self._script_sha, 1, key, str(now), str(self.window),
                str(self.max_requests), member,
            )
            if int(allowed) == 1:
                return True, 0
            # Caller should retry after at most `window` seconds; we don't
            # compute the exact oldest-entry age here to keep the Lua small.
            return False, self.window
        except Exception as e:
            log.warning("rate-limiter Redis call failed, fail-open: %s", e)
            return True, 0

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/health" or request.url.path == "/metrics":
            return await call_next(request)
        ip = self._client_key(request)
        allowed, retry_after = await self._check(ip)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded", "retry_after_seconds": retry_after},
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)
