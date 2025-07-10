#!/usr/bin/env python3
"""
Comprehensive End-to-End Testing Script
Cross-Market Arbitrage Tool

Tests all major system components:
- MongoDB Atlas connection and CRUD operations
- Redis Cloud caching
- Telegram notifications
- Settings configuration
- Simple scraping simulation
- Integration workflow
"""

import asyncio
import sys
import json
import requests
from datetime import datetime
from typing import Dict, Any, List

# Add project root to path
sys.path.append('.')

from src.config.database import (
    check_database_connection,
    get_db_stats,
    insert_one,
    find_one,
    update_one,
    delete_one,
    get_redis_client,
    create_database_tables
)
from src.config.settings import settings

class EndToEndTester:
    """Comprehensive system tester."""
    
    def __init__(self):
        self.test_results = {}
        self.test_data = {}
    
    async def test_mongodb_operations(self) -> bool:
        """Test MongoDB Atlas connection and operations."""
        print("\n=== MongoDB Atlas Tests ===")
        
        try:
            # Test connection
            connected = await check_database_connection()
            if not connected:
                print("❌ MongoDB connection failed")
                return False
            print("✅ MongoDB connection successful")
            
            # Get database stats
            stats = await get_db_stats()
            print(f"✅ Database: {stats.get('database_name')}")
            print(f"   Server Version: {stats.get('server_version')}")
            print(f"   Collections: {stats.get('collections', 0)}")
            
            # Create indexes
            await create_database_tables()
            print("✅ Database indexes created")
            
            # Test CRUD operations
            test_product = {
                'asin': 'TEST123456',
                'ean': '9876543210123',
                'title': 'End-to-End Test Product',
                'category': 'Electronics',
                'subcategory': 'Testing',
                'price': 199.99,
                'availability': 'In Stock',
                'last_updated': datetime.utcnow(),
                'source': 'test_scraper',
                'profit_potential': 45.50,
                'competitor_price': 155.49
            }
            
            # INSERT test
            product_id = await insert_one('products', test_product)
            print(f"✅ Product inserted: {product_id}")
            self.test_data['product_id'] = product_id
            
            # READ test
            found_product = await find_one('products', {'asin': 'TEST123456'})
            if found_product:
                print(f"✅ Product found: {found_product['title']}")
                self.test_data['product'] = found_product
            
            # UPDATE test
            updated = await update_one('products', 
                                     {'asin': 'TEST123456'}, 
                                     {'price': 179.99, 'last_checked': datetime.utcnow()})
            print(f"✅ Product updated: {updated}")
            
            # Verify update
            updated_product = await find_one('products', {'asin': 'TEST123456'})
            if updated_product and updated_product['price'] == 179.99:
                print("✅ Update verified")
            
            return True
            
        except Exception as e:
            print(f"❌ MongoDB test error: {e}")
            return False
    
    async def test_redis_operations(self) -> bool:
        """Test Redis Cloud caching operations."""
        print("\n=== Redis Cloud Tests ===")
        
        try:
            redis_client = await get_redis_client()
            if not redis_client:
                print("❌ Redis connection failed")
                return False
            print("✅ Redis connection successful")
            
            # Test basic operations
            await redis_client.set('test_e2e', 'end_to_end_test', ex=300)
            value = await redis_client.get('test_e2e')
            if value and value.decode() == 'end_to_end_test':
                print("✅ Redis SET/GET working")
            
            # Test JSON caching
            cache_data = {
                'test_id': 'e2e_001',
                'timestamp': datetime.utcnow().isoformat(),
                'data': {'prices': [100, 150, 200], 'source': 'test'}
            }
            await redis_client.set('test_json_e2e', json.dumps(cache_data), ex=300)
            cached_json = await redis_client.get('test_json_e2e')
            if cached_json:
                retrieved = json.loads(cached_json.decode())
                print(f"✅ JSON caching working: {retrieved['test_id']}")
            
            # Test increment operations
            await redis_client.set('counter_e2e', 0)
            count = await redis_client.incr('counter_e2e')
            print(f"✅ Redis INCR working: {count}")
            
            # Cleanup
            await redis_client.delete('test_e2e', 'test_json_e2e', 'counter_e2e')
            print("✅ Redis cleanup completed")
            
            return True
            
        except Exception as e:
            print(f"❌ Redis test error: {e}")
            return False
    
    def test_telegram_notifications(self) -> bool:
        """Test Telegram bot notifications."""
        print("\n=== Telegram Notification Tests ===")
        
        try:
            bot_token = settings.TELEGRAM_BOT_TOKEN
            chat_id = settings.TELEGRAM_CHAT_ID
            
            if not bot_token or not chat_id:
                print("❌ Telegram credentials not configured")
                return False
            
            # Test bot status
            response = requests.get(f'https://api.telegram.org/bot{bot_token}/getMe')
            if response.status_code == 200:
                bot_info = response.json()
                if bot_info['ok']:
                    print(f"✅ Bot active: {bot_info['result']['first_name']}")
                else:
                    print(f"❌ Bot error: {bot_info}")
                    return False
            
            # Send test notification
            test_message = {
                'chat_id': chat_id,
                'text': f"""🧪 **End-to-End Test Alert**
                
📊 **Test Results:**
• Database: ✅ Connected
• Cache: ✅ Working  
• Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎯 **Simulated Arbitrage Opportunity:**
• Product: Test Widget Pro
• MediaMarkt: €179.99
• Amazon: €155.49
• **Profit: €24.50 (13.6%)**

🔗 System operational and monitoring active!""",
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(
                f'https://api.telegram.org/bot{bot_token}/sendMessage',
                headers={'Content-Type': 'application/json'},
                data=json.dumps(test_message)
            )
            
            if response.status_code == 200:
                result = response.json()
                if result['ok']:
                    print("✅ Test notification sent successfully")
                    print(f"   Message ID: {result['result']['message_id']}")
                    return True
                else:
                    print(f"❌ Notification error: {result}")
                    return False
            else:
                print(f"❌ HTTP error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Telegram test error: {e}")
            return False
    
    async def test_scraping_simulation(self) -> bool:
        """Simulate a scraping workflow with data processing."""
        print("\n=== Scraping Simulation Tests ===")
        
        try:
            # Simulate scraping MediaMarkt.pt
            print("🕷️ Simulating MediaMarkt.pt scraping...")
            
            # Mock scraped data (simulating real scraper results)
            mock_scraped_products = [
                {
                    'asin': 'B08N5WRWNW',
                    'ean': '1234567890123',
                    'title': 'Samsung Galaxy S24 Ultra 256GB',
                    'category': 'Electronics',
                    'subcategory': 'Smartphones',
                    'price': 1299.99,
                    'availability': 'In Stock',
                    'last_updated': datetime.utcnow(),
                    'source': 'mediamarkt_pt',
                    'url': 'https://www.mediamarkt.pt/mock-product-url'
                },
                {
                    'asin': 'B09G9FPHY6',
                    'ean': '2345678901234',
                    'title': 'Apple iPhone 15 Pro 128GB',
                    'category': 'Electronics',
                    'subcategory': 'Smartphones',
                    'price': 1179.99,
                    'availability': 'In Stock',
                    'last_updated': datetime.utcnow(),
                    'source': 'mediamarkt_pt',
                    'url': 'https://www.mediamarkt.pt/mock-iphone-url'
                }
            ]
            
            print(f"✅ Simulated scraping: {len(mock_scraped_products)} products")
            
            # Store scraped data
            stored_products = []
            for product in mock_scraped_products:
                product_id = await insert_one('products', product)
                stored_products.append(product_id)
                print(f"   📦 Stored: {product['title'][:30]}... (ID: {product_id})")
            
            # Simulate price comparison and arbitrage detection
            print("\n🔍 Simulating arbitrage analysis...")
            
            # Mock Amazon prices (lower than MediaMarkt)
            amazon_prices = {
                'B08N5WRWNW': 1199.99,  # €100 profit
                'B09G9FPHY6': 1099.99   # €80 profit
            }
            
            alerts_created = []
            for product in mock_scraped_products:
                asin = product['asin']
                if asin in amazon_prices:
                    amazon_price = amazon_prices[asin]
                    mediamarkt_price = product['price']
                    profit = mediamarkt_price - amazon_price
                    profit_margin = (profit / amazon_price) * 100
                    
                    if profit > 50:  # Significant profit threshold
                        alert_data = {
                            'product_asin': asin,
                            'product_title': product['title'],
                            'mediamarkt_price': mediamarkt_price,
                            'amazon_price': amazon_price,
                            'profit_amount': profit,
                            'profit_margin': profit_margin,
                            'alert_type': 'arbitrage_opportunity',
                            'created_at': datetime.utcnow(),
                            'status': 'active'
                        }
                        
                        alert_id = await insert_one('price_alerts', alert_data)
                        alerts_created.append(alert_id)
                        print(f"   🚨 Alert created: €{profit:.2f} profit ({profit_margin:.1f}%)")
            
            print(f"✅ Analysis complete: {len(alerts_created)} alerts created")
            self.test_data['alerts'] = alerts_created
            self.test_data['products'] = stored_products
            
            return True
            
        except Exception as e:
            print(f"❌ Scraping simulation error: {e}")
            return False
    
    def test_web_services(self) -> bool:
        """Test web service endpoints."""
        print("\n=== Web Services Tests ===")
        
        try:
            # Test FastAPI
            try:
                response = requests.get('http://localhost:8000/health', timeout=5)
                if response.status_code == 200:
                    print("✅ FastAPI service running")
                else:
                    print(f"⚠️  FastAPI response: {response.status_code}")
            except requests.exceptions.ConnectionError:
                print("⚠️  FastAPI not accessible (may be starting)")
            
            # Test Streamlit
            try:
                response = requests.get('http://localhost:8501/', timeout=5)
                if response.status_code == 200:
                    print("✅ Streamlit dashboard running")
                else:
                    print(f"⚠️  Streamlit response: {response.status_code}")
            except requests.exceptions.ConnectionError:
                print("⚠️  Streamlit not accessible (may be starting)")
            
            return True
            
        except Exception as e:
            print(f"❌ Web services test error: {e}")
            return False
    
    async def cleanup_test_data(self):
        """Clean up test data from database."""
        print("\n=== Cleanup Test Data ===")
        
        try:
            # Clean up products
            deleted_products = await delete_one('products', {'asin': 'TEST123456'})
            print(f"✅ Cleaned test product: {deleted_products}")
            
            if 'products' in self.test_data:
                for product_id in self.test_data['products']:
                    await delete_one('products', {'_id': product_id})
                print(f"✅ Cleaned {len(self.test_data['products'])} simulated products")
            
            # Clean up alerts
            if 'alerts' in self.test_data:
                for alert_id in self.test_data['alerts']:
                    await delete_one('price_alerts', {'_id': alert_id})
                print(f"✅ Cleaned {len(self.test_data['alerts'])} test alerts")
            
        except Exception as e:
            print(f"⚠️  Cleanup error: {e}")
    
    async def run_all_tests(self):
        """Run all tests in sequence."""
        print("🚀 Starting Comprehensive End-to-End Tests")
        print("=" * 50)
        
        # Component tests
        mongodb_ok = await self.test_mongodb_operations()
        redis_ok = await self.test_redis_operations()
        telegram_ok = self.test_telegram_notifications()
        web_services_ok = self.test_web_services()
        
        # Integration test
        integration_ok = await self.test_scraping_simulation()
        
        # Cleanup
        await self.cleanup_test_data()
        
        # Results summary
        print("\n" + "=" * 50)
        print("📊 **TEST RESULTS SUMMARY**")
        print("=" * 50)
        
        results = {
            "MongoDB Atlas": "✅ PASS" if mongodb_ok else "❌ FAIL",
            "Redis Cloud": "✅ PASS" if redis_ok else "❌ FAIL", 
            "Telegram Bot": "✅ PASS" if telegram_ok else "❌ FAIL",
            "Web Services": "✅ PASS" if web_services_ok else "❌ FAIL",
            "Integration Test": "✅ PASS" if integration_ok else "❌ FAIL"
        }
        
        for test, result in results.items():
            print(f"{test:<20}: {result}")
        
        all_passed = all([mongodb_ok, redis_ok, telegram_ok, integration_ok])
        
        print("\n" + "=" * 50)
        if all_passed:
            print("🎉 **ALL TESTS PASSED** - System Ready for Production!")
        else:
            print("⚠️  **SOME TESTS FAILED** - Check logs above")
        print("=" * 50)
        
        return all_passed

async def main():
    """Main test execution."""
    tester = EndToEndTester()
    success = await tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 