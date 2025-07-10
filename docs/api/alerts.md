# Alerts API Documentation

## Overview

The Alerts API manages price alerts and arbitrage opportunities. It provides access to real-time notifications when profitable price differences are detected between MediaMarkt and Amazon, with comprehensive filtering, processing, and analytics capabilities.

**Base Path:** `/api/v1/alerts`

## Endpoints

### GET /api/v1/alerts

Get paginated list of price alerts with advanced filtering and sorting options.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number (1-based) |
| `size` | integer | 20 | Items per page (1-100) |
| `status` | string | null | Filter by alert status (pending, processed, dismissed) |
| `severity` | string | null | Filter by severity (critical, high, medium, low) |
| `min_profit` | float | null | Minimum profit amount in EUR |
| `category` | string | null | Filter by product category |
| `created_after` | datetime | null | Filter alerts created after date |
| `created_before` | datetime | null | Filter alerts created before date |
| `sort_by` | string | "created_at" | Sort field (created_at, profit_amount, severity, status) |
| `sort_order` | string | "desc" | Sort order (asc, desc) |

#### Example Request

```bash
curl -X GET "http://localhost:8000/api/v1/alerts?status=pending&min_profit=30&severity=high&sort_by=profit_amount&sort_order=desc" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### Response

```json
{
  "alerts": [
    {
      "id": 789,
      "product_id": 12345,
      "alert_type": "price_arbitrage",
      "severity": "high",
      "status": "pending",
      "profit_amount": 89.50,
      "profit_margin": 22.38,
      "mediamarkt_price": 399.99,
      "amazon_price": 489.49,
      "price_difference": 89.50,
      "message": "Significant price arbitrage opportunity detected for Samsung Galaxy S24 Ultra",
      "notification_sent": true,
      "telegram_sent": true,
      "created_at": "2024-01-15T14:30:00Z",
      "updated_at": "2024-01-15T14:30:00Z",
      "processed_at": null,
      "notes": null,
      "product": {
        "id": 12345,
        "name": "Samsung Galaxy S24 Ultra 256GB",
        "brand": "Samsung",
        "category": "Smartphones",
        "asin": "B0CMDRCZ8Q",
        "url": "https://www.mediamarkt.pt/pt/product/_samsung-galaxy-s24-ultra-256gb-1234567.html",
        "image_url": "https://assets.mmsrg.com/isr/166325/c1/-/ASSET_MMS_12345?x=960&y=960"
      }
    }
  ],
  "pagination": {
    "page": 1,
    "size": 20,
    "total": 47,
    "total_pages": 3,
    "has_next": true,
    "has_prev": false
  }
}
```

### GET /api/v1/alerts/{alert_id}

Get detailed information for a specific alert by ID.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `alert_id` | integer | Yes | Alert ID to retrieve |

#### Example Request

```bash
curl -X GET "http://localhost:8000/api/v1/alerts/789" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### Response

```json
{
  "id": 789,
  "product_id": 12345,
  "alert_type": "price_arbitrage",
  "severity": "high",
  "status": "pending",
  "profit_amount": 89.50,
  "profit_margin": 22.38,
  "mediamarkt_price": 399.99,
  "amazon_price": 489.49,
  "price_difference": 89.50,
  "message": "Significant price arbitrage opportunity detected for Samsung Galaxy S24 Ultra",
  "notification_sent": true,
  "telegram_sent": true,
  "email_sent": false,
  "created_at": "2024-01-15T14:30:00Z",
  "updated_at": "2024-01-15T14:30:00Z",
  "processed_at": null,
  "notes": null,
  "metadata": {
    "detection_method": "automated_scraping",
    "confidence_score": 0.97,
    "historical_high": false,
    "trending_product": true,
    "amazon_rank": 15,
    "mediamarkt_discount": 23.1
  },
  "product": {
    "id": 12345,
    "name": "Samsung Galaxy S24 Ultra 256GB",
    "brand": "Samsung",
    "category": "Smartphones",
    "ean": "8806095257891",
    "asin": "B0CMDRCZ8Q",
    "price": 399.99,
    "original_price": 519.99,
    "availability": "In Stock",
    "url": "https://www.mediamarkt.pt/pt/product/_samsung-galaxy-s24-ultra-256gb-1234567.html",
    "image_url": "https://assets.mmsrg.com/isr/166325/c1/-/ASSET_MMS_12345?x=960&y=960"
  }
}
```

