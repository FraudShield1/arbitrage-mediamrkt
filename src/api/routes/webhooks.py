"""
Webhook endpoints for external service callbacks.
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Header
import structlog
from pydantic import BaseModel

from ...config.settings import get_settings
from ...services.notifier.telegram_callback_handler import TelegramCallbackHandler

logger = structlog.get_logger(__name__)
router = APIRouter()

class TelegramUpdate(BaseModel):
    """Telegram update model."""
    
    update_id: int
    callback_query: Dict[str, Any] = None
    message: Dict[str, Any] = None

@router.post("/telegram/webhook")
async def telegram_webhook(
    update: TelegramUpdate,
    x_telegram_bot_api_secret_token: str = Header(None)
):
    """
    Handle Telegram webhook updates.
    
    This endpoint receives updates from Telegram when users interact
    with bot messages (pressing buttons, etc).
    """
    settings = get_settings()
    
    # Verify webhook secret token
    if not x_telegram_bot_api_secret_token or x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
        logger.warning("Invalid webhook secret token received")
        raise HTTPException(status_code=403, detail="Invalid webhook secret token")
    
    try:
        # Log incoming update
        logger.info(
            "Received Telegram webhook update",
            update_id=update.update_id,
            has_callback_query=bool(update.callback_query),
            has_message=bool(update.message)
        )
        
        # Handle callback queries (button clicks)
        if update.callback_query:
            handler = TelegramCallbackHandler()
            
            success = await handler.handle_callback_query(
                callback_query_id=update.callback_query["id"],
                data=update.callback_query["data"],
                chat_id=str(update.callback_query["message"]["chat"]["id"]),
                user_id=update.callback_query["from"]["id"],
                message_id=update.callback_query["message"]["message_id"]
            )
            
            if not success:
                logger.error(
                    "Failed to handle Telegram callback query",
                    update_id=update.update_id,
                    callback_query_id=update.callback_query["id"]
                )
                return {"status": "error", "message": "Failed to process callback query"}
            
            logger.info(
                "Successfully handled Telegram callback query",
                update_id=update.update_id,
                callback_query_id=update.callback_query["id"]
            )
        
        # Handle regular messages if needed
        elif update.message:
            # Log message receipt
            logger.info(
                "Received Telegram message",
                update_id=update.update_id,
                chat_id=update.message["chat"]["id"],
                message_id=update.message["message_id"]
            )
            # For now, we just acknowledge regular messages
            # You can add message handling logic here if needed
        
        return {"status": "success"}
        
    except KeyError as e:
        logger.error(
            "Malformed Telegram update data",
            error=str(e),
            update_id=update.update_id
        )
        raise HTTPException(
            status_code=400,
            detail=f"Malformed update data: missing {str(e)}"
        )
    except Exception as e:
        logger.error(
            "Error processing Telegram webhook",
            error=str(e),
            update_id=update.update_id
        )
        raise HTTPException(status_code=500, detail="Internal server error") 