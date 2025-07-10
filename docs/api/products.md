# Products API Documentation

## Overview

The Products API provides access to scraped MediaMarkt product data with comprehensive filtering, searching, and sorting capabilities. Products include price information, availability status, and Amazon ASIN matching for arbitrage opportunities.

**Base Path:** `/api/v1/products`

## Endpoints

### GET /api/v1/products

Get paginated list of products with advanced filtering and sorting options.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number (1-based) |
| `size` | integer | 20 | Items per page (1-100) |
| `category` | string | null | Filter by product category |
| `brand` | string | null | Filter by brand name |
| `min_price` | float | null | Minimum price filter (€) |
| `max_price` | float | null | Maximum price filter (€) |
| `min_discount` | float | null | Minimum discount percentage (0-100) |
| `in_stock` | boolean | null | Filter by stock availability |
| `has_asin` | boolean | null | Filter products with/without ASIN |
| `search` | string | null | Search in product names |
| `sort_by` | string | "created_at" | Sort field (created_at, current_price, discount_percentage, name, brand) |
| `sort_order` | string | "desc" | Sort order (asc, desc) |

#### Example Request

```bash
curl -X GET "http://localhost:8000/api/v1/products?category=smartphones&min_price=200&max_price=800&has_asin=true&sort_by=discount_percentage&sort_order=desc&page=1&size=20" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### Response

```json
{
  "products": [
    {
      "id": 12345,
      "name": "Samsung Galaxy S24 Ultra 256GB",
      "brand": "Samsung",
      "category": "Smartphones",
      "ean": "8806095257891",
      "asin": "B0CMDRCZ8Q",
      "price": 799.99,
      "original_price": 1299.99,
      "discount_percentage": 38.46,
      "availability": "In Stock",
      "url": "https://www.mediamarkt.pt/pt/product/_samsung-galaxy-s24-ultra-256gb-1234567.html",
      "image_url": "https://assets.mmsrg.com/isr/166325/c1/-/ASSET_MMS_12345?x=960&y=960",
      "description": "Latest flagship smartphone with AI features",
      "specs": {
        "storage": "256GB",
        "color": "Titanium Black",
        "screen_size": "6.8\""
      },
      "quality_score": 0.95,
      "last_updated": "2024-01-15T10:30:00Z",
      "created_at": "2024-01-10T08:00:00Z",
      "asin_matches": [
        {
          "asin": "B0CMDRCZ8Q",
          "confidence": 0.98,
          "match_type": "EAN",
          "last_checked": "2024-01-15T10:30:00Z"
        }
      ]
    }
  ],
  "pagination": {
    "page": 1,
    "size": 20,
    "total": 245,
    "total_pages": 13,
    "has_next": true,
    "has_prev": false
  }
}
```

### GET /api/v1/products/{product_id}

Get detailed information for a specific product by ID.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `product_id` | integer | Yes | Product ID to retrieve |

#### Example Request

```bash
curl -X GET "http://localhost:8000/api/v1/products/12345" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### Response

```json
{
  "id": 12345,
  "name": "Samsung Galaxy S24 Ultra 256GB",
  "brand": "Samsung",
  "category": "Smartphones", 
  "ean": "8806095257891",
  "asin": "B0CMDRCZ8Q",
  "price": 799.99,
  "original_price": 1299.99,
  "discount_percentage": 38.46,
  "availability": "In Stock",
  "url": "https://www.mediamarkt.pt/pt/product/_samsung-galaxy-s24-ultra-256gb-1234567.html",
  "image_url": "https://assets.mmsrg.com/isr/166325/c1/-/ASSET_MMS_12345?x=960&y=960",
  "description": "Latest flagship smartphone with advanced AI features and S Pen functionality",
  "specs": {
    "storage": "256GB",
    "color": "Titanium Black", 
    "screen_size": "6.8\"",
    "camera": "200MP main camera",
    "battery": "5000mAh",
    "ram": "12GB"
  },
  "quality_score": 0.95,
  "last_scraped": "2024-01-15T10:30:00Z",
  "last_updated": "2024-01-15T10:30:00Z",
  "created_at": "2024-01-10T08:00:00Z",
  "price_history": [
    {
      "price": 1299.99,
      "date": "2024-01-10T08:00:00Z"
    },
    {
      "price": 999.99,
      "date": "2024-01-12T12:00:00Z"
    },
    {
      "price": 799.99,
      "date": "2024-01-15T10:30:00Z"
    }
  ],
  "asin_matches": [
    {
      "asin": "B0CMDRCZ8Q",
      "confidence": 0.98,
      "match_type": "EAN",
      "source": "keepa_api",
      "last_checked": "2024-01-15T10:30:00Z",
      "amazon_data": {
        "title": "Samsung Galaxy S24 Ultra, 256GB, Titanium Black",
        "price_eur": 899.99,
        "availability": "In Stock",
        "rating": 4.5,
        "review_count": 1247
      }
    }
  ]
}
```

