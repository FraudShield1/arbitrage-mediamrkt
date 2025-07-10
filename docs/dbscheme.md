# Database Schema

## Overview

This document defines the MongoDB database schema for the Cross-Market Arbitrage Tool, ensuring data integrity, performance, and scalability. The system uses **MongoDB Atlas** as the primary database.

## Database Configuration

- **Database Type**: MongoDB Atlas
- **Database Name**: `arbitrage_tool`
- **Connection**: TLS-enabled with connection pooling
- **Indexes**: Optimized for query performance

## Collections Schema

### products

Stores scraped product data from MediaMarkt with comprehensive metadata.

```javascript
{
  "_id": ObjectId("..."),
  "title": String,                    // Product title (max 500 chars)
  "price": Number,                    // Current price (decimal)
  "original_price": Number,           // Price before discount (optional)
  "discount_percentage": Number,      // Discount percentage (optional)
  "ean": String,                      // European Article Number (optional)
  "asin": String,                     // Amazon ASIN if found (optional)
  "brand": String,                    // Product brand (optional)
  "category": String,                 // Product category
  "availability": String,             // Stock status
  "has_discount": Boolean,            // Whether product has discount
  "url": String,                      // MediaMarkt product URL
  "scraped_at": Date,                 // When product was scraped
  "source": String,                   // Always "mediamarkt"
  "business_grade": Boolean,          // Quality indicator
  "quality_grade": String,            // Quality grade (A, B, C)
  "profit_potential_score": Number,   // Calculated profit score
  "product_fingerprint": String,      // Unique product identifier
  "scraping_session": {
    "timestamp": Date,
    "scraper_version": String
  },
  "monitoring_data": {               // For 24/7 monitoring
    "discovery_cycle": Number,
    "discovery_timestamp": Date,
    "last_seen_cycle": Number,
    "price_history": Array,          // Last 10 price points
    "first_seen_price": Number
  },
  "quality_indicators": Object       // Scraping quality metrics
}
```

### price_alerts

Stores arbitrage opportunities and profit alerts.

```javascript
{
  "_id": ObjectId("..."),
  "product_id": String,              // Reference to product
  "asin": String,                    // Amazon ASIN
  "title": String,                   // Product title
  "current_price": Number,           // Current MediaMarkt price
  "amazon_price": Number,            // Current Amazon price
  "profit_amount": Number,           // Estimated profit
  "profit_percentage": Number,       // Profit margin percentage
  "confidence_score": Number,        // Match confidence (0-1)
  "severity": String,                // critical, high, medium, low
  "status": String,                  // active, processed, dismissed
  "created_at": Date,                // Alert creation time
  "processed_at": Date,              // When alert was processed (optional)
  "notifications_sent": Number,      // Number of notifications sent
  "opportunity_score": Number        // Business opportunity score
}
```

### keepa_data

Stores historical price data from Keepa API for Amazon products.

```javascript
{
  "_id": ObjectId("..."),
  "asin": String,                    // Amazon ASIN (primary key)
  "marketplace": String,             // Amazon marketplace (e.g., "DE", "FR")
  "title": String,                   // Product title from Amazon
  "brand": String,                   // Product brand
  "category": String,                // Amazon category
  "price_history": Array,            // Historical price data
  "sales_rank_history": Array,       // Sales rank data (optional)
  "stats": Object,                   // Keepa statistics
  "current_price": Number,           // Latest price
  "avg_price": Number,               // Average price
  "updated_at": Date,                // Last update timestamp
  "timestamp": Date                  // Data collection timestamp
}
```

### scraping_sessions

Tracks scraping run status and performance metrics.

```javascript
{
  "_id": ObjectId("..."),
  "session_id": String,              // Unique session identifier
  "source": String,                  // "mediamarkt"
  "started_at": Date,                // Session start time
  "completed_at": Date,              // Session completion time (optional)
  "status": String,                  // running, completed, failed
  "products_scraped": Number,        // Number of products scraped
  "products_new": Number,            // New products found
  "products_updated": Number,        // Existing products updated
  "errors_count": Number,            // Number of errors encountered
  "error_details": Array,            // Error details
  "performance_metrics": {
    "pages_processed": Number,
    "avg_page_time": Number,
    "total_duration": Number
  }
}
```

