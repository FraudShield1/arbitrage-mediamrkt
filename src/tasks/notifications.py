"""
Notification background tasks.
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
import structlog

from src.config.celery import celery_app, CallbackTask, TaskErrorHandler
from src.config.database import get_database_session
from src.models.product import Product
from src.models.asin import ASIN
from src.models.alert import PriceAlert
from src.services.notifier.telegram_notifier import TelegramNotifier
from src.services.notifier.slack_notifier import SlackNotifier
from src.services.notifier.email_notifier import EmailNotifier
from src.config.settings import settings

logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, base=CallbackTask, name="src.tasks.notifications.send_arbitrage_alert")
def send_arbitrage_alert(
    self,
    alert_id: int,
    priority: str = "medium"
) -> Dict[str, Any]:
    """
    Send arbitrage alert through all configured channels.
    
    Args:
        alert_id: ID of the alert to send
        priority: Alert priority (low, medium, high, critical)
        
    Returns:
        Notification statistics
    """
    return asyncio.run(_send_arbitrage_alert_async(
        task_id=self.request.id,
        alert_id=alert_id,
        priority=priority
    ))


async def _send_arbitrage_alert_async(
    task_id: str,
    alert_id: int,
    priority: str = "medium"
) -> Dict[str, Any]:
    """Async implementation of arbitrage alert sending."""
    stats = {
        "task_id": task_id,
        "alert_id": alert_id,
        "priority": priority,
        "channels_attempted": 0,
        "channels_successful": 0,
        "telegram_sent": False,
        "slack_sent": False,
        "email_sent": False,
        "errors": []
    }
    
    db_session = None
    
    try:
        # Initialize database session
        async for db_session in get_database_session():
            break
        
        # Get alert with related data
        result = await db_session.execute(
            select(PriceAlert, Product, ASIN)
            .select_from(
                PriceAlert
                .join(Product, PriceAlert.product_id == Product.id)
                .join(ASIN, PriceAlert.asin_id == ASIN.id)
            )
            .where(PriceAlert.id == alert_id)
        )
        
        row = result.first()
        if not row:
            error_msg = f"Alert {alert_id} not found"
            stats["errors"].append(error_msg)
            logger.error(error_msg, task_id=task_id)
            return stats
        
        alert, product, asin = row
        
        logger.info(
            f"Sending {priority} arbitrage alert",
            task_id=task_id,
            alert_id=alert_id,
            product_id=product.id,
            asin=asin.asin
        )
        
        # Prepare notification data
        product_data = {
            "title": product.title,
            "brand": product.brand,
            "category": product.category,
            "price": float(product.price),
            "original_price": float(product.original_price) if product.original_price else None,
            "discount_percentage": float(product.discount_percentage) if product.discount_percentage else 0,
            "ean": product.ean,
            "stock_status": product.stock_status,
            "url": product.url
        }
        
        alert_data = {
            "severity": alert.severity,
            "profit_potential": float(alert.profit_potential),
            "profit_percentage": float(alert.profit_percentage),
            "price_difference": float(alert.price_difference),
            "confidence_score": alert.confidence_score,
            "average_price": float(alert.amazon_average_price),
            "discount_percentage": float(product.discount_percentage) if product.discount_percentage else 0,
            "asin": asin.asin
        }
        
        # Send through configured channels based on priority
        channels_to_use = _get_channels_for_priority(priority)
        
        # Send Telegram notification
        if "telegram" in channels_to_use and settings.telegram.enabled:
            stats["channels_attempted"] += 1
            try:
                success = await TelegramNotifier().send_arbitrage_alert(
                    chat_ids=settings.telegram.chat_ids,
                    product_data=product_data,
                    alert_data=alert_data
                )
                if success:
                    stats["telegram_sent"] = True
                    stats["channels_successful"] += 1
                else:
                    stats["errors"].append("Telegram notification failed")
            except Exception as e:
                error_msg = f"Telegram notification error: {str(e)}"
                stats["errors"].append(error_msg)
                logger.error(error_msg, task_id=task_id, alert_id=alert_id)
        
        # Send Slack notification
        if "slack" in channels_to_use and settings.slack.enabled:
            stats["channels_attempted"] += 1
            try:
                success = await SlackNotifier().send_arbitrage_alert(
                    webhook_url=settings.slack.webhook_url,
                    product_data=product_data,
                    alert_data=alert_data
                )
                if success:
                    stats["slack_sent"] = True
                    stats["channels_successful"] += 1
                else:
                    stats["errors"].append("Slack notification failed")
            except Exception as e:
                error_msg = f"Slack notification error: {str(e)}"
                stats["errors"].append(error_msg)
                logger.error(error_msg, task_id=task_id, alert_id=alert_id)
        
        # Send Email notification
        if "email" in channels_to_use and settings.email.enabled:
            stats["channels_attempted"] += 1
            try:
                success = await EmailNotifier().send_arbitrage_alert(
                    recipients=settings.email.recipients,
                    product_data=product_data,
                    alert_data=alert_data
                )
                if success:
                    stats["email_sent"] = True
                    stats["channels_successful"] += 1
                else:
                    stats["errors"].append("Email notification failed")
            except Exception as e:
                error_msg = f"Email notification error: {str(e)}"
                stats["errors"].append(error_msg)
                logger.error(error_msg, task_id=task_id, alert_id=alert_id)
        
        # Update alert status
        if stats["channels_successful"] > 0:
            alert.status = "sent"
            alert.notification_sent_at = datetime.utcnow()
        else:
            alert.status = "failed"
        
        await db_session.commit()
        
        logger.info(
            f"Alert notification completed",
            task_id=task_id,
            alert_id=alert_id,
            **{k: v for k, v in stats.items() if k != "errors"}
        )
        
        return stats
        
    except Exception as e:
        error_msg = f"Critical error in alert notification task: {str(e)}"
        stats["errors"].append(error_msg)
        logger.error(error_msg, task_id=task_id, alert_id=alert_id)
        raise
        
    finally:
        if db_session:
            await db_session.close()


def _get_channels_for_priority(priority: str) -> List[str]:
    """Get notification channels based on alert priority."""
    channels_map = {
        "critical": ["telegram", "slack", "email"],
        "high": ["telegram", "slack"],
        "medium": ["telegram"],
        "low": ["telegram"]
    }
    return channels_map.get(priority, ["telegram"])


@celery_app.task(bind=True, base=CallbackTask, name="src.tasks.notifications.send_daily_summary")
def send_daily_summary(self) -> Dict[str, Any]:
    """
    Send daily summary report through all channels.
    
    Returns:
        Summary statistics
    """
    return asyncio.run(_send_daily_summary_async(
        task_id=self.request.id
    ))


async def _send_daily_summary_async(task_id: str) -> Dict[str, Any]:
    """Async implementation of daily summary sending."""
    stats = {
        "task_id": task_id,
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "channels_attempted": 0,
        "channels_successful": 0,
        "telegram_sent": False,
        "slack_sent": False,
        "email_sent": False,
        "errors": []
    }
    
    db_session = None
    
    try:
        # Initialize database session
        async for db_session in get_database_session():
            break
        
        logger.info(f"Generating daily summary", task_id=task_id)
        
        # Generate summary data
        summary_data = await _generate_daily_summary_data(db_session)
        
        # Send through all configured channels
        if settings.telegram.enabled:
            stats["channels_attempted"] += 1
            try:
                success = await TelegramNotifier().send_daily_summary(
                    chat_ids=settings.telegram.chat_ids,
                    summary_data=summary_data
                )
                if success:
                    stats["telegram_sent"] = True
                    stats["channels_successful"] += 1
                else:
                    stats["errors"].append("Telegram summary failed")
            except Exception as e:
                error_msg = f"Telegram summary error: {str(e)}"
                stats["errors"].append(error_msg)
                logger.error(error_msg, task_id=task_id)
        
        if settings.slack.enabled:
            stats["channels_attempted"] += 1
            try:
                success = await SlackNotifier().send_daily_summary(
                    webhook_url=settings.slack.webhook_url,
                    summary_data=summary_data
                )
                if success:
                    stats["slack_sent"] = True
                    stats["channels_successful"] += 1
                else:
                    stats["errors"].append("Slack summary failed")
            except Exception as e:
                error_msg = f"Slack summary error: {str(e)}"
                stats["errors"].append(error_msg)
                logger.error(error_msg, task_id=task_id)
        
        if settings.email.enabled:
            stats["channels_attempted"] += 1
            try:
                success = await EmailNotifier().send_daily_summary(
                    recipients=settings.email.recipients,
                    summary_data=summary_data
                )
                if success:
                    stats["email_sent"] = True
                    stats["channels_successful"] += 1
                else:
                    stats["errors"].append("Email summary failed")
            except Exception as e:
                error_msg = f"Email summary error: {str(e)}"
                stats["errors"].append(error_msg)
                logger.error(error_msg, task_id=task_id)
        
        logger.info(
            f"Daily summary completed",
            task_id=task_id,
            **{k: v for k, v in stats.items() if k != "errors"}
        )
        
        return stats
        
    except Exception as e:
        error_msg = f"Critical error in daily summary task: {str(e)}"
        stats["errors"].append(error_msg)
        logger.error(error_msg, task_id=task_id)
        raise
        
    finally:
        if db_session:
            await db_session.close()


async def _generate_daily_summary_data(db_session: AsyncSession) -> Dict[str, Any]:
    """Generate daily summary statistics."""
    today = datetime.utcnow().date()
    yesterday = today - timedelta(days=1)
    
    # Get today's alerts
    alerts_result = await db_session.execute(
        select(PriceAlert)
        .where(
            and_(
                PriceAlert.created_at >= datetime.combine(today, datetime.min.time()),
                PriceAlert.created_at < datetime.combine(today + timedelta(days=1), datetime.min.time())
            )
        )
    )
    today_alerts = alerts_result.scalars().all()
    
    # Get yesterday's alerts for comparison
    yesterday_alerts_result = await db_session.execute(
        select(func.count(PriceAlert.id))
        .where(
            and_(
                PriceAlert.created_at >= datetime.combine(yesterday, datetime.min.time()),
                PriceAlert.created_at < datetime.combine(today, datetime.min.time())
            )
        )
    )
    yesterday_count = yesterday_alerts_result.scalar() or 0
    
    # Calculate statistics
    total_alerts = len(today_alerts)
    total_profit_potential = sum(float(alert.profit_potential) for alert in today_alerts)
    
    # Get severity breakdown
    severity_counts = {}
    for alert in today_alerts:
        severity_counts[alert.severity] = severity_counts.get(alert.severity, 0) + 1
    
    # Get top opportunities
    top_opportunities = []
    for alert in sorted(today_alerts, key=lambda x: x.profit_potential, reverse=True)[:10]:
        try:
            # Get product data
            product_result = await db_session.execute(
                select(Product, ASIN)
                .select_from(Product.join(ASIN, alert.asin_id == ASIN.id))
                .where(Product.id == alert.product_id)
            )
            product_row = product_result.first()
            
            if product_row:
                product, asin = product_row
                top_opportunities.append({
                    "title": product.title,
                    "brand": product.brand,
                    "price": float(product.price),
                    "discount_percentage": float(product.discount_percentage) if product.discount_percentage else 0,
                    "profit_potential": float(alert.profit_potential),
                    "profit_percentage": float(alert.profit_percentage),
                    "severity": alert.severity,
                    "url": product.url,
                    "asin": asin.asin
                })
        except Exception as e:
            logger.warning(f"Error getting product data for alert {alert.id}: {str(e)}")
    
    # Get system statistics
    products_scraped_result = await db_session.execute(
        select(func.count(Product.id))
        .where(
            Product.last_seen >= datetime.combine(today, datetime.min.time())
        )
    )
    products_scraped = products_scraped_result.scalar() or 0
    
    # Calculate success rate (alerts / products scraped)
    success_rate = (total_alerts / max(products_scraped, 1)) * 100
    
    return {
        "date": today.strftime("%Y-%m-%d"),
        "total_alerts": total_alerts,
        "yesterday_alerts": yesterday_count,
        "alert_change": total_alerts - yesterday_count,
        "total_profit_potential": total_profit_potential,
        "average_profit": total_profit_potential / max(total_alerts, 1),
        "severity_breakdown": severity_counts,
        "top_opportunities": top_opportunities,
        "products_scraped": products_scraped,
        "success_rate": success_rate,
        "generated_at": datetime.utcnow().isoformat()
    }


@celery_app.task(bind=True, base=CallbackTask, name="src.tasks.notifications.send_system_notification")
def send_system_notification(
    self,
    message: str,
    severity: str = "info",
    channels: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Send system notification through specified channels.
    
    Args:
        message: Notification message
        severity: Notification severity (info, warning, error)
        channels: Specific channels to use (default: all)
        
    Returns:
        Notification statistics
    """
    return asyncio.run(_send_system_notification_async(
        task_id=self.request.id,
        message=message,
        severity=severity,
        channels=channels or ["telegram", "slack", "email"]
    ))


