#!/usr/bin/env python3
"""
Test script to verify API endpoints work correctly.
"""

import requests
import json
import time

def test_api_endpoints():
    """Test the API endpoints."""
    
    base_url = "https://arbitrage-api-uzg5.onrender.com"
    
    print("🧪 Testing API Endpoints...")
    print("=" * 50)
    
    # Test 1: Health check
    print("\n1️⃣ Testing health check...")
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            print("✅ Health check: SUCCESS")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Health check: {response.status_code}")
    except Exception as e:
        print(f"❌ Health check error: {e}")
    
    # Test 2: Scraper status
    print("\n2️⃣ Testing scraper status...")
    try:
        response = requests.get(f"{base_url}/api/v1/scraper/status", timeout=10)
        if response.status_code == 200:
            print("✅ Scraper status: SUCCESS")
            data = response.json()
            print(f"   Status: {data.get('status', 'unknown')}")
            print(f"   Total products: {data.get('total_products', 0)}")
        else:
            print(f"❌ Scraper status: {response.status_code}")
    except Exception as e:
        print(f"❌ Scraper status error: {e}")
    
    # Test 3: Start 24/7 scraper (GET)
    print("\n3️⃣ Testing 24/7 scraper start (GET)...")
    try:
        response = requests.get(f"{base_url}/api/v1/scraper/start-24-7", timeout=15)
        if response.status_code == 200:
            print("✅ 24/7 scraper start: SUCCESS")
            data = response.json()
            print(f"   Status: {data.get('status', 'unknown')}")
            print(f"   Message: {data.get('message', 'No message')}")
        else:
            print(f"❌ 24/7 scraper start: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ 24/7 scraper start error: {e}")
    
    # Test 4: Manual scraper start (POST)
    print("\n4️⃣ Testing manual scraper start (POST)...")
    try:
        response = requests.post(f"{base_url}/api/v1/scraper/start", timeout=15)
        if response.status_code == 200:
            print("✅ Manual scraper start: SUCCESS")
            data = response.json()
            print(f"   Status: {data.get('status', 'unknown')}")
            print(f"   Message: {data.get('message', 'No message')}")
        else:
            print(f"❌ Manual scraper start: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Manual scraper start error: {e}")
    
    # Test 5: Product count
    print("\n5️⃣ Testing product count...")
    try:
        response = requests.get(f"{base_url}/api/v1/products/count", timeout=10)
        if response.status_code == 200:
            print("✅ Product count: SUCCESS")
            data = response.json()
            print(f"   Count: {data.get('count', 0)}")
        else:
            print(f"❌ Product count: {response.status_code}")
    except Exception as e:
        print(f"❌ Product count error: {e}")
    
    # Test 6: Scraper control info
    print("\n6️⃣ Testing scraper control info...")
    try:
        response = requests.get(f"{base_url}/api/v1/scraper/control", timeout=10)
        if response.status_code == 200:
            print("✅ Scraper control: SUCCESS")
            data = response.json()
            print(f"   Current state: {data.get('current_state', {})}")
        else:
            print(f"❌ Scraper control: {response.status_code}")
    except Exception as e:
        print(f"❌ Scraper control error: {e}")
    
    print("\n" + "=" * 50)
    print("📋 SUMMARY:")
    print("✅ All endpoints tested")
    print("🌐 Base URL:", base_url)
    print("📖 API Docs:", f"{base_url}/docs")
    print("🔧 Next: Check Render logs for scraper activity")

if __name__ == "__main__":
    test_api_endpoints() 