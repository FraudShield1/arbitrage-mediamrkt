# Statistics API Documentation

## Overview

The Statistics API provides comprehensive system metrics, analytics, and performance data for the Cross-Market Arbitrage Tool. It offers insights into scraping operations, profit opportunities, trend analysis, and category breakdowns.

**Base Path:** `/api/v1/stats`

## Endpoints

### GET /api/v1/stats

Get comprehensive system statistics and metrics.

#### Example Request

```bash
curl -X GET "http://localhost:8000/api/v1/stats" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### Response

```json
{
  "timestamp": "2024-01-15T16:30:00Z",
  "products": {
    "total": 15247,
    "today": 342,
    "yesterday": 298,
    "growth_rate": 14.77,
    "with_asin": 8934,
    "in_stock": 12845,
    "match_rate": 58.6,
    "stock_rate": 84.2
  },
  "alerts": {
    "total": 2847,
    "active": 156,
    "today": 47,
    "yesterday": 39,
    "growth_rate": 20.51,
    "high_value": 23,
    "alert_rate": 18.9
  },
  "profit_metrics": {
    "total_potential": 45672.50,
    "average_profit": 52.34,
    "max_profit": 289.99,
    "high_value_count": 23
  },
  "top_categories": [
    {
      "_id": "Smartphones",
      "count": 2847,
      "avg_price": 456.78
    },
    {
      "_id": "Laptops", 
      "count": 1923,
      "avg_price": 1247.89
    },
    {
      "_id": "Headphones",
      "count": 1456,
      "avg_price": 189.34
    }
  ],
  "system_health": {
    "database_type": "mongodb",
    "collections": 4,
    "uptime_hours": 24,
    "last_scrape": "recent"
  }
}
```

### GET /api/v1/stats/trends

Get trend analysis for a specified time period.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | integer | 7 | Number of days for trend analysis (1-30) |

#### Example Request

```bash
curl -X GET "http://localhost:8000/api/v1/stats/trends?days=14" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### Response

```json
{
  "period": "14 days",
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-01-15T23:59:59Z",
  "product_trends": [
    {
      "_id": {
        "year": 2024,
        "month": 1,
        "day": 14
      },
      "count": 342,
      "avg_price": 287.45
    },
    {
      "_id": {
        "year": 2024,
        "month": 1,
        "day": 15
      },
      "count": 378,
      "avg_price": 294.12
    }
  ],
  "alert_trends": [
    {
      "_id": {
        "year": 2024,
        "month": 1,
        "day": 14
      },
      "count": 39,
      "avg_profit": 48.23
    },
    {
      "_id": {
        "year": 2024,
        "month": 1,
        "day": 15
      },
      "count": 47,
      "avg_profit": 52.67
    }
  ],
  "summary": {
    "total_products": 4892,
    "total_alerts": 634,
    "avg_daily_products": 349.4,
    "avg_daily_alerts": 45.3,
    "growth_trend": "positive",
    "best_day": "2024-01-15",
    "peak_alerts": 47
  }
}
```

### GET /api/v1/stats/categories

Get statistics broken down by product categories.

#### Example Request

```bash
curl -X GET "http://localhost:8000/api/v1/stats/categories" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### Response

```json
{
  "timestamp": "2024-01-15T16:30:00Z",
  "total_categories": 12,
  "categories": [
    {
      "_id": "Smartphones",
      "total_products": 2847,
      "avg_price": 456.78,
      "min_price": 89.99,
      "max_price": 1899.99,
      "in_stock": 2398,
      "stock_rate": 84.2,
      "with_asin": 1734,
      "asin_rate": 60.9,
      "total_alerts": 387,
      "avg_profit": 67.45,
      "profit_opportunities": 89
    },
    {
      "_id": "Laptops",
      "total_products": 1923,
      "avg_price": 1247.89,
      "min_price": 299.99,
      "max_price": 4999.99,
      "in_stock": 1587,
      "stock_rate": 82.5,
      "with_asin": 1345,
      "asin_rate": 69.9,
      "total_alerts": 234,
      "avg_profit": 124.78,
      "profit_opportunities": 56
    },
    {
      "_id": "Headphones",
      "total_products": 1456,
      "avg_price": 189.34,
      "min_price": 19.99,
      "max_price": 799.99,
      "in_stock": 1234,
      "stock_rate": 84.7,
      "with_asin": 998,
      "asin_rate": 68.5,
      "total_alerts": 156,
      "avg_profit": 34.23,
      "profit_opportunities": 34
    }
  ],
  "summary": {
    "most_profitable_category": "Laptops",
    "highest_volume_category": "Smartphones",
    "best_stock_rate": "Headphones",
    "best_asin_match_rate": "Laptops"
  }
}
```

### GET /api/v1/stats/scraping

Get detailed scraping operation statistics.

#### Example Request

```bash
curl -X GET "http://localhost:8000/api/v1/stats/scraping" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### Response

