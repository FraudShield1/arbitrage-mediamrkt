"""
System Statistics API Endpoints

Endpoints for retrieving system-wide metrics and performance statistics.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.config.database import get_db_session

router = APIRouter()


@router.get("/")
async def get_system_stats(
    db: AsyncIOMotorDatabase = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Get comprehensive system statistics and metrics.
    
    Args:
        db: Database connection
        
    Returns:
        System statistics including products, alerts, and performance metrics
    """
    try:
        # Get current time for calculations
        now = datetime.utcnow()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Products statistics
        products_collection = db.products
        total_products = await products_collection.count_documents({})
        
        products_today = await products_collection.count_documents({
            "last_updated": {"$gte": today}
        })
        
        products_with_asin = await products_collection.count_documents({
            "asin": {"$ne": None, "$exists": True}
        })
        
        in_stock_products = await products_collection.count_documents({
            "availability": {"$regex": "In Stock", "$options": "i"}
        })
        
        # Alert statistics  
        alerts_collection = db.price_alerts
        total_alerts = await alerts_collection.count_documents({})
        
        active_alerts = await alerts_collection.count_documents({
            "status": "active"
        })
        
        alerts_today = await alerts_collection.count_documents({
            "created_at": {"$gte": today}
        })
        
        high_value_alerts = await alerts_collection.count_documents({
            "profit_amount": {"$gte": 50.0},
            "status": "active"
        })
        
        # Profit statistics using aggregation pipeline
        profit_pipeline = [
            {"$match": {"status": "active", "profit_amount": {"$exists": True}}},
            {"$group": {
                "_id": None,
                "total_profit": {"$sum": "$profit_amount"},
                "avg_profit": {"$avg": "$profit_amount"},
                "max_profit": {"$max": "$profit_amount"},
                "count": {"$sum": 1}
            }}
        ]
        
        profit_stats = await alerts_collection.aggregate(profit_pipeline).to_list(1)
        if profit_stats:
            profit_data = profit_stats[0]
            total_profit_potential = profit_data.get("total_profit", 0.0)
            avg_profit = profit_data.get("avg_profit", 0.0)
            max_profit = profit_data.get("max_profit", 0.0)
        else:
            total_profit_potential = avg_profit = max_profit = 0.0
        
        # Calculate rates and percentages
        match_rate = (products_with_asin / total_products * 100) if total_products > 0 else 0.0
        stock_rate = (in_stock_products / total_products * 100) if total_products > 0 else 0.0
        alert_rate = (total_alerts / products_with_asin * 100) if products_with_asin > 0 else 0.0
        
        # Recent activity trends  
        products_yesterday = await products_collection.count_documents({
            "last_updated": {"$gte": yesterday, "$lt": today}
        })
        
        alerts_yesterday = await alerts_collection.count_documents({
            "created_at": {"$gte": yesterday, "$lt": today}
        })
        
        # Calculate growth rates
        products_growth = ((products_today - products_yesterday) / products_yesterday * 100) if products_yesterday > 0 else 0.0
        alerts_growth = ((alerts_today - alerts_yesterday) / alerts_yesterday * 100) if alerts_yesterday > 0 else 0.0
        
        # Category breakdown
        category_pipeline = [
            {"$group": {
                "_id": "$category",
                "count": {"$sum": 1},
                "avg_price": {"$avg": "$price"}
            }},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        
        categories = await products_collection.aggregate(category_pipeline).to_list(10)
        
        return {
            "timestamp": now.isoformat(),
            "products": {
                "total": total_products,
                "today": products_today,
                "yesterday": products_yesterday,
                "growth_rate": round(products_growth, 2),
                "with_asin": products_with_asin,
                "in_stock": in_stock_products,
                "match_rate": round(match_rate, 2),
                "stock_rate": round(stock_rate, 2)
            },
            "alerts": {
                "total": total_alerts,
                "active": active_alerts,
                "today": alerts_today,
                "yesterday": alerts_yesterday,
                "growth_rate": round(alerts_growth, 2),
                "high_value": high_value_alerts,
                "alert_rate": round(alert_rate, 2)
            },
            "profit_metrics": {
                "total_potential": round(float(total_profit_potential), 2),
                "average_profit": round(float(avg_profit), 2),
                "max_profit": round(float(max_profit), 2),
                "high_value_count": high_value_alerts
            },
            "top_categories": categories,
            "system_health": {
                "database_type": "mongodb",
                "collections": len(await db.list_collection_names()),
                "uptime_hours": 24,  # Placeholder
                "last_scrape": "recent"  # Placeholder
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving system statistics: {str(e)}")


@router.get("/trends")
async def get_trends(
    days: int = Query(7, ge=1, le=30, description="Number of days for trend analysis"),
    db: AsyncIOMotorDatabase = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Get trend analysis for the specified number of days.
    
    Args:
        days: Number of days for trend analysis
        db: Database connection
        
    Returns:
        Trend data for products, alerts, and profits
    """
    try:
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Daily product trends
        product_pipeline = [
            {"$match": {"last_updated": {"$gte": start_date, "$lte": end_date}}},
            {"$group": {
                "_id": {
                    "year": {"$year": "$last_updated"},
                    "month": {"$month": "$last_updated"},
                    "day": {"$dayOfMonth": "$last_updated"}
                },
                "count": {"$sum": 1},
                "avg_price": {"$avg": "$price"}
            }},
            {"$sort": {"_id": 1}}
        ]
        
        product_trends = await db.products.aggregate(product_pipeline).to_list(days)
        
        # Daily alert trends
        alert_pipeline = [
            {"$match": {"created_at": {"$gte": start_date, "$lte": end_date}}},
            {"$group": {
                "_id": {
                    "year": {"$year": "$created_at"},
                    "month": {"$month": "$created_at"},
                    "day": {"$dayOfMonth": "$created_at"}
                },
                "count": {"$sum": 1},
                "avg_profit": {"$avg": "$profit_amount"}
            }},
            {"$sort": {"_id": 1}}
        ]
        
        alert_trends = await db.price_alerts.aggregate(alert_pipeline).to_list(days)
        
        return {
            "period": f"{days} days",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "product_trends": product_trends,
            "alert_trends": alert_trends
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving trends: {str(e)}")


@router.get("/categories")
async def get_category_stats(
    db: AsyncIOMotorDatabase = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Get statistics by product categories.
    
    Args:
        db: Database connection
        
    Returns:
        Category-wise statistics
    """
    try:
        # Category breakdown with detailed stats
        pipeline = [
            {"$group": {
                "_id": "$category",
                "total_products": {"$sum": 1},
                "avg_price": {"$avg": "$price"},
                "min_price": {"$min": "$price"},
                "max_price": {"$max": "$price"},
                "in_stock": {"$sum": {"$cond": [{"$regexMatch": {"input": "$availability", "regex": "In Stock", "options": "i"}}, 1, 0]}}
            }},
            {"$sort": {"total_products": -1}}
        ]
        
        categories = await db.products.aggregate(pipeline).to_list(50)
        
        # Format the results
        for category in categories:
            if category["total_products"] > 0:
                category["stock_rate"] = round((category["in_stock"] / category["total_products"]) * 100, 2)
            else:
                category["stock_rate"] = 0.0
                
            # Round price values
            category["avg_price"] = round(float(category["avg_price"]) if category["avg_price"] else 0.0, 2)
            category["min_price"] = round(float(category["min_price"]) if category["min_price"] else 0.0, 2)
            category["max_price"] = round(float(category["max_price"]) if category["max_price"] else 0.0, 2)
        
        return {
            "categories": categories,
            "total_categories": len(categories),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving category statistics: {str(e)}")


@router.get("/scraping")
async def get_scraping_stats(
    db: AsyncIOMotorDatabase = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Get scraping performance statistics.
    
    Args:
        db: Database connection
        
    Returns:
        Scraping statistics and performance metrics
    """
    try:
        now = datetime.utcnow()
        
        # Recent scraping activity (last 24 hours)
        recent_products = await db.products.count_documents({
            "last_updated": {"$gte": now - timedelta(hours=24)}
        })
        
        # Source breakdown
        source_pipeline = [
            {"$group": {
                "_id": "$source",
                "count": {"$sum": 1},
                "latest": {"$max": "$last_updated"}
            }},
            {"$sort": {"count": -1}}
        ]
        
        sources = await db.products.aggregate(source_pipeline).to_list(10)
        
        # Performance metrics
        total_products = await db.products.count_documents({})
        
        return {
            "timestamp": now.isoformat(),
            "recent_activity": {
                "products_last_24h": recent_products,
                "scraping_rate": round(recent_products / 24, 2) if recent_products > 0 else 0.0
            },
            "sources": sources,
            "performance": {
                "total_products": total_products,
                "avg_products_per_hour": round(recent_products / 24, 2) if recent_products > 0 else 0.0,
                "uptime": "Active",  # Placeholder
                "last_successful_scrape": sources[0]["latest"].isoformat() if sources and sources[0].get("latest") else None
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving scraping statistics: {str(e)}") 