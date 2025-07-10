#!/usr/bin/env python3
"""
Simple test script to verify scraper functionality.
"""

import asyncio
import sys
import os

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

async def test_scraper():
    """Test the scraper functionality."""
    try:
        from services.scraper.mediamarkt_scraper import scrape_mediamarkt_products
        
        print("🧪 Testing scraper functionality...")
        
        # Test with minimal parameters
        products = await scrape_mediamarkt_products(max_pages=1, max_products=5)
        
        print(f"✅ Scraper test successful!")
        print(f"   Products found: {len(products)}")
        
        if products:
            print(f"   Sample product: {products[0].get('title', 'N/A')[:50]}...")
            print(f"   Price: {products[0].get('price', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Scraper test failed: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_scraper())
    if result:
        print("🎉 Scraper is working correctly!")
    else:
        print("💥 Scraper needs fixing!") 