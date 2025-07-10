"""
Telegram callback query handler for interactive buttons.
"""

import logging
from typing import Dict, Any, Optional
import json
from datetime import datetime

import structlog
from motor.motor_asyncio import AsyncIOMotorClient

from ...config.settings import get_settings
from ...config.database import get_database
from .telegram_notifier import TelegramNotifier

logger = structlog.get_logger(__name__)

class TelegramCallbackHandler:
    """Handler for Telegram callback queries from interactive buttons."""
    
    def __init__(self):
        self.settings = get_settings()
        self.notifier = TelegramNotifier()
    
    async def handle_callback_query(
        self,
        callback_query_id: str,
        data: str,
        chat_id: str,
        user_id: int,
        message_id: int
    ) -> bool:
        """
        Handle callback query from Telegram buttons.
        
        Args:
            callback_query_id: Unique identifier for the callback query
            data: Callback data from button (e.g., "track_123" or "ignore_123")
            chat_id: Chat where the button was pressed
            user_id: User who pressed the button
            message_id: Message ID containing the button
            
        Returns:
            True if handled successfully
        """
        try:
            # Parse callback data
            action, product_id = data.split('_', 1)
            
            if action == "track":
                return await self._handle_track_action(
                    callback_query_id,
                    product_id,
                    chat_id,
                    user_id,
                    message_id
                )
            elif action == "ignore":
                return await self._handle_ignore_action(
                    callback_query_id,
                    product_id,
                    chat_id,
                    user_id,
                    message_id
                )
            else:
                logger.warning(f"Unknown callback action: {action}")
                await self._answer_callback_query(
                    callback_query_id,
                    "Invalid action. Please try again."
                )
                return False
                
        except Exception as e:
            logger.error(f"Error handling callback query: {e}")
            await self._answer_callback_query(
                callback_query_id,
                "An error occurred. Please try again."
            )
            return False
    
    async def _handle_track_action(
        self,
        callback_query_id: str,
        product_id: str,
        chat_id: str,
        user_id: int,
        message_id: int
    ) -> bool:
        """Handle price tracking activation."""
        try:
            # Get database connection
            db = await get_database()
            
            # Add user to product tracking list
            await db.product_tracking.update_one(
                {"product_id": product_id},
                {
                    "$addToSet": {
                        "tracking_users": {
                            "user_id": user_id,
                            "chat_id": chat_id,
                            "added_at": datetime.utcnow()
                        }
                    }
                },
                upsert=True
            )
            
            # Update message to reflect tracking status
            await self.notifier._make_request(
                "editMessageReplyMarkup",
                {
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "reply_markup": json.dumps({
                        "inline_keyboard": [
                            [
                                {"text": "🏪 View on MediaMarkt", "url": self.settings.mediamarkt_url},
                                {"text": "🛒 View on Amazon", "url": self.settings.amazon_url}
                            ],
                            [
                                {"text": "✅ Tracking Active", "callback_data": f"untrack_{product_id}"},
                                {"text": "🔕 Ignore", "callback_data": f"ignore_{product_id}"}
                            ]
                        ]
                    })
                }
            )
            
            # Confirm to user
            await self._answer_callback_query(
                callback_query_id,
                "Price tracking activated! You'll be notified of changes."
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling track action: {e}")
            await self._answer_callback_query(
                callback_query_id,
                "Failed to activate tracking. Please try again."
            )
            return False
    
    async def _handle_ignore_action(
        self,
        callback_query_id: str,
        product_id: str,
        chat_id: str,
        user_id: int,
        message_id: int
    ) -> bool:
        """Handle product ignore request."""
        try:
            # Get database connection
            db = await get_database()
            
            # Add product to user's ignore list
            await db.user_preferences.update_one(
                {"user_id": user_id},
                {
                    "$addToSet": {
                        "ignored_products": {
                            "product_id": product_id,
                            "ignored_at": datetime.utcnow()
                        }
                    }
                },
                upsert=True
            )
            
            # Update message to show ignored status
            await self.notifier._make_request(
                "editMessageReplyMarkup",
                {
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "reply_markup": json.dumps({
                        "inline_keyboard": [
                            [
                                {"text": "🏪 View on MediaMarkt", "url": self.settings.mediamarkt_url},
                                {"text": "🛒 View on Amazon", "url": self.settings.amazon_url}
                            ],
                            [
                                {"text": "📊 Track Price", "callback_data": f"track_{product_id}"},
                                {"text": "✅ Ignored", "callback_data": f"unignore_{product_id}"}
                            ]
                        ]
                    })
                }
            )
            
            # Confirm to user
            await self._answer_callback_query(
                callback_query_id,
                "Product ignored. You won't receive alerts for this item."
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling ignore action: {e}")
            await self._answer_callback_query(
                callback_query_id,
                "Failed to ignore product. Please try again."
            )
            return False
    
    async def _answer_callback_query(
        self,
        callback_query_id: str,
        text: str,
        show_alert: bool = False
    ) -> bool:
        """Answer callback query with response message."""
        try:
            await self.notifier._make_request(
                "answerCallbackQuery",
                {
                    "callback_query_id": callback_query_id,
                    "text": text,
                    "show_alert": show_alert
                }
            )
            return True
        except Exception as e:
            logger.error(f"Error answering callback query: {e}")
            return False 