```json
{
  "timestamp": "2024-01-15T16:30:00Z",
  "current_session": {
    "session_id": "session_20240115_163000",
    "status": "active",
    "started_at": "2024-01-15T16:00:00Z",
    "products_scraped": 342,
    "target_count": 500,
    "progress": 68.4,
    "success_rate": 97.2,
    "avg_processing_time": 2.3,
    "errors": 10
  },
  "daily_stats": {
    "total_sessions": 8,
    "total_products": 3876,
    "successful_scrapes": 3756,
    "failed_scrapes": 120,
    "success_rate": 96.9,
    "avg_session_duration": 24.5,
    "new_products": 124,
    "updated_products": 3752,
    "duplicates_found": 89
  },
  "performance_metrics": {
    "requests_per_minute": 25.4,
    "avg_response_time_ms": 1247,
    "timeout_rate": 2.1,
    "retry_rate": 5.3,
    "quality_score": 0.94
  },
  "recent_sessions": [
    {
      "session_id": "session_20240115_120000",
      "started_at": "2024-01-15T12:00:00Z",
      "ended_at": "2024-01-15T12:23:45Z",
      "duration_minutes": 23.75,
      "products_scraped": 500,
      "success_rate": 98.2,
      "status": "completed"
    },
    {
      "session_id": "session_20240115_080000",
      "started_at": "2024-01-15T08:00:00Z",
      "ended_at": "2024-01-15T08:21:12Z",
      "duration_minutes": 21.2,
      "products_scraped": 500,
      "success_rate": 97.8,
      "status": "completed"
    }
  ],
  "alerts_generated": {
    "today": 47,
    "this_session": 12,
    "high_value_alerts": 5,
    "total_potential_profit": 1247.56
  }
}
```

## Data Models

### System Statistics Object

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | datetime | Statistics generation timestamp |
| `products` | object | Product-related metrics |
| `alerts` | object | Alert-related metrics |
| `profit_metrics` | object | Profit analysis data |
| `top_categories` | array | Top product categories |
| `system_health` | object | System health indicators |

### Product Metrics

| Field | Type | Description |
|-------|------|-------------|
| `total` | integer | Total products in database |
| `today` | integer | Products updated today |
| `yesterday` | integer | Products updated yesterday |
| `growth_rate` | float | Day-over-day growth percentage |
| `with_asin` | integer | Products with Amazon ASIN matches |
| `in_stock` | integer | Products currently in stock |
| `match_rate` | float | ASIN match rate percentage |
| `stock_rate` | float | In-stock rate percentage |

### Alert Metrics

| Field | Type | Description |
|-------|------|-------------|
| `total` | integer | Total alerts generated |
| `active` | integer | Currently active alerts |
| `today` | integer | Alerts generated today |
| `yesterday` | integer | Alerts generated yesterday |
| `growth_rate` | float | Day-over-day growth percentage |
| `high_value` | integer | High-value alerts (>€50 profit) |
| `alert_rate` | float | Alert generation rate per product |

### Profit Metrics

| Field | Type | Description |
|-------|------|-------------|
| `total_potential` | float | Total potential profit across all alerts |
| `average_profit` | float | Average profit per alert |
| `max_profit` | float | Maximum profit opportunity |
| `high_value_count` | integer | Count of high-value opportunities |

### Category Statistics

| Field | Type | Description |
|-------|------|-------------|
| `_id` | string | Category name |
| `total_products` | integer | Products in category |
| `avg_price` | float | Average price in category |
| `min_price` | float | Minimum price in category |
| `max_price` | float | Maximum price in category |
| `in_stock` | integer | In-stock products |
| `stock_rate` | float | Stock availability rate |
| `with_asin` | integer | Products with ASIN matches |
| `asin_rate` | float | ASIN match rate |
| `total_alerts` | integer | Total alerts generated |
| `avg_profit` | float | Average profit per alert |
| `profit_opportunities` | integer | Current profit opportunities |

