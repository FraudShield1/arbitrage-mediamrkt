"""
Comprehensive health check system for monitoring service status.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import asyncpg
import redis.asyncio as redis
import httpx
import structlog

from src.config.settings import get_settings
from src.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class HealthStatus(str, Enum):
    """Health check status enumeration."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class HealthCheckResult:
    """Result of a health check."""
    
    def __init__(
        self,
        name: str,
        status: HealthStatus,
        message: str = "",
        details: Dict[str, Any] = None,
        duration_ms: float = 0,
        timestamp: datetime = None
    ):
        self.name = name
        self.status = status
        self.message = message
        self.details = details or {}
        self.duration_ms = duration_ms
        self.timestamp = timestamp or datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat() + "Z"
        }


class BaseHealthCheck:
    """Base class for health checks."""
    
    def __init__(self, name: str, timeout: float = 5.0):
        self.name = name
        self.timeout = timeout
        self.logger = get_logger(f"{__name__}.{name}")
    
    async def check(self) -> HealthCheckResult:
        """Perform the health check."""
        start_time = time.time()
        
        try:
            result = await asyncio.wait_for(self._perform_check(), timeout=self.timeout)
            duration_ms = (time.time() - start_time) * 1000
            
            if result:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.HEALTHY,
                    message="Service is healthy",
                    duration_ms=duration_ms
                )
            else:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.UNHEALTHY,
                    message="Service check failed",
                    duration_ms=duration_ms
                )
        
        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.warning(f"Health check timeout for {self.name}")
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timed out after {self.timeout}s",
                duration_ms=duration_ms
            )
        
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.error(f"Health check error for {self.name}", error=str(e))
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                duration_ms=duration_ms
            )
    
    async def _perform_check(self) -> bool:
        """Override this method to implement specific health check logic."""
        raise NotImplementedError


class DatabaseHealthCheck(BaseHealthCheck):
    """Health check for PostgreSQL database connectivity."""
    
    def __init__(self):
        super().__init__("database", timeout=10.0)
    
    async def _perform_check(self) -> bool:
        """Check database connectivity and basic query execution."""
        try:
            conn = await asyncpg.connect(str(settings.DATABASE_URL))
            
            # Simple query to test connectivity
            result = await conn.fetchval("SELECT 1")
            
            # Check connection pool status
            if hasattr(conn, '_con') and conn._con:
                pool_size = 1  # Single connection for health check
            else:
                pool_size = 0
            
            await conn.close()
            
            self.logger.debug("Database health check passed", pool_size=pool_size)
            return result == 1
            
        except Exception as e:
            self.logger.error("Database health check failed", error=str(e))
            return False


class RedisHealthCheck(BaseHealthCheck):
    """Health check for Redis connectivity."""
    
    def __init__(self):
        super().__init__("redis", timeout=5.0)
    
    async def _perform_check(self) -> bool:
        """Check Redis connectivity and basic operations."""
        try:
            redis_client = redis.from_url(str(settings.REDIS_URL))
            
            # Test basic operations
            test_key = "health_check:test"
            await redis_client.set(test_key, "test_value", ex=60)
            result = await redis_client.get(test_key)
            await redis_client.delete(test_key)
            
            # Get Redis info
            info = await redis_client.info()
            memory_usage = info.get('used_memory', 0)
            
            await redis_client.close()
            
            self.logger.debug("Redis health check passed", memory_usage=memory_usage)
            return result == b"test_value"
            
        except Exception as e:
            self.logger.error("Redis health check failed", error=str(e))
            return False


class CeleryHealthCheck(BaseHealthCheck):
    """Health check for Celery worker availability."""
    
    def __init__(self):
        super().__init__("celery", timeout=10.0)
    
    async def _perform_check(self) -> bool:
        """Check if Celery workers are available and responsive."""
        try:
            from celery import Celery
            
            # Create Celery app instance
            celery_app = Celery('arbitrage')
            celery_app.conf.broker_url = str(settings.REDIS_URL)
            celery_app.conf.result_backend = str(settings.REDIS_URL)
            
            # Get active workers
            inspect = celery_app.control.inspect()
            active_workers = inspect.active()
            
            if active_workers:
                worker_count = len(active_workers)
                self.logger.debug("Celery health check passed", worker_count=worker_count)
                return True
            else:
                self.logger.warning("No active Celery workers found")
                return False
                
        except Exception as e:
            self.logger.error("Celery health check failed", error=str(e))
            return False