async def _send_system_notification_async(
    task_id: str,
    message: str,
    severity: str = "info",
    channels: List[str] = None
) -> Dict[str, Any]:
    """Async implementation of system notification sending."""
    stats = {
        "task_id": task_id,
        "message": message[:100] + "..." if len(message) > 100 else message,
        "severity": severity,
        "channels_attempted": 0,
        "channels_successful": 0,
        "errors": []
    }
    
    try:
        subject = f"Arbitrage Tool - {severity.title()} Notification"
        
        if "telegram" in channels and settings.telegram.enabled:
            stats["channels_attempted"] += 1
            try:
                success = await TelegramNotifier().send_system_notification(
                    chat_ids=settings.telegram.chat_ids,
                    message=message,
                    severity=severity
                )
                if success:
                    stats["channels_successful"] += 1
                else:
                    stats["errors"].append("Telegram system notification failed")
            except Exception as e:
                stats["errors"].append(f"Telegram error: {str(e)}")
        
        if "slack" in channels and settings.slack.enabled:
            stats["channels_attempted"] += 1
            try:
                success = await SlackNotifier().send_system_notification(
                    webhook_url=settings.slack.webhook_url,
                    message=message,
                    severity=severity
                )
                if success:
                    stats["channels_successful"] += 1
                else:
                    stats["errors"].append("Slack system notification failed")
            except Exception as e:
                stats["errors"].append(f"Slack error: {str(e)}")
        
        if "email" in channels and settings.email.enabled:
            stats["channels_attempted"] += 1
            try:
                success = await EmailNotifier().send_system_notification(
                    recipients=settings.email.recipients,
                    subject=subject,
                    message=message,
                    severity=severity
                )
                if success:
                    stats["channels_successful"] += 1
                else:
                    stats["errors"].append("Email system notification failed")
            except Exception as e:
                stats["errors"].append(f"Email error: {str(e)}")
        
        logger.info(
            f"System notification completed",
            task_id=task_id,
            severity=severity,
            **{k: v for k, v in stats.items() if k not in ["errors", "message"]}
        )
        
        return stats
        
    except Exception as e:
        error_msg = f"Critical error in system notification task: {str(e)}"
        stats["errors"].append(error_msg)
        logger.error(error_msg, task_id=task_id)
        raise


