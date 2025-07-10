# Cross-Market Arbitrage Tool API Documentation

## Overview

The Cross-Market Arbitrage Tool API provides comprehensive access to arbitrage opportunities, product data, price alerts, and system statistics. The API is built with FastAPI and includes authentication, real-time monitoring, and extensive filtering capabilities.

**Base URL:** `http://localhost:8000/api/v1`  
**API Version:** 1.0.0  
**Documentation:** `http://localhost:8000/docs` (Swagger UI)  
**Status:** Production Ready

## Quick Start

### Authentication
All endpoints except health checks require JWT authentication:

```bash
# Login to get access token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'

# Use token in subsequent requests
curl -X GET "http://localhost:8000/api/v1/products" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Basic Usage Examples

```bash
# Get system statistics
curl -X GET "http://localhost:8000/api/v1/stats" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get products with profit opportunities
curl -X GET "http://localhost:8000/api/v1/products?has_asin=true&min_discount=20" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get active price alerts
curl -X GET "http://localhost:8000/api/v1/alerts?status=active&min_profit=30" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## API Endpoints Overview

### 📊 System & Health
- `GET /health` - Basic health check (no auth required)
- `GET /api/v1/health/` - Detailed health status
- `GET /api/v1/health/live` - Kubernetes liveness probe
- `GET /api/v1/health/ready` - Kubernetes readiness probe
- `GET /api/v1/stats` - System statistics and metrics
- `GET /api/v1/stats/trends` - Trend analysis
- `GET /api/v1/stats/categories` - Category statistics

### 🛍️ Products
- `GET /api/v1/products` - List products with filtering
- `GET /api/v1/products/{id}` - Get specific product details

### 🚨 Alerts
- `GET /api/v1/alerts` - List price alerts with filtering
- `GET /api/v1/alerts/{id}` - Get specific alert details
- `POST /api/v1/alerts/{id}/process` - Process/update alert status
- `POST /api/v1/alerts/{id}/dismiss` - Dismiss alert
- `GET /api/v1/alerts/stats/summary` - Alert statistics
- `GET /api/v1/alerts/top-opportunities` - Top profit opportunities

### 🔐 Authentication
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/register` - Register new user (admin only)
- `POST /api/v1/auth/refresh` - Refresh access token
- `GET /api/v1/auth/me` - Get current user info
- `PUT /api/v1/auth/me` - Update current user
- `POST /api/v1/auth/change-password` - Change password
- `GET /api/v1/auth/users` - List all users (admin only)
- `GET /api/v1/auth/users/{id}` - Get user by ID (admin only)
- `PUT /api/v1/auth/users/{id}` - Update user (admin only)
- `DELETE /api/v1/auth/users/{id}` - Delete user (admin only)

## Response Format

All API responses follow a consistent format:

### Success Response
```json
{
  "data": { ... },
  "pagination": { ... }, // For paginated responses
  "message": "Success"
}
```

### Error Response
```json
{
  "error": {
    "type": "ValidationError",
    "message": "Request validation failed",
    "details": [ ... ]
  }
}
```

## Pagination

Paginated endpoints support these parameters:
- `page`: Page number (1-based, default: 1)
- `size`: Items per page (1-100, default: 20)

Response includes pagination metadata:
```json
{
  "pagination": {
    "page": 1,
    "size": 20,
    "total": 150,
    "total_pages": 8,
    "has_next": true,
    "has_prev": false
  }
}
```

## Error Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 409 | Conflict |
| 422 | Validation Error |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

## Rate Limiting

API requests are rate-limited to 100 requests per minute per user. Rate limit headers are included in responses:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## WebSocket Support

Real-time updates are available via WebSocket connections:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/alerts');
ws.onmessage = function(event) {
    const alert = JSON.parse(event.data);
    console.log('New alert:', alert);
};
```

## Data Models

### Product
```json
{
  "id": 123,
  "name": "Product Name",
  "brand": "Brand Name",
  "category": "Electronics",
  "ean": "1234567890123",
  "asin": "B08XYZ123",
  "price": 299.99,
  "original_price": 399.99,
  "discount_percentage": 25.0,
  "availability": "In Stock",
  "url": "https://mediamarkt.pt/...",
  "image_url": "https://...",
  "last_updated": "2024-01-15T10:30:00Z",
  "created_at": "2024-01-10T08:00:00Z"
}
```

### Price Alert
```json
{
  "id": 456,
  "product_id": 123,
  "alert_type": "price_drop",
  "severity": "high",
  "status": "active",
  "profit_amount": 45.50,
  "profit_margin": 18.2,
  "mediamarkt_price": 249.99,
  "amazon_price": 295.49,
  "price_difference": 45.50,
  "message": "Significant price arbitrage opportunity detected",
  "created_at": "2024-01-15T10:30:00Z",
  "product": { ... } // Full product object
}
```

## Advanced Features

### Filtering Products
```bash
# Complex product filtering
curl -X GET "http://localhost:8000/api/v1/products?category=smartphones&min_price=200&max_price=800&has_asin=true&sort_by=discount_percentage&sort_order=desc" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Alert Management
```bash
# Process an alert
curl -X POST "http://localhost:8000/api/v1/alerts/123/process" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "processed", "notes": "Opportunity validated and executed"}'
```

### System Monitoring
```bash
# Get comprehensive health status
curl -X GET "http://localhost:8000/api/v1/health/detailed" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get trend analysis
curl -X GET "http://localhost:8000/api/v1/stats/trends?days=30" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## SDK and Client Libraries

Official client libraries are available for:
- Python: `pip install arbitrage-api-client`
- JavaScript/Node.js: `npm install arbitrage-api-client`
- PHP: `composer require arbitrage/api-client`

## Support

- **API Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **GitHub Issues:** [Repository Issues](https://github.com/your-repo/issues)
- **API Status:** [http://localhost:8000/health](http://localhost:8000/health)

---

**Last Updated:** January 2024  
**API Version:** 1.0.0 