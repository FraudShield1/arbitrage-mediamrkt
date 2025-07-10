"""
Celery configuration for background task processing with enhanced scalability.
"""

from celery import Celery
from celery.schedules import crontab
from kombu import Queue, Exchange
from celery.signals import worker_ready, worker_shutdown, task_prerun, task_postrun
import structlog
import os
import socket
from typing import Dict, Any

from src.config.settings import settings

logger = structlog.get_logger(__name__)

# Enhanced Celery app with scalability features
celery_app = Celery(
    "arbitrage_tool",
    broker=settings.redis.url,
    backend=settings.redis.url,
    include=[
        "src.tasks.scraping",
        "src.tasks.matching", 
        "src.tasks.analysis",
        "src.tasks.notifications",
        "src.tasks.maintenance"
    ]
)

# Enhanced Celery configuration for scalability
celery_app.conf.update(
    # Task routing with priority queues
    task_routes={
        "src.tasks.scraping.*": {"queue": "scraping"},
        "src.tasks.matching.*": {"queue": "matching"},
        "src.tasks.analysis.*": {"queue": "analysis"},
        "src.tasks.notifications.*": {"queue": "notifications"},
        "src.tasks.maintenance.*": {"queue": "maintenance"},
        # High priority tasks
        "src.tasks.notifications.send_urgent_alert": {"queue": "urgent"},
        "src.tasks.analysis.analyze_new_opportunity": {"queue": "priority"},
    },
    
    # Task serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Enhanced task execution for scalability
    task_acks_late=True,
    worker_prefetch_multiplier=4,  # Increased for better throughput
    task_reject_on_worker_lost=True,
    task_track_started=True,
    task_send_sent_event=True,
    
    # Result backend optimization
    result_expires=7200,  # 2 hours
    result_backend_transport_options={
        "master_name": "mymaster",
        "retry_on_timeout": True,
        "connection_pool_kwargs": {
            "max_connections": 50,
            "retry_on_timeout": True,
        },
    },
    
    # Enhanced error handling and retry logic
    task_annotations={
        "*": {
            "rate_limit": "200/m",  # Increased rate limit
            "time_limit": 600,      # 10 minutes
            "soft_time_limit": 480, # 8 minutes
            "retry_kwargs": {
                "max_retries": 5,
                "countdown": 30,    # 30 second delay
                "retry_backoff": True,
                "retry_backoff_max": 600,  # Max 10 minutes
                "retry_jitter": True,
            },
        },
        "src.tasks.scraping.scrape_mediamarkt": {
            "rate_limit": "20/m",    # Increased scraping rate
            "time_limit": 2400,      # 40 minutes
            "soft_time_limit": 2100, # 35 minutes
            "retry_kwargs": {
                "max_retries": 3,
                "countdown": 300,    # 5 minute delay for scraping
            },
        },
        "src.tasks.analysis.analyze_prices": {
            "rate_limit": "100/m",   # Increased analysis rate
            "time_limit": 1200,      # 20 minutes
            "soft_time_limit": 900,  # 15 minutes
        },
        "src.tasks.matching.bulk_match_products": {
            "rate_limit": "50/m",
            "time_limit": 1800,      # 30 minutes for bulk operations
            "soft_time_limit": 1500, # 25 minutes
        },
        "src.tasks.notifications.send_urgent_alert": {
            "rate_limit": "500/m",   # High rate for urgent alerts
            "time_limit": 60,        # 1 minute
            "priority": 9,           # Highest priority
        },
    },
    
    # Enhanced worker configuration for scalability
    worker_disable_rate_limits=False,
    worker_max_tasks_per_child=200,        # Increased task limit
    worker_max_memory_per_child=400000,    # 400MB memory limit
    worker_autoscaler="celery.worker.autoscale:Autoscaler",
    worker_concurrency=os.cpu_count() * 2, # Dynamic based on CPU cores
    
    # Enhanced monitoring and events
    worker_send_task_events=True,
    task_store_eager_result=True,
    worker_enable_remote_control=True,
    
    # Connection pool settings for better performance
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    broker_pool_limit=20,
    broker_transport_options={
        "priority_steps": list(range(10)),
        "sep": ":",
        "queue_order_strategy": "priority",
        "connection_pool_kwargs": {
            "max_connections": 50,
            "retry_on_timeout": True,
        },
    },
    
    # Enhanced beat schedule with dynamic timing
    beat_schedule={
        "scrape-mediamarkt-frequent": {
            "task": "src.tasks.scraping.scrape_mediamarkt",
            "schedule": crontab(minute="*/15"),  # Every 15 minutes for more frequent updates
            "options": {"queue": "scraping", "priority": 5},
        },
        "scrape-mediamarkt-deep": {
            "task": "src.tasks.scraping.scrape_mediamarkt_deep",
            "schedule": crontab(minute="0", hour="*/3"),  # Deep scrape every 3 hours
            "options": {"queue": "scraping", "priority": 3},
        },
        "process-unmatched-products": {
            "task": "src.tasks.matching.process_unmatched_products", 
            "schedule": crontab(minute="5", hour="*/1"),  # Every hour at :05
            "options": {"queue": "matching", "priority": 4},
        },
        "bulk-match-products": {
            "task": "src.tasks.matching.bulk_match_products",
            "schedule": crontab(minute="30", hour="*/6"),  # Bulk matching every 6 hours
            "options": {"queue": "matching", "priority": 2},
        },
        "analyze-price-opportunities": {
            "task": "src.tasks.analysis.analyze_price_opportunities",
            "schedule": crontab(minute="10", hour="*/1"),  # Every hour at :10
            "options": {"queue": "analysis", "priority": 6},
        },
        "analyze-market-trends": {
            "task": "src.tasks.analysis.analyze_market_trends",
            "schedule": crontab(minute="0", hour="*/4"),  # Market analysis every 4 hours
            "options": {"queue": "analysis", "priority": 3},
        },
        "send-hourly-alerts": {
            "task": "src.tasks.notifications.send_hourly_alerts",
            "schedule": crontab(minute="45"),  # Every hour at :45
            "options": {"queue": "notifications", "priority": 7},
        },
        "send-daily-summary": {
            "task": "src.tasks.notifications.send_daily_summary",
            "schedule": crontab(hour=8, minute=0),  # 8 AM daily
            "options": {"queue": "notifications", "priority": 5},
        },
        "cleanup-old-data": {
            "task": "src.tasks.maintenance.cleanup_old_data",
            "schedule": crontab(hour=2, minute=0),  # 2 AM daily
            "options": {"queue": "maintenance", "priority": 1},
        },
        "optimize-database": {
            "task": "src.tasks.maintenance.optimize_database",
            "schedule": crontab(hour=3, minute=0, day_of_week=0),  # Weekly on Sunday
            "options": {"queue": "maintenance", "priority": 1},
        },
        "health-check": {
            "task": "src.tasks.maintenance.system_health_check",
            "schedule": crontab(minute="*/5"),  # Every 5 minutes
            "options": {"queue": "maintenance", "priority": 8},
        },
    },
    
    # Enhanced queue configuration with priorities
    task_default_queue="default",
    task_queues=(
        Queue("urgent", Exchange("urgent"), routing_key="urgent", 
              queue_arguments={"x-max-priority": 10}),
        Queue("priority", Exchange("priority"), routing_key="priority",
              queue_arguments={"x-max-priority": 8}),
        Queue("default", Exchange("default"), routing_key="default",
              queue_arguments={"x-max-priority": 5}),
        Queue("scraping", Exchange("scraping"), routing_key="scraping",
              queue_arguments={"x-max-priority": 5}),
        Queue("matching", Exchange("matching"), routing_key="matching",
              queue_arguments={"x-max-priority": 4}), 
        Queue("analysis", Exchange("analysis"), routing_key="analysis",
              queue_arguments={"x-max-priority": 6}),
        Queue("notifications", Exchange("notifications"), routing_key="notifications",
              queue_arguments={"x-max-priority": 7}),
        Queue("maintenance", Exchange("maintenance"), routing_key="maintenance",
              queue_arguments={"x-max-priority": 1}),
    ),
    
    # Task compression for large payloads
    task_compression="gzip",
    result_compression="gzip",
)


