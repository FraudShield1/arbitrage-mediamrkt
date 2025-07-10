"""
API routes initialization.
"""

from fastapi import APIRouter
from .routes import products, alerts, stats, health, webhooks

# Create main router
router = APIRouter()

# Include route modules
router.include_router(products.router, prefix="/products", tags=["Products"])
router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
router.include_router(stats.router, prefix="/stats", tags=["Statistics"])
router.include_router(health.router, prefix="/health", tags=["Health"])
router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"]) 