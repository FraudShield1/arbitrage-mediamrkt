#!/usr/bin/env python3
"""
Simple script to check Render service status and scraper activity.
"""

import requests
import json
from datetime import datetime

def check_render_services():
    """Check if Render services are running."""
    
    print("🔍 Checking Render Services Status...")
    print("=" * 50)
    
    # List of possible service URLs to check
    service_urls = [
        "https://arbitrage-api.onrender.com",
        "https://arbitrage-dashboard.onrender.com",
        "https://your-api-service-name.onrender.com",
        "https://your-dashboard-service-name.onrender.com"
    ]
    
    for url in service_urls:
        try:
            print(f"\n🌐 Checking: {url}")
            
            # Check health endpoint
            health_response = requests.get(f"{url}/health", timeout=10)
            if health_response.status_code == 200:
                print(f"✅ Service is RUNNING")
                print(f"   Response: {health_response.text[:100]}...")
            else:
                print(f"⚠️  Service responded with status: {health_response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Service not accessible: {e}")
    
    print("\n" + "=" * 50)
    print("📋 NEXT STEPS TO CHECK SCRAPER:")
    print("1. Go to your Render dashboard")
    print("2. Check the logs for both services")
    print("3. Look for messages like:")
    print("   - 'Scraping MediaMarkt products...'")
    print("   - 'Found X new products'")
    print("   - 'Celery worker ready'")
    print("4. Check your Telegram bot for alerts")
    print("5. If services are suspended, restart them")

if __name__ == "__main__":
    check_render_services() 