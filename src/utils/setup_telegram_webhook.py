"""
Script to set up Telegram webhook for the arbitrage bot.
"""

import asyncio
import os
import sys
from typing import Optional

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.config.settings import get_settings
from src.services.notifier.telegram_notifier import TelegramNotifier

async def setup_webhook(webhook_url: Optional[str] = None) -> bool:
    """
    Set up Telegram webhook.
    
    Args:
        webhook_url: Optional custom webhook URL. If not provided, uses settings.
        
    Returns:
        True if webhook was set up successfully.
    """
    settings = get_settings()
    
    # Use provided URL or construct from settings
    final_webhook_url = webhook_url or settings.TELEGRAM_WEBHOOK_URL
    if not final_webhook_url:
        print("❌ No webhook URL provided and TELEGRAM_WEBHOOK_URL not set in settings")
        return False
        
    try:
        async with TelegramNotifier() as notifier:
            # First test the bot connection
            connection_ok = await notifier.test_connection()
            if not connection_ok:
                print("❌ Failed to connect to Telegram bot")
                return False
                
            print("✅ Telegram bot connection successful")
            
            # Set webhook
            result = await notifier._make_request(
                "setWebhook",
                {
                    "url": final_webhook_url,
                    "secret_token": settings.TELEGRAM_WEBHOOK_SECRET,
                    "allowed_updates": ["callback_query", "message"],
                    "drop_pending_updates": True
                }
            )
            
            if result.get("ok"):
                print(f"✅ Webhook set successfully to: {final_webhook_url}")
                
                # Get webhook info
                info = await notifier._make_request("getWebhookInfo", {})
                if info.get("ok"):
                    webhook_info = info["result"]
                    print("\nWebhook Info:")
                    print(f"URL: {webhook_info.get('url')}")
                    print(f"Pending updates: {webhook_info.get('pending_update_count', 0)}")
                    print(f"Last error: {webhook_info.get('last_error_message', 'None')}")
                    print(f"Max connections: {webhook_info.get('max_connections', 40)}")
                    
                return True
            else:
                print(f"❌ Failed to set webhook: {result.get('description')}")
                return False
                
    except Exception as e:
        print(f"❌ Error setting up webhook: {e}")
        return False

if __name__ == "__main__":
    # Get webhook URL from command line or use settings
    webhook_url = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(setup_webhook(webhook_url)) 