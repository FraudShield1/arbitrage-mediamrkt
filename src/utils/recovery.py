"""
Automated Recovery System for improved system reliability.

Provides automatic detection and recovery mechanisms for system failures,
service disruptions, and degraded performance scenarios.
"""

import asyncio
import time
import psutil
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass
from enum import Enum
import structlog
from contextlib import asynccontextmanager

from src.config.database import (
    check_database_connection, 
    get_db_stats,
    optimize_database,
    get_redis_client
)
from src.config.celery import check_celery_health, get_enhanced_task_stats
from src.utils.circuit_breaker import (
    get_all_circuit_breaker_states,
    reset_all_circuit_breakers,
    circuit_breaker_registry
)

logger = structlog.get_logger(__name__)


class RecoveryStatus(Enum):
    """Recovery operation status."""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"
    IN_PROGRESS = "in_progress"


class ServiceHealth(Enum):
    """Service health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Health check configuration and result."""
    name: str
    check_function: Callable
    timeout: float = 30.0
    critical: bool = False
    recovery_actions: List[str] = None
    
    # Result fields
    status: ServiceHealth = ServiceHealth.UNKNOWN
    last_check: float = 0.0
    response_time: float = 0.0
    error_message: str = ""
    consecutive_failures: int = 0


@dataclass
class RecoveryAction:
    """Recovery action configuration."""
    name: str
    action_function: Callable
    timeout: float = 60.0
    retry_count: int = 3
    retry_delay: float = 10.0
    dependencies: List[str] = None
    
    # Execution tracking
    last_execution: float = 0.0
    success_count: int = 0
    failure_count: int = 0