### POST /api/v1/alerts/{alert_id}/process

Process or update the status of a specific alert.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `alert_id` | integer | Yes | Alert ID to process |

#### Request Body

```json
{
  "status": "processed",
  "notes": "Opportunity validated and order placed successfully"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `status` | string | Yes | New status (pending, processed, dismissed) |
| `notes` | string | No | Processing notes or comments |

#### Example Request

```bash
curl -X POST "http://localhost:8000/api/v1/alerts/789/process" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "processed", "notes": "Order placed - €89.50 profit secured"}'
```

#### Response

```json
{
  "message": "Alert 789 status updated to 'processed'",
  "alert": {
    "id": 789,
    "status": "processed",
    "processed_at": "2024-01-15T15:45:00Z",
    "notes": "Order placed - €89.50 profit secured",
    "updated_at": "2024-01-15T15:45:00Z"
  }
}
```

### POST /api/v1/alerts/{alert_id}/dismiss

Dismiss a specific alert (convenience endpoint).

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `alert_id` | integer | Yes | Alert ID to dismiss |
| `notes` | string | No | Optional dismissal notes |

#### Example Request

```bash
curl -X POST "http://localhost:8000/api/v1/alerts/789/dismiss?notes=Price%20changed,%20opportunity%20expired" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### Response

```json
{
  "message": "Alert 789 status updated to 'dismissed'",
  "alert": {
    "id": 789,
    "status": "dismissed",
    "processed_at": "2024-01-15T15:50:00Z",
    "notes": "Price changed, opportunity expired",
    "updated_at": "2024-01-15T15:50:00Z"
  }
}
```

### GET /api/v1/alerts/stats/summary

Get alert statistics summary for a specified time period.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | integer | 7 | Number of days for statistics (1-365) |

#### Example Request

```bash
curl -X GET "http://localhost:8000/api/v1/alerts/stats/summary?days=30" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### Response

```json
{
  "period": "30 days",
  "start_date": "2023-12-16T00:00:00Z",
  "end_date": "2024-01-15T23:59:59Z",
  "total_alerts": 284,
  "by_status": {
    "pending": 47,
    "processed": 198,
    "dismissed": 39
  },
  "by_severity": {
    "critical": 12,
    "high": 89,
    "medium": 145,
    "low": 38
  },
  "profit_metrics": {
    "total_potential": 12470.50,
    "total_realized": 8934.25,
    "average_profit": 43.89,
    "max_profit": 289.99,
    "realization_rate": 71.6
  },
  "top_categories": [
    {
      "category": "Smartphones",
      "count": 89,
      "avg_profit": 67.45
    },
    {
      "category": "Laptops",
      "count": 56,
      "avg_profit": 124.78
    }
  ],
  "processing_stats": {
    "avg_processing_time_hours": 4.2,
    "fastest_processing_minutes": 12,
    "success_rate": 83.7
  }
}
```

### GET /api/v1/alerts/top-opportunities

Get top profit opportunities with advanced filtering.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 10 | Number of opportunities (1-50) |
| `min_profit` | float | 50.0 | Minimum profit threshold |
| `status` | string | "pending" | Alert status filter |

#### Example Request

```bash
curl -X GET "http://localhost:8000/api/v1/alerts/top-opportunities?limit=5&min_profit=100" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### Response

```json
{
  "opportunities": [
    {
      "alert_id": 892,
      "product_name": "MacBook Pro M3 16-inch",
      "category": "Laptops",
      "profit_amount": 289.99,
      "profit_margin": 18.7,
      "mediamarkt_price": 1549.99,
      "amazon_price": 1839.98,
      "confidence_score": 0.98,
      "created_at": "2024-01-15T16:15:00Z",
      "urgency_level": "high"
    },
    {
      "alert_id": 895,
      "product_name": "Sony WH-1000XM5 Headphones",
      "category": "Audio",
      "profit_amount": 145.50,
      "profit_margin": 41.2,
      "mediamarkt_price": 353.00,
      "amazon_price": 498.50,
      "confidence_score": 0.95,
      "created_at": "2024-01-15T16:20:00Z",
      "urgency_level": "medium"
    }
  ],
  "summary": {
    "total_opportunities": 5,
    "total_potential_profit": 724.85,
    "avg_profit_margin": 24.8,
    "highest_profit": 289.99
  }
}
```

