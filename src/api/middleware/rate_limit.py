import time
from collections import defaultdict
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    In-memory rate limiter to prevent basic scraping/abuse.
    For horizontal scaling, this would be backed by Redis.
    """
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.rpm = requests_per_minute
        self.requests = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # We respect the X-Forwarded-For header set by the Cloudflare Worker proxy
        client_ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "127.0.0.1")
        now = time.time()

        # Clean entries older than 60 seconds
        self.requests[client_ip] = [
            t for t in self.requests[client_ip] if now - t < 60
        ]

        # Check limit
        if len(self.requests[client_ip]) >= self.rpm:
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")

        self.requests[client_ip].append(now)
        
        return await call_next(request)
