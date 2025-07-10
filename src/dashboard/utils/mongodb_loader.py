"""
MongoDB Data Loader for Dashboard

Direct MongoDB connection for dashboard to work with existing data
without requiring the API layer. Uses Streamlit session state to manage
singleton instance and caching.
"""

import streamlit as st
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
from pymongo import MongoClient
import os
import ssl
from functools import wraps

# Load environment variables explicitly
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

def get_mongodb_client():
    """Get MongoDB client from session state or create new one."""
    if 'mongodb_client' not in st.session_state:
        mongodb_uri = os.getenv('MONGODB_URL') or os.getenv('MONGODB_URI') or os.getenv('DATABASE_URL', 'mongodb://localhost:27017')
        database_name = os.getenv('MONGODB_DATABASE', 'arbitrage_tool')
        
        logger.info(f"🔗 Creating new MongoDB client for: {database_name}")
        
        if 'mongodb+srv://' in mongodb_uri or 'mongodb.net' in mongodb_uri:
            client = MongoClient(
                mongodb_uri,
                tls=True,
                tlsAllowInvalidCertificates=True,
                tlsAllowInvalidHostnames=True,
                retryWrites=True,
                w='majority',
                maxPoolSize=5,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                socketTimeoutMS=10000
            )
        else:
            client = MongoClient(mongodb_uri, maxPoolSize=5)
            
        st.session_state.mongodb_client = client
        st.session_state.mongodb_db = client[database_name]
        
        # Test connection
        st.session_state.mongodb_db.command("ping")
        logger.info("✅ MongoDB connection established successfully")
    
    return st.session_state.mongodb_client, st.session_state.mongodb_db

