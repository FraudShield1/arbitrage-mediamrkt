"""
Cross-Market Arbitrage Tool - FastAPI Application

Main FastAPI application with middleware configuration, CORS setup,
and error handlers for the arbitrage detection system.
"""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import uvicorn

from src.config.settings import get_settings
from src.config.database import get_database, close_database
from src.api import products, alerts, stats, auth
from src.api import health
from src.auth.middleware import AuthMiddleware
from src.utils.logging import configure_logging, get_logger

# Configure logging on startup
configure_logging()
logger = get_logger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info("Starting Cross-Market Arbitrage Tool API...")
    await get_database()
    logger.info("Database connection established")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Cross-Market Arbitrage Tool API...")
    await close_database()
    logger.info("Database connection closed")


# Create FastAPI application
app = FastAPI(
    title="Cross-Market Arbitrage Tool API",
    description="API for finding profitable arbitrage opportunities between MediaMarkt.pt and Amazon EU",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# Authentication Middleware
auth_middleware = AuthMiddleware()
app.middleware("http")(auth_middleware)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# Trusted Host Middleware (security)
if not settings.DEBUG:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )


# Global Exception Handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTP exceptions with consistent error format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "HTTPException",
                "message": exc.detail,
                "status_code": exc.status_code
            }
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors with detailed messages."""
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "type": "ValidationError",
                "message": "Request validation failed",
                "details": exc.errors()
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions with error logging."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "type": "InternalServerError",
                "message": "An unexpected error occurred" if not settings.DEBUG else str(exc)
            }
        }
    )


# Health Check Endpoint
@app.get("/health", tags=["System"])
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "arbitrage-api",
        "version": "1.0.0"
    }


@app.get("/", tags=["System"])
async def root() -> Dict[str, str]:
    """Root endpoint with API information."""
    return {
        "message": "Cross-Market Arbitrage Tool API",
        "docs": "/docs",
        "health": "/health"
    }


# Include routers
app.include_router(products.router, prefix="/api/v1/products", tags=["Products"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["Alerts"]) 
app.include_router(stats.router, prefix="/api/v1/stats", tags=["Statistics"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(health.router, prefix="/api/v1/health", tags=["Health"])

# Add webhooks router
from src.api.routes.webhooks import router as webhooks_router
app.include_router(webhooks_router, prefix="/api/v1/webhooks", tags=["Webhooks"])


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level="info"
    ) 