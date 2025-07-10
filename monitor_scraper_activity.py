#!/usr/bin/env python3
"""
Monitor scraper activity and show next scheduled runs.
"""

import requests
import json
from datetime import datetime, timedelta
import time

def monitor_scraper_activity():
    """Monitor scraper activity and show next scheduled runs."""
    
    base_url = "https://arbitrage-api-uzg5.onrender.com"
    
    print("🔍 Monitoring Scraper Activity...")
    print("=" * 50)
    
    try:
        # Get current scraper status
        response = requests.get(f"{base_url}/api/v1/scraper/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            print(f"📊 Current Status: {data.get('status', 'unknown')}")
            print(f"📦 Total Products: {data.get('total_products', 0)}")
            print(f"🔄 Scheduled: {data.get('scheduled', False)}")
            
            scraper_state = data.get('scraper_state', {})
            if scraper_state.get('last_start'):
                last_start = datetime.fromisoformat(scraper_state['last_start'].replace('Z', '+00:00'))
                print(f"🚀 Started: {last_start.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Calculate next runs
                now = datetime.utcnow()
                time_since_start = now - last_start
                
                print(f"\n⏰ Next Scheduled Runs:")
                
                # Next light scraping (every 15 minutes)
                next_light = now.replace(second=0, microsecond=0)
                while next_light.minute % 15 != 0:
                    next_light += timedelta(minutes=1)
                time_to_light = (next_light - now).total_seconds() / 60
                print(f"   🔄 Light Scraping: {next_light.strftime('%H:%M')} (in {time_to_light:.1f} minutes)")
                
                # Next deep scraping (every 3 hours)
                next_deep = now.replace(second=0, microsecond=0, minute=0)
                while next_deep.hour % 3 != 0:
                    next_deep += timedelta(hours=1)
                time_to_deep = (next_deep - now).total_seconds() / 60
                print(f"   🔥 Deep Scraping: {next_deep.strftime('%H:%M')} (in {time_to_deep:.1f} minutes)")
                
                # Next analysis (every hour)
                next_analysis = now.replace(second=0, microsecond=0, minute=0) + timedelta(hours=1)
                time_to_analysis = (next_analysis - now).total_seconds() / 60
                print(f"   📊 Analysis: {next_analysis.strftime('%H:%M')} (in {time_to_analysis:.1f} minutes)")
                
                print(f"\n📈 Activity Indicators:")
                print(f"   • Recent Products (24h): {data.get('recent_products_24h', 0)}")
                print(f"   • Recent Sessions: {data.get('recent_sessions', 0)}")
                print(f"   • Total Sessions: {scraper_state.get('total_sessions', 0)}")
                
                if data.get('recent_products_24h', 0) == 0:
                    print(f"\n💡 Note: No recent activity yet. The scraper is waiting for the next scheduled run.")
                    print(f"   Check back in {time_to_light:.1f} minutes for light scraping activity.")
                
            else:
                print("❌ No start time found")
                
        else:
            print(f"❌ Failed to get status: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error monitoring scraper: {e}")
    
    print("\n" + "=" * 50)
    print("📋 How to Monitor:")
    print("1. Check Render logs every 15 minutes")
    print("2. Monitor product count: curl {base_url}/api/v1/products/count")
    print("3. Check Telegram for alerts (if configured)")
    print("4. Use this script to see next scheduled runs")

def check_product_count():
    """Check if product count has increased."""
    base_url = "https://arbitrage-api-uzg5.onrender.com"
    
    try:
        response = requests.get(f"{base_url}/api/v1/products/count", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('count', 0)
    except:
        pass
    return None

if __name__ == "__main__":
    monitor_scraper_activity()
    
    # Also show current product count
    current_count = check_product_count()
    if current_count is not None:
        print(f"\n📦 Current Product Count: {current_count}")
        if current_count > 703:  # Previous count
            print(f"✅ NEW PRODUCTS FOUND! Count increased by {current_count - 703}")
        else:
            print(f"📊 No new products yet (waiting for next scheduled run)") 