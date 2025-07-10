#!/usr/bin/env python3
"""
Scraper Management Script
Control your 24/7 scraper with start/stop commands.
"""

import requests
import json
import time
from datetime import datetime

# Your API service URL
API_URL = "https://arbitrage-api-uzg5.onrender.com"

def check_scraper_status():
    """Check current scraper status."""
    try:
        response = requests.get(f"{API_URL}/api/v1/scraper/status")
        if response.status_code == 200:
            data = response.json()
            print("🔍 Current Scraper Status:")
            print(f"   Status: {data['status']}")
            print(f"   Total Products: {data['total_products']}")
            print(f"   Recent Products (24h): {data['recent_products_24h']}")
            print(f"   Scheduled: {data.get('scheduled', False)}")
            print(f"   Scraper State: {data.get('scraper_state', {})}")
            return data
        else:
            print(f"❌ Error checking status: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def start_24_7_scraper():
    """Start 24/7 scraper."""
    try:
        response = requests.post(f"{API_URL}/api/v1/scraper/start-24-7")
        if response.status_code == 200:
            data = response.json()
            print("✅ 24/7 Scraper Started!")
            print(f"   Message: {data['message']}")
            print(f"   Schedule: {data.get('schedule', {})}")
            return True
        else:
            data = response.json()
            print(f"⚠️  {data.get('message', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ Error starting scraper: {e}")
        return False

def stop_24_7_scraper():
    """Stop 24/7 scraper."""
    try:
        response = requests.post(f"{API_URL}/api/v1/scraper/stop-24-7")
        if response.status_code == 200:
            data = response.json()
            print("🛑 24/7 Scraper Stopped!")
            print(f"   Message: {data['message']}")
            return True
        else:
            data = response.json()
            print(f"⚠️  {data.get('message', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ Error stopping scraper: {e}")
        return False

def start_single_session():
    """Start a single scraping session."""
    try:
        response = requests.post(f"{API_URL}/api/v1/scraper/start")
        if response.status_code == 200:
            data = response.json()
            print("🚀 Single Scraping Session Started!")
            print(f"   Message: {data['message']}")
            return True
        else:
            data = response.json()
            print(f"⚠️  {data.get('detail', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ Error starting session: {e}")
        return False

def show_control_options():
    """Show available control options."""
    try:
        response = requests.get(f"{API_URL}/api/v1/scraper/control")
        if response.status_code == 200:
            data = response.json()
            print("🎛️  Scraper Control Options:")
            print(f"   Current State: {data['current_state']}")
            print("\n📋 Available Actions:")
            for action in data['available_actions']:
                print(f"   • {action}")
            print("\n⏰ Schedule Info:")
            for schedule, info in data['schedule_info'].items():
                print(f"   • {schedule}: {info}")
        else:
            print(f"❌ Error getting control options: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

def monitor_scraper(duration_minutes=5):
    """Monitor scraper activity for specified duration."""
    print(f"📊 Monitoring scraper for {duration_minutes} minutes...")
    print("Press Ctrl+C to stop monitoring")
    
    start_time = datetime.now()
    try:
        while True:
            elapsed = (datetime.now() - start_time).total_seconds() / 60
            if elapsed >= duration_minutes:
                break
                
            status = check_scraper_status()
            if status:
                print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - Elapsed: {elapsed:.1f}m")
                print(f"   Status: {status['status']}")
                print(f"   Products: {status['total_products']} (+{status['recent_products_24h']} new)")
            
            time.sleep(30)  # Check every 30 seconds
            
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped by user")

def main():
    """Main management interface."""
    print("🤖 Arbitrage Scraper Management")
    print("=" * 40)
    
    while True:
        print("\n📋 Available Commands:")
        print("1. Check Status")
        print("2. Start 24/7 Scraper")
        print("3. Stop 24/7 Scraper")
        print("4. Start Single Session")
        print("5. Show Control Options")
        print("6. Monitor Activity (5 min)")
        print("7. Exit")
        
        choice = input("\nEnter your choice (1-7): ").strip()
        
        if choice == "1":
            check_scraper_status()
        elif choice == "2":
            start_24_7_scraper()
        elif choice == "3":
            stop_24_7_scraper()
        elif choice == "4":
            start_single_session()
        elif choice == "5":
            show_control_options()
        elif choice == "6":
            monitor_scraper()
        elif choice == "7":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please try again.")

if __name__ == "__main__":
    main() 