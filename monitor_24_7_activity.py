#!/usr/bin/env python3
"""
24/7 Scraper Activity Monitor

This script provides comprehensive monitoring of the 24/7 scraper with detailed logging.
"""

import requests
import json
import time
from datetime import datetime, timedelta
import sys

def monitor_24_7_activity():
    """Monitor 24/7 scraper activity with detailed logging."""
    
    base_url = "https://arbitrage-api-uzg5.onrender.com"
    
    print("🚀 24/7 Scraper Activity Monitor")
    print("=" * 60)
    print("📊 Configuration: Continuous monitoring with detailed logging")
    print("⏰ Schedule: Light scraping every 15 min, Deep every 3 hours, Analysis every hour")
    print("=" * 60)
    
    session_count = 0
    last_product_count = 0
    last_check = None
    
    while True:
        try:
            current_time = datetime.utcnow()
            
            # Get detailed monitor information
            response = requests.get(f"{base_url}/api/v1/scraper/monitor", timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract key information
                status_24_7 = data.get("24_7_status", {})
                current_session = data.get("current_session", {})
                statistics = data.get("statistics", {})
                
                # Calculate time since last check
                time_since_last = ""
                if last_check:
                    time_diff = (current_time - last_check).total_seconds()
                    time_since_last = f" (+{time_diff:.0f}s)"
                
                print(f"\n⏰ {current_time.strftime('%Y-%m-%d %H:%M:%S')}{time_since_last}")
                print("-" * 50)
                
                # 24/7 Status
                print(f"🔄 24/7 Status:")
                print(f"   • Scheduled: {'✅' if status_24_7.get('scheduled') else '❌'}")
                print(f"   • Running: {'✅' if status_24_7.get('running') else '⏸️'}")
                print(f"   • Uptime: {status_24_7.get('uptime_formatted', 'N/A')}")
                print(f"   • Total Sessions: {status_24_7.get('total_sessions', 0)}")
                
                # Current Session
                session_status = current_session.get('status', 'idle')
                session_emoji = {
                    'active': '🟢',
                    'completed': '✅',
                    'failed': '❌',
                    'idle': '⏸️'
                }.get(session_status, '❓')
                
                print(f"\n📊 Current Session: {session_emoji} {session_status.upper()}")
                
                session_details = current_session.get('details', {})
                if session_details:
                    if session_details.get('type'):
                        print(f"   • Type: {session_details['type']}")
                    if session_details.get('started_at'):
                        print(f"   • Started: {session_details['started_at'][11:19]}")
                    if session_details.get('duration_seconds'):
                        print(f"   • Duration: {session_details['duration_seconds']:.1f}s")
                    if session_details.get('products_found'):
                        print(f"   • Products: {session_details['products_found']}")
                    if session_details.get('error'):
                        print(f"   • Error: {session_details['error']}")
                
                # Statistics
                current_product_count = statistics.get('total_products', 0)
                product_change = current_product_count - last_product_count
                product_change_str = f" (+{product_change})" if product_change > 0 else f" ({product_change})" if product_change < 0 else ""
                
                print(f"\n📈 Statistics:")
                print(f"   • Total Products: {current_product_count}{product_change_str}")
                print(f"   • Recent (24h): {statistics.get('recent_products_24h', 0)}")
                print(f"   • Sessions (24h): {statistics.get('recent_sessions_24h', 0)}")
                
                # Next scheduled runs
                current_minute = current_time.minute
                current_hour = current_time.hour
                
                print(f"\n⏰ Next Scheduled Runs:")
                
                # Light scraping (every 15 minutes)
                next_light_minute = ((current_minute // 15) + 1) * 15
                if next_light_minute >= 60:
                    next_light_minute = 0
                    next_light_hour = current_hour + 1
                else:
                    next_light_hour = current_hour
                
                minutes_to_light = (next_light_minute - current_minute) % 15
                print(f"   🔄 Light Scraping: {next_light_hour:02d}:{next_light_minute:02d} (in {minutes_to_light} min)")
                
                # Deep scraping (every 3 hours)
                next_deep_hour = ((current_hour // 3) + 1) * 3
                hours_to_deep = (next_deep_hour - current_hour) % 3
                print(f"   🔥 Deep Scraping: {next_deep_hour:02d}:00 (in {hours_to_deep} hours)")
                
                # Analysis (every hour)
                next_analysis_hour = current_hour + 1
                minutes_to_analysis = 60 - current_minute
                print(f"   📊 Analysis: {next_analysis_hour:02d}:00 (in {minutes_to_analysis} min)")
                
                # Activity indicators
                if product_change > 0:
                    print(f"\n🎉 NEW PRODUCTS FOUND! +{product_change} products")
                elif session_status == 'active':
                    print(f"\n⚡ SCRAPING IN PROGRESS...")
                elif session_status == 'completed':
                    print(f"\n✅ SESSION COMPLETED")
                elif session_status == 'failed':
                    print(f"\n❌ SESSION FAILED")
                
                # Update tracking variables
                last_product_count = current_product_count
                last_check = current_time
                session_count += 1
                
            else:
                print(f"❌ Failed to get monitor data: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                
        except Exception as e:
            print(f"❌ Monitor error: {e}")
        
        # Wait 30 seconds before next check
        print(f"\n⏳ Waiting 30 seconds for next check...")
        time.sleep(30)

def quick_status_check():
    """Quick status check without continuous monitoring."""
    base_url = "https://arbitrage-api-uzg5.onrender.com"
    
    print("🔍 Quick 24/7 Status Check")
    print("=" * 40)
    
    try:
        # Get basic status
        response = requests.get(f"{base_url}/api/v1/scraper/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"📊 Status: {data.get('status', 'unknown')}")
            print(f"📦 Products: {data.get('total_products', 0)}")
            print(f"🔄 Scheduled: {data.get('scheduled', False)}")
            
            scraper_state = data.get('scraper_state', {})
            if scraper_state.get('last_start'):
                print(f"🚀 Started: {scraper_state['last_start'][:19]}")
                print(f"📈 Sessions: {scraper_state.get('total_sessions', 0)}")
        
        # Get detailed monitor
        response = requests.get(f"{base_url}/api/v1/scraper/monitor", timeout=10)
        if response.status_code == 200:
            data = response.json()
            status_24_7 = data.get("24_7_status", {})
            current_session = data.get("current_session", {})
            
            print(f"\n🔄 24/7 Details:")
            print(f"   • Uptime: {status_24_7.get('uptime_formatted', 'N/A')}")
            print(f"   • Current Session: {current_session.get('status', 'idle')}")
            
            if current_session.get('details', {}).get('type'):
                print(f"   • Session Type: {current_session['details']['type']}")
        
    except Exception as e:
        print(f"❌ Status check failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        quick_status_check()
    else:
        print("🚀 Starting 24/7 Activity Monitor...")
        print("Press Ctrl+C to stop monitoring")
        print("Use 'python3 monitor_24_7_activity.py quick' for one-time check")
        print()
        
        try:
            monitor_24_7_activity()
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user")
        except Exception as e:
            print(f"\n❌ Monitor stopped due to error: {e}") 