class ExternalAPIHealthCheck(BaseHealthCheck):
    """Health check for external API availability."""
    
    def __init__(self, name: str, url: str, expected_status: int = 200):
        super().__init__(f"external_api_{name}", timeout=10.0)
        self.url = url
        self.expected_status = expected_status
    
    async def _perform_check(self) -> bool:
        """Check external API availability."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.url, timeout=self.timeout)
                
                is_healthy = response.status_code == self.expected_status
                self.logger.debug(
                    f"External API health check for {self.name}",
                    url=self.url,
                    status_code=response.status_code,
                    healthy=is_healthy
                )
                return is_healthy
                
        except Exception as e:
            self.logger.error(f"External API health check failed for {self.name}", error=str(e))
            return False


class DiskSpaceHealthCheck(BaseHealthCheck):
    """Health check for disk space availability."""
    
    def __init__(self, path: str = "/", threshold_percent: float = 90.0):
        super().__init__("disk_space", timeout=5.0)
        self.path = path
        self.threshold_percent = threshold_percent
    
    async def _perform_check(self) -> bool:
        """Check disk space usage."""
        try:
            import shutil
            
            total, used, free = shutil.disk_usage(self.path)
            used_percent = (used / total) * 100
            
            is_healthy = used_percent < self.threshold_percent
            
            self.logger.debug(
                "Disk space health check",
                path=self.path,
                used_percent=round(used_percent, 2),
                threshold_percent=self.threshold_percent,
                healthy=is_healthy
            )
            
            return is_healthy
            
        except Exception as e:
            self.logger.error("Disk space health check failed", error=str(e))
            return False


class MemoryHealthCheck(BaseHealthCheck):
    """Health check for memory usage."""
    
    def __init__(self, threshold_percent: float = 90.0):
        super().__init__("memory", timeout=5.0)
        self.threshold_percent = threshold_percent
    
    async def _perform_check(self) -> bool:
        """Check memory usage."""
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            used_percent = memory.percent
            
            is_healthy = used_percent < self.threshold_percent
            
            self.logger.debug(
                "Memory health check",
                used_percent=used_percent,
                threshold_percent=self.threshold_percent,
                healthy=is_healthy
            )
            
            return is_healthy
            
        except Exception as e:
            self.logger.error("Memory health check failed", error=str(e))
            return False


class HealthCheckManager:
    """Manager for running and aggregating health checks."""
    
    def __init__(self):
        self.checks: List[BaseHealthCheck] = []
        self.logger = get_logger(__name__)
        self.last_results: Dict[str, HealthCheckResult] = {}
        
        # Register default health checks
        self._register_default_checks()
    
    def _register_default_checks(self):
        """Register default health checks."""
        self.checks = [
            DatabaseHealthCheck(),
            RedisHealthCheck(),
            CeleryHealthCheck(),
            DiskSpaceHealthCheck(),
            MemoryHealthCheck(),
        ]
        
        # Add external API checks
        if hasattr(settings, 'keepa') and settings.keepa.api_key:
            self.checks.append(
                ExternalAPIHealthCheck("keepa", "https://api.keepa.com/")
            )
    
    def register_check(self, health_check: BaseHealthCheck):
        """Register a custom health check."""
        self.checks.append(health_check)
        self.logger.info(f"Registered health check: {health_check.name}")
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all registered health checks."""
        start_time = time.time()
        
        # Run all checks concurrently
        check_tasks = [check.check() for check in self.checks]
        results = await asyncio.gather(*check_tasks, return_exceptions=True)
        
        # Process results
        check_results = {}
        healthy_count = 0
        total_count = len(self.checks)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Handle exceptions from gather
                check_name = self.checks[i].name
                check_results[check_name] = HealthCheckResult(
                    name=check_name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check exception: {str(result)}"
                ).to_dict()
            else:
                check_results[result.name] = result.to_dict()
                if result.status == HealthStatus.HEALTHY:
                    healthy_count += 1
                
                # Cache result
                self.last_results[result.name] = result
        
        # Determine overall status
        if healthy_count == total_count:
            overall_status = HealthStatus.HEALTHY
        elif healthy_count > 0:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.UNHEALTHY
        
        duration_ms = (time.time() - start_time) * 1000
        
        health_summary = {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "duration_ms": duration_ms,
            "summary": {
                "total_checks": total_count,
                "healthy_checks": healthy_count,
                "unhealthy_checks": total_count - healthy_count
            },
            "checks": check_results
        }
        
        self.logger.info(
            "Health checks completed",
            overall_status=overall_status.value,
            healthy_count=healthy_count,
            total_count=total_count,
            duration_ms=duration_ms
        )
        
        return health_summary
    
    async def run_check(self, check_name: str) -> Optional[Dict[str, Any]]:
        """Run a specific health check by name."""
        for check in self.checks:
            if check.name == check_name:
                result = await check.check()
                self.last_results[check_name] = result
                return result.to_dict()
        
        return None
    
    def get_last_results(self) -> Dict[str, Any]:
        """Get the last health check results without running new checks."""
        if not self.last_results:
            return {
                "status": HealthStatus.UNKNOWN.value,
                "message": "No health checks have been performed yet",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "checks": {}
            }
        
        # Determine overall status from cached results
        healthy_count = sum(
            1 for result in self.last_results.values() 
            if result.status == HealthStatus.HEALTHY
        )
        total_count = len(self.last_results)
        
        if healthy_count == total_count:
            overall_status = HealthStatus.HEALTHY
        elif healthy_count > 0:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.UNHEALTHY
        
        return {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "summary": {
                "total_checks": total_count,
                "healthy_checks": healthy_count,
                "unhealthy_checks": total_count - healthy_count
            },
            "checks": {name: result.to_dict() for name, result in self.last_results.items()}
        }


# Global health check manager
health_manager = HealthCheckManager()


# Convenience functions
async def run_all_health_checks() -> Dict[str, Any]:
    """Run all health checks."""
    return await health_manager.run_all_checks()


async def run_health_check(check_name: str) -> Optional[Dict[str, Any]]:
    """Run a specific health check."""
    return await health_manager.run_check(check_name)


def get_health_status() -> Dict[str, Any]:
    """Get last health check results."""
    return health_manager.get_last_results() 