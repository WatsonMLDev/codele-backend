from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds standard security headers to API responses.
    """
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Prevent browsers from MIME-sniffing a response away from the declared content-type
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent clickjacking by forbidding rendering inside a frame/iframe
        response.headers["X-Frame-Options"] = "DENY"
        
        # Strict-Transport-Security (HSTS) - Force HTTPS
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Basic Content-Security-Policy (API should only return JSON, not execute scripts)
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        
        return response
