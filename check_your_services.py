#!/usr/bin/env python3
"""
Script to check the user's actual Render services and scraper status.
"""

import requests
import json
import time

def check_your_services():
    """Check the user's actual Render services."""
    
    print("🔍 Checking Your Render Services...")
    print("=" * 50)
    
    # Your actual service URLs
    api_url = "https://arbitrage-api-uzg5.onrender.com"
    dashboard_url = "https://arbitrage-dashboard-184w.onrender.com"
    
    services = [
        ("API Service", api_url),
        ("Dashboard Service", dashboard_url)
    ]
    
    for service_name, url in services:
        print(f"\n🌐 Checking {service_name}: {url}")
        
        try:
            # Check health endpoint
            health_response = requests.get(f"{url}/health", timeout=15)
            
            if health_response.status_code == 200:
                print(f"✅ {service_name} is RUNNING")
                print(f"   Response: {health_response.text}")
                
                # Try to get scraper status for API service
                if "api" in service_name.lower():
                    try:
                        scraper_response = requests.get(f"{url}/api/v1/scraper/status", timeout=10)
                        if scraper_response.status_code == 200:
                            print(f"   Scraper Status: {scraper_response.text}")
                        else:
                            print(f"   ⚠️  Scraper endpoint returned: {scraper_response.status_code}")
                    except Exception as e:
                        print(f"   ⚠️  Scraper endpoint error: {e}")
                    
            elif health_response.status_code == 503:
                print(f"⚠️  {service_name} is SUSPENDED - Restart it on Render dashboard")
            elif health_response.status_code == 404:
                print(f"❌ {service_name} not found - Check URL")
            else:
                print(f"❌ {service_name} error: {health_response.status_code}")
                print(f"   Response: {health_response.text[:200]}...")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ {service_name} not accessible: {e}")
    
    print("\n" + "=" * 50)
    print("📋 SCRAPER ACTIVITY CHECK:")
    print("1. If services are running, check Render logs for:")
    print("   - 'Celery worker ready'")
    print("   - 'Scraping MediaMarkt products...'")
    print("   - 'Found X new products'")
    print("   - 'Scraping session completed'")
    print("\n2. Check your Telegram bot (@ShemsyMediaBot) for:")
    print("   - Scraping start messages")
    print("   - New product notifications")
    print("   - Arbitrage opportunity alerts")
    print("\n3. If services are suspended, restart them on Render dashboard")

if __name__ == "__main__":
    check_your_services() 