## Data Models

### Alert Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Unique alert identifier |
| `product_id` | integer | Associated product ID |
| `alert_type` | string | Type of alert (price_arbitrage, price_drop) |
| `severity` | string | Alert severity (critical, high, medium, low) |
| `status` | string | Alert status (pending, processed, dismissed) |
| `profit_amount` | float | Profit amount in EUR |
| `profit_margin` | float | Profit margin percentage |
| `mediamarkt_price` | float | MediaMarkt price in EUR |
| `amazon_price` | float | Amazon price in EUR |
| `price_difference` | float | Price difference in EUR |
| `message` | string | Alert message |
| `notification_sent` | boolean | Whether notification was sent |
| `telegram_sent` | boolean | Whether Telegram notification was sent |
| `email_sent` | boolean | Whether email notification was sent |
| `created_at` | datetime | Creation timestamp |
| `updated_at` | datetime | Last update timestamp |
| `processed_at` | datetime | Processing timestamp |
| `notes` | string | Processing notes |
| `metadata` | object | Additional alert metadata |
| `product` | object | Associated product object |

### Alert Severity Levels

| Level | Description | Criteria |
|-------|-------------|----------|
| `critical` | Exceptional opportunities | Profit ≥ €200 or margin ≥ 50% |
| `high` | High-value opportunities | Profit ≥ €75 or margin ≥ 30% |
| `medium` | Good opportunities | Profit ≥ €30 or margin ≥ 15% |
| `low` | Minor opportunities | Profit ≥ €10 or margin ≥ 5% |

### Alert Status Flow

```
pending → processed (successful execution)
       → dismissed (opportunity expired/rejected)
```

## Error Responses

### 404 Not Found
```json
{
  "error": {
    "type": "HTTPException",
    "message": "Alert with ID 789 not found",
    "status_code": 404
  }
}
```

### 400 Bad Request
```json
{
  "error": {
    "type": "HTTPException",
    "message": "Invalid status 'invalid_status'. Must be one of: pending, processed, dismissed",
    "status_code": 400
  }
}
```

## Webhook Integration

Set up webhooks to receive real-time alert notifications:

```bash
# Configure webhook endpoint
curl -X POST "http://localhost:8000/api/v1/webhooks/alerts" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-app.com/webhook/alerts", "secret": "your_secret"}'
```

Webhook payload example:
```json
{
  "event": "alert.created",
  "timestamp": "2024-01-15T16:30:00Z",
  "data": {
    "alert_id": 901,
    "profit_amount": 156.75,
    "product_name": "iPad Pro 12.9-inch",
    "urgency": "high"
  }
}
```

## Common Use Cases

### 1. Monitor High-Value Opportunities
```bash
# Get alerts with profits above €100
curl -X GET "http://localhost:8000/api/v1/alerts?min_profit=100&status=pending&sort_by=profit_amount&sort_order=desc" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 2. Process Multiple Alerts
```bash
# Process alert as successful
curl -X POST "http://localhost:8000/api/v1/alerts/789/process" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "processed", "notes": "Order placed successfully"}'
```

### 3. Daily Performance Review
```bash
# Get daily alert statistics
curl -X GET "http://localhost:8000/api/v1/alerts/stats/summary?days=1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. Category Analysis
```bash
# Analyze electronics alerts
curl -X GET "http://localhost:8000/api/v1/alerts?category=electronics&created_after=2024-01-01" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Real-time Features

- **Live Updates**: WebSocket connection for real-time alert notifications
- **Push Notifications**: Telegram and email alerts for high-value opportunities
- **Auto-Processing**: Configurable rules for automatic alert processing
- **Smart Filtering**: AI-powered opportunity scoring and prioritization

## Performance Notes

- Alert data is updated in real-time as new opportunities are detected
- Historical statistics are cached for 15 minutes
- Complex queries may require additional processing time
- Rate limiting applies to all endpoints

---

**Last Updated:** January 2024 