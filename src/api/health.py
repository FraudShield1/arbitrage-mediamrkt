"""
Health check API endpoints for system monitoring.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any, Optional
import structlog

from src.utils.health_checks import (
    run_all_health_checks, 
    run_health_check, 
    get_health_status,
    HealthStatus
)
from src.auth.middleware import require_auth
from src.auth.models import User

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/", response_model=Dict[str, Any])
async def get_health():
    """
    Get basic health status without running checks.
    This is a lightweight endpoint for load balancer health checks.
    """
    try:
        health_data = get_health_status()
        
        # Return appropriate HTTP status based on health
        if health_data.get("status") == HealthStatus.HEALTHY.value:
            return health_data
        elif health_data.get("status") == HealthStatus.DEGRADED.value:
            return health_data
        else:
            # Return 503 for unhealthy status
            return HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=health_data
            )
    
    except Exception as e:
        logger.error("Health check endpoint error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"status": "error", "message": "Health check failed"}
        )


@router.get("/live", response_model=Dict[str, Any])
async def liveness_probe():
    """
    Kubernetes liveness probe endpoint.
    Returns 200 if the application is alive and can handle requests.
    """
    return {
        "status": "alive",
        "timestamp": "2024-01-01T00:00:00Z",
        "service": "arbitrage-tool"
    }


@router.get("/ready", response_model=Dict[str, Any])
async def readiness_probe():
    """
    Kubernetes readiness probe endpoint.
    Returns 200 if the application is ready to handle requests.
    """
    try:
        # Run critical health checks for readiness
        from src.utils.health_checks import health_manager
        
        # Check database and Redis (critical for readiness)
        db_result = await health_manager.run_check("database")
        redis_result = await health_manager.run_check("redis")
        
        if (db_result and db_result["status"] == "healthy" and 
            redis_result and redis_result["status"] == "healthy"):
            return {
                "status": "ready",
                "timestamp": "2024-01-01T00:00:00Z",
                "checks": {
                    "database": db_result,
                    "redis": redis_result
                }
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "status": "not_ready",
                    "checks": {
                        "database": db_result,
                        "redis": redis_result
                    }
                }
            )
    
    except Exception as e:
        logger.error("Readiness probe error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "error": str(e)}
        )


@router.get("/detailed", response_model=Dict[str, Any])
async def get_detailed_health(current_user: User = Depends(require_auth)):
    """
    Get detailed health status by running all health checks.
    Requires authentication as this is more resource-intensive.
    """
    try:
        logger.info("Running detailed health checks", user_id=current_user.id)
        
        health_data = await run_all_health_checks()
        
        # Log health check results
        logger.info(
            "Detailed health check completed",
            overall_status=health_data.get("status"),
            healthy_count=health_data.get("summary", {}).get("healthy_checks"),
            total_count=health_data.get("summary", {}).get("total_checks"),
            user_id=current_user.id
        )
        
        return health_data
    
    except Exception as e:
        logger.error("Detailed health check error", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"status": "error", "message": "Detailed health check failed"}
        )


@router.get("/check/{check_name}", response_model=Dict[str, Any])
async def get_specific_health_check(
    check_name: str,
    current_user: User = Depends(require_auth)
):
    """
    Run a specific health check by name.
    """
    try:
        logger.info(f"Running specific health check: {check_name}", user_id=current_user.id)
        
        result = await run_health_check(check_name)
        
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Health check '{check_name}' not found"
            )
        
        logger.info(
            f"Health check '{check_name}' completed",
            status=result.get("status"),
            duration_ms=result.get("duration_ms"),
            user_id=current_user.id
        )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check '{check_name}' error", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check '{check_name}' failed: {str(e)}"
        )


@router.get("/metrics", response_model=Dict[str, Any])
async def get_health_metrics(current_user: User = Depends(require_auth)):
    """
    Get health metrics for monitoring and alerting.
    """
    try:
        from src.utils.health_checks import health_manager
        
        # Get last results and calculate metrics
        health_data = health_manager.get_last_results()
        
        # Calculate availability metrics
        checks = health_data.get("checks", {})
        total_checks = len(checks)
        healthy_checks = sum(1 for check in checks.values() if check.get("status") == "healthy")
        
        availability_percentage = (healthy_checks / total_checks * 100) if total_checks > 0 else 0
        
        # Calculate average response time
        durations = [check.get("duration_ms", 0) for check in checks.values()]
        avg_response_time = sum(durations) / len(durations) if durations else 0
        
        metrics = {
            "availability_percentage": round(availability_percentage, 2),
            "total_checks": total_checks,
            "healthy_checks": healthy_checks,
            "unhealthy_checks": total_checks - healthy_checks,
            "average_response_time_ms": round(avg_response_time, 2),
            "last_check_timestamp": health_data.get("timestamp"),
            "status_breakdown": {}
        }
        
        # Status breakdown
        status_counts = {}
        for check in checks.values():
            status = check.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        metrics["status_breakdown"] = status_counts
        
        logger.info(
            "Health metrics calculated",
            availability=availability_percentage,
            avg_response_time=avg_response_time,
            user_id=current_user.id
        )
        
        return metrics
    
    except Exception as e:
        logger.error("Health metrics calculation error", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to calculate health metrics"}
        ) 