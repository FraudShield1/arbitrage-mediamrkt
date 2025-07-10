# 🤖 24/7 Arbitrage Scraper System Guide

## 🎯 **Overview**

Your arbitrage scraper is now equipped with a **24/7 automated system** that can run continuously with full control over start/stop operations.

## 🚀 **How to Use Your 24/7 Scraper**

### **Method 1: Using the Management Script (Recommended)**

Run the management script for easy control:

```bash
python3 manage_scraper.py
```

This gives you an interactive menu with options:
- ✅ Check Status
- 🚀 Start 24/7 Scraper
- 🛑 Stop 24/7 Scraper
- 📊 Monitor Activity

### **Method 2: Direct API Calls**

#### **Start 24/7 Scraper:**
```bash
curl -X POST "https://arbitrage-api-uzg5.onrender.com/api/v1/scraper/start-24-7"
```

#### **Stop 24/7 Scraper:**
```bash
curl -X POST "https://arbitrage-api-uzg5.onrender.com/api/v1/scraper/stop-24-7"
```

#### **Check Status:**
```bash
curl "https://arbitrage-api-uzg5.onrender.com/api/v1/scraper/status"
```

#### **Start Single Session:**
```bash
curl -X POST "https://arbitrage-api-uzg5.onrender.com/api/v1/scraper/start"
```

## ⏰ **Scraper Schedule**

When running 24/7, your scraper follows this schedule:

### **🔄 Light Scraping: Every 15 minutes**
- Scrapes 3 pages
- Collects up to 50 products
- Fast, efficient updates

### **🔍 Deep Scraping: Every 3 hours**
- Scrapes 10 pages
- Collects up to 200 products
- Comprehensive data collection

### **📊 Analysis: Every hour**
- Analyzes collected data
- Identifies arbitrage opportunities
- Sends alerts

### **🚨 Real-time Alerts**
- Instant notifications via Telegram
- Price change alerts
- New opportunity detection

## 📊 **Monitoring Your Scraper**

### **1. Check Scraper Status**
```bash
curl -s "https://arbitrage-api-uzg5.onrender.com/api/v1/scraper/status" | python3 -m json.tool
```

**Expected Response:**
```json
{
  "status": "active",
  "total_products": 703,
  "recent_products_24h": 25,
  "scheduled": true,
  "scraper_state": {
    "is_running": false,
    "is_scheduled": true,
    "total_sessions": 5
  }
}
```

### **2. Monitor via Telegram**
- Open @ShemsyMediaBot
- Look for scraping notifications
- Check for new product alerts

### **3. Check Render Logs**
- Go to [render.com/dashboard](https://render.com/dashboard)
- Click on your `arbitrage-api-uzg5` service
- Check "Logs" tab for activity

## 🎛️ **Control Commands**

### **Start 24/7 Mode:**
```bash
# Using management script
python3 manage_scraper.py
# Choose option 2

# Or direct API call
curl -X POST "https://arbitrage-api-uzg5.onrender.com/api/v1/scraper/start-24-7"
```

### **Stop 24/7 Mode:**
```bash
# Using management script
python3 manage_scraper.py
# Choose option 3

# Or direct API call
curl -X POST "https://arbitrage-api-uzg5.onrender.com/api/v1/scraper/stop-24-7"
```

### **Single Session:**
```bash
# Start one scraping session
curl -X POST "https://arbitrage-api-uzg5.onrender.com/api/v1/scraper/start"
```

## 📈 **Expected Results**

### **When 24/7 Scraper is Running:**

1. **Database Growth:**
   - New products added every 15 minutes
   - Product count increases steadily
   - Fresh data for analysis

2. **Telegram Notifications:**
   - "🔄 Scraping started"
   - "✅ Found X new products"
   - "💰 New arbitrage opportunity detected"

3. **Performance Metrics:**
   - 50-200 products per session
   - 96+ scraping sessions per day
   - Continuous data collection

## 🔧 **Troubleshooting**

### **If Scraper Won't Start:**
1. Check if service is running: `curl "https://arbitrage-api-uzg5.onrender.com/health"`
2. Check Render logs for errors
3. Restart the service on Render dashboard

### **If No New Products:**
1. Check scraper status: `curl "https://arbitrage-api-uzg5.onrender.com/api/v1/scraper/status"`
2. Look for errors in Render logs
3. Try manual session: `curl -X POST "https://arbitrage-api-uzg5.onrender.com/api/v1/scraper/start"`

### **If Telegram Not Working:**
1. Check bot token in environment variables
2. Verify chat ID is correct
3. Test bot manually: @ShemsyMediaBot

## 🎯 **Quick Start Commands**

### **Start 24/7 Scraper:**
```bash
curl -X POST "https://arbitrage-api-uzg5.onrender.com/api/v1/scraper/start-24-7"
```

### **Check if Running:**
```bash
curl "https://arbitrage-api-uzg5.onrender.com/api/v1/scraper/status"
```

### **Stop Scraper:**
```bash
curl -X POST "https://arbitrage-api-uzg5.onrender.com/api/v1/scraper/stop-24-7"
```

## 🚀 **Your Scraper is Ready!**

Your 24/7 arbitrage scraper system is now:
- ✅ **Deployed** and functional
- ✅ **Controllable** with start/stop commands
- ✅ **Scheduled** for automatic operation
- ✅ **Monitored** with status endpoints
- ✅ **Alerted** via Telegram notifications

**Start your 24/7 scraper now and begin collecting arbitrage opportunities automatically!** 🎉 