@st.cache_data(ttl=300)
def get_system_stats() -> Optional[Dict[str, Any]]:
    """Get system statistics from MongoDB with caching."""
    try:
        _, db = get_mongodb_client()
        
        now = datetime.utcnow()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        
        # Products statistics
        products_collection = db.products
        total_products = products_collection.count_documents({})
        
        products_today = products_collection.count_documents({
            "scraped_at": {"$gte": today}
        })
        
        products_yesterday = products_collection.count_documents({
            "scraped_at": {"$gte": yesterday, "$lt": today}
        })
        
        in_stock_products = products_collection.count_documents({
            "availability": {"$regex": "available|in stock", "$options": "i"}
        })
        
        # Alert statistics  
        alerts_collection = db.price_alerts
        total_alerts = alerts_collection.count_documents({})
        
        active_alerts = alerts_collection.count_documents({
            "status": "active"
        })
        
        alerts_today = alerts_collection.count_documents({
            "created_at": {"$gte": today}
        })
        
        # Critical alerts count
        critical_alerts = alerts_collection.count_documents({
            "status": "active",
            "severity": "critical"
        })
        
        # Calculate growth rates
        products_growth = ((products_today - products_yesterday) / products_yesterday * 100) if products_yesterday > 0 else 0.0
        stock_rate = (in_stock_products / total_products * 100) if total_products > 0 else 0.0
        
        # Profit metrics from alerts
        profit_pipeline = [
            {"$match": {"status": "active"}},
            {"$group": {
                "_id": None,
                "total_potential": {"$sum": "$profit_amount"},
                "avg_profit": {"$avg": "$profit_amount"},
                "max_profit": {"$max": "$profit_amount"},
                "avg_discount": {"$avg": "$profit_margin"},
                "count": {"$sum": 1}
            }}
        ]
        
        profit_result = list(alerts_collection.aggregate(profit_pipeline))
        profit_data = profit_result[0] if profit_result else {}
        
        # Safely extract profit data with null checks
        total_potential = profit_data.get("total_potential") or 0
        avg_profit = profit_data.get("avg_profit") or 0
        max_profit = profit_data.get("max_profit") or 0
        avg_discount = profit_data.get("avg_discount") or 0
        count = profit_data.get("count") or 0
        
        # Get last scraping session timestamp
        last_scrape_time = None
        try:
            last_session = db.scraping_sessions.find_one(
                {"status": {"$in": ["completed", "running"]}},
                sort=[("started_at", -1)]
            )
            if last_session and last_session.get("started_at"):
                last_scrape_time = last_session["started_at"].isoformat()
            else:
                latest_product = db.products.find_one(
                    {"scraped_at": {"$exists": True}},
                    sort=[("scraped_at", -1)]
                )
                if latest_product and latest_product.get("scraped_at"):
                    last_scrape_time = latest_product["scraped_at"].isoformat()
        except Exception:
            pass
        
        return {
            "total_products": total_products,
            "products_today": products_today,
            "products_growth": products_growth,
            "in_stock_rate": stock_rate,
            "total_alerts": total_alerts,
            "active_alerts": active_alerts,
            "alerts_today": alerts_today,
            "critical_alerts": critical_alerts,
            "total_potential_profit": total_potential,
            "average_profit": avg_profit,
            "max_profit": max_profit,
            "average_discount": avg_discount,
            "success_rate": (active_alerts / total_alerts * 100) if total_alerts > 0 else 0.0,
            "last_updated": datetime.utcnow().isoformat(),
            "last_scrape_time": last_scrape_time,
            "system_health": {
                "database_type": "mongodb",
                "uptime_hours": 24,
                "last_scrape": _get_scrape_status(last_scrape_time)
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get system stats: {e}")
        return None

def _get_scrape_status(last_scrape_time: Optional[str]) -> str:
    """Helper to determine the scrape status based on last_scrape_time."""
    if last_scrape_time:
        try:
            last_scrape_dt = datetime.fromisoformat(last_scrape_time)
            time_diff = datetime.utcnow() - last_scrape_dt
            if time_diff < timedelta(minutes=15):
                return "recent"
            elif time_diff < timedelta(hours=1):
                return "last_hour"
            elif time_diff < timedelta(hours=24):
                return "last_day"
            else:
                return "older"
        except ValueError:
            return "never"
    return "never"

@st.cache_data(ttl=300)
def get_trends(days: int = 7) -> Optional[Dict[str, Any]]:
    """Get trend data with caching."""
    try:
        _, db = get_mongodb_client()
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Daily product trends
        product_pipeline = [
            {"$match": {"scraped_at": {"$gte": start_date, "$lte": end_date}}},
            {"$group": {
                "_id": {
                    "year": {"$year": "$scraped_at"},
                    "month": {"$month": "$scraped_at"},
                    "day": {"$dayOfMonth": "$scraped_at"}
                },
                "products": {"$sum": 1},
                "avg_price": {"$avg": "$price"}
            }},
            {"$sort": {"_id": 1}}
        ]
        
        product_trends = list(db.products.aggregate(product_pipeline))
        
        # Daily alert trends
        alert_pipeline = [
            {"$match": {"created_at": {"$gte": start_date, "$lte": end_date}}},
            {"$group": {
                "_id": {
                    "year": {"$year": "$created_at"},
                    "month": {"$month": "$created_at"},
                    "day": {"$dayOfMonth": "$created_at"}
                },
                "alerts": {"$sum": 1},
                "avg_profit": {"$avg": "$profit_amount"}
            }},
            {"$sort": {"_id": 1}}
        ]
        
        alert_trends = list(db.price_alerts.aggregate(alert_pipeline))
        
        # Format trends data
        trends = []
        for i in range(days):
            date = start_date + timedelta(days=i)
            date_key = {
                "year": date.year,
                "month": date.month,
                "day": date.day
            }
            
            product_data = next((t for t in product_trends if t["_id"] == date_key), {"products": 0, "avg_price": 0})
            alert_data = next((t for t in alert_trends if t["_id"] == date_key), {"alerts": 0, "avg_profit": 0})
            
            trends.append({
                "date": date.strftime("%Y-%m-%d"),
                "products": product_data["products"],
                "alerts": alert_data["alerts"],
                "avg_price": round(float(product_data.get("avg_price") or 0), 2),
                "avg_profit": round(float(alert_data.get("avg_profit") or 0), 2)
            })
        
        return {"trends": trends}
        
    except Exception as e:
        logger.error(f"Error getting trends: {e}")
        return None

@st.cache_data(ttl=300)
def get_top_opportunities(limit: int = 10) -> Optional[Dict[str, Any]]:
    """Get top opportunities from alerts with caching."""
    try:
        _, db = get_mongodb_client()
        pipeline = [
            {"$match": {"status": "active"}},
            {"$sort": {"profit_margin": -1}},
            {"$limit": limit},
            {"$project": {
                "product_name": "$title",
                "profit_margin": 1,
                "profit_amount": 1,
                "current_price": 1,
                "amazon_price": 1,
                "category": 1,
                "brand": 1,
                "created_at": 1
            }}
        ]
        
        opportunities = list(db.price_alerts.aggregate(pipeline))
        
        formatted_opportunities = []
        for opp in opportunities:
            formatted_opportunities.append({
                "product_name": opp.get("product_name", "Unknown Product"),
                "profit_amount": opp.get("profit_amount", 0),
                "mediamarkt_price": opp.get("current_price", 0),
                "amazon_price": opp.get("amazon_price", 0),
                "profit_margin": opp.get("profit_margin", 0),
                "category": opp.get("category", "Electronics"),
                "brand": opp.get("brand", "Unknown"),
                "created_at": opp.get("created_at", datetime.utcnow()).isoformat()
            })
        
        return {"top_opportunities": formatted_opportunities}
        
    except Exception as e:
        logger.error(f"Error getting opportunities: {e}")
        return None
    
    def get_products(self, 
                    page: int = 1,
                    size: int = 20,
                    category: Optional[str] = None,
                    brand: Optional[str] = None,
                    min_price: Optional[float] = None,
                    max_price: Optional[float] = None,
                    search: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get paginated products."""
        try:
            # Build filter
            filter_query = {}
            
            if category:
                filter_query["category"] = {"$regex": category, "$options": "i"}
            
            if brand:
                filter_query["brand"] = {"$regex": brand, "$options": "i"}
            
            if min_price is not None:
                filter_query["price"] = {"$gte": min_price}
            
            if max_price is not None:
                if "price" in filter_query:
                    filter_query["price"]["$lte"] = max_price
                else:
                    filter_query["price"] = {"$lte": max_price}
            
            if search:
                filter_query["title"] = {"$regex": search, "$options": "i"}
            
            # Get total count
            total = self.db.products.count_documents(filter_query)
            
            # Get paginated results
            skip = (page - 1) * size
            cursor = self.db.products.find(filter_query).sort("scraped_at", -1).skip(skip).limit(size)
            products = list(cursor)
            
            # Format products
            formatted_products = []
            for product in products:
                formatted_products.append({
                    "id": str(product.get("_id")),
                    "name": product.get("title", "Unknown Product"),
                    "price": product.get("price", 0),
                    "original_price": product.get("original_price"),
                    "discount_percentage": product.get("discount_percentage", 0),
                    "brand": product.get("brand"),
                    "category": product.get("category", "Electronics"),
                    "availability": product.get("availability", "Unknown"),
                    "ean": product.get("ean"),
                    "scraped_at": product.get("scraped_at", datetime.utcnow()).isoformat()
                })
            
            # Calculate pagination
            total_pages = (total + size - 1) // size
            
            return {
                "products": formatted_products,
                "pagination": {
                    "page": page,
                    "size": size,
                    "total": total,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting products: {e}")
            return None
    
    def get_alerts(self, 
                  page: int = 1,
                  size: int = 20,
                  status: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get paginated alerts."""
        try:
            # Build filter
            filter_query = {}
            if status:
                filter_query["status"] = status
            
            # Get total count
            total = self.db.price_alerts.count_documents(filter_query)
            
            # Get paginated results
            skip = (page - 1) * size
            cursor = self.db.price_alerts.find(filter_query).sort("created_at", -1).skip(skip).limit(size)
            alerts = list(cursor)
            
            # Format alerts
            formatted_alerts = []
            for alert in alerts:
                formatted_alerts.append({
                    "id": str(alert.get("_id")),
                    "product_name": alert.get("title", "Unknown Product"),
                    "discount_percentage": alert.get("discount_percentage", 0),
                    "savings_amount": alert.get("savings_amount", 0),
                    "price": alert.get("price", 0),
                    "original_price": alert.get("original_price"),
                    "urgency": alert.get("urgency", "MEDIUM"),
                    "status": alert.get("status", "active"),
                    "category": alert.get("category", "Electronics"),
                    "brand": alert.get("brand"),
                    "created_at": alert.get("created_at", datetime.utcnow()).isoformat()
                })
            
            # Calculate pagination
            total_pages = (total + size - 1) // size
            
            return {
                "alerts": formatted_alerts,
                "pagination": {
                    "page": page,
                    "size": size,
                    "total": total,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting alerts: {e}")
            return None
    
    def clear_cache(self):
        """Clear all cached data."""
        self._cache.clear()
        self._cache_timestamps.clear()
    
    def health_check(self) -> bool:
        """Check if MongoDB connection is healthy."""
        try:
            result = self.db.command("ping")
            return result.get("ok") == 1.0
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def get_analytics_data(self, start_date, end_date) -> Optional[Dict[str, Any]]:
        """Get analytics data for the specified date range."""
        try:
            start_dt = datetime.combine(start_date, datetime.min.time())
            end_dt = datetime.combine(end_date, datetime.max.time())
            
            # Products analytics
            products_pipeline = [
                {"$match": {"scraped_at": {"$gte": start_dt, "$lte": end_dt}}},
                {"$group": {
                    "_id": None,
                    "total_products": {"$sum": 1},
                    "avg_price": {"$avg": "$price"},
                    "min_price": {"$min": "$price"},
                    "max_price": {"$max": "$price"},
                    "categories": {"$addToSet": "$category"},
                    "brands": {"$addToSet": "$brand"}
                }}
            ]
            
            products_analytics = list(self.db.products.aggregate(products_pipeline))
            products_data = products_analytics[0] if products_analytics else {}
            
            # Alerts analytics
            alerts_pipeline = [
                {"$match": {"created_at": {"$gte": start_dt, "$lte": end_dt}}},
                {"$group": {
                    "_id": None,
                    "total_alerts": {"$sum": 1},
                    "avg_savings": {"$avg": "$savings_amount"},
                    "total_savings": {"$sum": "$savings_amount"},
                    "avg_discount": {"$avg": "$discount_percentage"},
                    "max_discount": {"$max": "$discount_percentage"}
                }}
            ]
            
            alerts_analytics = list(self.db.price_alerts.aggregate(alerts_pipeline))
            alerts_data = alerts_analytics[0] if alerts_analytics else {}
            
            # Category performance
            category_pipeline = [
                {"$match": {"created_at": {"$gte": start_dt, "$lte": end_dt}}},
                {"$group": {
                    "_id": "$category",
                    "alert_count": {"$sum": 1},
                    "total_savings": {"$sum": "$savings_amount"},
                    "avg_discount": {"$avg": "$discount_percentage"}
                }},
                {"$sort": {"total_savings": -1}},
                {"$limit": 10}
            ]
            
            category_performance = list(self.db.price_alerts.aggregate(category_pipeline))
            
            return {
                "overview": {
                    "total_products": products_data.get("total_products", 0),
                    "total_alerts": alerts_data.get("total_alerts", 0),
                    "total_savings": round(float(alerts_data.get("total_savings") or 0), 2),
                    "avg_savings": round(float(alerts_data.get("avg_savings") or 0), 2),
                    "avg_discount": round(float(alerts_data.get("avg_discount") or 0), 2),
                    "categories_count": len(products_data.get("categories", [])),
                    "brands_count": len(products_data.get("brands", []))
                },
                "category_performance": category_performance,
                "price_analytics": {
                    "avg_price": round(float(products_data.get("avg_price") or 0), 2),
                    "min_price": round(float(products_data.get("min_price") or 0), 2),
                    "max_price": round(float(products_data.get("max_price") or 0), 2)
                },
                "discount_analytics": {
                    "avg_discount": round(float(alerts_data.get("avg_discount") or 0), 2),
                    "max_discount": round(float(alerts_data.get("max_discount") or 0), 2)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting analytics data: {e}")
            return None
    
    def get_settings(self) -> Optional[Dict[str, Any]]:
        """Get system settings."""
        # Return default settings since we don't have a settings collection yet
        return {
            "scraping": {
                "interval_minutes": 30,
                "max_pages": 25,
                "request_delay": 2.0,
                "retry_attempts": 3,
                "use_proxies": False,
                "headless": True,
                "categories": ["Electronics", "Home & Garden", "Sports", "Fashion"]
            },
            "matching": {
                "ean_confidence": 0.95,
                "fuzzy_confidence": 0.85,
                "semantic_confidence": 0.80,
                "enable_ean": True,
                "enable_fuzzy": True,
                "enable_semantic": True,
                "max_matches": 3
            },
            "alerts": {
                "min_profit": 30.0,
                "min_roi": 20.0,
                "enable_telegram": True,
                "enable_email": False,
                "enable_slack": False
            },
            "notifications": {
                "telegram_token": "",
                "telegram_chat_id": "",
                "email_smtp_host": "",
                "email_smtp_port": 587,
                "slack_webhook_url": ""
            }
        }
    
    def update_settings(self, category: str, settings: Dict[str, Any]) -> bool:
        """Update system settings."""
        try:
            # For now, just return True since we don't have settings persistence
            # In a real implementation, this would update a settings collection
            logger.info(f"Settings update requested for {category}: {settings}")
            return True
        except Exception as e:
            logger.error(f"Error updating settings: {e}")
            return False 
    
    def process_alert(self, alert_id: str, update_data: Dict[str, Any]) -> bool:
        """Process/update an alert."""
        try:
            # Convert string ID to ObjectId if needed
            from bson import ObjectId
            if isinstance(alert_id, str):
                object_id = ObjectId(alert_id)
            else:
                object_id = alert_id
            
            result = self.db.price_alerts.update_one(
                {"_id": object_id},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error processing alert {alert_id}: {e}")
            return False
    
    def dismiss_alert(self, alert_id: str) -> bool:
        """Dismiss an alert by setting status to dismissed."""
        return self.process_alert(alert_id, {"status": "dismissed"})
    
    def export_system_data(self) -> Optional[Dict[str, Any]]:
        """Export system data for backup."""
        try:
            # Export key collections
            products = list(self.db.products.find({}).limit(1000))
            alerts = list(self.db.price_alerts.find({}).limit(1000))
            sessions = list(self.db.scraping_sessions.find({}).limit(100))
            
            # Convert ObjectIds to strings for JSON serialization
            for collection in [products, alerts, sessions]:
                for item in collection:
                    if "_id" in item:
                        item["_id"] = str(item["_id"])
            
            return {
                "products": products,
                "alerts": alerts,
                "sessions": sessions,
                "export_timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error exporting system data: {e}")
            return None
    
    def import_settings(self, settings: Dict[str, Any]) -> bool:
        """Import settings configuration."""
        try:
            # For now, just log the import request
            # In a real implementation, this would update a settings collection
            logger.info(f"Settings import requested: {len(settings)} categories")
            return True
        except Exception as e:
            logger.error(f"Error importing settings: {e}")
            return False
    
    def reset_settings_to_defaults(self) -> bool:
        """Reset all settings to default values."""
        try:
            # For now, just return True since we don't have settings persistence
            # In a real implementation, this would reset a settings collection
            logger.info("Settings reset to defaults requested")
            return True
        except Exception as e:
            logger.error(f"Error resetting settings: {e}")
            return False
    
    def get_stats(self) -> Optional[Dict[str, Any]]:
        """Alias for get_system_stats for backward compatibility."""
        return self.get_system_stats() 

    def _get_scrape_status(self, last_scrape_time: Optional[str]) -> str:
        """Helper to determine the scrape status based on last_scrape_time."""
        if last_scrape_time:
            try:
                last_scrape_dt = datetime.fromisoformat(last_scrape_time)
                time_diff = datetime.utcnow() - last_scrape_dt
                if time_diff < timedelta(minutes=15):
                    return "recent"
                elif time_diff < timedelta(hours=1):
                    return "last_hour"
                elif time_diff < timedelta(hours=24):
                    return "last_day"
                else:
                    return "older"
            except ValueError:
                return "never"
        return "never" 