#!/usr/bin/env python3
"""
Script to check if the scraper is actively working by querying MongoDB.
"""

import asyncio
import motor.motor_asyncio
from datetime import datetime, timedelta
import json

# Your MongoDB connection string
MONGODB_URL = "mongodb+srv://shemsybot:Xonique99@cluster0.7i47zbl.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

async def check_scraper_status():
    """Check if scraper is actively working."""
    
    # Connect to MongoDB
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
    db = client.arbitrage_tool  # or your database name
    
    print("🔍 Checking scraper status...")
    print("=" * 50)
    
    try:
        # 1. Check total products count
        total_products = await db.products.count_documents({})
        print(f"📦 Total products in database: {total_products}")
        
        # 2. Check recent products (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_products = await db.products.count_documents({
            "created_at": {"$gte": yesterday}
        })
        print(f"🆕 Products added in last 24h: {recent_products}")
        
        # 3. Check scraping sessions
        recent_sessions = await db.scraping_sessions.find({
            "created_at": {"$gte": yesterday}
        }).sort("created_at", -1).limit(5).to_list(length=5)
        
        print(f"\n📊 Recent scraping sessions:")
        for session in recent_sessions:
            status = session.get("status", "unknown")
            created = session.get("created_at", "unknown")
            products_found = session.get("products_found", 0)
            print(f"  • {created}: {status} - {products_found} products")
        
        # 4. Check price alerts
        recent_alerts = await db.price_alerts.count_documents({
            "created_at": {"$gte": yesterday}
        })
        print(f"\n🚨 Price alerts in last 24h: {recent_alerts}")
        
        # 5. Check arbitrage opportunities
        opportunities = await db.products.count_documents({
            "arbitrage_opportunity": True
        })
        print(f"💰 Active arbitrage opportunities: {opportunities}")
        
        # 6. Check latest product
        latest_product = await db.products.find_one(
            sort=[("created_at", -1)]
        )
        
        if latest_product:
            latest_time = latest_product.get("created_at", "unknown")
            print(f"\n🕒 Latest product added: {latest_time}")
            print(f"   Title: {latest_product.get('title', 'N/A')[:50]}...")
        
        # 7. Determine if scraper is active
        if recent_products > 0:
            print(f"\n✅ SCRAPER IS ACTIVE! Found {recent_products} new products in 24h")
        elif total_products > 0:
            print(f"\n⚠️  SCRAPER MAY BE INACTIVE - No new products in 24h")
            print(f"   Total products: {total_products}")
        else:
            print(f"\n❌ SCRAPER NOT WORKING - No products in database")
            
    except Exception as e:
        print(f"❌ Error checking database: {e}")
    finally:
        client.close()

def main():
    """Main function to run the async check."""
    asyncio.run(check_scraper_status())

if __name__ == "__main__":
    main() 