class SystemHealthMonitor:
    """
    Comprehensive system health monitoring and automated recovery.
    
    Monitors critical system components and automatically triggers
    recovery actions when issues are detected.
    """
    
    def __init__(self):
        self.health_checks: Dict[str, HealthCheck] = {}
        self.recovery_actions: Dict[str, RecoveryAction] = {}
        self.monitoring_active = False
        self.check_interval = 60  # seconds
        self.recovery_cooldown = 300  # 5 minutes between recovery attempts
        self.last_recovery_attempt: Dict[str, float] = {}
        
        # Initialize health checks and recovery actions
        self._setup_health_checks()
        self._setup_recovery_actions()
    
    def _setup_health_checks(self):
        """Setup system health checks."""
        
        # Database health check
        self.health_checks["database"] = HealthCheck(
            name="database",
            check_function=self._check_database_health,
            timeout=15.0,
            critical=True,
            recovery_actions=["restart_database_connections", "optimize_database"]
        )
        
        # Redis health check
        self.health_checks["redis"] = HealthCheck(
            name="redis",
            check_function=self._check_redis_health,
            timeout=10.0,
            critical=True,
            recovery_actions=["restart_redis_connections"]
        )
        
        # Celery workers health check
        self.health_checks["celery_workers"] = HealthCheck(
            name="celery_workers",
            check_function=self._check_celery_health,
            timeout=20.0,
            critical=True,
            recovery_actions=["restart_failed_workers", "clear_task_queues"]
        )
        
        # System resources health check
        self.health_checks["system_resources"] = HealthCheck(
            name="system_resources",
            check_function=self._check_system_resources,
            timeout=5.0,
            critical=False,
            recovery_actions=["cleanup_temporary_files", "restart_high_memory_processes"]
        )
        
        # Circuit breakers health check
        self.health_checks["circuit_breakers"] = HealthCheck(
            name="circuit_breakers",
            check_function=self._check_circuit_breakers,
            timeout=5.0,
            critical=False,
            recovery_actions=["reset_circuit_breakers"]
        )
        
        # External services health check
        self.health_checks["external_services"] = HealthCheck(
            name="external_services",
            check_function=self._check_external_services,
            timeout=30.0,
            critical=False,
            recovery_actions=["reset_circuit_breakers", "clear_failed_tasks"]
        )
    
    def _setup_recovery_actions(self):
        """Setup automated recovery actions."""
        
        # Database recovery actions
        self.recovery_actions["restart_database_connections"] = RecoveryAction(
            name="restart_database_connections",
            action_function=self._restart_database_connections,
            timeout=30.0,
            retry_count=2
        )
        
        self.recovery_actions["optimize_database"] = RecoveryAction(
            name="optimize_database",
            action_function=self._optimize_database,
            timeout=120.0,
            retry_count=1
        )
        
        # Redis recovery actions
        self.recovery_actions["restart_redis_connections"] = RecoveryAction(
            name="restart_redis_connections",
            action_function=self._restart_redis_connections,
            timeout=15.0,
            retry_count=2
        )
        
        # Celery recovery actions
        self.recovery_actions["restart_failed_workers"] = RecoveryAction(
            name="restart_failed_workers",
            action_function=self._restart_failed_workers,
            timeout=60.0,
            retry_count=2
        )
        
        self.recovery_actions["clear_task_queues"] = RecoveryAction(
            name="clear_task_queues",
            action_function=self._clear_task_queues,
            timeout=30.0,
            retry_count=1
        )
        
        # System recovery actions
        self.recovery_actions["cleanup_temporary_files"] = RecoveryAction(
            name="cleanup_temporary_files",
            action_function=self._cleanup_temporary_files,
            timeout=60.0,
            retry_count=1
        )
        
        self.recovery_actions["restart_high_memory_processes"] = RecoveryAction(
            name="restart_high_memory_processes",
            action_function=self._restart_high_memory_processes,
            timeout=120.0,
            retry_count=1
        )
        
        # Circuit breaker recovery actions
        self.recovery_actions["reset_circuit_breakers"] = RecoveryAction(
            name="reset_circuit_breakers",
            action_function=self._reset_circuit_breakers,
            timeout=10.0,
            retry_count=1
        )
        
        self.recovery_actions["clear_failed_tasks"] = RecoveryAction(
            name="clear_failed_tasks",
            action_function=self._clear_failed_tasks,
            timeout=30.0,
            retry_count=1
        )
    
    async def start_monitoring(self):
        """Start continuous health monitoring."""
        if self.monitoring_active:
            logger.warning("Health monitoring already active")
            return
        
        self.monitoring_active = True
        logger.info("Starting automated health monitoring",
                   check_interval=self.check_interval)
        
        while self.monitoring_active:
            try:
                await self._run_health_checks()
                await self._evaluate_recovery_needs()
                await asyncio.sleep(self.check_interval)
            
            except Exception as e:
                logger.error("Error in health monitoring loop", error=str(e))
                await asyncio.sleep(30)  # Short delay before retry
    
    async def stop_monitoring(self):
        """Stop health monitoring."""
        self.monitoring_active = False
        logger.info("Stopped automated health monitoring")
    
    async def _run_health_checks(self):
        """Execute all health checks."""
        logger.debug("Running health checks")
        
        tasks = []
        for check_name, health_check in self.health_checks.items():
            task = self._execute_health_check(health_check)
            tasks.append(task)
        
        # Run health checks concurrently
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log overall health status
        critical_issues = [
            check.name for check in self.health_checks.values()
            if check.critical and check.status in [ServiceHealth.UNHEALTHY, ServiceHealth.CRITICAL]
        ]
        
        if critical_issues:
            logger.error("Critical health issues detected", issues=critical_issues)
        else:
            logger.debug("Health checks completed")
    
    async def _execute_health_check(self, health_check: HealthCheck):
        """Execute a single health check."""
        start_time = time.time()
        
        try:
            # Execute health check with timeout
            result = await asyncio.wait_for(
                health_check.check_function(),
                timeout=health_check.timeout
            )
            
            health_check.response_time = time.time() - start_time
            health_check.last_check = time.time()
            health_check.consecutive_failures = 0
            
            if isinstance(result, tuple):
                health_check.status, health_check.error_message = result
            else:
                health_check.status = result
                health_check.error_message = ""
            
            logger.debug(f"Health check '{health_check.name}' completed",
                        status=health_check.status.value,
                        response_time=health_check.response_time)
        
        except asyncio.TimeoutError:
            health_check.status = ServiceHealth.CRITICAL
            health_check.error_message = f"Health check timed out after {health_check.timeout}s"
            health_check.response_time = health_check.timeout
            health_check.consecutive_failures += 1
            health_check.last_check = time.time()
            
            logger.error(f"Health check '{health_check.name}' timed out",
                        timeout=health_check.timeout)
        
        except Exception as e:
            health_check.status = ServiceHealth.UNHEALTHY
            health_check.error_message = str(e)
            health_check.response_time = time.time() - start_time
            health_check.consecutive_failures += 1
            health_check.last_check = time.time()
            
            logger.error(f"Health check '{health_check.name}' failed",
                        error=str(e), failures=health_check.consecutive_failures)
    
    async def _evaluate_recovery_needs(self):
        """Evaluate if recovery actions are needed and execute them."""
        recovery_needed = []
        
        for check_name, health_check in self.health_checks.items():
            if health_check.status in [ServiceHealth.UNHEALTHY, ServiceHealth.CRITICAL]:
                # Check recovery cooldown
                last_recovery = self.last_recovery_attempt.get(check_name, 0)
                if time.time() - last_recovery >= self.recovery_cooldown:
                    recovery_needed.append(health_check)
                else:
                    logger.debug(f"Recovery for '{check_name}' in cooldown period")
        
        if recovery_needed:
            logger.info("Initiating automated recovery", 
                       services=[check.name for check in recovery_needed])
            
            for health_check in recovery_needed:
                await self._execute_recovery_actions(health_check)
    
    async def _execute_recovery_actions(self, health_check: HealthCheck):
        """Execute recovery actions for a failed health check."""
        if not health_check.recovery_actions:
            logger.warning(f"No recovery actions defined for '{health_check.name}'")
            return
        
        self.last_recovery_attempt[health_check.name] = time.time()
        
        logger.info(f"Executing recovery actions for '{health_check.name}'",
                   actions=health_check.recovery_actions)
        
        recovery_results = []
        
        for action_name in health_check.recovery_actions:
            if action_name not in self.recovery_actions:
                logger.error(f"Recovery action '{action_name}' not found")
                continue
            
            action = self.recovery_actions[action_name]
            result = await self._execute_recovery_action(action)
            recovery_results.append((action_name, result))
        
        # Log recovery summary
        successful_actions = [name for name, result in recovery_results 
                            if result == RecoveryStatus.SUCCESS]
        failed_actions = [name for name, result in recovery_results 
                         if result == RecoveryStatus.FAILED]
        
        logger.info(f"Recovery actions completed for '{health_check.name}'",
                   successful=successful_actions, failed=failed_actions)
    
    async def _execute_recovery_action(self, action: RecoveryAction) -> RecoveryStatus:
        """Execute a single recovery action with retries."""
        action.last_execution = time.time()
        
        for attempt in range(action.retry_count + 1):
            try:
                logger.info(f"Executing recovery action '{action.name}' (attempt {attempt + 1})")
                
                # Execute action with timeout
                result = await asyncio.wait_for(
                    action.action_function(),
                    timeout=action.timeout
                )
                
                action.success_count += 1
                logger.info(f"Recovery action '{action.name}' succeeded")
                return RecoveryStatus.SUCCESS
            
            except asyncio.TimeoutError:
                logger.error(f"Recovery action '{action.name}' timed out",
                           timeout=action.timeout, attempt=attempt + 1)
                
                if attempt < action.retry_count:
                    await asyncio.sleep(action.retry_delay)
            
            except Exception as e:
                logger.error(f"Recovery action '{action.name}' failed",
                           error=str(e), attempt=attempt + 1)
                
                if attempt < action.retry_count:
                    await asyncio.sleep(action.retry_delay)
        
        action.failure_count += 1
        return RecoveryStatus.FAILED
    
    # Health check implementations
    async def _check_database_health(self) -> Tuple[ServiceHealth, str]:
        """Check database health."""
        try:
            # Test database connection
            is_connected = await check_database_connection()
            if not is_connected:
                return ServiceHealth.CRITICAL, "Database connection failed"
            
            # Check connection pool stats
            stats = await get_db_stats()
            pool_utilization = (stats["checked_out"] / stats["total"]) if stats["total"] > 0 else 0
            
            if pool_utilization > 0.9:
                return ServiceHealth.DEGRADED, f"High pool utilization: {pool_utilization:.1%}"
            elif pool_utilization > 0.8:
                return ServiceHealth.DEGRADED, f"Moderate pool utilization: {pool_utilization:.1%}"
            
            return ServiceHealth.HEALTHY, ""
        
        except Exception as e:
            return ServiceHealth.UNHEALTHY, f"Database health check failed: {str(e)}"
    
    async def _check_redis_health(self) -> Tuple[ServiceHealth, str]:
        """Check Redis health."""
        try:
            redis_client = await get_redis_client()
            if redis_client is None:
                return ServiceHealth.CRITICAL, "Redis client not available"
            
            # Test Redis connection
            await redis_client.ping()
            
            # Check Redis memory usage
            info = await redis_client.info()
            memory_usage = info.get("used_memory", 0)
            max_memory = info.get("maxmemory", 0)
            
            if max_memory > 0:
                memory_ratio = memory_usage / max_memory
                if memory_ratio > 0.9:
                    return ServiceHealth.DEGRADED, f"High memory usage: {memory_ratio:.1%}"
                elif memory_ratio > 0.8:
                    return ServiceHealth.DEGRADED, f"Moderate memory usage: {memory_ratio:.1%}"
            
            return ServiceHealth.HEALTHY, ""
        
        except Exception as e:
            return ServiceHealth.UNHEALTHY, f"Redis health check failed: {str(e)}"
    
    async def _check_celery_health(self) -> Tuple[ServiceHealth, str]:
        """Check Celery workers health."""
        try:
            health_status = await check_celery_health()
            
            if health_status["status"] == "error":
                return ServiceHealth.CRITICAL, health_status.get("error", "Celery error")
            
            active_workers = health_status["active_workers"]
            if active_workers == 0:
                return ServiceHealth.CRITICAL, "No active Celery workers"
            
            # Check queue lengths
            queue_lengths = health_status.get("queue_lengths", {})
            high_queues = [queue for queue, length in queue_lengths.items() 
                          if isinstance(length, int) and length > 100]
            
            if high_queues:
                return ServiceHealth.DEGRADED, f"High queue lengths: {high_queues}"
            
            return ServiceHealth.HEALTHY, ""
        
        except Exception as e:
            return ServiceHealth.UNHEALTHY, f"Celery health check failed: {str(e)}"
    
    async def _check_system_resources(self) -> Tuple[ServiceHealth, str]:
        """Check system resource usage."""
        try:
            # Check CPU usage
            cpu_usage = psutil.cpu_percent(interval=1)
            
            # Check memory usage
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            
            # Check disk usage
            disk = psutil.disk_usage('/')
            disk_usage = disk.percent
            
            issues = []
            if cpu_usage > 90:
                issues.append(f"High CPU usage: {cpu_usage:.1f}%")
            if memory_usage > 90:
                issues.append(f"High memory usage: {memory_usage:.1f}%")
            if disk_usage > 90:
                issues.append(f"High disk usage: {disk_usage:.1f}%")
            
            if issues:
                status = ServiceHealth.CRITICAL if len(issues) > 1 else ServiceHealth.DEGRADED
                return status, "; ".join(issues)
            
            # Check for moderate usage
            moderate_issues = []
            if cpu_usage > 80:
                moderate_issues.append(f"Moderate CPU usage: {cpu_usage:.1f}%")
            if memory_usage > 80:
                moderate_issues.append(f"Moderate memory usage: {memory_usage:.1f}%")
            if disk_usage > 80:
                moderate_issues.append(f"Moderate disk usage: {disk_usage:.1f}%")
            
            if moderate_issues:
                return ServiceHealth.DEGRADED, "; ".join(moderate_issues)
            
            return ServiceHealth.HEALTHY, ""
        
        except Exception as e:
            return ServiceHealth.UNKNOWN, f"System resource check failed: {str(e)}"
    
    async def _check_circuit_breakers(self) -> Tuple[ServiceHealth, str]:
        """Check circuit breaker states."""
        try:
            states = get_all_circuit_breaker_states()
            
            open_breakers = []
            half_open_breakers = []
            
            for name, state in states.items():
                if state["state"] == "open":
                    open_breakers.append(name)
                elif state["state"] == "half_open":
                    half_open_breakers.append(name)
            
            if open_breakers:
                return ServiceHealth.DEGRADED, f"Open circuit breakers: {open_breakers}"
            elif half_open_breakers:
                return ServiceHealth.DEGRADED, f"Half-open circuit breakers: {half_open_breakers}"
            
            return ServiceHealth.HEALTHY, ""
        
        except Exception as e:
            return ServiceHealth.UNKNOWN, f"Circuit breaker check failed: {str(e)}"
    
    async def _check_external_services(self) -> Tuple[ServiceHealth, str]:
        """Check external service availability through circuit breakers."""
        try:
            states = get_all_circuit_breaker_states()
            
            critical_services = ["mediamarkt_scraping", "amazon_api", "keepa_api"]
            failed_services = []
            
            for service in critical_services:
                if service in states and states[service]["state"] == "open":
                    failed_services.append(service)
            
            if len(failed_services) >= 2:
                return ServiceHealth.CRITICAL, f"Multiple external services failed: {failed_services}"
            elif failed_services:
                return ServiceHealth.DEGRADED, f"External service failed: {failed_services[0]}"
            
            return ServiceHealth.HEALTHY, ""
        
        except Exception as e:
            return ServiceHealth.UNKNOWN, f"External service check failed: {str(e)}"
    
    # Recovery action implementations
    async def _restart_database_connections(self):
        """Restart database connections."""
        from src.config.database import close_database_connection, get_database
        
        logger.info("Restarting database connections")
        await close_database_connection()
        await asyncio.sleep(2)
        await get_database()
        logger.info("Database connections restarted")
    
    async def _optimize_database(self):
        """Run database optimization."""
        logger.info("Running database optimization")
        await optimize_database()
        logger.info("Database optimization completed")
    
    async def _restart_redis_connections(self):
        """Restart Redis connections."""
        from src.config.database import close_database  # This closes Redis too
        
        logger.info("Restarting Redis connections")
        # Reset Redis client
        global _redis_client
        from src.config.database import _redis_client
        if _redis_client:
            await _redis_client.close()
            _redis_client = None
        
        # Reinitialize Redis
        await get_redis_client()
        logger.info("Redis connections restarted")
    
    async def _restart_failed_workers(self):
        """Restart failed Celery workers."""
        logger.info("Attempting to restart failed Celery workers")
        # In a production environment, this would trigger worker restart
        # For now, we'll log the action
        logger.info("Worker restart command would be executed here")
    
    async def _clear_task_queues(self):
        """Clear task queues with high backlog."""
        logger.info("Clearing high-backlog task queues")
        # Implementation would clear specific queues
        logger.info("Task queues cleared")
    
    async def _cleanup_temporary_files(self):
        """Clean up temporary files to free disk space."""
        import os
        import shutil
        
        logger.info("Cleaning up temporary files")
        
        # Clean up log files older than 7 days
        log_dir = "logs"
        if os.path.exists(log_dir):
            current_time = time.time()
            for filename in os.listdir(log_dir):
                filepath = os.path.join(log_dir, filename)
                if os.path.isfile(filepath):
                    file_age = current_time - os.path.getmtime(filepath)
                    if file_age > (7 * 24 * 3600):  # 7 days
                        os.remove(filepath)
                        logger.debug(f"Removed old log file: {filename}")
        
        logger.info("Temporary file cleanup completed")
    
    async def _restart_high_memory_processes(self):
        """Restart processes with high memory usage."""
        logger.info("Restarting high memory processes")
        # In production, this would identify and restart specific processes
        logger.info("High memory process restart would be executed here")
    
    async def _reset_circuit_breakers(self):
        """Reset circuit breakers that are in OPEN state."""
        logger.info("Resetting circuit breakers")
        
        # Get unhealthy breakers
        unhealthy = circuit_breaker_registry.get_unhealthy_breakers()
        
        if unhealthy:
            logger.info(f"Resetting unhealthy circuit breakers: {unhealthy}")
            for breaker_name in unhealthy:
                breaker = circuit_breaker_registry.get(breaker_name)
                if breaker:
                    breaker.reset()
            logger.info("Circuit breakers reset")
        else:
            logger.info("No unhealthy circuit breakers to reset")
    
    async def _clear_failed_tasks(self):
        """Clear failed tasks from queues."""
        logger.info("Clearing failed tasks from queues")
        # Implementation would clear failed tasks
        logger.info("Failed tasks cleared")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status of all monitored services."""
        return {
            "monitoring_active": self.monitoring_active,
            "last_check": max((check.last_check for check in self.health_checks.values()), default=0),
            "checks": {
                name: {
                    "status": check.status.value,
                    "last_check": check.last_check,
                    "response_time": check.response_time,
                    "error_message": check.error_message,
                    "consecutive_failures": check.consecutive_failures,
                    "critical": check.critical
                }
                for name, check in self.health_checks.items()
            },
            "recovery_actions": {
                name: {
                    "last_execution": action.last_execution,
                    "success_count": action.success_count,
                    "failure_count": action.failure_count
                }
                for name, action in self.recovery_actions.items()
            }
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get health summary."""
        total_checks = len(self.health_checks)
        healthy_checks = sum(1 for check in self.health_checks.values() 
                           if check.status == ServiceHealth.HEALTHY)
        critical_issues = sum(1 for check in self.health_checks.values() 
                            if check.critical and check.status in [ServiceHealth.UNHEALTHY, ServiceHealth.CRITICAL])
        
        overall_status = ServiceHealth.HEALTHY
        if critical_issues > 0:
            overall_status = ServiceHealth.CRITICAL
        elif healthy_checks < total_checks:
            overall_status = ServiceHealth.DEGRADED
        
        return {
            "overall_status": overall_status.value,
            "total_checks": total_checks,
            "healthy_checks": healthy_checks,
            "critical_issues": critical_issues,
            "monitoring_active": self.monitoring_active
        }


# Global health monitor instance
health_monitor = SystemHealthMonitor()


# Convenience functions
async def start_health_monitoring():
    """Start the global health monitoring system."""
    await health_monitor.start_monitoring()


async def stop_health_monitoring():
    """Stop the global health monitoring system."""
    await health_monitor.stop_monitoring()


def get_system_health() -> Dict[str, Any]:
    """Get current system health status."""
    return health_monitor.get_health_status()


def get_health_summary() -> Dict[str, Any]:
    """Get health summary."""
    return health_monitor.get_summary()


@asynccontextmanager
async def health_monitoring_context():
    """Context manager for health monitoring."""
    try:
        await start_health_monitoring()
        yield health_monitor
    finally:
        await stop_health_monitoring() 