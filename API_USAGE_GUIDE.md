# API Usage Guide

## 🚀 Cross-Market Arbitrage Tool API

**Base URL**: `https://arbitrage-api-uzg5.onrender.com`

## 📋 Available Endpoints

### Health & Status

#### Health Check
```bash
GET /health
```
**Response**: Service health status
```json
{
  "status": "healthy",
  "service": "Cross-Market Arbitrage Tool",
  "version": "1.0.0",
  "environment": "production",
  "debug": false
}
```

#### Database Health
```bash
GET /health/database
```
**Response**: Database connection status

### Scraper Control

#### Get Scraper Status
```bash
GET /api/v1/scraper/status
```
**Response**: Current scraper status and statistics
```json
{
  "status": "active|inactive",
  "total_products": 703,
  "recent_products_24h": 0,
  "recent_sessions": 0,
  "scraper_state": {...},
  "scheduled": false,
  "timestamp": "2025-07-10T17:13:39.128655"
}
```

#### Start 24/7 Scraper
```bash
POST /api/v1/scraper/start-24-7
```
**Response**: 24/7 scraper start confirmation
```json
{
  "status": "started|already_running",
  "message": "24/7 scraper started successfully",
  "schedule": {
    "light_scraping": "Every 15 minutes",
    "deep_scraping": "Every 3 hours",
    "analysis": "Every hour"
  },
  "timestamp": "2025-07-10T17:14:01.027314"
}
```

#### Stop 24/7 Scraper
```bash
POST /api/v1/scraper/stop-24-7
```
**Response**: 24/7 scraper stop confirmation

#### Manual Scraper Start
```bash
POST /api/v1/scraper/start
```
**Response**: Manual scraping session start
```json
{
  "status": "started",
  "message": "Scraping session started in background",
  "timestamp": "2025-07-10T17:13:39.128655"
}
```

#### Test Scraper
```bash
GET /api/v1/scraper/test
```
**Response**: Scraper initialization test

#### Scraper Control Info
```bash
GET /api/v1/scraper/control
```
**Response**: Available scraper actions and current state

### Data Endpoints

#### Product Count
```bash
GET /api/v1/products/count
```
**Response**: Total number of products in database
```json
{
  "count": 703,
  "timestamp": "2025-07-10T17:13:39.128655"
}
```

#### Recent Alerts
```bash
GET /api/v1/alerts/recent
```
**Response**: Recent price alerts from last 24 hours

#### Arbitrage Opportunities
```bash
GET /api/v1/opportunities
```
**Response**: Current arbitrage opportunities

## 🔧 Usage Examples

### Using curl

#### Start 24/7 Scraper
```bash
curl -X POST "https://arbitrage-api-uzg5.onrender.com/api/v1/scraper/start-24-7"
```

#### Check Scraper Status
```bash
curl -X GET "https://arbitrage-api-uzg5.onrender.com/api/v1/scraper/status"
```

#### Start Manual Scraping
```bash
curl -X POST "https://arbitrage-api-uzg5.onrender.com/api/v1/scraper/start"
```

#### Get Product Count
```bash
curl -X GET "https://arbitrage-api-uzg5.onrender.com/api/v1/products/count"
```

### Using Python requests

```python
import requests

base_url = "https://arbitrage-api-uzg5.onrender.com"

# Start 24/7 scraper
response = requests.post(f"{base_url}/api/v1/scraper/start-24-7")
print(response.json())

# Check status
response = requests.get(f"{base_url}/api/v1/scraper/status")
print(response.json())

# Get product count
response = requests.get(f"{base_url}/api/v1/products/count")
print(response.json())
```

### Using JavaScript fetch

```javascript
const baseUrl = "https://arbitrage-api-uzg5.onrender.com";

// Start 24/7 scraper
fetch(`${baseUrl}/api/v1/scraper/start-24-7`, {
  method: 'POST'
})
.then(response => response.json())
.then(data => console.log(data));

// Check status
fetch(`${baseUrl}/api/v1/scraper/status`)
.then(response => response.json())
.then(data => console.log(data));
```

## 🚨 Important Notes

1. **HTTP Methods**: 
   - Use `POST` for actions that change state (start/stop scraper)
   - Use `GET` for retrieving information (status, counts)

2. **24/7 Scraper**: 
   - Runs automatically every 15 minutes (light scraping)
   - Deep scraping every 3 hours
   - Analysis every hour

3. **Manual Scraping**: 
   - Runs once and stops
   - Good for testing or immediate needs

4. **Status Codes**:
   - `200`: Success
   - `405`: Method Not Allowed (wrong HTTP method)
   - `500`: Server Error

## 📊 Current System Status

- **Total Products**: 703
- **Scraper Status**: Active/Inactive
- **24/7 Mode**: Available
- **Database**: MongoDB Atlas
- **Notifications**: Telegram Bot

## 🔍 Troubleshooting

### "Method Not Allowed" Error
- **Cause**: Using GET instead of POST for action endpoints
- **Solution**: Use POST for `/api/v1/scraper/start-24-7` and `/api/v1/scraper/stop-24-7`

### Scraper Not Starting
- **Check**: Render logs for errors
- **Verify**: Environment variables are set
- **Test**: Use `/api/v1/scraper/test` endpoint

### No Products Found
- **Check**: Database connection
- **Verify**: Scraper is running
- **Monitor**: Render logs for scraping activity

## 📞 Support

- **API Documentation**: `https://arbitrage-api-uzg5.onrender.com/docs`
- **Health Check**: `https://arbitrage-api-uzg5.onrender.com/health`
- **GitHub**: Repository with full source code
- **Render Dashboard**: Monitor service status and logs 