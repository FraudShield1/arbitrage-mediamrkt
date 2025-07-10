#!/usr/bin/env python3
"""
Script to check MongoDB for recent scraper activity.
"""

import asyncio
import motor.motor_asyncio
from datetime import datetime, timedelta
import ssl

# Your MongoDB connection string
MONGODB_URL = "mongodb+srv://shemsybot:Xonique99@cluster0.7i47zbl.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

async def check_database_activity():
    """Check MongoDB for recent scraper activity."""
    
    print("🔍 Checking Database for Recent Scraper Activity...")
    print("=" * 50)
    
    # Connect to MongoDB with SSL settings
    client = motor.motor_asyncio.AsyncIOMotorClient(
        MONGODB_URL,
        tls=True,
        tlsAllowInvalidCertificates=True,
        tlsAllowInvalidHostnames=True
    )
    db = client.arbitrage_tool
    
    try:
        # 1. Check total products
        total_products = await db.products.count_documents({})
        print(f"📦 Total products in database: {total_products}")
        
        # 2. Check recent products (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_products = await db.products.count_documents({
            "created_at": {"$gte": yesterday}
        })
        print(f"🆕 Products added in last 24h: {recent_products}")
        
        # 3. Check very recent products (last hour)
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        very_recent = await db.products.count_documents({
            "created_at": {"$gte": one_hour_ago}
        })
        print(f"⚡ Products added in last hour: {very_recent}")
        
        # 4. Check latest product
        latest_product = await db.products.find_one(
            sort=[("created_at", -1)]
        )
        
        if latest_product:
            latest_time = latest_product.get("created_at", "unknown")
            print(f"\n🕒 Latest product added: {latest_time}")
            print(f"   Title: {latest_product.get('title', 'N/A')[:50]}...")
            print(f"   Price: {latest_product.get('price', 'N/A')}")
        
        # 5. Check scraping sessions
        recent_sessions = await db.scraping_sessions.find({
            "created_at": {"$gte": yesterday}
        }).sort("created_at", -1).limit(3).to_list(length=3)
        
        print(f"\n📊 Recent scraping sessions:")
        if recent_sessions:
            for session in recent_sessions:
                status = session.get("status", "unknown")
                created = session.get("created_at", "unknown")
                products_found = session.get("products_found", 0)
                print(f"  • {created}: {status} - {products_found} products")
        else:
            print(f"  • No recent scraping sessions found")
        
        # 6. Determine scraper status
        if very_recent > 0:
            print(f"\n✅ SCRAPER IS ACTIVE! Found {very_recent} products in last hour")
        elif recent_products > 0:
            print(f"\n⚠️  SCRAPER WAS ACTIVE - Found {recent_products} products in 24h")
        elif total_products > 0:
            print(f"\n❌ SCRAPER INACTIVE - No new products in 24h")
            print(f"   Total products: {total_products}")
        else:
            print(f"\n❌ SCRAPER NOT WORKING - No products in database")
            
    except Exception as e:
        print(f"❌ Error checking database: {e}")
    finally:
        client.close()

def main():
    """Main function to run the async check."""
    asyncio.run(check_database_activity())

if __name__ == "__main__":
    main() 