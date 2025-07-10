"""
API v1 Router

Main router that includes all API endpoint modules for the arbitrage tool.
"""

from fastapi import APIRouter

from api.v1.endpoints import products, alerts, stats

# Create main API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(
    products.router,
    prefix="/products",
    tags=["Products"]
)

api_router.include_router(
    alerts.router,
    prefix="/alerts", 
    tags=["Alerts"]
)

api_router.include_router(
    stats.router,
    prefix="/stats",
    tags=["Statistics"]
) 