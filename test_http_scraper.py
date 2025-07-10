#!/usr/bin/env python3
"""
Test HTTP-only scraper functionality.
"""

import asyncio
import sys
import os

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

async def test_http_scraper():
    """Test the HTTP-only scraper functionality."""
    
    print("🧪 Testing HTTP-only scraper...")
    
    try:
        from services.scraper.mediamarkt_scraper import MediaMarktScraper
        
        # Create scraper instance
        scraper = MediaMarktScraper()
        
        print("📦 Testing HTTP-only scraping...")
        
        # Test HTTP-only scraping
        products = await scraper.scrape_products_http_only(max_pages=1, max_products=5)
        
        print(f"✅ HTTP-only scraping completed!")
        print(f"📊 Results:")
        print(f"   • Products found: {len(products)}")
        
        if products:
            print(f"   • First product: {products[0].get('title', 'No title')[:50]}...")
            print(f"   • Price: {products[0].get('price', 'No price')}")
        
        return len(products)
        
    except Exception as e:
        print(f"❌ HTTP-only scraper test failed: {e}")
        return 0

if __name__ == "__main__":
    result = asyncio.run(test_http_scraper())
    print(f"\n📊 Test completed with {result} products found") 