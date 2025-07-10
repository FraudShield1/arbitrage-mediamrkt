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

# Detailed 24/7 monitoring endpoint
@app.get("/api/v1/scraper/monitor")
async def get_detailed_monitor():
    """Get detailed 24/7 scraper monitoring information."""
    try:
        db = get_database_session()
        
        # Get current statistics
        total_products = await db.products.count_documents({})
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_products = await db.products.count_documents({
            "scraped_at": {"$gte": yesterday}
        })
        
        # Calculate uptime
        uptime_seconds = 0
        if scraper_state["last_start"]:
            start_time = datetime.fromisoformat(scraper_state["last_start"].replace('Z', '+00:00'))
            uptime_seconds = (datetime.utcnow() - start_time).total_seconds()
        
        # Get current session info
        current_session = scraper_state.get("current_session", {})
        session_status = "idle"
        if current_session:
            if current_session.get("status") == "running":
                session_status = "active"
            elif current_session.get("status") == "completed":
                session_status = "completed"
            elif current_session.get("status") == "failed":
                session_status = "failed"
        
        return {
            "24_7_status": {
                "scheduled": scraper_state["is_scheduled"],
                "running": scraper_state["is_running"],
                "uptime_seconds": uptime_seconds,
                "uptime_formatted": f"{int(uptime_seconds // 3600)}h {int((uptime_seconds % 3600) // 60)}m",
                "total_sessions": scraper_state["total_sessions"],
                "last_start": scraper_state["last_start"],
                "last_stop": scraper_state["last_stop"]
            },
            "current_session": {
                "status": session_status,
                "details": current_session
            },
            "statistics": {
                "total_products": total_products,
                "recent_products_24h": recent_products,
                "recent_sessions_24h": scraper_state.get("recent_sessions_24h", 0),
                "last_analysis": scraper_state.get("last_analysis")
            },
            "schedule": {
                "light_scraping": "Every 15 minutes (3 pages, 50 products)",
                "deep_scraping": "Every 3 hours (10 pages, 200 products)",
                "analysis": "Every hour (database statistics)",
                "monitoring": "Continuous (every minute)"
            },
            "next_runs": {
                "light_scraping": "Next 15-minute mark",
                "deep_scraping": "Next 3-hour mark",
                "analysis": "Next hour mark"
            },
            "logging": {
                "level": "Detailed",
                "features": [
                    "Session start/end timestamps",
                    "Product count tracking",
                    "Duration measurements",
                    "Error details with stack traces",
                    "Heartbeat monitoring",
                    "Database statistics"
                ]
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get detailed monitor: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

def run_scheduled_scraping():
    """Run continuous 24/7 scraping with detailed logging."""
    global scraper_state
    
    logger.info("🚀 Starting 24/7 continuous scraping thread")
    logger.info("📊 Configuration: Continuous scraping with detailed logging")
    logger.info("⏰ Schedule: Light scraping every 15 min, Deep every 3 hours, Analysis every hour")
    
    session_count = 0
    last_light_scraping = None
    last_deep_scraping = None
    last_analysis = None
    
    while not stop_scheduler.is_set():
        try:
            current_time = datetime.utcnow()
            minute = current_time.minute
            hour = current_time.hour
            
            logger.info(f"⏰ 24/7 Check - Time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}, Minute: {minute}, Hour: {hour}")
            
            # Light scraping every 15 minutes (continuous)
            if minute % 15 == 0:
                if last_light_scraping != minute:  # Prevent duplicate runs
                    logger.info("🔄 Starting scheduled light scraping session")
                    try:
                        # Create new event loop for this thread
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                        logger.info("📦 Executing light scraping: 3 pages, 50 products max")
                        products_found = loop.run_until_complete(execute_scraping_session("light"))
                        
                        session_count += 1
                        last_light_scraping = minute
                        
                        logger.info(f"✅ Light scraping session #{session_count} completed", 
                                   products_found=products_found,
                                   session_count=session_count,
                                   timestamp=current_time.strftime('%H:%M:%S'))
                        
                        loop.close()
                    except Exception as e:
                        logger.error(f"❌ Error in light scraping session #{session_count}: {e}")
                        logger.error(f"🔧 Error details: {type(e).__name__}: {str(e)}")
            
            # Deep scraping every 3 hours (continuous)
            if hour % 3 == 0 and minute == 0:
                if last_deep_scraping != hour:  # Prevent duplicate runs
                    logger.info("🔥 Starting scheduled deep scraping session")
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                        logger.info("📦 Executing deep scraping: 10 pages, 200 products max")
                        products_found = loop.run_until_complete(execute_scraping_session("deep"))
                        
                        session_count += 1
                        last_deep_scraping = hour
                        
                        logger.info(f"✅ Deep scraping session #{session_count} completed", 
                                   products_found=products_found,
                                   session_count=session_count,
                                   timestamp=current_time.strftime('%H:%M:%S'))
                        
                        loop.close()
                    except Exception as e:
                        logger.error(f"❌ Error in deep scraping session #{session_count}: {e}")
                        logger.error(f"🔧 Error details: {type(e).__name__}: {str(e)}")
            
            # Analysis every hour (continuous)
            if minute == 0:
                if last_analysis != hour:  # Prevent duplicate runs
                    logger.info("📊 Starting scheduled analysis session")
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                        logger.info("📈 Executing analysis: Database statistics and monitoring")
                        loop.run_until_complete(execute_analysis_session())
                        
                        last_analysis = hour
                        
                        logger.info(f"✅ Analysis session completed", 
                                   session_count=session_count,
                                   timestamp=current_time.strftime('%H:%M:%S'))
                        
                        loop.close()
                    except Exception as e:
                        logger.error(f"❌ Error in analysis session: {e}")
                        logger.error(f"🔧 Error details: {type(e).__name__}: {str(e)}")
            
            # Continuous monitoring and health check
            logger.info(f"💓 24/7 Heartbeat - Active sessions: {session_count}, " +
                       f"Last light: {last_light_scraping}, Last deep: {last_deep_scraping}, " +
                       f"Last analysis: {last_analysis}")
            
            # Sleep for 1 minute before next check (continuous monitoring)
            time.sleep(60)
            
        except Exception as e:
            logger.error(f"❌ Critical error in 24/7 scraping loop: {e}")
            logger.error(f"🔧 Error type: {type(e).__name__}")
            logger.error(f"🔧 Error details: {str(e)}")
            logger.info("🔄 Retrying in 60 seconds...")
            time.sleep(60)  # Wait before retrying
    
    logger.info("🛑 24/7 continuous scraping thread stopped")
    logger.info(f"📊 Final session count: {session_count}")

async def execute_scraping_session(scraping_type: str):
    """Execute a scraping session with detailed logging."""
    try:
        session_start = datetime.utcnow()
        logger.info(f"🎯 Starting {scraping_type} scraping session at {session_start.strftime('%H:%M:%S')}")
        
        from src.services.scraper.mediamarkt_scraper import scrape_mediamarkt_products
        
        # Update scraper state
        scraper_state["is_running"] = True
        scraper_state["current_session"] = {
            "type": scraping_type,
            "started_at": session_start.isoformat(),
            "status": "running"
        }
        
        logger.info(f"📦 {scraping_type.capitalize()} scraping configuration:")
        if scraping_type == "light":
            logger.info("   • Pages: 3")
            logger.info("   • Max products: 50")
            logger.info("   • Type: Light scraping (quick scan)")
            products = await scrape_mediamarkt_products(max_pages=3, max_products=50)
        else:  # deep
            logger.info("   • Pages: 10")
            logger.info("   • Max products: 200")
            logger.info("   • Type: Deep scraping (comprehensive scan)")
            products = await scrape_mediamarkt_products(max_pages=10, max_products=200)
        
        session_end = datetime.utcnow()
        session_duration = (session_end - session_start).total_seconds()
        
        # Update scraper state
        scraper_state["is_running"] = False
        scraper_state["total_sessions"] += 1
        scraper_state["current_session"] = {
            "type": scraping_type,
            "started_at": session_start.isoformat(),
            "completed_at": session_end.isoformat(),
            "duration_seconds": session_duration,
            "products_found": len(products),
            "status": "completed"
        }
        
        logger.info(f"✅ {scraping_type.capitalize()} scraping session completed successfully")
        logger.info(f"📊 Session statistics:")
        logger.info(f"   • Products found: {len(products)}")
        logger.info(f"   • Duration: {session_duration:.2f} seconds")
        logger.info(f"   • Started: {session_start.strftime('%H:%M:%S')}")
        logger.info(f"   • Completed: {session_end.strftime('%H:%M:%S')}")
        logger.info(f"   • Session type: {scraping_type}")
        
        return len(products)
        
    except Exception as e:
        session_end = datetime.utcnow()
        session_duration = (session_end - session_start).total_seconds()
        
        logger.error(f"❌ {scraping_type.capitalize()} scraping session failed")
        logger.error(f"📊 Failed session statistics:")
        logger.error(f"   • Duration: {session_duration:.2f} seconds")
        logger.error(f"   • Started: {session_start.strftime('%H:%M:%S')}")
        logger.error(f"   • Failed: {session_end.strftime('%H:%M:%S')}")
        logger.error(f"   • Error: {type(e).__name__}: {str(e)}")
        
        scraper_state["is_running"] = False
        scraper_state["current_session"] = {
            "type": scraping_type,
            "started_at": session_start.isoformat(),
            "failed_at": session_end.isoformat(),
            "duration_seconds": session_duration,
            "error": str(e),
            "status": "failed"
        }
        
        return 0

async def execute_analysis_session():
    """Execute analysis session with detailed logging."""
    try:
        session_start = datetime.utcnow()
        logger.info(f"📊 Starting analysis session at {session_start.strftime('%H:%M:%S')}")
        
        # Get current product count
        from src.config.database import get_database_session
        db = get_database_session()
        
        logger.info("📈 Collecting database statistics...")
        total_products = await db.products.count_documents({})
        
        # Get recent products (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_products = await db.products.count_documents({
            "scraped_at": {"$gte": yesterday}
        })
        
        # Get session statistics
        recent_sessions = await db.scraping_sessions.find({
            "created_at": {"$gte": yesterday}
        }).sort("created_at", -1).limit(10).to_list(length=10)
        
        session_end = datetime.utcnow()
        session_duration = (session_end - session_start).total_seconds()
        
        logger.info("📈 Analysis session completed successfully")
        logger.info(f"📊 Analysis statistics:")
        logger.info(f"   • Total products in DB: {total_products}")
        logger.info(f"   • Recent products (24h): {recent_products}")
        logger.info(f"   • Recent sessions (24h): {len(recent_sessions)}")
        logger.info(f"   • Duration: {session_duration:.2f} seconds")
        logger.info(f"   • Started: {session_start.strftime('%H:%M:%S')}")
        logger.info(f"   • Completed: {session_end.strftime('%H:%M:%S')}")
        
        # Update scraper state with analysis results
        scraper_state["last_analysis"] = session_end.isoformat()
        scraper_state["total_products"] = total_products
        scraper_state["recent_products_24h"] = recent_products
        scraper_state["recent_sessions_24h"] = len(recent_sessions)
        
    except Exception as e:
        session_end = datetime.utcnow()
        session_duration = (session_end - session_start).total_seconds()
        
        logger.error(f"❌ Analysis session failed")
        logger.error(f"📊 Failed analysis statistics:")
        logger.error(f"   • Duration: {session_duration:.2f} seconds")
        logger.error(f"   • Started: {session_start.strftime('%H:%M:%S')}")
        logger.error(f"   • Failed: {session_end.strftime('%H:%M:%S')}")
        logger.error(f"   • Error: {type(e).__name__}: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    ) 