import os
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

class APIKeyValidationMiddleware(BaseHTTPMiddleware):
    """
    Ensures that incoming requests have the correct X-API-Key header,
    injected by the Cloudflare Worker proxy.
    """
    def __init__(self, app):
        super().__init__(app)
        self.expected_key = os.getenv("API_KEY")

    async def dispatch(self, request: Request, call_next):
        # Exclude health check from API key validation
        if request.url.path == "/health":
            return await call_next(request)
            
        # Only validate if an API_KEY is configured in the backend environment
        if self.expected_key:
            provided_key = request.headers.get("X-API-Key")
            if not provided_key or provided_key != self.expected_key:
                raise HTTPException(status_code=403, detail="Forbidden: Invalid or missing API key")
                
        return await call_next(request)
