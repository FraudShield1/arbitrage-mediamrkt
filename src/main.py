"""
Cross-Market Arbitrage Tool API

FastAPI application for detecting arbitrage opportunities between MediaMarkt and Amazon.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from src.config.settings import get_settings
from src.config.database import get_database_session, check_database_connection
import structlog
import asyncio
from datetime import datetime, timedelta
import json

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

# Database health check
@app.get("/health/database")
async def database_health_check():
    """Check database connection."""
    try:
        is_healthy = await check_database_connection()
        return {
            "database": "healthy" if is_healthy else "unhealthy",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(status_code=503, detail="Database connection failed")

# Scraper status endpoint
@app.get("/api/v1/scraper/status")
async def scraper_status():
    """Get current scraper status."""
    try:
        db = get_database_session()
        
        # Get recent scraping sessions
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_sessions = await db.scraping_sessions.find({
            "created_at": {"$gte": yesterday}
        }).sort("created_at", -1).limit(5).to_list(length=5)
        
        # Get product counts
        total_products = await db.products.count_documents({})
        recent_products = await db.products.count_documents({
            "created_at": {"$gte": yesterday}
        })
        
        return {
            "status": "active" if recent_sessions else "inactive",
            "total_products": total_products,
            "recent_products_24h": recent_products,
            "recent_sessions": len(recent_sessions),
            "last_session": recent_sessions[0] if recent_sessions else None,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Scraper status check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

# Manual scraper start endpoint
@app.post("/api/v1/scraper/start")
async def start_scraping(background_tasks: BackgroundTasks):
    """Manually start a scraping session."""
    try:
        # Import scraper here to avoid circular imports
        from src.services.scraper.mediamarkt_scraper import MediaMarktScraper
        
        scraper = MediaMarktScraper()
        
        # Add scraping task to background
        background_tasks.add_task(scraper.scrape_products)
        
        return {
            "status": "started",
            "message": "Scraping session started in background",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to start scraping: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start scraping: {str(e)}")

# Product count endpoint
@app.get("/api/v1/products/count")
async def get_product_count():
    """Get total product count."""
    try:
        db = get_database_session()
        count = await db.products.count_documents({})
        return {
            "count": count,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get product count: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# Recent alerts endpoint
@app.get("/api/v1/alerts/recent")
async def get_recent_alerts():
    """Get recent alerts."""
    try:
        db = get_database_session()
        yesterday = datetime.utcnow() - timedelta(days=1)
        
        alerts = await db.price_alerts.find({
            "created_at": {"$gte": yesterday}
        }).sort("created_at", -1).limit(10).to_list(length=10)
        
        return {
            "alerts": alerts,
            "count": len(alerts),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get recent alerts: {e}")
        return {
            "alerts": [],
            "count": 0,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

# Arbitrage opportunities endpoint
@app.get("/api/v1/opportunities")
async def get_opportunities():
    """Get current arbitrage opportunities."""
    try:
        db = get_database_session()
        
        opportunities = await db.products.find({
            "arbitrage_opportunity": True
        }).sort("profit_margin", -1).limit(20).to_list(length=20)
        
        return {
            "opportunities": opportunities,
            "count": len(opportunities),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get opportunities: {e}")
        return {
            "opportunities": [],
            "count": 0,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    ) 