# Worker lifecycle hooks for monitoring
@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Handle worker ready signal."""
    hostname = socket.gethostname()
    logger.info(f"Celery worker ready on {hostname}", extra={"worker": sender.hostname})


@worker_shutdown.connect
def worker_shutdown_handler(sender=None, **kwargs):
    """Handle worker shutdown signal."""
    logger.info(f"Celery worker shutting down", extra={"worker": sender.hostname})


# Task execution hooks for monitoring
@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Handle task pre-run for monitoring."""
    logger.info(f"Task starting: {task.name}", extra={
        "task_id": task_id,
        "task_name": task.name,
        "args_count": len(args) if args else 0,
        "kwargs_count": len(kwargs) if kwargs else 0,
    })


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, 
                        retval=None, state=None, **kwds):
    """Handle task post-run for monitoring."""
    logger.info(f"Task completed: {task.name}", extra={
        "task_id": task_id,
        "task_name": task.name,
        "state": state,
        "success": state == "SUCCESS",
    })


@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery configuration."""
    logger.info(f"Request: {self.request!r}")
    return {"status": "success", "message": "Celery is working!", "worker": socket.gethostname()}


# Enhanced task base classes
@celery_app.task(bind=True, base=celery_app.Task)
class CallbackTask(celery_app.Task):
    """Enhanced base task with comprehensive callbacks."""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure with enhanced logging."""
        logger.error(
            "Task failed",
            task_id=task_id,
            task_name=self.name,
            exception=str(exc),
            exception_type=type(exc).__name__,
            args=args,
            kwargs=kwargs,
            traceback=str(einfo),
            worker=socket.gethostname(),
        )
        
        # Trigger alert for critical task failures
        if self.name in ["src.tasks.scraping.scrape_mediamarkt", 
                        "src.tasks.notifications.send_urgent_alert"]:
            self.retry(countdown=60, max_retries=2)
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Handle task retry with exponential backoff."""
        retry_count = self.request.retries
        logger.warning(
            "Task retry",
            task_id=task_id,
            task_name=self.name,
            exception=str(exc),
            retry_count=retry_count,
            max_retries=self.max_retries,
            worker=socket.gethostname(),
        )
    
    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success with performance metrics."""
        execution_time = getattr(self.request, 'execution_time', None)
        logger.info(
            "Task completed successfully",
            task_id=task_id,
            task_name=self.name,
            execution_time=execution_time,
            result_type=type(retval).__name__ if retval else None,
            worker=socket.gethostname(),
        )


