"""
Prometheus metrics collection for monitoring and observability.
"""

import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from functools import wraps
from contextlib import contextmanager
import structlog
from prometheus_client import (
    Counter, Histogram, Gauge, Info, Enum,
    CollectorRegistry, CONTENT_TYPE_LATEST,
    generate_latest, multiprocess, REGISTRY
)

from src.config.settings import get_settings
from src.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class MetricsCollector:
    """Centralized metrics collection for the arbitrage tool."""
    
    def __init__(self, registry: CollectorRegistry = REGISTRY):
        self.registry = registry
        self.logger = get_logger(__name__)
        
        # Application Info Metrics
        self.app_info = Info(
            'arbitrage_app_info',
            'Application information',
            registry=registry
        )
        
        # HTTP Request Metrics
        self.http_requests_total = Counter(
            'arbitrage_http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status_code'],
            registry=registry
        )
        
        self.http_request_duration = Histogram(
            'arbitrage_http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint'],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
            registry=registry
        )
        
        # Database Metrics
        self.db_connections_active = Gauge(
            'arbitrage_db_connections_active',
            'Number of active database connections',
            registry=registry
        )
        
        self.db_query_duration = Histogram(
            'arbitrage_db_query_duration_seconds',
            'Database query duration in seconds',
            ['operation', 'table'],
            buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0),
            registry=registry
        )
        
        self.db_queries_total = Counter(
            'arbitrage_db_queries_total',
            'Total database queries',
            ['operation', 'table', 'status'],
            registry=registry
        )
        
        # Background Task Metrics
        self.celery_tasks_total = Counter(
            'arbitrage_celery_tasks_total',
            'Total Celery tasks',
            ['task_name', 'status'],
            registry=registry
        )
        
        self.celery_task_duration = Histogram(
            'arbitrage_celery_task_duration_seconds',
            'Celery task duration in seconds',
            ['task_name'],
            buckets=(1, 5, 10, 30, 60, 120, 300, 600),
            registry=registry
        )
        
        self.celery_queue_size = Gauge(
            'arbitrage_celery_queue_size',
            'Number of tasks in Celery queue',
            ['queue_name'],
            registry=registry
        )
        
        # Business Logic Metrics
        self.products_scraped_total = Counter(
            'arbitrage_products_scraped_total',
            'Total products scraped',
            ['source', 'status'],
            registry=registry
        )
        
        self.products_matched_total = Counter(
            'arbitrage_products_matched_total',
            'Total products matched to Amazon',
            ['match_type', 'confidence_level'],
            registry=registry
        )
        
        self.opportunities_detected_total = Counter(
            'arbitrage_opportunities_detected_total',
            'Total arbitrage opportunities detected',
            ['severity', 'category'],
            registry=registry
        )
        
        self.profit_potential_euros = Gauge(
            'arbitrage_profit_potential_euros',
            'Current total profit potential in euros',
            registry=registry
        )
        
        self.alerts_sent_total = Counter(
            'arbitrage_alerts_sent_total',
            'Total alerts sent',
            ['channel', 'severity', 'status'],
            registry=registry
        )
        
        # External API Metrics
        self.external_api_requests_total = Counter(
            'arbitrage_external_api_requests_total',
            'Total external API requests',
            ['service', 'endpoint', 'status_code'],
            registry=registry
        )
        
        self.external_api_duration = Histogram(
            'arbitrage_external_api_duration_seconds',
            'External API request duration in seconds',
            ['service', 'endpoint'],
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
            registry=registry
        )
        
        # System Health Metrics
        self.health_check_status = Enum(
            'arbitrage_health_check_status',
            'Health check status',
            ['check_name'],
            states=['healthy', 'unhealthy', 'degraded', 'unknown'],
            registry=registry
        )
        
        self.health_check_duration = Histogram(
            'arbitrage_health_check_duration_seconds',
            'Health check duration in seconds',
            ['check_name'],
            buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 5.0),
            registry=registry
        )
        
        # Redis Metrics
        self.redis_operations_total = Counter(
            'arbitrage_redis_operations_total',
            'Total Redis operations',
            ['operation', 'status'],
            registry=registry
        )
        
        self.redis_memory_usage_bytes = Gauge(
            'arbitrage_redis_memory_usage_bytes',
            'Redis memory usage in bytes',
            registry=registry
        )
        
        # Authentication Metrics
        self.auth_attempts_total = Counter(
            'arbitrage_auth_attempts_total',
            'Total authentication attempts',
            ['status', 'method'],
            registry=registry
        )
        
        self.active_sessions = Gauge(
            'arbitrage_active_sessions',
            'Number of active user sessions',
            registry=registry
        )
        
        # Initialize app info
        self.app_info.info({
            'version': '1.0.0',
            'service': 'arbitrage-tool',
            'environment': settings.environment
        })
    
    # HTTP Request Tracking
    def track_http_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Track HTTP request metrics."""
        self.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
        
        self.http_request_duration.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    @contextmanager
    def track_request_duration(self, method: str, endpoint: str):
        """Context manager to track HTTP request duration."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.http_request_duration.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
    
    # Database Tracking
    def track_db_query(self, operation: str, table: str, duration: float, success: bool = True):
        """Track database query metrics."""
        status = 'success' if success else 'error'
        
        self.db_queries_total.labels(
            operation=operation,
            table=table,
            status=status
        ).inc()
        
        self.db_query_duration.labels(
            operation=operation,
            table=table
        ).observe(duration)
    
    def update_db_connections(self, active_connections: int):
        """Update active database connections count."""
        self.db_connections_active.set(active_connections)
    
    # Celery Task Tracking
    def track_celery_task(self, task_name: str, duration: float, success: bool = True):
        """Track Celery task execution metrics."""
        status = 'success' if success else 'error'
        
        self.celery_tasks_total.labels(
            task_name=task_name,
            status=status
        ).inc()
        
        self.celery_task_duration.labels(
            task_name=task_name
        ).observe(duration)
    
    def update_celery_queue_size(self, queue_name: str, size: int):
        """Update Celery queue size."""
        self.celery_queue_size.labels(queue_name=queue_name).set(size)
    
    # Business Metrics
    def track_products_scraped(self, source: str, count: int, success: bool = True):
        """Track products scraped."""
        status = 'success' if success else 'error'
        self.products_scraped_total.labels(source=source, status=status).inc(count)
    
    def track_product_matched(self, match_type: str, confidence: str):
        """Track product matching."""
        self.products_matched_total.labels(
            match_type=match_type,
            confidence_level=confidence
        ).inc()
    
    def track_opportunity_detected(self, severity: str, category: str):
        """Track arbitrage opportunity detection."""
        self.opportunities_detected_total.labels(
            severity=severity,
            category=category
        ).inc()
    
    def update_profit_potential(self, amount_euros: float):
        """Update total profit potential."""
        self.profit_potential_euros.set(amount_euros)
    
    def track_alert_sent(self, channel: str, severity: str, success: bool = True):
        """Track alert sending."""
        status = 'success' if success else 'error'
        self.alerts_sent_total.labels(
            channel=channel,
            severity=severity,
            status=status
        ).inc()
    
    # External API Tracking
    def track_external_api_request(self, service: str, endpoint: str, 
                                 status_code: int, duration: float):
        """Track external API requests."""
        self.external_api_requests_total.labels(
            service=service,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
        
        self.external_api_duration.labels(
            service=service,
            endpoint=endpoint
        ).observe(duration)
    
    # Health Check Tracking
    def track_health_check(self, check_name: str, status: str, duration: float):
        """Track health check results."""
        self.health_check_status.labels(check_name=check_name).state(status)
        self.health_check_duration.labels(check_name=check_name).observe(duration)
    
    # Redis Tracking
    def track_redis_operation(self, operation: str, success: bool = True):
        """Track Redis operations."""
        status = 'success' if success else 'error'
        self.redis_operations_total.labels(operation=operation, status=status).inc()
    
    def update_redis_memory_usage(self, bytes_used: int):
        """Update Redis memory usage."""
        self.redis_memory_usage_bytes.set(bytes_used)
    
    # Authentication Tracking
    def track_auth_attempt(self, success: bool, method: str = 'jwt'):
        """Track authentication attempts."""
        status = 'success' if success else 'failure'
        self.auth_attempts_total.labels(status=status, method=method).inc()
    
    def update_active_sessions(self, count: int):
        """Update active sessions count."""
        self.active_sessions.set(count)


# Global metrics collector instance
metrics = MetricsCollector()


# Decorator for tracking function execution time
def track_execution_time(metric_name: str, labels: Dict[str, str] = None):
    """Decorator to track function execution time."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                success = True
                return result
            except Exception as e:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                logger.debug(
                    f"Function {func.__name__} execution tracked",
                    duration=duration,
                    success=success
                )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                success = True
                return result
            except Exception as e:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                logger.debug(
                    f"Function {func.__name__} execution tracked",
                    duration=duration,
                    success=success
                )
        
        return async_wrapper if hasattr(func, '__code__') and func.__code__.co_flags & 0x80 else sync_wrapper
    return decorator


# Context manager for tracking operations
@contextmanager
def track_operation(operation_name: str, labels: Dict[str, str] = None):
    """Context manager to track operation duration and success."""
    start_time = time.time()
    success = True
    
    try:
        yield
    except Exception as e:
        success = False
        logger.error(f"Operation {operation_name} failed", error=str(e))
        raise
    finally:
        duration = time.time() - start_time
        logger.info(
            f"Operation {operation_name} completed",
            duration=duration,
            success=success,
            **(labels or {})
        )


def get_metrics_text() -> str:
    """Get Prometheus metrics in text format."""
    try:
        return generate_latest(metrics.registry).decode('utf-8')
    except Exception as e:
        logger.error("Failed to generate metrics", error=str(e))
        return ""


def get_metrics_content_type() -> str:
    """Get the content type for Prometheus metrics."""
    return CONTENT_TYPE_LATEST


# Business-specific tracking functions
def track_scraping_session(source: str, products_count: int, duration: float, success: bool = True):
    """Track a scraping session."""
    metrics.track_products_scraped(source, products_count, success)
    logger.info(
        "Scraping session tracked",
        source=source,
        products_count=products_count,
        duration=duration,
        success=success
    )


def track_matching_session(total_products: int, matched_count: int, match_type: str):
    """Track a product matching session."""
    for _ in range(matched_count):
        metrics.track_product_matched(match_type, "high" if match_type == "ean" else "medium")
    
    logger.info(
        "Matching session tracked",
        total_products=total_products,
        matched_count=matched_count,
        match_type=match_type
    )


def update_business_metrics(total_opportunities: int, total_profit_potential: float):
    """Update high-level business metrics."""
    metrics.update_profit_potential(total_profit_potential)
    logger.info(
        "Business metrics updated",
        total_opportunities=total_opportunities,
        total_profit_potential=total_profit_potential
    ) 