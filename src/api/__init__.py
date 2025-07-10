"""
API routes initialization.
"""

from fastapi import APIRouter
from .v1.endpoints import products, alerts, stats
from . import health
from .routes import webhooks

# Create main router
router = APIRouter()

# Include v1 endpoint modules
router.include_router(products.router, prefix="/v1/products", tags=["Products"])
router.include_router(alerts.router, prefix="/v1/alerts", tags=["Alerts"])  
router.include_router(stats.router, prefix="/v1/stats", tags=["Statistics"])

# Include standalone modules
router.include_router(health.router, prefix="/health", tags=["Health"])
router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"]) 