@celery_app.task(bind=True, base=CallbackTask, name="src.tasks.notifications.batch_send_alerts")
def batch_send_alerts(
    self,
    alert_ids: List[int],
    priority_override: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send multiple alerts in batch.
    
    Args:
        alert_ids: List of alert IDs to send
        priority_override: Override priority for all alerts
        
    Returns:
        Batch statistics
    """
    return asyncio.run(_batch_send_alerts_async(
        task_id=self.request.id,
        alert_ids=alert_ids,
        priority_override=priority_override
    ))


async def _batch_send_alerts_async(
    task_id: str,
    alert_ids: List[int],
    priority_override: Optional[str] = None
) -> Dict[str, Any]:
    """Async implementation of batch alert sending."""
    stats = {
        "task_id": task_id,
        "alerts_requested": len(alert_ids),
        "alerts_sent": 0,
        "alerts_failed": 0,
        "errors": []
    }
    
    try:
        # Send alerts individually (could be optimized with batching later)
        for alert_id in alert_ids:
            try:
                # Use the existing send_arbitrage_alert task
                result = await _send_arbitrage_alert_async(
                    task_id=f"{task_id}-{alert_id}",
                    alert_id=alert_id,
                    priority=priority_override or "medium"
                )
                
                if result["channels_successful"] > 0:
                    stats["alerts_sent"] += 1
                else:
                    stats["alerts_failed"] += 1
                    stats["errors"].extend(result["errors"])
                    
            except Exception as e:
                stats["alerts_failed"] += 1
                error_msg = f"Error sending alert {alert_id}: {str(e)}"
                stats["errors"].append(error_msg)
                logger.error(error_msg, task_id=task_id, alert_id=alert_id)
        
        logger.info(
            f"Batch alert sending completed",
            task_id=task_id,
            **{k: v for k, v in stats.items() if k != "errors"}
        )
        
        return stats
        
    except Exception as e:
        error_msg = f"Critical error in batch alert task: {str(e)}"
        stats["errors"].append(error_msg)
        logger.error(error_msg, task_id=task_id)
        raise 