# Error handling configuration
class TaskErrorHandler:
    """Centralized task error handling with enhanced features."""
    
    @staticmethod
    def handle_scraping_error(exc, task_id, product_data=None, retry_count=0):
        """Handle scraping task errors with context."""
        logger.error(
            "Scraping task error",
            task_id=task_id,
            exception=str(exc),
            exception_type=type(exc).__name__,
            product_data=product_data,
            retry_count=retry_count,
            worker=socket.gethostname(),
        )
        
        # Send alert for critical scraping failures
        if retry_count >= 2:
            celery_app.send_task(
                "src.tasks.notifications.send_system_alert",
                args=["Scraping Error", f"Task {task_id} failed after {retry_count} retries: {str(exc)}"],
                queue="urgent",
                priority=9
            )
    
    @staticmethod
    def handle_matching_error(exc, task_id, product_id=None, retry_count=0):
        """Handle matching task errors with context."""
        logger.error(
            "Matching task error",
            task_id=task_id,
            exception=str(exc),
            exception_type=type(exc).__name__,
            product_id=product_id,
            retry_count=retry_count,
            worker=socket.gethostname(),
        )
    
    @staticmethod
    def handle_analysis_error(exc, task_id, asin=None, retry_count=0):
        """Handle analysis task errors with context."""
        logger.error(
            "Analysis task error",
            task_id=task_id,
            exception=str(exc),
            exception_type=type(exc).__name__,
            asin=asin,
            retry_count=retry_count,
            worker=socket.gethostname(),
        )
    
    @staticmethod
    def handle_notification_error(exc, task_id, notification_type=None, retry_count=0):
        """Handle notification task errors with context."""
        logger.error(
            "Notification task error",
            task_id=task_id,
            exception=str(exc),
            exception_type=type(exc).__name__,
            notification_type=notification_type,
            retry_count=retry_count,
            worker=socket.gethostname(),
        )
        
        # For critical notification failures, try alternative channels
        if notification_type == "urgent" and retry_count >= 1:
            # Fallback to different notification method
            pass


