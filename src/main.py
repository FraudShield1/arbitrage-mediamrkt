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
import threading
import time
from typing import Dict, Any

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

# Global scraper state management
scraper_state = {
    "is_running": False,
    "is_scheduled": False,
    "last_start": None,
    "last_stop": None,
    "total_sessions": 0,
    "current_session": None
}

# Scheduled task management
scheduler_thread = None
stop_scheduler = threading.Event()

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
            "status": "active" if recent_sessions or scraper_state["is_running"] else "inactive",
            "total_products": total_products,
            "recent_products_24h": recent_products,
            "recent_sessions": len(recent_sessions),
            "last_session": recent_sessions[0] if recent_sessions else None,
            "scraper_state": scraper_state,
            "scheduled": scraper_state["is_scheduled"],
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Scraper status check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

# Start 24/7 scraper
@app.post("/api/v1/scraper/start-24-7")
async def start_24_7_scraper():
    """Start 24/7 scheduled scraping."""
    global scraper_state, scheduler_thread, stop_scheduler
    
    if scraper_state["is_scheduled"]:
        return {
            "status": "already_running",
            "message": "24/7 scraper is already running",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    try:
        # Reset stop flag
        stop_scheduler.clear()
        
        # Start scheduler thread
        scheduler_thread = threading.Thread(target=run_scheduled_scraping, daemon=True)
        scheduler_thread.start()
        
        scraper_state["is_scheduled"] = True
        scraper_state["last_start"] = datetime.utcnow().isoformat()
        
        logger.info("24/7 scraper started")
        
        return {
            "status": "started",
            "message": "24/7 scraper started successfully",
            "schedule": {
                "light_scraping": "Every 15 minutes",
                "deep_scraping": "Every 3 hours",
                "analysis": "Every hour"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to start 24/7 scraper: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start 24/7 scraper: {str(e)}")

# GET endpoint for easy browser testing
@app.get("/api/v1/scraper/start-24-7")
async def start_24_7_scraper_get():
    """Start 24/7 scheduled scraping (GET version for browser testing)."""
    return await start_24_7_scraper()

# Stop 24/7 scraper
@app.post("/api/v1/scraper/stop-24-7")
async def stop_24_7_scraper():
    """Stop 24/7 scheduled scraping."""
    global scraper_state, stop_scheduler
    
    if not scraper_state["is_scheduled"]:
        return {
            "status": "not_running",
            "message": "24/7 scraper is not running",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    try:
        # Signal scheduler to stop
        stop_scheduler.set()
        
        scraper_state["is_scheduled"] = False
        scraper_state["last_stop"] = datetime.utcnow().isoformat()
        
        logger.info("24/7 scraper stopped")
        
        return {
            "status": "stopped",
            "message": "24/7 scraper stopped successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to stop 24/7 scraper: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop 24/7 scraper: {str(e)}")

# GET endpoint for easy browser testing
@app.get("/api/v1/scraper/stop-24-7")
async def stop_24_7_scraper_get():
    """Stop 24/7 scheduled scraping (GET version for browser testing)."""
    return await stop_24_7_scraper()

# Manual scraper start endpoint
@app.post("/api/v1/scraper/start")
async def start_scraping(background_tasks: BackgroundTasks):
    """Manually start a single scraping session."""
    try:
        # Import scraper here to avoid circular imports
        from src.services.scraper.mediamarkt_scraper import scrape_mediamarkt_products
        
        # Use the standalone function instead of class instantiation
        background_tasks.add_task(scrape_mediamarkt_products, 3, 20)
        
        scraper_state["is_running"] = True
        scraper_state["last_start"] = datetime.utcnow().isoformat()
        scraper_state["total_sessions"] += 1
        
        return {
            "status": "started",
            "message": "Scraping session started in background",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to start scraping: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start scraping: {str(e)}")

# Manual trigger for immediate scraping (for testing)
@app.post("/api/v1/scraper/trigger-now")
async def trigger_immediate_scraping():
    """Trigger immediate scraping session for testing."""
    try:
        logger.info("🎯 Manual trigger: Starting immediate scraping session")
        
        # Execute scraping session immediately
        products_found = await execute_scraping_session("light")
        
        return {
            "status": "completed",
            "message": f"Immediate scraping completed with {products_found} products",
            "products_found": products_found,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to trigger immediate scraping: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger scraping: {str(e)}")

# GET version for browser testing
@app.get("/api/v1/scraper/trigger-now")
async def trigger_immediate_scraping_get():
    """Trigger immediate scraping session (GET version for browser testing)."""
    return await trigger_immediate_scraping()

# Test scraper endpoint
@app.get("/api/v1/scraper/test")
async def test_scraper():
    """Test if scraper can be initialized."""
    try:
        # Import scraper here to avoid circular imports
        from src.services.scraper.mediamarkt_scraper import MediaMarktScraper
        
        scraper = MediaMarktScraper()
        
        return {
            "status": "success",
            "message": "Scraper can be initialized",
            "scraper_class": "MediaMarktScraper",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to initialize scraper: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

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

# Scraper control endpoint
@app.get("/api/v1/scraper/control")
async def get_scraper_control():
    """Get scraper control status and options."""
    return {
        "current_state": scraper_state,
        "available_actions": [
            "POST /api/v1/scraper/start-24-7 - Start 24/7 scraper",
            "POST /api/v1/scraper/stop-24-7 - Stop 24/7 scraper", 
            "POST /api/v1/scraper/start - Start single session",
            "GET /api/v1/scraper/status - Check status"
        ],
        "schedule_info": {
            "light_scraping": "Every 15 minutes",
            "deep_scraping": "Every 3 hours", 
            "analysis": "Every hour",
            "alerts": "Real-time"
        },
        "timestamp": datetime.utcnow().isoformat()
    }

def run_scheduled_scraping():
    """Run scheduled scraping in background thread."""
    global scraper_state
    
    logger.info("🚀 Starting scheduled scraping thread")
    
    while not stop_scheduler.is_set():
        try:
            current_time = datetime.utcnow()
            minute = current_time.minute
            hour = current_time.hour
            
            logger.info(f"⏰ Scheduled scraping check - Time: {current_time.strftime('%H:%M')}, Minute: {minute}, Hour: {hour}")
            
            # Light scraping every 15 minutes
            if minute % 15 == 0:
                logger.info("🔄 Starting scheduled light scraping")
                try:
                    # Create new event loop for this thread
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(execute_scraping_session("light"))
                    loop.close()
                except Exception as e:
                    logger.error(f"❌ Error in light scraping: {e}")
            
            # Deep scraping every 3 hours
            if hour % 3 == 0 and minute == 0:
                logger.info("🔥 Starting scheduled deep scraping")
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(execute_scraping_session("deep"))
                    loop.close()
                except Exception as e:
                    logger.error(f"❌ Error in deep scraping: {e}")
            
            # Analysis every hour
            if minute == 0:
                logger.info("📊 Starting scheduled analysis")
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(execute_analysis_session())
                    loop.close()
                except Exception as e:
                    logger.error(f"❌ Error in analysis: {e}")
            
            # Sleep for 1 minute before next check
            time.sleep(60)
            
        except Exception as e:
            logger.error(f"❌ Error in scheduled scraping loop: {e}")
            time.sleep(60)  # Wait before retrying
    
    logger.info("🛑 Scheduled scraping thread stopped")

async def execute_scraping_session(scraping_type: str):
    """Execute a scraping session."""
    try:
        logger.info(f"🎯 Starting {scraping_type} scraping session")
        
        from src.services.scraper.mediamarkt_scraper import scrape_mediamarkt_products
        
        scraper_state["is_running"] = True
        scraper_state["current_session"] = {
            "type": scraping_type,
            "started_at": datetime.utcnow().isoformat()
        }
        
        if scraping_type == "light":
            logger.info("📦 Light scraping: 3 pages, 50 products max")
            products = await scrape_mediamarkt_products(max_pages=3, max_products=50)
        else:  # deep
            logger.info("📦 Deep scraping: 10 pages, 200 products max")
            products = await scrape_mediamarkt_products(max_pages=10, max_products=200)
        
        scraper_state["is_running"] = False
        scraper_state["total_sessions"] += 1
        scraper_state["current_session"] = None
        
        logger.info(f"✅ {scraping_type.capitalize()} scraping completed", 
                   products_found=len(products),
                   session_type=scraping_type)
        
        return len(products)
        
    except Exception as e:
        logger.error(f"❌ Error in {scraping_type} scraping session: {e}")
        scraper_state["is_running"] = False
        scraper_state["current_session"] = None
        return 0

async def execute_analysis_session():
    """Execute analysis session."""
    try:
        logger.info("📊 Starting scheduled analysis session")
        
        # Get current product count
        from src.config.database import get_database_session
        db = get_database_session()
        total_products = await db.products.count_documents({})
        
        # Get recent products (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_products = await db.products.count_documents({
            "scraped_at": {"$gte": yesterday}
        })
        
        logger.info("📈 Analysis completed",
                   total_products=total_products,
                   recent_products_24h=recent_products)
        
        # Update scraper state with analysis results
        scraper_state["last_analysis"] = datetime.utcnow().isoformat()
        scraper_state["total_products"] = total_products
        scraper_state["recent_products_24h"] = recent_products
        
    except Exception as e:
        logger.error(f"❌ Error in analysis session: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    ) 