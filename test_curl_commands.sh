#!/bin/bash

# Test script for API endpoints using curl

BASE_URL="https://arbitrage-api-uzg5.onrender.com"

echo "🧪 Testing API Endpoints with curl..."
echo "=================================================="

# Test 1: Health check
echo -e "\n1️⃣ Testing health check..."
curl -s -X GET "${BASE_URL}/health" | jq '.'

# Test 2: Scraper status
echo -e "\n2️⃣ Testing scraper status..."
curl -s -X GET "${BASE_URL}/api/v1/scraper/status" | jq '.'

# Test 3: Start 24/7 scraper (POST method)
echo -e "\n3️⃣ Testing 24/7 scraper start (POST)..."
curl -s -X POST "${BASE_URL}/api/v1/scraper/start-24-7" | jq '.'

# Test 4: Manual scraper start (POST)
echo -e "\n4️⃣ Testing manual scraper start (POST)..."
curl -s -X POST "${BASE_URL}/api/v1/scraper/start" | jq '.'

# Test 5: Product count
echo -e "\n5️⃣ Testing product count..."
curl -s -X GET "${BASE_URL}/api/v1/products/count" | jq '.'

# Test 6: Scraper control info
echo -e "\n6️⃣ Testing scraper control info..."
curl -s -X GET "${BASE_URL}/api/v1/scraper/control" | jq '.'

echo -e "\n=================================================="
echo "📋 SUMMARY:"
echo "✅ All endpoints tested with curl"
echo "🌐 Base URL: ${BASE_URL}"
echo "📖 API Docs: ${BASE_URL}/docs"
echo "🔧 Next: Check Render logs for scraper activity" 