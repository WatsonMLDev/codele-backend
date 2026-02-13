"""Rate limiting middleware for FastAPI.

Simple in-memory rate limiter using a sliding window per IP address.
For production, swap this with a Redis-backed solution.
"""

import time
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP rate limiting middleware.

    Args:
        app: The FastAPI application.
        rate_limit: Max requests allowed in the window.
        window_seconds: Time window in seconds.
        protected_paths: List of path prefixes to rate-limit.
            If empty, all paths are rate-limited.
    """

    def __init__(
        self,
        app,
        rate_limit: int = 10,
        window_seconds: int = 60,
        protected_paths: list[str] | None = None,
    ):
        super().__init__(app)
        self.rate_limit = rate_limit
        self.window_seconds = window_seconds
        self.protected_paths = protected_paths or []
        # Track request timestamps per IP: {ip: [timestamp, ...]}
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _is_protected(self, path: str) -> bool:
        """Check if the request path should be rate-limited."""
        if not self.protected_paths:
            return True
        return any(path.startswith(prefix) for prefix in self.protected_paths)

    def _clean_old_requests(self, ip: str, now: float) -> None:
        """Remove request timestamps outside the current window."""
        cutoff = now - self.window_seconds
        self._requests[ip] = [
            ts for ts in self._requests[ip] if ts > cutoff
        ]

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        # Skip rate limiting for non-protected paths
        if not self._is_protected(request.url.path):
            return await call_next(request)

        # Get client IP (handle proxies via X-Forwarded-For)
        client_ip = request.headers.get(
            "X-Forwarded-For", request.client.host if request.client else "unknown"
        )
        # Take the first IP if X-Forwarded-For has multiple
        client_ip = client_ip.split(",")[0].strip()

        now = time.time()
        self._clean_old_requests(client_ip, now)

        if len(self._requests[client_ip]) >= self.rate_limit:
            # Calculate retry-after
            oldest = self._requests[client_ip][0]
            retry_after = int(self.window_seconds - (now - oldest)) + 1
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please slow down.",
                    "retry_after_seconds": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        # Record this request
        self._requests[client_ip].append(now)
        return await call_next(request)
