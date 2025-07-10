"""
Enhanced Monitoring System for comprehensive observability.

Provides detailed metrics collection, alerting, and performance monitoring
for all system components with integration to Prometheus and custom alerting.
"""

import asyncio
import time
import psutil
import json
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import structlog
from datetime import datetime, timedelta
import aiohttp

from src.config.database import get_db_stats, get_redis_client
from src.config.celery import check_celery_health, get_enhanced_task_stats
from src.utils.circuit_breaker import get_all_circuit_breaker_states
from src.utils.recovery import get_system_health, get_health_summary

logger = structlog.get_logger(__name__)


class MetricType(Enum):
    """Types of metrics collected."""
    COUNTER = "counter"         # Incrementing values
    GAUGE = "gauge"            # Current value
    HISTOGRAM = "histogram"    # Distribution of values
    SUMMARY = "summary"        # Statistical summary


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Metric:
    """Individual metric data point."""
    name: str
    value: Union[int, float]
    timestamp: float
    metric_type: MetricType
    labels: Dict[str, str] = field(default_factory=dict)
    description: str = ""


@dataclass
class Alert:
    """Alert definition and state."""
    name: str
    condition: Callable[[Dict[str, Any]], bool]
    severity: AlertSeverity
    message_template: str
    cooldown_seconds: int = 300  # 5 minutes default
    
    # State tracking
    last_triggered: float = 0.0
    triggered_count: int = 0
    active: bool = False


@dataclass
class PerformanceBaseline:
    """Performance baseline for anomaly detection."""
    metric_name: str
    baseline_value: float
    deviation_threshold: float  # Percentage deviation to trigger alert
    sample_size: int = 100
    samples: deque = field(default_factory=lambda: deque(maxlen=100))
    last_updated: float = 0.0


