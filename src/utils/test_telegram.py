"""
Test script for enhanced Telegram notifications.
"""

import asyncio
import sys
import os

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.services.notifier.telegram_notifier import TelegramNotifier

async def test_enhanced_telegram():
    """Test enhanced Telegram notification features."""
    
    try:
        async with TelegramNotifier() as notifier:
            # Test basic connection
            connection_ok = await notifier.test_connection()
            if not connection_ok:
                print("❌ Telegram connection failed")
                return False
            
            print("✅ Telegram connection successful")
            
            # Test enhanced notification with chart
            test_result = await notifier.send_arbitrage_alert(
                product_title="Test Product - Enhanced Notification",
                mediamarkt_price=199.99,
                amazon_price=149.99,
                profit_amount=50.00,
                profit_percentage=25.0,
                mediamarkt_url="https://mediamarkt.pt/test",
                amazon_url="https://amazon.es/test",
                product_id="TEST123",
                brand="Test Brand",
                category="Electronics"
            )
            
            if any(test_result.values()):
                print("✅ Enhanced notification sent successfully")
                print("Features tested:")
                print("- Price comparison chart")
                print("- Interactive buttons")
                print("- Rich formatting")
                return True
            else:
                print("❌ Failed to send enhanced notification")
                return False
                
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_enhanced_telegram()) 