async def check_celery_health() -> Dict[str, Any]:
    """
    Enhanced health check for Celery workers and queues.
    
    Returns:
        Dictionary with health status information
    """
    try:
        # Check worker availability
        inspect = celery_app.control.inspect()
        
        # Get active workers
        active_workers = inspect.active()
        registered_workers = inspect.registered()
        
        # Check queue lengths
        queue_lengths = {}
        for queue_name in ["scraping", "matching", "analysis", "notifications", "maintenance"]:
            try:
                queue_length = celery_app.broker_connection().default_channel.queue_declare(
                    queue=queue_name, passive=True
                ).message_count
                queue_lengths[queue_name] = queue_length
            except Exception as e:
                queue_lengths[queue_name] = f"Error: {str(e)}"
        
        # Check recent task statistics
        stats = inspect.stats()
        
        health_status = {
            "status": "healthy" if active_workers else "unhealthy",
            "active_workers": len(active_workers) if active_workers else 0,
            "registered_workers": len(registered_workers) if registered_workers else 0,
            "queue_lengths": queue_lengths,
            "worker_stats": stats,
            "broker_url": celery_app.conf.broker_url.replace(
                celery_app.conf.broker_url.split('@')[0].split('://')[1] + '@', '***@'
            ) if '@' in celery_app.conf.broker_url else celery_app.conf.broker_url,
        }
        
        return health_status
        
    except Exception as e:
        logger.error(f"Celery health check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "active_workers": 0,
            "registered_workers": 0,
        }


def get_enhanced_task_stats() -> Dict[str, Any]:
    """
    Get enhanced task execution statistics.
    
    Returns:
        Dictionary with comprehensive task statistics
    """
    try:
        inspect = celery_app.control.inspect()
        
        # Get comprehensive stats
        active_tasks = inspect.active()
        scheduled_tasks = inspect.scheduled()
        reserved_tasks = inspect.reserved()
        
        # Calculate totals
        total_active = sum(len(tasks) for tasks in (active_tasks or {}).values())
        total_scheduled = sum(len(tasks) for tasks in (scheduled_tasks or {}).values())
        total_reserved = sum(len(tasks) for tasks in (reserved_tasks or {}).values())
        
        return {
            "active_tasks": total_active,
            "scheduled_tasks": total_scheduled,
            "reserved_tasks": total_reserved,
            "revoked_tasks": len(revoked_tasks) if revoked_tasks else 0,
            "worker_details": {
                "active": active_tasks,
                "scheduled": scheduled_tasks,
                "reserved": reserved_tasks,
            },
            "timestamp": celery_app.now(),
        }
        
    except Exception as e:
        logger.error(f"Failed to get task stats: {e}")
        return {
            "error": str(e),
            "active_tasks": 0,
            "scheduled_tasks": 0,
            "reserved_tasks": 0,
        }


# Dynamic worker scaling based on queue length
def scale_workers_dynamically():
    """
    Scale workers dynamically based on queue lengths and system load.
    This would be called by a monitoring system.
    """
    try:
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()
        
        if not active_workers:
            logger.warning("No active workers found for scaling")
            return
        
        # Check queue lengths and scale accordingly
        # This is a placeholder for actual scaling logic
        for worker_name in active_workers:
            # Example scaling logic
            control = celery_app.control
            control.pool_grow(n=1, destination=[worker_name])
            
    except Exception as e:
        logger.error(f"Dynamic scaling failed: {e}")


# Task priority management
def set_task_priority(task_name: str, priority: int):
    """Set priority for a specific task type."""
    if task_name in celery_app.conf.task_annotations:
        celery_app.conf.task_annotations[task_name]["priority"] = priority
    else:
        celery_app.conf.task_annotations[task_name] = {"priority": priority}
    
    logger.info(f"Updated priority for {task_name} to {priority}") 