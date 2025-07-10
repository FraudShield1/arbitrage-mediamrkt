"""
Telegram notification service for sending arbitrage alerts.

This module provides integration with Telegram Bot API for sending
formatted notifications about profitable arbitrage opportunities.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import json
from io import BytesIO

import aiohttp
from pydantic import BaseModel
import matplotlib.pyplot as plt
import seaborn as sns

from ...config.settings import get_settings


logger = logging.getLogger(__name__)


class MessageFormat(Enum):
    """Message formatting options."""
    
    TEXT = "text"
    MARKDOWN = "MarkdownV2"
    HTML = "HTML"


class TelegramMessage(BaseModel):
    """Telegram message model."""
    
    chat_id: str
    text: str
    parse_mode: MessageFormat = MessageFormat.HTML
    disable_web_page_preview: bool = False
    disable_notification: bool = False
    reply_markup: Optional[Dict[str, Any]] = None


class TelegramNotifierError(Exception):
    """Custom exception for Telegram notification errors."""
    pass


class TelegramNotifier:
    """
    Enhanced Telegram bot notification service.
    
    Sends formatted alerts about arbitrage opportunities to configured
    Telegram chats using the Bot API with interactive components.
    """
    
    def __init__(self, bot_token: Optional[str] = None):
        self.settings = get_settings()
        self.bot_token = bot_token or self.settings.TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        # Default chat IDs from settings
        self.default_chat_ids = [self.settings.TELEGRAM_CHAT_ID] if self.settings.TELEGRAM_CHAT_ID else []
        
        self.session: Optional[aiohttp.ClientSession] = None
        
        if not self.bot_token:
            raise ValueError("Telegram bot token is required")

    async def __aenter__(self):
        """Async context manager entry."""
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(
            ssl=ssl_context,
            limit=10  # Connection pooling
        )
        self.session = aiohttp.ClientSession(
            connector=connector,
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

    async def _make_request(
        self,
        method: str,
        data: Dict[str, Any],
        files: Optional[Dict[str, Any]] = None,
        retries: int = 3
    ) -> Dict[str, Any]:
        """Make request to Telegram Bot API with enhanced error handling."""
        
        if not self.session:
            raise RuntimeError("Notifier not initialized. Use async context manager.")
        
        url = f"{self.base_url}/{method}"
        
        for attempt in range(retries + 1):
            try:
                if files:
                    # Multipart form data for file uploads
                    form_data = aiohttp.FormData()
                    for key, value in data.items():
                        form_data.add_field(key, str(value))
                    for file_key, file_data in files.items():
                        form_data.add_field(file_key, file_data)
                    
                    async with self.session.post(url, data=form_data) as response:
                        response_data = await response.json()
                else:
                    async with self.session.post(url, json=data) as response:
                        response_data = await response.json()
                
                if response.status == 200 and response_data.get("ok"):
                    return response_data
                else:
                    error_msg = response_data.get("description", "Unknown error")
                    error_code = response_data.get("error_code", response.status)
                    
                    if error_code == 429:  # Rate limited
                        retry_after = response_data.get("parameters", {}).get("retry_after", 1)
                        logger.warning(f"Telegram rate limited, waiting {retry_after} seconds")
                        await asyncio.sleep(retry_after)
                        continue
                    elif error_code in [400, 403]:  # Bad request or forbidden
                        raise ValueError(f"Telegram API error: {error_msg}")
                    else:
                        raise ValueError(f"Telegram API error {error_code}: {error_msg}")
                        
            except aiohttp.ClientError as e:
                if attempt == retries:
                    raise ConnectionError(f"Network error: {str(e)}")
                
                wait_time = 2 ** attempt
                logger.warning(f"Network error, retrying in {wait_time} seconds: {e}")
                await asyncio.sleep(wait_time)
        
        raise RuntimeError("Max retries exceeded")

    async def send_photo(
        self,
        chat_id: str,
        photo: Union[str, BytesIO],
        caption: Optional[str] = None,
        parse_mode: Optional[MessageFormat] = None,
        reply_markup: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send a photo message."""
        try:
            data = {
                "chat_id": chat_id,
                "parse_mode": parse_mode.value if parse_mode else MessageFormat.HTML.value
            }
            
            if caption:
                data["caption"] = caption
                
            if reply_markup:
                data["reply_markup"] = json.dumps(reply_markup)

            files = None
            if isinstance(photo, str) and (photo.startswith('http://') or photo.startswith('https://')):
                data["photo"] = photo
            else:
                files = {"photo": photo}

            result = await self._make_request("sendPhoto", data, files)
            return True
        except Exception as e:
            logger.error(f"Failed to send photo: {e}")
            return False

    async def send_message(
        self,
        message: TelegramMessage,
        thread_id: Optional[str] = None
    ) -> bool:
        """Send a message with optional threading and interactive components."""
        try:
            data = {
                "chat_id": message.chat_id,
                "text": message.text,
                "parse_mode": message.parse_mode.value,
                "disable_web_page_preview": message.disable_web_page_preview,
                "disable_notification": message.disable_notification
            }
            
            if thread_id:
                data["message_thread_id"] = thread_id
                
            if message.reply_markup:
                data["reply_markup"] = json.dumps(message.reply_markup)
            
            result = await self._make_request("sendMessage", data)
            
            message_id = result.get("result", {}).get("message_id")
            logger.info(f"Telegram message sent successfully (ID: {message_id})")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    def _create_price_chart(
        self,
        product_title: str,
        price_data: Dict[str, float],
        profit_margin: float
    ) -> BytesIO:
        """Create a price comparison chart."""
        plt.figure(figsize=(10, 6))
        sns.set_style("whitegrid")
        
        # Create bar chart
        prices = list(price_data.values())
        platforms = list(price_data.keys())
        
        bars = plt.bar(platforms, prices)
        
        # Customize chart
        plt.title(f"Price Comparison - {product_title[:30]}...", pad=20)
        plt.ylabel("Price (€)")
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'€{height:.2f}',
                    ha='center', va='bottom')
        
        # Add profit margin annotation
        plt.text(0.98, 0.98, f"Profit Margin: {profit_margin:.1f}%",
                transform=plt.gca().transAxes,
                ha='right', va='top',
                bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))
        
        # Save to BytesIO
        buf = BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return buf

    async def send_arbitrage_alert(
        self,
        product_title: str,
        mediamarkt_price: float,
        amazon_price: float,
        profit_amount: float,
        profit_percentage: float,
        mediamarkt_url: str,
        amazon_url: str,
        product_id: str,
        ean: Optional[str] = None,
        brand: Optional[str] = None,
        category: Optional[str] = None,
        chat_ids: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """Send enhanced arbitrage opportunity alert with interactive components."""
        
        if not chat_ids:
            chat_ids = self.default_chat_ids
        
        if not chat_ids:
            logger.warning("No Telegram chat IDs configured")
            return {}
        
        # Create price comparison chart
        price_data = {
            "MediaMarkt": mediamarkt_price,
            "Amazon": amazon_price
        }
        chart = self._create_price_chart(product_title, price_data, profit_percentage)
        
        # Create inline keyboard
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "🏪 View on MediaMarkt", "url": mediamarkt_url},
                    {"text": "🛒 View on Amazon", "url": amazon_url}
                ],
                [
                    {"text": "📊 Track Price", "callback_data": f"track_{product_id}"},
                    {"text": "🔕 Ignore", "callback_data": f"ignore_{product_id}"}
                ]
            ]
        }
        
        # Format the alert message
        message_text = self._format_arbitrage_alert(
            product_title=product_title,
            mediamarkt_price=mediamarkt_price,
            amazon_price=amazon_price,
            profit_amount=profit_amount,
            profit_percentage=profit_percentage,
            ean=ean,
            brand=brand,
            category=category
        )
        
        # Send to all configured chats
        results = {}
        
        for chat_id in chat_ids:
            try:
                # First send the price comparison chart
                photo_success = await self.send_photo(
                    chat_id=chat_id,
                    photo=chart,
                    caption="Price Comparison Chart",
                    parse_mode=MessageFormat.HTML
                )
                
                # Then send the detailed message with buttons
                message = TelegramMessage(
                    chat_id=chat_id,
                    text=message_text,
                    parse_mode=MessageFormat.HTML,
                    reply_markup=keyboard
                )
                
                message_success = await self.send_message(message)
                results[chat_id] = photo_success and message_success
                
            except Exception as e:
                logger.error(f"Failed to send arbitrage alert to {chat_id}: {e}")
                results[chat_id] = False
        
        successful_sends = sum(results.values())
        logger.info(f"Sent enhanced arbitrage alert to {successful_sends}/{len(chat_ids)} Telegram chats")
        
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
    ) -> str:
        """Format arbitrage alert message for Telegram."""
        
        # Escape HTML special characters
        def escape_html(text: str) -> str:
            if not text:
                return ""
            return (text.replace("&", "&amp;")
                       .replace("<", "&lt;")
                       .replace(">", "&gt;")
                       .replace('"', "&quot;")
                       .replace("'", "&#x27;"))
        
        title = escape_html(product_title)[:50] + ("..." if len(product_title) > 50 else "")
        
        # Profit indicator emoji
        profit_emoji = "🚀" if profit_percentage >= 50 else "💰" if profit_percentage >= 30 else "📈"
        
        # Build message
        message_parts = [
            f"{profit_emoji} <b>ARBITRAGE ALERT</b> {profit_emoji}",
            "",
            f"📦 <b>Product:</b> {title}",
        ]
        
        if brand:
            message_parts.append(f"🏷️ <b>Brand:</b> {escape_html(brand)}")
        
        if category:
            message_parts.append(f"📂 <b>Category:</b> {escape_html(category)}")
        
        if ean:
            message_parts.append(f"🔢 <b>EAN:</b> <code>{ean}</code>")
        
        message_parts.extend([
            "",
            f"💵 <b>MediaMarkt Price:</b> €{mediamarkt_price:.2f}",
            f"💳 <b>Amazon Price:</b> €{amazon_price:.2f}",
            f"💰 <b>Profit:</b> €{profit_amount:.2f} ({profit_percentage:.1f}%)",
            "",
            f"🔗 <a href='{mediamarkt_url}'>View on MediaMarkt</a>",
            f"🛒 <a href='{amazon_url}'>View on Amazon</a>",
            "",
            f"⏰ <i>Alert sent at {datetime.now().strftime('%H:%M:%S')}</i>"
        ])
        
        return "\n".join(message_parts)
    
    async def send_system_notification(
        self,
        title: str,
        message: str,
        severity: str = "info",
        chat_ids: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """
        Send system notification.
        
        Args:
            title: Notification title
            message: Notification message
            severity: Severity level (info, warning, error)
            chat_ids: List of chat IDs to send to
            
        Returns:
            Dictionary mapping chat_id to success status
        """
        
        if not chat_ids:
            chat_ids = self.default_chat_ids
        
        if not chat_ids:
            return {}
        
        # Format system notification
        severity_emojis = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "🚨",
            "success": "✅"
        }
        
        emoji = severity_emojis.get(severity, "ℹ️")
        
        def escape_html(text: str) -> str:
            if not text:
                return ""
            return (text.replace("&", "&amp;")
                       .replace("<", "&lt;")
                       .replace(">", "&gt;"))
        
        message_text = f"{emoji} <b>{escape_html(title)}</b>\n\n{escape_html(message)}\n\n<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"
        
        # Send to all configured chats
        results = {}
        
        for chat_id in chat_ids:
            telegram_message = TelegramMessage(
                chat_id=chat_id,
                text=message_text,
                parse_mode=MessageFormat.HTML
            )
            
            success = await self.send_message(telegram_message)
            results[chat_id] = success
        
        return results
    
    async def send_daily_summary(
        self,
        total_alerts: int,
        profitable_alerts: int,
        total_profit_potential: float,
        top_opportunities: List[Dict[str, Any]],
        chat_ids: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """
        Send daily summary report.
        
        Args:
            total_alerts: Total number of alerts generated
            profitable_alerts: Number of profitable alerts
            total_profit_potential: Total profit potential in EUR
            top_opportunities: List of top arbitrage opportunities
            chat_ids: List of chat IDs to send to
            
        Returns:
            Dictionary mapping chat_id to success status
        """
        
        if not chat_ids:
            chat_ids = self.default_chat_ids
        
        if not chat_ids:
            return {}
        
        # Format daily summary
        message_parts = [
            "📊 <b>DAILY ARBITRAGE SUMMARY</b>",
            "",
            f"🎯 <b>Total Alerts:</b> {total_alerts}",
            f"💰 <b>Profitable Alerts:</b> {profitable_alerts}",
            f"🚀 <b>Total Profit Potential:</b> €{total_profit_potential:.2f}",
            ""
        ]
        
        if top_opportunities:
            message_parts.append("🏆 <b>Top Opportunities:</b>")
            for i, opportunity in enumerate(top_opportunities[:5], 1):
                title = opportunity.get("title", "Unknown")[:30] + "..."
                profit = opportunity.get("profit_percentage", 0)
                message_parts.append(f"{i}. {title} (+{profit:.1f}%)")
            message_parts.append("")
        
        message_parts.append(f"📅 <i>Report for {datetime.now().strftime('%Y-%m-%d')}</i>")
        
        message_text = "\n".join(message_parts)
        
        # Send to all configured chats
        results = {}
        
        for chat_id in chat_ids:
            telegram_message = TelegramMessage(
                chat_id=chat_id,
                text=message_text,
                parse_mode=MessageFormat.HTML
            )
            
            success = await self.send_message(telegram_message)
            results[chat_id] = success
        
        return results
    
    async def test_connection(self, chat_id: Optional[str] = None) -> bool:
        """
        Test Telegram bot connection.
        
        Args:
            chat_id: Specific chat ID to test (uses first default if not provided)
            
        Returns:
            True if connection test successful
        """
        
        try:
            # First test bot info
            bot_info = await self._make_request("getMe", {})
            bot_username = bot_info.get("result", {}).get("username", "Unknown")
            
            logger.info(f"Telegram bot connection successful: @{bot_username}")
            
            # Test sending a message if chat_id provided
            if chat_id or self.default_chat_ids:
                test_chat_id = chat_id or self.default_chat_ids[0]
                
                test_message = TelegramMessage(
                    chat_id=test_chat_id,
                    text="🤖 <b>Test Message</b>\n\nTelegram bot connection is working correctly!",
                    parse_mode=MessageFormat.HTML
                )
                
                return await self.send_message(test_message)
            
            return True
            
        except Exception as e:
            logger.error(f"Telegram connection test failed: {e}")
            return False


# Convenience functions
async def send_arbitrage_alert_telegram(
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
    Quick function to send arbitrage alert via Telegram.
    
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
        True if alert was sent successfully to at least one chat
    """
    async with TelegramNotifier() as notifier:
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


async def test_telegram_connection() -> bool:
    """
    Quick function to test Telegram bot connection.
    
    Returns:
        True if connection test successful
    """
    async with TelegramNotifier() as notifier:
        return await notifier.test_connection() 