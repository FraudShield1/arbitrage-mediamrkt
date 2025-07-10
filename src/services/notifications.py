"""
Simple notifications service for testing and basic functionality.
"""

import asyncio
import aiohttp
import structlog
from typing import Optional

from src.config.settings import settings

logger = structlog.get_logger(__name__)


async def send_telegram_notification(title: str, message: str) -> bool:
    """
    Send a Telegram notification.
    
    Args:
        title: Message title
        message: Message body
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
            logger.warning("Telegram credentials not configured")
            return False
        
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        
        text = f"*{title}*\n\n{message}"
        
        payload = {
            "chat_id": settings.TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "Markdown"
        }
        
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    logger.info("Telegram notification sent successfully", title=title)
                    return True
                else:
                    response_text = await response.text()
                    logger.error("Telegram notification failed", 
                               status=response.status, 
                               response=response_text)
                    return False
                    
    except Exception as e:
        logger.error("Telegram notification error", error=str(e))
        return False


async def send_slack_notification(title: str, message: str, webhook_url: Optional[str] = None) -> bool:
    """
    Send a Slack notification.
    
    Args:
        title: Message title
        message: Message body
        webhook_url: Slack webhook URL (optional, uses settings if not provided)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        webhook = webhook_url or settings.SLACK_WEBHOOK_URL
        
        if not webhook:
            logger.warning("Slack webhook URL not configured")
            return False
        
        payload = {
            "text": f"*{title}*",
            "attachments": [
                {
                    "text": message,
                    "color": "good"
                }
            ]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook, json=payload) as response:
                if response.status == 200:
                    logger.info("Slack notification sent successfully", title=title)
                    return True
                else:
                    response_text = await response.text()
                    logger.error("Slack notification failed", 
                               status=response.status, 
                               response=response_text)
                    return False
                    
    except Exception as e:
        logger.error("Slack notification error", error=str(e))
        return False 