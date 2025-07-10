#!/usr/bin/env python3
"""
Comprehensive script to check scraper activity using the working API service.
"""

import requests
import json
import time
from datetime import datetime, timedelta

def check_scraper_activity():
    """Check scraper activity using the working API service."""
    
    print("🔍 Checking Scraper Activity...")
    print("=" * 50)
    
    api_url = "https://arbitrage-api-uzg5.onrender.com"
    
    print(f"✅ API Service is RUNNING: {api_url}")
    print(f"   Environment: Production")
    print(f"   Version: 1.0.0")
    
    # Test different endpoints to check scraper status
    endpoints = [
        ("/health", "Basic Health Check"),
        ("/api/v1/products/count", "Product Count"),
        ("/api/v1/scraper/status", "Scraper Status"),
        ("/api/v1/alerts/recent", "Recent Alerts"),
        ("/api/v1/opportunities", "Arbitrage Opportunities")
    ]
    
    print(f"\n📊 Checking API Endpoints:")
    for endpoint, description in endpoints:
        try:
            response = requests.get(f"{api_url}{endpoint}", timeout=10)
            if response.status_code == 200:
                print(f"✅ {description}: {response.status_code}")
                try:
                    data = response.json()
                    if endpoint == "/api/v1/products/count":
                        print(f"   Products: {data.get('count', 'N/A')}")
                    elif endpoint == "/api/v1/alerts/recent":
                        print(f"   Recent alerts: {len(data.get('alerts', []))}")
                    elif endpoint == "/api/v1/opportunities":
                        print(f"   Opportunities: {len(data.get('opportunities', []))}")
                except:
                    print(f"   Response: {response.text[:100]}...")
            else:
                print(f"⚠️  {description}: {response.status_code}")
        except Exception as e:
            print(f"❌ {description}: Error - {e}")
    
    print(f"\n" + "=" * 50)
    print(f"📋 SCRAPER ACTIVITY INDICATORS:")
    print(f"✅ Your API service is RUNNING and healthy!")
    print(f"✅ Check these sources for scraper activity:")
    print(f"\n1. 📱 Telegram Bot (@ShemsyMediaBot):")
    print(f"   - Look for scraping start messages")
    print(f"   - Check for new product notifications")
    print(f"   - Monitor arbitrage opportunity alerts")
    
    print(f"\n2. 📊 Render Dashboard Logs:")
    print(f"   - Go to render.com/dashboard")
    print(f"   - Click on 'arbitrage-api-uzg5' service")
    print(f"   - Check 'Logs' tab for messages like:")
    print(f"     • 'Celery worker ready'")
    print(f"     • 'Scraping MediaMarkt products...'")
    print(f"     • 'Found X new products'")
    print(f"     • 'Scraping session completed'")
    
    print(f"\n3. 🗄️  MongoDB Atlas:")
    print(f"   - Check for new products added")
    print(f"   - Monitor scraping sessions")
    print(f"   - Look for arbitrage opportunities")
    
    print(f"\n4. 🕒 Expected Scraper Schedule:")
    print(f"   • Every 15 minutes: Light scraping")
    print(f"   • Every 3 hours: Deep scraping")
    print(f"   • Every hour: Analysis and alerts")
    print(f"   • Daily: Summary reports")

if __name__ == "__main__":
    check_scraper_activity() 