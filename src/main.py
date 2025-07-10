"""
Cross-Market Arbitrage Tool API

FastAPI application for detecting arbitrage opportunities between MediaMarkt and Amazon.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config.settings import get_settings
import structlog

logger = structlog.get_logger(__name__)

# Create FastAPI app
settings = get_settings()
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.app_version,
    description="Cross-market arbitrage detection and monitoring system",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Basic health check endpoint
@app.get("/health")
async def health_check():
    """Basic health check endpoint for load balancers."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.app_version,
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with welcome message."""
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": settings.app_version,
        "docs": "/docs" if settings.DEBUG else "Documentation disabled in production",
        "health": "/health",
        "status": "Production ready for deployment"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    ) 