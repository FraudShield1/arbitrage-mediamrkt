#!/usr/bin/env python3
"""
Script to help find your actual Render service URLs.
"""

import requests
import time

def find_render_services():
    """Try to find your actual Render service URLs."""
    
    print("🔍 Finding Your Render Services...")
    print("=" * 50)
    
    # Common service name patterns
    possible_names = [
        "arbitrage-api",
        "arbitrage-dashboard", 
        "arbitrage",
        "api",
        "dashboard",
        "mediamrkt",
        "arbitrage-tool",
        "arbitrage-system"
    ]
    
    print("Trying common service names...")
    
    for name in possible_names:
        url = f"https://{name}.onrender.com"
        try:
            print(f"\n🌐 Testing: {url}")
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                print(f"✅ FOUND WORKING SERVICE: {url}")
                print(f"   Response: {response.text[:100]}...")
            elif response.status_code == 503:
                print(f"⚠️  Service exists but suspended: {url}")
            else:
                print(f"❌ Not found: {url}")
        except:
            print(f"❌ Not accessible: {url}")
    
    print("\n" + "=" * 50)
    print("📋 MANUAL CHECK:")
    print("1. Go to render.com/dashboard")
    print("2. Look for your services in the list")
    print("3. Copy the actual URLs")
    print("4. Update the check scripts with correct URLs")

if __name__ == "__main__":
    find_render_services() 