### Scraping Statistics

| Field | Type | Description |
|-------|------|-------------|
| `current_session` | object | Active scraping session data |
| `daily_stats` | object | Daily aggregated statistics |
| `performance_metrics` | object | Performance and quality metrics |
| `recent_sessions` | array | Recent completed sessions |
| `alerts_generated` | object | Alert generation statistics |

## Analytics Endpoints

### GET /api/v1/stats/performance

Get system performance analytics.

```bash
curl -X GET "http://localhost:8000/api/v1/stats/performance?hours=24" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### GET /api/v1/stats/profits

Get detailed profit analysis.

```bash
curl -X GET "http://localhost:8000/api/v1/stats/profits?period=weekly" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### GET /api/v1/stats/comparison

Compare current period with previous period.

```bash
curl -X GET "http://localhost:8000/api/v1/stats/comparison?days=7" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Error Responses

### 400 Bad Request
```json
{
  "error": {
    "type": "HTTPException",
    "message": "Invalid days parameter: must be between 1 and 30",
    "status_code": 400
  }
}
```

### 500 Internal Server Error
```json
{
  "error": {
    "type": "HTTPException",
    "message": "Error retrieving system statistics: Database connection failed",
    "status_code": 500
  }
}
```

## Usage Examples

### Dashboard Integration

```javascript
// Fetch and display system overview
async function loadDashboard() {
  const response = await fetch('/api/v1/stats', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  const stats = await response.json();
  
  // Update dashboard metrics
  updateMetric('total-products', stats.products.total);
  updateMetric('active-alerts', stats.alerts.active);
  updateMetric('total-profit', stats.profit_metrics.total_potential);
  
  // Load trend chart
  const trends = await fetch('/api/v1/stats/trends?days=7');
  renderTrendChart(await trends.json());
}
```

### Monitoring and Alerting

```bash
#!/bin/bash
# System monitoring script

# Get current stats
STATS=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/stats")

# Extract metrics
PRODUCTS_TODAY=$(echo $STATS | jq '.products.today')
ALERTS_TODAY=$(echo $STATS | jq '.alerts.today')
SUCCESS_RATE=$(echo $STATS | jq '.scraping.daily_stats.success_rate')

# Alert conditions
if [ $PRODUCTS_TODAY -lt 100 ]; then
  echo "WARNING: Low product scraping today: $PRODUCTS_TODAY"
fi

if [ $(echo "$SUCCESS_RATE < 95" | bc) -eq 1 ]; then
  echo "WARNING: Low success rate: $SUCCESS_RATE%"
fi
```

### Performance Analysis

```python
import requests
import pandas as pd
import matplotlib.pyplot as plt

# Fetch trend data
response = requests.get(
    'http://localhost:8000/api/v1/stats/trends?days=30',
    headers={'Authorization': f'Bearer {token}'}
)

trends = response.json()

# Create DataFrame for analysis
df = pd.DataFrame(trends['product_trends'])
df['date'] = pd.to_datetime(df['_id'].apply(
    lambda x: f"{x['year']}-{x['month']:02d}-{x['day']:02d}"
))

# Plot trends
plt.figure(figsize=(12, 6))
plt.plot(df['date'], df['count'], label='Products Scraped')
plt.plot(df['date'], df['avg_price'], label='Average Price')
plt.legend()
plt.title('30-Day Product Scraping Trends')
plt.show()
```

## Real-time Updates

Statistics are updated in real-time as the system operates:

- **Product stats**: Updated every 5 minutes during scraping
- **Alert metrics**: Updated immediately when alerts are generated
- **Profit calculations**: Recalculated every 15 minutes
- **Category breakdowns**: Updated every 30 minutes
- **Performance metrics**: Updated every minute during active scraping

## Caching and Performance

- Statistics responses are cached for 5 minutes
- Complex aggregations use MongoDB aggregation pipeline
- Trend analysis is optimized with indexed date queries
- Large datasets are paginated automatically

---

**Last Updated:** January 2024 