class MetricsCollector:
    """
    Comprehensive metrics collection system.
    
    Collects metrics from all system components and provides
    alerting, trend analysis, and performance monitoring.
    """
    
    def __init__(self):
        self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.current_metrics: Dict[str, Metric] = {}
        self.alerts: Dict[str, Alert] = {}
        self.baselines: Dict[str, PerformanceBaseline] = {}
        
        self.collection_interval = 30  # seconds
        self.collecting = False
        
        # Setup metrics and alerts
        self._setup_alerts()
        self._setup_performance_baselines()
    
    def _setup_alerts(self):
        """Setup system alerts."""
        
        # Database alerts
        self.alerts["high_db_pool_usage"] = Alert(
            name="high_db_pool_usage",
            condition=lambda metrics: metrics.get("database_pool_utilization", 0) > 0.8,
            severity=AlertSeverity.WARNING,
            message_template="Database pool utilization is high: {database_pool_utilization:.1%}",
            cooldown_seconds=300
        )
        
        self.alerts["database_connection_failure"] = Alert(
            name="database_connection_failure",
            condition=lambda metrics: not metrics.get("database_connected", True),
            severity=AlertSeverity.CRITICAL,
            message_template="Database connection failed",
            cooldown_seconds=60
        )
        
        # System resource alerts
        self.alerts["high_cpu_usage"] = Alert(
            name="high_cpu_usage",
            condition=lambda metrics: metrics.get("cpu_usage_percent", 0) > 85,
            severity=AlertSeverity.WARNING,
            message_template="High CPU usage: {cpu_usage_percent:.1f}%",
            cooldown_seconds=600
        )
        
        self.alerts["high_memory_usage"] = Alert(
            name="high_memory_usage",
            condition=lambda metrics: metrics.get("memory_usage_percent", 0) > 90,
            severity=AlertSeverity.ERROR,
            message_template="High memory usage: {memory_usage_percent:.1f}%",
            cooldown_seconds=300
        )
        
        self.alerts["low_disk_space"] = Alert(
            name="low_disk_space",
            condition=lambda metrics: metrics.get("disk_usage_percent", 0) > 90,
            severity=AlertSeverity.CRITICAL,
            message_template="Low disk space: {disk_usage_percent:.1f}% used",
            cooldown_seconds=1800
        )
        
        # Celery worker alerts
        self.alerts["no_active_workers"] = Alert(
            name="no_active_workers",
            condition=lambda metrics: metrics.get("celery_active_workers", 1) == 0,
            severity=AlertSeverity.CRITICAL,
            message_template="No active Celery workers detected",
            cooldown_seconds=300
        )
        
        self.alerts["high_queue_backlog"] = Alert(
            name="high_queue_backlog",
            condition=lambda metrics: max(metrics.get("celery_queue_lengths", {}).values(), default=0) > 500,
            severity=AlertSeverity.WARNING,
            message_template="High task queue backlog detected",
            cooldown_seconds=600
        )
        
        # Circuit breaker alerts
        self.alerts["circuit_breakers_open"] = Alert(
            name="circuit_breakers_open",
            condition=lambda metrics: len(metrics.get("open_circuit_breakers", [])) > 0,
            severity=AlertSeverity.ERROR,
            message_template="Circuit breakers are open: {open_circuit_breakers}",
            cooldown_seconds=300
        )
        
        # API performance alerts
        self.alerts["high_api_response_time"] = Alert(
            name="high_api_response_time",
            condition=lambda metrics: metrics.get("api_avg_response_time", 0) > 2.0,
            severity=AlertSeverity.WARNING,
            message_template="High API response time: {api_avg_response_time:.2f}s",
            cooldown_seconds=300
        )
        
        # Health monitoring alerts
        self.alerts["critical_health_issues"] = Alert(
            name="critical_health_issues",
            condition=lambda metrics: metrics.get("health_critical_issues", 0) > 0,
            severity=AlertSeverity.CRITICAL,
            message_template="Critical health issues detected: {health_critical_issues}",
            cooldown_seconds=300
        )
    
    def _setup_performance_baselines(self):
        """Setup performance baselines for anomaly detection."""
        
        # API response time baseline
        self.baselines["api_response_time"] = PerformanceBaseline(
            metric_name="api_avg_response_time",
            baseline_value=0.5,  # 500ms baseline
            deviation_threshold=50.0  # 50% deviation
        )
        
        # Database query time baseline
        self.baselines["db_query_time"] = PerformanceBaseline(
            metric_name="database_avg_query_time",
            baseline_value=0.1,  # 100ms baseline
            deviation_threshold=100.0  # 100% deviation
        )
        
        # Memory usage baseline
        self.baselines["memory_usage"] = PerformanceBaseline(
            metric_name="memory_usage_percent",
            baseline_value=60.0,  # 60% baseline
            deviation_threshold=25.0  # 25% deviation
        )
        
        # Task processing rate baseline
        self.baselines["task_processing_rate"] = PerformanceBaseline(
            metric_name="celery_tasks_per_minute",
            baseline_value=50.0,  # 50 tasks/minute baseline
            deviation_threshold=30.0  # 30% deviation
        )
    
    async def start_collection(self):
        """Start metrics collection."""
        if self.collecting:
            logger.warning("Metrics collection already active")
            return
        
        self.collecting = True
        logger.info("Starting metrics collection", interval=self.collection_interval)
        
        while self.collecting:
            try:
                await self._collect_all_metrics()
                await self._evaluate_alerts()
                await self._update_baselines()
                await asyncio.sleep(self.collection_interval)
            
            except Exception as e:
                logger.error("Error in metrics collection loop", error=str(e))
                await asyncio.sleep(10)  # Short delay before retry
    
    async def stop_collection(self):
        """Stop metrics collection."""
        self.collecting = False
        logger.info("Stopped metrics collection")
    
    async def _collect_all_metrics(self):
        """Collect all system metrics."""
        timestamp = time.time()
        
        # Collect metrics from different sources concurrently
        tasks = [
            self._collect_system_metrics(timestamp),
            self._collect_database_metrics(timestamp),
            self._collect_redis_metrics(timestamp),
            self._collect_celery_metrics(timestamp),
            self._collect_circuit_breaker_metrics(timestamp),
            self._collect_health_metrics(timestamp),
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.debug("Metrics collection completed", metrics_count=len(self.current_metrics))
    
    async def _collect_system_metrics(self, timestamp: float):
        """Collect system resource metrics."""
        try:
            # CPU metrics
            cpu_usage = psutil.cpu_percent(interval=0.1)
            self._record_metric("cpu_usage_percent", cpu_usage, timestamp, MetricType.GAUGE,
                              description="CPU usage percentage")
            
            cpu_count = psutil.cpu_count()
            self._record_metric("cpu_count", cpu_count, timestamp, MetricType.GAUGE,
                              description="Number of CPU cores")
            
            # Memory metrics
            memory = psutil.virtual_memory()
            self._record_metric("memory_usage_percent", memory.percent, timestamp, MetricType.GAUGE,
                              description="Memory usage percentage")
            self._record_metric("memory_used_gb", memory.used / (1024**3), timestamp, MetricType.GAUGE,
                              description="Memory used in GB")
            self._record_metric("memory_available_gb", memory.available / (1024**3), timestamp, MetricType.GAUGE,
                              description="Memory available in GB")
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            self._record_metric("disk_usage_percent", (disk.used / disk.total) * 100, timestamp, MetricType.GAUGE,
                              description="Disk usage percentage")
            self._record_metric("disk_free_gb", disk.free / (1024**3), timestamp, MetricType.GAUGE,
                              description="Disk free space in GB")
            
            # Network metrics
            network = psutil.net_io_counters()
            self._record_metric("network_bytes_sent", network.bytes_sent, timestamp, MetricType.COUNTER,
                              description="Total network bytes sent")
            self._record_metric("network_bytes_recv", network.bytes_recv, timestamp, MetricType.COUNTER,
                              description="Total network bytes received")
            
            # Process metrics
            process_count = len(psutil.pids())
            self._record_metric("process_count", process_count, timestamp, MetricType.GAUGE,
                              description="Number of running processes")
            
        except Exception as e:
            logger.error("Failed to collect system metrics", error=str(e))
    
    async def _collect_database_metrics(self, timestamp: float):
        """Collect database metrics."""
        try:
            # Database connection pool stats
            db_stats = await get_db_stats()
            
            pool_utilization = (db_stats["checked_out"] / db_stats["total"]) if db_stats["total"] > 0 else 0
            self._record_metric("database_pool_utilization", pool_utilization, timestamp, MetricType.GAUGE,
                              description="Database connection pool utilization")
            
            self._record_metric("database_connections_active", db_stats["checked_out"], timestamp, MetricType.GAUGE,
                              description="Active database connections")
            self._record_metric("database_connections_idle", db_stats["checked_in"], timestamp, MetricType.GAUGE,
                              description="Idle database connections")
            self._record_metric("database_connections_total", db_stats["total"], timestamp, MetricType.GAUGE,
                              description="Total database connections")
            
            # Database health check
            from src.config.database import check_database_connection
            db_connected = await check_database_connection()
            self._record_metric("database_connected", 1 if db_connected else 0, timestamp, MetricType.GAUGE,
                              description="Database connection status")
            
        except Exception as e:
            logger.error("Failed to collect database metrics", error=str(e))
    
    async def _collect_redis_metrics(self, timestamp: float):
        """Collect Redis metrics."""
        try:
            redis_client = await get_redis_client()
            if redis_client:
                # Redis connection test
                await redis_client.ping()
                self._record_metric("redis_connected", 1, timestamp, MetricType.GAUGE,
                                  description="Redis connection status")
                
                # Redis info
                info = await redis_client.info()
                
                # Memory metrics
                self._record_metric("redis_memory_used_mb", info.get("used_memory", 0) / (1024**2), 
                                  timestamp, MetricType.GAUGE, description="Redis memory used in MB")
                
                # Connection metrics
                self._record_metric("redis_connected_clients", info.get("connected_clients", 0), 
                                  timestamp, MetricType.GAUGE, description="Redis connected clients")
                
                # Operations metrics
                self._record_metric("redis_total_commands", info.get("total_commands_processed", 0), 
                                  timestamp, MetricType.COUNTER, description="Redis total commands processed")
                
                # Keyspace metrics
                keyspace_hits = info.get("keyspace_hits", 0)
                keyspace_misses = info.get("keyspace_misses", 0)
                total_operations = keyspace_hits + keyspace_misses
                hit_rate = (keyspace_hits / total_operations) if total_operations > 0 else 0
                
                self._record_metric("redis_hit_rate", hit_rate, timestamp, MetricType.GAUGE,
                                  description="Redis cache hit rate")
            else:
                self._record_metric("redis_connected", 0, timestamp, MetricType.GAUGE,
                                  description="Redis connection status")
                
        except Exception as e:
            logger.error("Failed to collect Redis metrics", error=str(e))
            self._record_metric("redis_connected", 0, timestamp, MetricType.GAUGE,
                              description="Redis connection status")
    
    async def _collect_celery_metrics(self, timestamp: float):
        """Collect Celery worker metrics."""
        try:
            # Celery health check
            celery_health = await check_celery_health()
            
            active_workers = celery_health.get("active_workers", 0)
            self._record_metric("celery_active_workers", active_workers, timestamp, MetricType.GAUGE,
                              description="Active Celery workers")
            
            # Queue lengths
            queue_lengths = celery_health.get("queue_lengths", {})
            for queue_name, length in queue_lengths.items():
                if isinstance(length, int):
                    self._record_metric(f"celery_queue_length_{queue_name}", length, timestamp, MetricType.GAUGE,
                                      labels={"queue": queue_name}, description=f"Queue length for {queue_name}")
            
            # Overall queue metrics
            total_queued = sum(length for length in queue_lengths.values() if isinstance(length, int))
            self._record_metric("celery_total_queued_tasks", total_queued, timestamp, MetricType.GAUGE,
                              description="Total queued tasks across all queues")
            
            # Enhanced task stats
            task_stats = get_enhanced_task_stats()
            self._record_metric("celery_active_tasks", task_stats.get("active_tasks", 0), timestamp, MetricType.GAUGE,
                              description="Currently active tasks")
            self._record_metric("celery_scheduled_tasks", task_stats.get("scheduled_tasks", 0), timestamp, MetricType.GAUGE,
                              description="Scheduled tasks")
            self._record_metric("celery_reserved_tasks", task_stats.get("reserved_tasks", 0), timestamp, MetricType.GAUGE,
                              description="Reserved tasks")
            
        except Exception as e:
            logger.error("Failed to collect Celery metrics", error=str(e))
    
    async def _collect_circuit_breaker_metrics(self, timestamp: float):
        """Collect circuit breaker metrics."""
        try:
            cb_states = get_all_circuit_breaker_states()
            
            open_breakers = []
            half_open_breakers = []
            
            for name, state in cb_states.items():
                breaker_state = state["state"]
                
                # Individual breaker metrics
                state_value = {"closed": 0, "half_open": 1, "open": 2}.get(breaker_state, 0)
                self._record_metric(f"circuit_breaker_state_{name}", state_value, timestamp, MetricType.GAUGE,
                                  labels={"breaker": name}, description=f"Circuit breaker state for {name}")
                
                # Failure count
                failure_count = state.get("failure_count", 0)
                self._record_metric(f"circuit_breaker_failures_{name}", failure_count, timestamp, MetricType.GAUGE,
                                  labels={"breaker": name}, description=f"Failure count for {name}")
                
                # Success rate
                stats = state.get("stats", {})
                success_rate = stats.get("success_rate", 0)
                self._record_metric(f"circuit_breaker_success_rate_{name}", success_rate, timestamp, MetricType.GAUGE,
                                  labels={"breaker": name}, description=f"Success rate for {name}")
                
                # Track open/half-open breakers
                if breaker_state == "open":
                    open_breakers.append(name)
                elif breaker_state == "half_open":
                    half_open_breakers.append(name)
            
            # Overall circuit breaker metrics
            self._record_metric("circuit_breakers_open_count", len(open_breakers), timestamp, MetricType.GAUGE,
                              description="Number of open circuit breakers")
            self._record_metric("circuit_breakers_half_open_count", len(half_open_breakers), timestamp, MetricType.GAUGE,
                              description="Number of half-open circuit breakers")
            
            # Store for alerting
            self.current_metrics["open_circuit_breakers"] = Metric(
                "open_circuit_breakers", open_breakers, timestamp, MetricType.GAUGE
            )
            
        except Exception as e:
            logger.error("Failed to collect circuit breaker metrics", error=str(e))
    
    async def _collect_health_metrics(self, timestamp: float):
        """Collect health monitoring metrics."""
        try:
            health_status = get_system_health()
            health_summary = get_health_summary()
            
            # Overall health status
            overall_status = health_summary.get("overall_status", "unknown")
            status_value = {"healthy": 0, "degraded": 1, "unhealthy": 2, "critical": 3, "unknown": 4}.get(overall_status, 4)
            self._record_metric("health_overall_status", status_value, timestamp, MetricType.GAUGE,
                              description="Overall system health status")
            
            # Health check counts
            self._record_metric("health_total_checks", health_summary.get("total_checks", 0), timestamp, MetricType.GAUGE,
                              description="Total health checks")
            self._record_metric("health_healthy_checks", health_summary.get("healthy_checks", 0), timestamp, MetricType.GAUGE,
                              description="Healthy checks count")
            self._record_metric("health_critical_issues", health_summary.get("critical_issues", 0), timestamp, MetricType.GAUGE,
                              description="Critical health issues count")
            
            # Individual health check metrics
            checks = health_status.get("checks", {})
            for check_name, check_data in checks.items():
                status = check_data.get("status", "unknown")
                status_value = {"healthy": 0, "degraded": 1, "unhealthy": 2, "critical": 3, "unknown": 4}.get(status, 4)
                
                self._record_metric(f"health_check_status_{check_name}", status_value, timestamp, MetricType.GAUGE,
                                  labels={"check": check_name}, description=f"Health check status for {check_name}")
                
                response_time = check_data.get("response_time", 0)
                self._record_metric(f"health_check_response_time_{check_name}", response_time, timestamp, MetricType.GAUGE,
                                  labels={"check": check_name}, description=f"Health check response time for {check_name}")
                
                consecutive_failures = check_data.get("consecutive_failures", 0)
                self._record_metric(f"health_check_failures_{check_name}", consecutive_failures, timestamp, MetricType.GAUGE,
                                  labels={"check": check_name}, description=f"Consecutive failures for {check_name}")
            
        except Exception as e:
            logger.error("Failed to collect health metrics", error=str(e))
    
    def _record_metric(self, name: str, value: Union[int, float], timestamp: float, 
                      metric_type: MetricType, labels: Dict[str, str] = None, description: str = ""):
        """Record a metric value."""
        metric = Metric(
            name=name,
            value=value,
            timestamp=timestamp,
            metric_type=metric_type,
            labels=labels or {},
            description=description
        )
        
        self.current_metrics[name] = metric
        self.metrics_history[name].append(metric)
    
    async def _evaluate_alerts(self):
        """Evaluate all alert conditions."""
        current_values = {name: metric.value for name, metric in self.current_metrics.items()}
        current_time = time.time()
        
        for alert_name, alert in self.alerts.items():
            try:
                # Check if alert condition is met
                condition_met = alert.condition(current_values)
                
                # Check cooldown period
                time_since_last = current_time - alert.last_triggered
                in_cooldown = time_since_last < alert.cooldown_seconds
                
                if condition_met and not in_cooldown:
                    # Trigger alert
                    await self._trigger_alert(alert, current_values)
                elif not condition_met and alert.active:
                    # Clear alert
                    await self._clear_alert(alert)
            
            except Exception as e:
                logger.error(f"Error evaluating alert {alert_name}", error=str(e))
    
    async def _trigger_alert(self, alert: Alert, current_values: Dict[str, Any]):
        """Trigger an alert."""
        alert.last_triggered = time.time()
        alert.triggered_count += 1
        alert.active = True
        
        # Format alert message
        try:
            message = alert.message_template.format(**current_values)
        except KeyError as e:
            message = f"{alert.message_template} (missing value: {e})"
        
        logger.log(
            alert.severity.value.upper(),
            f"ALERT TRIGGERED: {alert.name}",
            message=message,
            severity=alert.severity.value,
            triggered_count=alert.triggered_count
        )
        
        # Send alert to external systems
        await self._send_alert_notification(alert, message)
    
    async def _clear_alert(self, alert: Alert):
        """Clear an active alert."""
        alert.active = False
        
        logger.info(
            f"ALERT CLEARED: {alert.name}",
            severity=alert.severity.value,
            duration=time.time() - alert.last_triggered
        )
    
    async def _send_alert_notification(self, alert: Alert, message: str):
        """Send alert notification to external systems."""
        try:
            # Here you would integrate with:
            # - Slack/Discord webhooks
            # - Email notifications
            # - PagerDuty/OpsGenie
            # - Custom webhook endpoints
            
            alert_data = {
                "alert_name": alert.name,
                "severity": alert.severity.value,
                "message": message,
                "timestamp": time.time(),
                "triggered_count": alert.triggered_count
            }
            
            # Log alert for now (replace with actual notification service)
            logger.info("Alert notification sent", alert_data=alert_data)
            
        except Exception as e:
            logger.error("Failed to send alert notification", 
                        alert_name=alert.name, error=str(e))
    
    async def _update_baselines(self):
        """Update performance baselines with new data."""
        current_time = time.time()
        
        for baseline_name, baseline in self.baselines.items():
            if baseline.metric_name in self.current_metrics:
                current_value = self.current_metrics[baseline.metric_name].value
                baseline.samples.append(current_value)
                baseline.last_updated = current_time
                
                # Update baseline if we have enough samples
                if len(baseline.samples) >= baseline.sample_size:
                    # Calculate new baseline (moving average)
                    baseline.baseline_value = sum(baseline.samples) / len(baseline.samples)
                    
                    # Check for anomalies
                    deviation = abs(current_value - baseline.baseline_value) / baseline.baseline_value * 100
                    if deviation > baseline.deviation_threshold:
                        logger.warning(
                            f"Performance anomaly detected for {baseline.metric_name}",
                            current_value=current_value,
                            baseline=baseline.baseline_value,
                            deviation_percent=deviation,
                            threshold_percent=baseline.deviation_threshold
                        )
    
    def get_metrics(self, metric_names: List[str] = None, 
                   time_range: int = 3600) -> Dict[str, List[Metric]]:
        """Get metrics for specified names and time range."""
        end_time = time.time()
        start_time = end_time - time_range
        
        if metric_names is None:
            metric_names = list(self.metrics_history.keys())
        
        result = {}
        for name in metric_names:
            if name in self.metrics_history:
                # Filter by time range
                filtered_metrics = [
                    metric for metric in self.metrics_history[name]
                    if start_time <= metric.timestamp <= end_time
                ]
                result[name] = filtered_metrics
        
        return result
    
    def get_current_metrics(self) -> Dict[str, Metric]:
        """Get current metric values."""
        return self.current_metrics.copy()
    
    def get_alert_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all alerts."""
        return {
            name: {
                "active": alert.active,
                "last_triggered": alert.last_triggered,
                "triggered_count": alert.triggered_count,
                "severity": alert.severity.value,
                "cooldown_seconds": alert.cooldown_seconds
            }
            for name, alert in self.alerts.items()
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary with trends."""
        summary = {
            "timestamp": time.time(),
            "metrics_count": len(self.current_metrics),
            "active_alerts": sum(1 for alert in self.alerts.values() if alert.active),
            "total_alerts_triggered": sum(alert.triggered_count for alert in self.alerts.values()),
            "baselines": {
                name: {
                    "current_baseline": baseline.baseline_value,
                    "sample_count": len(baseline.samples),
                    "last_updated": baseline.last_updated
                }
                for name, baseline in self.baselines.items()
            }
        }
        
        # Add key performance indicators
        if "cpu_usage_percent" in self.current_metrics:
            summary["cpu_usage"] = self.current_metrics["cpu_usage_percent"].value
        if "memory_usage_percent" in self.current_metrics:
            summary["memory_usage"] = self.current_metrics["memory_usage_percent"].value
        if "database_pool_utilization" in self.current_metrics:
            summary["db_pool_usage"] = self.current_metrics["database_pool_utilization"].value
        if "celery_active_workers" in self.current_metrics:
            summary["active_workers"] = self.current_metrics["celery_active_workers"].value
        
        return summary
    
    async def export_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        
        for metric in self.current_metrics.values():
            # Add metric help/description
            if metric.description:
                lines.append(f"# HELP {metric.name} {metric.description}")
            
            # Add metric type
            lines.append(f"# TYPE {metric.name} {metric.metric_type.value}")
            
            # Add metric value with labels
            if metric.labels:
                label_str = ",".join(f'{k}="{v}"' for k, v in metric.labels.items())
                lines.append(f"{metric.name}{{{label_str}}} {metric.value}")
            else:
                lines.append(f"{metric.name} {metric.value}")
        
        return "\n".join(lines)


# Global metrics collector instance
metrics_collector = MetricsCollector()


# Convenience functions
async def start_metrics_collection():
    """Start the global metrics collection system."""
    await metrics_collector.start_collection()


async def stop_metrics_collection():
    """Stop the global metrics collection system."""
    await metrics_collector.stop_collection()


def get_current_metrics() -> Dict[str, Metric]:
    """Get current metric values."""
    return metrics_collector.get_current_metrics()


def get_metrics_history(metric_names: List[str] = None, time_range: int = 3600) -> Dict[str, List[Metric]]:
    """Get metrics history."""
    return metrics_collector.get_metrics(metric_names, time_range)


def get_alert_status() -> Dict[str, Dict[str, Any]]:
    """Get alert status."""
    return metrics_collector.get_alert_status()


def get_performance_summary() -> Dict[str, Any]:
    """Get performance summary."""
    return metrics_collector.get_performance_summary()


async def export_prometheus_metrics() -> str:
    """Export metrics in Prometheus format."""
    return await metrics_collector.export_prometheus_metrics() 