## Data Models

### Product Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Unique product identifier |
| `name` | string | Product name |
| `brand` | string | Brand name |
| `category` | string | Product category |
| `ean` | string | European Article Number (barcode) |
| `asin` | string | Amazon Standard Identification Number |
| `price` | float | Current price in EUR |
| `original_price` | float | Original/MSRP price in EUR |
| `discount_percentage` | float | Discount percentage (0-100) |
| `availability` | string | Stock status ("In Stock", "Out of Stock", "Limited") |
| `url` | string | MediaMarkt product URL |
| `image_url` | string | Product image URL |
| `description` | string | Product description |
| `specs` | object | Product specifications |
| `quality_score` | float | Data quality score (0-1) |
| `last_scraped` | datetime | Last scraping timestamp |
| `last_updated` | datetime | Last update timestamp |
| `created_at` | datetime | Creation timestamp |
| `price_history` | array | Historical price data |
| `asin_matches` | array | Amazon ASIN matching data |

### ASIN Match Object

| Field | Type | Description |
|-------|------|-------------|
| `asin` | string | Amazon ASIN |
| `confidence` | float | Match confidence (0-1) |
| `match_type` | string | Type of match (EAN, fuzzy, semantic) |
| `source` | string | Data source (keepa_api, manual) |
| `last_checked` | datetime | Last verification timestamp |
| `amazon_data` | object | Amazon product data |

## Error Responses

### 404 Not Found
```json
{
  "error": {
    "type": "HTTPException",
    "message": "Product with ID 12345 not found",
    "status_code": 404
  }
}
```

### 422 Validation Error
```json
{
  "error": {
    "type": "ValidationError",
    "message": "Request validation failed",
    "details": [
      {
        "loc": ["query", "min_price"],
        "msg": "ensure this value is greater than or equal to 0",
        "type": "value_error.number.not_ge"
      }
    ]
  }
}
```

## Common Use Cases

### 1. Find Arbitrage Opportunities
```bash
# Products with ASIN matches and high discounts
curl -X GET "http://localhost:8000/api/v1/products?has_asin=true&min_discount=25&sort_by=discount_percentage&sort_order=desc" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 2. Monitor Specific Categories
```bash
# All electronics under €500
curl -X GET "http://localhost:8000/api/v1/products?category=electronics&max_price=500&in_stock=true" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. Brand Analysis
```bash
# All Samsung products with discounts
curl -X GET "http://localhost:8000/api/v1/products?brand=samsung&min_discount=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. Search Products
```bash
# Search for iPhone products
curl -X GET "http://localhost:8000/api/v1/products?search=iphone&sort_by=price&sort_order=asc" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Performance Notes

- Responses are cached for 5 minutes for optimal performance
- Use pagination to handle large result sets efficiently
- Complex filters may take longer to process
- ASIN matching data is updated every 24 hours

## Rate Limits

- 100 requests per minute per user
- Burst allowance of 20 requests per 10 seconds
- Rate limit headers included in all responses

---

**Last Updated:** January 2024 