## Database Indexes

### products Collection Indexes

```javascript
// ASIN index (unique, partial - only for non-null ASINs)
db.products.createIndex(
  { "asin": 1 }, 
  { 
    unique: true, 
    partialFilterExpression: { 
      "asin": { "$exists": true, "$type": "string" } 
    } 
  }
)

// Performance indexes
db.products.createIndex({ "ean": 1 })
db.products.createIndex({ "title": 1 })
db.products.createIndex({ "category": 1, "subcategory": 1 })
db.products.createIndex({ "scraped_at": -1 })
db.products.createIndex({ "price": 1 })
db.products.createIndex({ "brand": 1 })
db.products.createIndex({ "product_fingerprint": 1 })
```

### price_alerts Collection Indexes

```javascript
db.price_alerts.createIndex({ "product_id": 1 })
db.price_alerts.createIndex({ "asin": 1 })
db.price_alerts.createIndex({ "status": 1, "created_at": -1 })
db.price_alerts.createIndex({ "severity": 1 })
db.price_alerts.createIndex({ "profit_amount": -1 })
db.price_alerts.createIndex({ "created_at": -1 })
```

### keepa_data Collection Indexes

```javascript
db.keepa_data.createIndex({ "asin": 1 }, { unique: true })
db.keepa_data.createIndex({ "marketplace": 1 })
db.keepa_data.createIndex({ "updated_at": -1 })
db.keepa_data.createIndex({ "timestamp": -1 })
```

### scraping_sessions Collection Indexes

```javascript
db.scraping_sessions.createIndex({ "session_id": 1 }, { unique: true })
db.scraping_sessions.createIndex({ "status": 1 })
db.scraping_sessions.createIndex({ "started_at": -1 })
db.scraping_sessions.createIndex({ "source": 1 })
```

## Data Integrity Rules

### Product Data Validation

- `title` is required (non-empty string)
- `price` must be positive number
- `discount_percentage` must be between 0-100 if present
- `ean` must be valid EAN format if present
- `asin` must be valid Amazon ASIN format if present

### Price Alert Validation

- `profit_amount` must be positive
- `confidence_score` must be between 0-1
- `severity` must be one of: critical, high, medium, low
- `status` must be one of: active, processed, dismissed

### Data Relationships

- `price_alerts.product_id` references `products._id`
- `price_alerts.asin` should match `keepa_data.asin`
- `scraping_sessions.session_id` is unique across all sessions

## Data Retention Policy

- **products**: Retain for 90 days, auto-cleanup old records
- **price_alerts**: Retain for 180 days, archive processed alerts
- **keepa_data**: Retain for 1 year for trend analysis
- **scraping_sessions**: Retain for 30 days for debugging

## Performance Optimizations

### Query Optimization

- Use compound indexes for multi-field queries
- Implement proper sorting with indexed fields
- Use aggregation pipelines for complex analytics

### Connection Management

- Connection pooling (max 10 connections)
- TLS encryption enabled
- Automatic retry on connection failures

### Storage Optimization

- Remove large binary fields (images stored separately)
- Use lean documents for better performance
- Implement field projection for large datasets

## Migration from PostgreSQL

This schema replaces the previous PostgreSQL implementation:

- **UUID fields** → **ObjectId** (MongoDB native)
- **JSONB columns** → **Native objects** (MongoDB native)
- **Foreign keys** → **Reference fields** (manual integrity)
- **SQL queries** → **MongoDB aggregation pipelines**

## Related Documentation

- **[Technology Choices](technology-choices.md)**: MongoDB selection rationale
- **[Setup Guide](setup-guide.md)**: Database configuration
- **[Troubleshooting](troubleshooting.md)**: Common database issues
