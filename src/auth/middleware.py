"""
Authentication middleware for FastAPI.
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

class AuthMiddleware(BaseHTTPMiddleware):
    """Authentication middleware."""

    async def dispatch(self, request: Request, call_next):
        """Process the request."""
        # Allow all requests without authentication for now
        response = await call_next(request)
        return response 