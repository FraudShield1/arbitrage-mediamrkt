#!/usr/bin/env python3
"""
Script to test manual scraping via API endpoints.
"""

import requests
import json
import time

def test_manual_scraping():
    """Test manual scraping via API."""
    
    print("🔧 Testing Manual Scraping...")
    print("=" * 50)
    
    api_url = "https://arbitrage-api-uzg5.onrender.com"
    
    # Test different scraping endpoints
    endpoints = [
        ("/api/v1/scraper/start", "Start Scraping"),
        ("/api/v1/scraper/mediamarkt", "MediaMarkt Scraper"),
        ("/api/v1/scraper/status", "Scraper Status"),
        ("/api/v1/tasks/scrape", "Task Scraping"),
        ("/api/v1/scraper/test", "Test Scraper")
    ]
    
    print(f"🌐 Testing endpoints on: {api_url}")
    
    for endpoint, description in endpoints:
        try:
            print(f"\n🔍 Testing: {description}")
            response = requests.get(f"{api_url}{endpoint}", timeout=15)
            
            if response.status_code == 200:
                print(f"✅ {description}: SUCCESS")
                try:
                    data = response.json()
                    print(f"   Response: {json.dumps(data, indent=2)[:200]}...")
                except:
                    print(f"   Response: {response.text[:100]}...")
            elif response.status_code == 404:
                print(f"❌ {description}: NOT FOUND (404)")
            elif response.status_code == 503:
                print(f"⚠️  {description}: SERVICE UNAVAILABLE (503)")
            else:
                print(f"⚠️  {description}: {response.status_code}")
                print(f"   Response: {response.text[:100]}...")
                
        except Exception as e:
            print(f"❌ {description}: ERROR - {e}")
    
    print(f"\n" + "=" * 50)
    print(f"📋 NEXT STEPS:")
    print(f"1. Check Render logs for Celery worker errors")
    print(f"2. Restart the service if needed")
    print(f"3. Check if Redis is properly configured")
    print(f"4. Verify environment variables are set correctly")

if __name__ == "__main__":
    test_manual_scraping() 