#!/usr/bin/env python3
"""
Script to check scraper status after Render services are restarted.
"""

import requests
import json
import time

def check_scraper_after_restart():
    """Check scraper status after services are restarted."""
    
    print("🔍 Checking Scraper Status After Restart...")
    print("=" * 50)
    
    # Your actual service URLs
    api_url = "https://arbitrage-api.onrender.com"
    main_url = "https://arbitrage.onrender.com"
    
    services = [
        ("API Service", api_url),
        ("Main Service", main_url)
    ]
    
    for service_name, url in services:
        print(f"\n🌐 Checking {service_name}: {url}")
        
        try:
            # Check health endpoint
            health_response = requests.get(f"{url}/health", timeout=10)
            
            if health_response.status_code == 200:
                print(f"✅ {service_name} is RUNNING")
                print(f"   Response: {health_response.text}")
                
                # Try to get scraper status
                try:
                    scraper_response = requests.get(f"{url}/api/v1/scraper/status", timeout=10)
                    if scraper_response.status_code == 200:
                        print(f"   Scraper Status: {scraper_response.text}")
                except:
                    print(f"   ⚠️  Scraper endpoint not available")
                    
            elif health_response.status_code == 503:
                print(f"⚠️  {service_name} is SUSPENDED - Restart it on Render dashboard")
            else:
                print(f"❌ {service_name} error: {health_response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ {service_name} not accessible: {e}")
    
    print("\n" + "=" * 50)
    print("📋 SCRAPER ACTIVITY INDICATORS:")
    print("✅ Check Render logs for:")
    print("   - 'Celery worker ready'")
    print("   - 'Scraping MediaMarkt products...'")
    print("   - 'Found X new products'")
    print("   - 'Scraping session completed'")
    print("\n✅ Check Telegram bot for:")
    print("   - Scraping start messages")
    print("   - New product notifications")
    print("   - Arbitrage opportunity alerts")
    print("\n✅ Check MongoDB for new products:")
    print("   - Products added in last 24h")
    print("   - Recent scraping sessions")

if __name__ == "__main__":
    check_scraper_after_restart() 