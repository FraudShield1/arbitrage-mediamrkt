"""
Slack notification service for sending arbitrage alerts.

This module provides integration with Slack webhooks for sending
formatted notifications about profitable arbitrage opportunities.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

import aiohttp
from pydantic import BaseModel

from ...config.settings import get_settings


logger = logging.getLogger(__name__)


class SlackColor(Enum):
    """Slack message colors."""
    
    GOOD = "good"       # Green
    WARNING = "warning" # Yellow
    DANGER = "danger"   # Red
    DEFAULT = "#36a64f" # Custom green


@dataclass
class SlackAttachment:
    """Slack message attachment structure."""
    
    color: str
    title: Optional[str] = None
    title_link: Optional[str] = None
    text: Optional[str] = None
    fields: List[Dict[str, Any]] = None
    footer: Optional[str] = None
    ts: Optional[int] = None
    
    def __post_init__(self):
        if self.fields is None:
            self.fields = []


@dataclass
class SlackMessage:
    """Slack message structure."""
    
    text: str
    channel: Optional[str] = None
    username: Optional[str] = "ArbitrageBot"
    icon_emoji: Optional[str] = ":moneybag:"
    attachments: List[SlackAttachment] = None
    
    def __post_init__(self):
        if self.attachments is None:
            self.attachments = []


class SlackNotifierError(Exception):
    """Custom exception for Slack notification errors."""
    pass


class SlackNotifier:
    """
    Slack webhook notification service.
    
    Sends formatted alerts about arbitrage opportunities to configured
    Slack channels using incoming webhooks.
    """
    
    def __init__(self, webhook_url: Optional[str] = None):
        self.settings = get_settings()
        self.webhook_url = webhook_url or self.settings.slack_webhook_url
        
        # Default channels from settings
        self.default_channels = self.settings.slack_channels
        
        self.session: Optional[aiohttp.ClientSession] = None
        
        if not self.webhook_url:
            raise ValueError("Slack webhook URL is required")
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                "User-Agent": "ArbitrageBot/1.0",
                "Content-Type": "application/json"
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def _send_webhook(
        self,
        payload: Dict[str, Any],
        retries: int = 3
    ) -> bool:
        """Send message via Slack webhook."""
        
        if not self.session:
            raise RuntimeError("Notifier not initialized. Use async context manager.")
        
        for attempt in range(retries + 1):
            try:
                async with self.session.post(self.webhook_url, json=payload) as response:
                    if response.status == 200:
                        response_text = await response.text()
                        if response_text == "ok":
                            return True
                        else:
                            logger.warning(f"Slack webhook returned: {response_text}")
                            return False
                    elif response.status == 429:
                        # Rate limited
                        wait_time = 2 ** attempt
                        logger.warning(f"Slack webhook rate limited, waiting {wait_time} seconds")
                        await asyncio.sleep(wait_time)
                        continue
                    elif response.status == 400:
                        error_text = await response.text()
                        raise SlackNotifierError(f"Bad request: {error_text}")
                    elif response.status == 403:
                        raise SlackNotifierError("Forbidden - check webhook URL")
                    elif response.status == 404:
                        raise SlackNotifierError("Webhook URL not found")
                    else:
                        error_text = await response.text()
                        raise SlackNotifierError(f"Webhook error {response.status}: {error_text}")
                        
            except aiohttp.ClientError as e:
                if attempt == retries:
                    raise SlackNotifierError(f"Network error: {str(e)}")
                
                wait_time = 2 ** attempt
                logger.warning(f"Network error, retrying in {wait_time} seconds: {e}")
                await asyncio.sleep(wait_time)
        
        raise SlackNotifierError("Max retries exceeded")
    
    async def send_message(self, message: SlackMessage) -> bool:
        """
        Send a message to Slack.
        
        Args:
            message: SlackMessage to send
            
        Returns:
            True if message was sent successfully
        """
        
        try:
            payload = {
                "text": message.text,
                "username": message.username,
                "icon_emoji": message.icon_emoji
            }
            
            if message.channel:
                payload["channel"] = message.channel
            
            if message.attachments:
                payload["attachments"] = []
                for attachment in message.attachments:
                    attachment_dict = {
                        "color": attachment.color
                    }
                    
                    if attachment.title:
                        attachment_dict["title"] = attachment.title
                    if attachment.title_link:
                        attachment_dict["title_link"] = attachment.title_link
                    if attachment.text:
                        attachment_dict["text"] = attachment.text
                    if attachment.fields:
                        attachment_dict["fields"] = attachment.fields
                    if attachment.footer:
                        attachment_dict["footer"] = attachment.footer
                    if attachment.ts:
                        attachment_dict["ts"] = attachment.ts
                    
                    payload["attachments"].append(attachment_dict)
            
            success = await self._send_webhook(payload)
            
            if success:
                logger.info("Slack message sent successfully")
            else:
                logger.error("Failed to send Slack message")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send Slack message: {e}")
            return False
    
    async def send_arbitrage_alert(
        self,
        product_title: str,
        mediamarkt_price: float,
        amazon_price: float,
        profit_amount: float,
        profit_percentage: float,
        mediamarkt_url: str,
        amazon_url: str,
        ean: Optional[str] = None,
        brand: Optional[str] = None,
        category: Optional[str] = None,
        channels: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """
        Send arbitrage opportunity alert.
        
        Args:
            product_title: Product name
            mediamarkt_price: Price on MediaMarkt
            amazon_price: Price on Amazon
            profit_amount: Profit amount in EUR
            profit_percentage: Profit percentage
            mediamarkt_url: MediaMarkt product URL
            amazon_url: Amazon product URL
            ean: Product EAN code
            brand: Product brand
            category: Product category
            channels: List of channels to send to (defaults to configured channels)
            
        Returns:
            Dictionary mapping channel to success status
        """
        
        if not channels:
            channels = self.default_channels
        
        if not channels:
            logger.warning("No Slack channels configured")
            return {}
        
        # Format the alert message
        slack_message = self._format_arbitrage_alert(
            product_title=product_title,
            mediamarkt_price=mediamarkt_price,
            amazon_price=amazon_price,
            profit_amount=profit_amount,
            profit_percentage=profit_percentage,
            mediamarkt_url=mediamarkt_url,
            amazon_url=amazon_url,
            ean=ean,
            brand=brand,
            category=category
        )
        
        # Send to all configured channels
        results = {}
        
        for channel in channels:
            slack_message.channel = channel
            success = await self.send_message(slack_message)
            results[channel] = success
        
        successful_sends = sum(results.values())
        logger.info(f"Sent arbitrage alert to {successful_sends}/{len(channels)} Slack channels")
        
        return results
    
    def _format_arbitrage_alert(
        self,
        product_title: str,
        mediamarkt_price: float,
        amazon_price: float,
        profit_amount: float,
        profit_percentage: float,
        mediamarkt_url: str,
        amazon_url: str,
        ean: Optional[str] = None,
        brand: Optional[str] = None,
        category: Optional[str] = None
    ) -> SlackMessage:
        """Format arbitrage alert message for Slack."""
        
        # Determine color based on profit percentage
        if profit_percentage >= 50:
            color = SlackColor.GOOD.value
        elif profit_percentage >= 30:
            color = SlackColor.WARNING.value
        else:
            color = SlackColor.DEFAULT.value
        
        # Main message text
        profit_emoji = "🚀" if profit_percentage >= 50 else "💰" if profit_percentage >= 30 else "📈"
        main_text = f"{profit_emoji} *ARBITRAGE ALERT* - {profit_percentage:.1f}% profit opportunity!"
        
        # Create attachment with product details
        attachment = SlackAttachment(
            color=color,
            title=product_title[:100] + ("..." if len(product_title) > 100 else ""),
            text=f"Potential profit: €{profit_amount:.2f} ({profit_percentage:.1f}%)"
        )
        
        # Add fields with details
        fields = [
            {
                "title": "MediaMarkt Price",
                "value": f"€{mediamarkt_price:.2f}",
                "short": True
            },
            {
                "title": "Amazon Price",
                "value": f"€{amazon_price:.2f}",
                "short": True
            }
        ]
        
        if brand:
            fields.append({
                "title": "Brand",
                "value": brand,
                "short": True
            })
        
        if category:
            fields.append({
                "title": "Category",
                "value": category,
                "short": True
            })
        
        if ean:
            fields.append({
                "title": "EAN",
                "value": ean,
                "short": True
            })
        
        # Add action buttons/links
        fields.extend([
            {
                "title": "MediaMarkt Link",
                "value": f"<{mediamarkt_url}|View Product>",
                "short": True
            },
            {
                "title": "Amazon Link",
                "value": f"<{amazon_url}|View Product>",
                "short": True
            }
        ])
        
        attachment.fields = fields
        attachment.footer = "ArbitrageBot"
        attachment.ts = int(datetime.now().timestamp())
        
        return SlackMessage(
            text=main_text,
            attachments=[attachment]
        )
    
    async def send_system_notification(
        self,
        title: str,
        message: str,
        severity: str = "info",
        channels: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """
        Send system notification.
        
        Args:
            title: Notification title
            message: Notification message
            severity: Severity level (info, warning, error, success)
            channels: List of channels to send to
            
        Returns:
            Dictionary mapping channel to success status
        """
        
        if not channels:
            channels = self.default_channels
        
        if not channels:
            return {}
        
        # Map severity to color and emoji
        severity_config = {
            "info": {"color": SlackColor.DEFAULT.value, "emoji": ":information_source:"},
            "warning": {"color": SlackColor.WARNING.value, "emoji": ":warning:"},
            "error": {"color": SlackColor.DANGER.value, "emoji": ":x:"},
            "success": {"color": SlackColor.GOOD.value, "emoji": ":white_check_mark:"}
        }
        
        config = severity_config.get(severity, severity_config["info"])
        
        # Create notification message
        main_text = f"{config['emoji']} *{title}*"
        
        attachment = SlackAttachment(
            color=config["color"],
            text=message,
            footer="ArbitrageBot System",
            ts=int(datetime.now().timestamp())
        )
        
        slack_message = SlackMessage(
            text=main_text,
            attachments=[attachment]
        )
        
        # Send to all configured channels
        results = {}
        
        for channel in channels:
            slack_message.channel = channel
            success = await self.send_message(slack_message)
            results[channel] = success
        
        return results
    
    async def send_daily_summary(
        self,
        total_alerts: int,
        profitable_alerts: int,
        total_profit_potential: float,
        top_opportunities: List[Dict[str, Any]],
        channels: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """
        Send daily summary report.
        
        Args:
            total_alerts: Total number of alerts generated
            profitable_alerts: Number of profitable alerts
            total_profit_potential: Total profit potential in EUR
            top_opportunities: List of top arbitrage opportunities
            channels: List of channels to send to
            
        Returns:
            Dictionary mapping channel to success status
        """
        
        if not channels:
            channels = self.default_channels
        
        if not channels:
            return {}
        
        # Create summary message
        main_text = ":bar_chart: *Daily Arbitrage Summary*"
        
        # Summary fields
        fields = [
            {
                "title": "Total Alerts",
                "value": str(total_alerts),
                "short": True
            },
            {
                "title": "Profitable Alerts",
                "value": str(profitable_alerts),
                "short": True
            },
            {
                "title": "Total Profit Potential",
                "value": f"€{total_profit_potential:.2f}",
                "short": True
            },
            {
                "title": "Success Rate",
                "value": f"{(profitable_alerts/total_alerts*100):.1f}%" if total_alerts > 0 else "0%",
                "short": True
            }
        ]
        
        attachment = SlackAttachment(
            color=SlackColor.GOOD.value,
            title="Performance Metrics",
            fields=fields,
            footer=f"Report for {datetime.now().strftime('%Y-%m-%d')}",
            ts=int(datetime.now().timestamp())
        )
        
        # Add top opportunities if available
        if top_opportunities:
            opportunities_text = []
            for i, opportunity in enumerate(top_opportunities[:5], 1):
                title = opportunity.get("title", "Unknown")[:40] + "..."
                profit = opportunity.get("profit_percentage", 0)
                opportunities_text.append(f"{i}. {title} (+{profit:.1f}%)")
            
            opportunities_attachment = SlackAttachment(
                color=SlackColor.WARNING.value,
                title="🏆 Top Opportunities",
                text="\n".join(opportunities_text)
            )
            
            attachments = [attachment, opportunities_attachment]
        else:
            attachments = [attachment]
        
        slack_message = SlackMessage(
            text=main_text,
            attachments=attachments
        )
        
        # Send to all configured channels
        results = {}
        
        for channel in channels:
            slack_message.channel = channel
            success = await self.send_message(slack_message)
            results[channel] = success
        
        return results
    
    async def test_connection(self, channel: Optional[str] = None) -> bool:
        """
        Test Slack webhook connection.
        
        Args:
            channel: Specific channel to test (uses first default if not provided)
            
        Returns:
            True if connection test successful
        """
        
        try:
            test_message = SlackMessage(
                text=":robot_face: *Test Message*",
                channel=channel or (self.default_channels[0] if self.default_channels else None),
                attachments=[
                    SlackAttachment(
                        color=SlackColor.GOOD.value,
                        title="Connection Test",
                        text="Slack webhook connection is working correctly!",
                        footer="ArbitrageBot",
                        ts=int(datetime.now().timestamp())
                    )
                ]
            )
            
            return await self.send_message(test_message)
            
        except Exception as e:
            logger.error(f"Slack connection test failed: {e}")
            return False


# Convenience functions
async def send_arbitrage_alert_slack(
    product_title: str,
    mediamarkt_price: float,
    amazon_price: float,
    profit_amount: float,
    profit_percentage: float,
    mediamarkt_url: str,
    amazon_url: str,
    **kwargs
) -> bool:
    """
    Quick function to send arbitrage alert via Slack.
    
    Args:
        product_title: Product name
        mediamarkt_price: Price on MediaMarkt
        amazon_price: Price on Amazon
        profit_amount: Profit amount
        profit_percentage: Profit percentage
        mediamarkt_url: MediaMarkt URL
        amazon_url: Amazon URL
        **kwargs: Additional parameters
        
    Returns:
        True if alert was sent successfully to at least one channel
    """
    async with SlackNotifier() as notifier:
        results = await notifier.send_arbitrage_alert(
            product_title=product_title,
            mediamarkt_price=mediamarkt_price,
            amazon_price=amazon_price,
            profit_amount=profit_amount,
            profit_percentage=profit_percentage,
            mediamarkt_url=mediamarkt_url,
            amazon_url=amazon_url,
            **kwargs
        )
        
        return any(results.values())


async def test_slack_connection() -> bool:
    """
    Quick function to test Slack webhook connection.
    
    Returns:
        True if connection test successful
    """
    async with SlackNotifier() as notifier:
        return await notifier.test_connection() 