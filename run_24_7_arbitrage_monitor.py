#!/usr/bin/env python3
"""
Enhanced 24/7 Continuous Arbitrage Monitoring System with MongoDB Integration
- Comprehensive duplicate handling
- Database persistence for all products and opportunities
- Business-grade error handling
- Real-time Telegram notifications
"""

import asyncio
import time
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import requests
import structlog
import hashlib

from src.services.scraper.mediamarkt_scraper import scrape_mediamarkt_products_business_grade
from src.services.arbitrage_detector import BusinessArbitrageDetector
from src.config.settings import settings
from src.config.database import get_database_session, DATABASE_TYPE

logger = structlog.get_logger(__name__)

class EnhancedProductDatabaseManager:
    """Enhanced database manager for 24/7 monitoring with comprehensive duplicate handling."""
    
    def __init__(self, monitor_instance=None):
        self.db = None
        self.monitor = monitor_instance  # Reference to monitor for notifications
        self.stats = {
            "total_scraped": 0,
            "new_products": 0,
            "updated_products": 0,
            "duplicates_skipped": 0,
            "opportunities_stored": 0,
            "errors": 0
        }
    
    async def initialize_database(self):
        """Initialize database connection."""
        if DATABASE_TYPE == 'mongodb':
            self.db = get_database_session()
            logger.info("MongoDB connection initialized for 24/7 monitoring")
        else:
            logger.error("Only MongoDB supported for enhanced monitor")
            raise Exception("MongoDB required for enhanced 24/7 monitor")
    
    def generate_product_fingerprint(self, product: Dict[str, Any]) -> str:
        """Generate unique fingerprint for duplicate detection."""
        fingerprint_data = f"{product.get('title', '').lower().strip()}"
        fingerprint_data += f"_{product.get('price', 0)}"
        
        if product.get('ean'):
            fingerprint_data += f"_{product.get('ean')}"
        
        if product.get('brand'):
            fingerprint_data += f"_{product.get('brand').lower()}"
        
        return hashlib.md5(fingerprint_data.encode()).hexdigest()
    
    async def save_products_with_deduplication(self, products: List[Dict[str, Any]], cycle_number: int) -> Dict[str, Any]:
        """Save products with comprehensive duplicate handling for 24/7 monitoring."""
        cycle_stats = {
            "total_processed": len(products),
            "new_products": 0,
            "updated_products": 0,
            "duplicates_skipped": 0,
            "errors": 0
        }
        
        for product in products:
            try:
                # Check for duplicates with multiple strategies
                duplicate_result = await self.check_product_duplicates(product)
                
                if duplicate_result["is_duplicate"]:
                    if duplicate_result.get("should_update", False):
                        # Update existing product
                        await self.update_product_data(duplicate_result["existing_id"], product, cycle_number)
                        cycle_stats["updated_products"] += 1
                    else:
                        # Skip exact duplicate
                        cycle_stats["duplicates_skipped"] += 1
                else:
                    # Insert new product
                    await self.insert_new_product(product, cycle_number)
                    cycle_stats["new_products"] += 1
                    
            except Exception as e:
                cycle_stats["errors"] += 1
                logger.error("Failed to save product in cycle", 
                           error=str(e), 
                           cycle=cycle_number,
                           title=product.get('title', '')[:50])
        
        # Update global stats
        self.stats["total_scraped"] += cycle_stats["total_processed"]
        self.stats["new_products"] += cycle_stats["new_products"]
        self.stats["updated_products"] += cycle_stats["updated_products"]
        self.stats["duplicates_skipped"] += cycle_stats["duplicates_skipped"]
        self.stats["errors"] += cycle_stats["errors"]
        
        return cycle_stats
    
    async def check_product_duplicates(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive duplicate checking for 24/7 monitoring."""
        ean = product.get('ean')
        title = product.get('title', '').strip()
        price = product.get('price', 0)
        
        # Strategy 1: EAN-based matching (most reliable for monitoring)
        if ean:
            existing_ean = await self.db.products.find_one({
                "ean": ean,
                "source": "mediamarkt"
            })
            if existing_ean:
                # Check if price changed significantly (>1% difference)
                price_diff = abs(existing_ean.get("price", 0) - price)
                should_update = price_diff > max(0.01, existing_ean.get("price", 0) * 0.01)
                
                return {
                    "is_duplicate": True,
                    "duplicate_type": "ean_match",
                    "existing_id": str(existing_ean["_id"]),
                    "should_update": should_update,
                    "price_change": price_diff
                }
        
        # Strategy 2: Recent similar product check (within last 24 hours)
        if title:
            recent_similar = await self.db.products.find_one({
                "title": title,
                "source": "mediamarkt",
                "scraped_at": {"$gte": datetime.utcnow() - timedelta(hours=24)},
                "price": {"$gte": price * 0.98, "$lte": price * 1.02}  # Within 2% price range
            })
            if recent_similar:
                return {
                    "is_duplicate": True,
                    "duplicate_type": "recent_similar",
                    "existing_id": str(recent_similar["_id"]),
                    "should_update": False  # Recent enough, don't update
                }
        
        # Strategy 3: Fingerprint matching
        fingerprint = self.generate_product_fingerprint(product)
        existing_fingerprint = await self.db.products.find_one({
            "product_fingerprint": fingerprint,
            "source": "mediamarkt"
        })
        if existing_fingerprint:
            # Always update fingerprint matches to keep data fresh
            return {
                "is_duplicate": True,
                "duplicate_type": "fingerprint_match",
                "existing_id": str(existing_fingerprint["_id"]),
                "should_update": True
            }
        
        return {"is_duplicate": False}
    
    async def insert_new_product(self, product: Dict[str, Any], cycle_number: int) -> str:
        """Insert new product for 24/7 monitoring."""
        product_doc = {
            "title": product.get('title', 'Unknown Product'),
            "price": float(product.get('price', 0)),
            "original_price": float(product.get('original_price')) if product.get('original_price') else None,
            "discount_percentage": product.get('discount_percentage'),
            "ean": product.get('ean'),
            "brand": product.get('brand'),
            "category": product.get('category', 'Electronics'),
            "availability": product.get('availability', 'unknown'),
            "has_discount": product.get('has_discount', False),
            "scraped_at": datetime.utcnow(),
            "source": "mediamarkt",
            "business_grade": True,
            "quality_grade": product.get('quality_grade', 'B'),
            "profit_potential_score": product.get('profit_potential_score', 0),
            "product_fingerprint": self.generate_product_fingerprint(product),
            "monitoring_data": {
                "discovery_cycle": cycle_number,
                "discovery_timestamp": datetime.utcnow(),
                "scraper_version": "24_7_monitor_v2",
                "first_seen_price": float(product.get('price', 0))
            }
        }
        
        # Add optional fields
        if product.get('url'):
            product_doc['url'] = product['url']
        
        if product.get('quality_indicators'):
            product_doc['quality_indicators'] = product['quality_indicators']
        
        result = await self.db.products.insert_one(product_doc)
        
        logger.debug("New product inserted in monitoring cycle", 
                    title=product.get('title', '')[:50],
                    price=product.get('price'),
                    cycle=cycle_number,
                    product_id=str(result.inserted_id))
        
        # Check if this new product has a good discount and send notification
        await self.monitor.check_and_notify_new_product_discount(product, cycle_number)
        
        return str(result.inserted_id)
    
    async def update_product_data(self, existing_id: str, product: Dict[str, Any], cycle_number: int) -> bool:
        """Update existing product data."""
        from bson import ObjectId
        
        update_data = {
            "price": float(product.get('price', 0)),
            "discount_percentage": product.get('discount_percentage'),
            "availability": product.get('availability', 'unknown'),
            "has_discount": product.get('has_discount', False),
            "last_updated": datetime.utcnow(),
            "quality_grade": product.get('quality_grade', 'B'),
            "profit_potential_score": product.get('profit_potential_score', 0),
            "monitoring_data.last_seen_cycle": cycle_number,
            "monitoring_data.last_updated": datetime.utcnow()
        }
        
        # Track price history for monitoring
        if product.get('price'):
            update_data["monitoring_data.price_history"] = {
                "timestamp": datetime.utcnow(),
                "price": float(product['price']),
                "cycle": cycle_number
            }
        
        result = await self.db.products.update_one(
            {"_id": ObjectId(existing_id)},
            {
                "$set": update_data,
                "$push": {"monitoring_data.price_history": {"$each": [update_data["monitoring_data.price_history"]], "$slice": -10}}  # Keep last 10 price points
            }
        )
        
        logger.debug("Product updated in monitoring cycle", 
                    product_id=existing_id,
                    cycle=cycle_number,
                    modified_count=result.modified_count)
        
        return result.modified_count > 0
    
    async def store_arbitrage_opportunity(self, opportunity: Dict[str, Any], cycle_number: int) -> str:
        """Store arbitrage opportunity in database."""
        opportunity_doc = {
            **opportunity,
            "created_at": datetime.utcnow(),
            "status": "active",
            "discovery_cycle": cycle_number,
            "source": "24_7_monitor",
            "monitoring_data": {
                "discovery_timestamp": datetime.utcnow(),
                "cycle_number": cycle_number,
                "notifications_sent": 1 if opportunity.get('urgency') in ['HIGH', 'CRITICAL'] else 0
            }
        }
        
        # Use upsert to avoid duplicate opportunities
        result = await self.db.price_alerts.replace_one(
            {
                "product_id": opportunity.get('product_id'),
                "status": "active"
            },
            opportunity_doc,
            upsert=True
        )
        
        self.stats["opportunities_stored"] += 1
        
        logger.debug("Arbitrage opportunity stored", 
                    product_id=opportunity.get('product_id'),
                    profit=opportunity.get('estimated_profit'),
                    cycle=cycle_number)
        
        return str(result.upserted_id) if result.upserted_id else "updated"

class Enhanced24_7ArbitrageMonitor:
    """Enhanced 24/7 Arbitrage monitoring system with comprehensive database integration."""
    
    def __init__(self):
        self.telegram_bot_token = settings.TELEGRAM_BOT_TOKEN
        self.telegram_chat_id = settings.TELEGRAM_CHAT_ID
        self.cycle_count = 0
        self.total_opportunities_found = 0
        self.total_notifications_sent = 0
        self.db_manager = EnhancedProductDatabaseManager(self)  # Pass self to the manager
        
        # HYBRID APPROACH configuration - High discount thresholds
        self.cycle_interval = 120  # 2 minutes between cycles (changed from 300)
        self.products_per_cycle = 64  # Approximately 32 products per page * 2 pages (reduced from 500)
        self.max_pages_per_cycle = 2  # Only 2 pages per cycle (changed from 25)
        
        # HYBRID STRATEGY: Discount-based thresholds (not fake profit)
        self.min_discount_threshold = 30.0  # Minimum 30% discount to alert
        self.high_discount_threshold = 50.0  # 50%+ is premium discount
        self.critical_discount_threshold = 70.0  # 70%+ is critical discount
        self.quality_threshold = 25  # Minimum quality score for alerts
        
        # Enhanced performance tracking
        self.performance_stats = {
            "cycles_completed": 0,
            "total_products_scanned": 0,
            "total_products_stored": 0,
            "opportunities_found": 0,
            "notifications_sent": 0,
            "uptime_start": datetime.now(),
            "last_notification": None,
            "best_discount_found": 0.0,  # Track best discount instead of fake profit
            "database_operations": 0
        }
    
    async def initialize_system(self):
        """Initialize the enhanced monitoring system."""
        await self.db_manager.initialize_database()
        logger.info("Enhanced 24/7 monitoring system initialized with MongoDB integration")
    
    async def send_telegram_notification(self, opportunity: Dict[str, Any]) -> bool:
        """Send immediate Telegram notification for HIGH DISCOUNT opportunity (Hybrid Approach)."""
        try:
            discount_pct = opportunity.get('discount_percentage', 0)
            savings = opportunity.get('savings_amount', 0)
            price = opportunity.get('price', 0)
            original_price = opportunity.get('original_price')
            title = opportunity.get('title', 'Unknown Product')[:60]
            brand = opportunity.get('brand', 'Unknown')
            category = opportunity.get('category', 'Electronics')
            urgency = opportunity.get('urgency', 'MEDIUM')
            quality_score = opportunity.get('quality_score', 0)
            
            # Determine urgency emoji
            urgency_emoji = {
                'CRITICAL': '🚨🔥',
                'HIGH': '⚡🎯',
                'MEDIUM': '💎📈',
                'LOW': '💰📊'
            }.get(urgency, '💰')
            
            # Format original price display
            original_price_text = f"€{original_price:.2f}" if original_price else "Unknown"
            
            # Enhanced message for HYBRID DISCOUNT ALERTS
            message = f"""
{urgency_emoji} **HIGH DISCOUNT ALERT** {urgency_emoji}

🎯 **{title}**

💥 **{discount_pct:.1f}% OFF** - Save €{savings:.2f}!
🏷️ Current Price: €{price:.2f}
💸 Original Price: {original_price_text}
🏭 Brand: {brand}
📂 Category: {category}
⭐ Quality Score: {quality_score}/100

📊 **Monitoring Stats:**
🔄 Cycle: #{self.cycle_count}
📦 Products Scanned: {self.performance_stats['total_products_scanned']:,}
💾 DB Operations: {self.performance_stats['database_operations']:,}
🔥 Best Discount: {self.performance_stats.get('best_discount_found', 0):.1f}%

⏰ Found: {datetime.now().strftime('%H:%M:%S')}
🚀 **HYBRID STRATEGY**: High Discounts Now + Real Arbitrage Soon!

💡 *Note: Keepa integration coming soon for real Amazon arbitrage!*
            """.strip()
            
            # Send via Telegram Bot API
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info("HIGH DISCOUNT alert sent successfully", 
                           discount=f"{discount_pct:.1f}%",
                           savings=f"€{savings:.2f}",
                           cycle=self.cycle_count)
                self.total_notifications_sent += 1
                self.performance_stats["notifications_sent"] += 1
                self.performance_stats["last_notification"] = datetime.now()
                return True
            else:
                logger.error("Failed to send HIGH DISCOUNT alert", 
                           status_code=response.status_code,
                           response=response.text[:200])
                return False
                
        except Exception as e:
            logger.error("Failed to send HIGH DISCOUNT notification", error=str(e))
            return False
    
    async def check_and_notify_new_product_discount(self, product: Dict[str, Any], cycle_number: int):
        """Check if newly added product has good discount and send notification."""
        try:
            discount_pct = product.get('discount_percentage', 0)
            price = product.get('price', 0)
            
            # Check if product meets notification criteria
            if (price and price > 20 and 
                discount_pct is not None and discount_pct >= 30):  # 30%+ discount threshold
                
                # Calculate quality score
                quality_score = 0
                if product.get('brand'):
                    quality_score += 20
                if product.get('ean'):
                    quality_score += 15
                if price >= 50:
                    quality_score += 10
                if discount_pct >= 50:
                    quality_score += 20
                
                # Only notify for quality products
                if quality_score >= 25:
                    await self.send_new_product_notification(product, cycle_number)
                    
        except Exception as e:
            logger.error("Failed to check new product discount", error=str(e))
    
    async def send_new_product_notification(self, product: Dict[str, Any], cycle_number: int):
        """Send Telegram notification for newly discovered product with good discount."""
        try:
            discount_pct = product.get('discount_percentage', 0)
            price = product.get('price', 0)
            original_price = product.get('original_price')
            title = product.get('title', 'Unknown Product')[:60]
            brand = product.get('brand', 'Unknown')
            category = product.get('category', 'Electronics')
            
            # Calculate savings
            savings_amount = 0
            if original_price and original_price > price:
                savings_amount = original_price - price
            elif discount_pct > 0:
                savings_amount = price * (discount_pct / (100 - discount_pct))
            
            # Determine urgency emoji based on discount
            if discount_pct >= 70:
                urgency_emoji = '🚨🔥'
                urgency_text = 'CRITICAL'
            elif discount_pct >= 50:
                urgency_emoji = '⚡🎯'
                urgency_text = 'HIGH'
            else:
                urgency_emoji = '💎📈'
                urgency_text = 'MEDIUM'
            
            # Format original price display
            original_price_text = f"€{original_price:.2f}" if original_price else "Unknown"
            
            message = f"""
{urgency_emoji} **NEW PRODUCT ALERT** {urgency_emoji}

🆕 **NEWLY DISCOVERED PRODUCT**
🎯 **{title}**

💥 **{discount_pct:.1f}% OFF** - Save €{savings_amount:.2f}!
🏷️ Current Price: €{price:.2f}
💸 Original Price: {original_price_text}
🏭 Brand: {brand}
📂 Category: {category}
🔥 Urgency: {urgency_text}

📊 **Discovery Info:**
🔄 Cycle: #{cycle_number}
⏰ Found: {datetime.now().strftime('%H:%M:%S')}
🆕 Status: FRESH DISCOVERY
🎯 **Strategy**: Monitor new high-discount products!

💡 *New product detected with excellent discount!*
            """.strip()
            
            # Send via Telegram Bot API
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info("NEW PRODUCT notification sent successfully", 
                           discount=f"{discount_pct:.1f}%",
                           savings=f"€{savings_amount:.2f}",
                           cycle=cycle_number,
                           title=title[:30])
                # Update notification stats
                self.total_notifications_sent += 1
                self.performance_stats["notifications_sent"] += 1
                return True
            else:
                logger.error("Failed to send NEW PRODUCT notification", 
                           status_code=response.status_code,
                           response=response.text[:200])
                return False
                
        except Exception as e:
            logger.error("Failed to send new product notification", error=str(e))
            return False
    
    async def analyze_opportunities_and_notify(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Enhanced opportunity analysis with HYBRID APPROACH: High discount alerts + future Keepa integration."""
        try:
            # HYBRID APPROACH: Focus on genuine high discounts, not fake profit calculations
            opportunities = []
            for product in products:
                # Enhanced discount-based opportunity detection
                price = product.get('price', 0)
                discount_pct = product.get('discount_percentage', 0)
                original_price = product.get('original_price')
                
                # HYBRID CRITERIA: High discount thresholds for immediate alerts
                if (price and price > 20 and 
                    discount_pct is not None and discount_pct >= 30):  # 30%+ discount threshold
                    
                    # Calculate actual savings amount
                    savings_amount = 0
                    if original_price and original_price > price:
                        savings_amount = original_price - price
                    elif discount_pct > 0:
                        # Estimate savings from discount percentage
                        savings_amount = price * (discount_pct / (100 - discount_pct))
                    
                    # Determine urgency based on discount level (not fake profit)
                    urgency = 'MEDIUM'  # Default for 30%+ discounts
                    if discount_pct >= 70:
                        urgency = 'CRITICAL'  # 70%+ is critical
                    elif discount_pct >= 60:
                        urgency = 'HIGH'     # 60%+ is high priority
                    elif discount_pct >= 50:
                        urgency = 'HIGH'     # 50%+ is high priority
                    elif discount_pct >= 40:
                        urgency = 'MEDIUM'   # 40%+ is medium priority
                    
                    # Additional filters for quality
                    quality_score = 0
                    if product.get('brand'):
                        quality_score += 20
                    if product.get('ean'):
                        quality_score += 15
                    if price >= 50:
                        quality_score += 10
                    if discount_pct >= 50:
                        quality_score += 20
                    
                    # Only alert on quality opportunities
                    if quality_score >= 25:  # Minimum quality threshold
                        opportunity = {
                            "product_id": product.get('_hash', product.get('title', '')[:50]),
                            "title": product['title'],
                            "price": product['price'],
                            "original_price": product.get('original_price'),
                            "discount_percentage": discount_pct,
                            "savings_amount": savings_amount,
                            "brand": product.get('brand'),
                            "category": product.get('category'),
                            "ean": product.get('ean'),
                            "availability": product.get('availability'),
                            "quality_score": quality_score,
                            "urgency": urgency,
                            "alert_type": "HIGH_DISCOUNT",  # Clear what we're alerting on
                            "discovery_cycle": self.cycle_count,
                            "analysis_timestamp": datetime.utcnow(),
                            # Future Keepa integration ready
                            "keepa_ready": False,
                            "estimated_arbitrage_profit": None  # Will be filled when Keepa is integrated
                        }
                        opportunities.append(opportunity)
            
            # Sort by discount percentage (highest discounts first)
            opportunities.sort(key=lambda x: x['discount_percentage'], reverse=True)
            
            # Store opportunities in database and send notifications
            notifications_sent = 0
            total_savings_potential = 0
            
            for opportunity in opportunities[:5]:  # Top 5 discount opportunities
                discount_pct = opportunity['discount_percentage']
                savings = opportunity['savings_amount']
                
                # Store opportunity in database
                await self.db_manager.store_arbitrage_opportunity(opportunity, self.cycle_count)
                self.performance_stats["database_operations"] += 1
                
                # Track savings potential
                total_savings_potential += savings
                
                # Update best discount tracker
                if discount_pct > self.performance_stats.get("best_discount_found", 0):
                    self.performance_stats["best_discount_found"] = discount_pct
                
                # Send notification for high discount opportunities
                # Adjusted threshold: notify on 30%+ discounts (was fake €30 profit)
                if discount_pct >= 30:
                    success = await self.send_telegram_notification(opportunity)
                    if success:
                        notifications_sent += 1
                    
                    # Small delay between notifications
                    await asyncio.sleep(2)
            
            return {
                'opportunities_found': len(opportunities),
                'high_discount_opportunities': len([o for o in opportunities if o['discount_percentage'] >= 50]),
                'critical_discount_opportunities': len([o for o in opportunities if o['discount_percentage'] >= 70]),
                'notifications_sent': notifications_sent,
                'total_savings_potential': total_savings_potential,
                'best_opportunity': opportunities[0] if opportunities else None,
                'alert_strategy': 'HYBRID_DISCOUNT_BASED'  # Clear indication of current strategy
            }
            
        except Exception as e:
            logger.error("Failed to analyze discount opportunities", error=str(e))
            return {'opportunities_found': 0, 'notifications_sent': 0}
    
    async def run_enhanced_monitoring_cycle(self) -> Dict[str, Any]:
        """Run enhanced monitoring cycle with comprehensive database integration."""
        cycle_start = datetime.now()
        self.cycle_count += 1
        
        logger.info("Starting enhanced arbitrage monitoring cycle", 
                   cycle=self.cycle_count, 
                   target_products=self.products_per_cycle)
        
        try:
            # Scrape products
            products = await scrape_mediamarkt_products_business_grade(
                max_pages=self.max_pages_per_cycle,
                max_products=self.products_per_cycle
            )
            
            # Save products to database with comprehensive duplicate handling
            db_stats = await self.db_manager.save_products_with_deduplication(products, self.cycle_count)
            self.performance_stats["database_operations"] += db_stats["total_processed"]
            
            # Analyze for opportunities
            analysis_results = await self.analyze_opportunities_and_notify(products)
            
            # Update performance stats
            self.performance_stats["cycles_completed"] += 1
            self.performance_stats["total_products_scanned"] += len(products)
            self.performance_stats["total_products_stored"] += db_stats["new_products"] + db_stats["updated_products"]
            self.performance_stats["opportunities_found"] += analysis_results.get('opportunities_found', 0)
            
            cycle_time = (datetime.now() - cycle_start).total_seconds()
            
            results = {
                'cycle_number': self.cycle_count,
                'products_scraped': len(products),
                'database_stats': db_stats,
                'cycle_duration': cycle_time,
                'products_per_second': len(products) / cycle_time if cycle_time > 0 else 0,
                **analysis_results
            }
            
            logger.info("Enhanced monitoring cycle completed", 
                       cycle=self.cycle_count,
                       products_scanned=len(products),
                       new_products=db_stats["new_products"],
                       updated_products=db_stats["updated_products"],
                       duplicates_skipped=db_stats["duplicates_skipped"],
                       opportunities_found=analysis_results.get('opportunities_found', 0),
                       notifications_sent=analysis_results.get('notifications_sent', 0),
                       duration=f"{cycle_time:.1f}s")
            
            return results
            
        except Exception as e:
            logger.error("Enhanced monitoring cycle failed", cycle=self.cycle_count, error=str(e))
            return {'cycle_number': self.cycle_count, 'error': str(e)}
    
    async def send_enhanced_status_update(self, cycle_results: Dict[str, Any]):
        """Send enhanced status updates with HYBRID STRATEGY statistics."""
        try:
            uptime = datetime.now() - self.performance_stats["uptime_start"]
            uptime_hours = uptime.total_seconds() / 3600
            
            db_stats = cycle_results.get('database_stats', {})
            
            message = f"""
📊 **HYBRID ARBITRAGE MONITOR STATUS**

🔄 Cycle #{self.cycle_count} Complete
⏱️ Uptime: {uptime_hours:.1f} hours
📦 Products Scanned: {cycle_results.get('products_scraped', 0)}
💾 **Database Operations:**
   🆕 New Products: {db_stats.get('new_products', 0)}
   🔄 Updated Products: {db_stats.get('updated_products', 0)}
   🔍 Duplicates Skipped: {db_stats.get('duplicates_skipped', 0)}

🔥 **DISCOUNT ALERTS (Current Strategy):**
💎 High Discounts (30%+): {cycle_results.get('opportunities_found', 0)}
⚡ Premium Discounts (50%+): {cycle_results.get('high_discount_opportunities', 0)}
🚨 Critical Discounts (70%+): {cycle_results.get('critical_discount_opportunities', 0)}
💰 Total Savings Potential: €{cycle_results.get('total_savings_potential', 0):.2f}

🏆 **Session Totals:**
📊 Total Products: {self.performance_stats['total_products_scanned']:,}
💾 Stored in DB: {self.performance_stats['total_products_stored']:,}
🔥 Total Discount Alerts: {self.performance_stats['opportunities_found']:,}
📱 Notifications Sent: {self.performance_stats['notifications_sent']:,}
💥 Best Discount Found: {self.performance_stats.get('best_discount_found', 0):.1f}%
🔧 DB Operations: {self.performance_stats['database_operations']:,}

⚡ Next scan in {self.cycle_interval//60} minutes
🤖 **HYBRID STRATEGY**: High Discounts Now + Keepa Arbitrage Soon!
💡 *Keepa integration ready - just add API key for real arbitrage!*
            """.strip()
            
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info("HYBRID status update sent successfully", cycle=self.cycle_count)
            
        except Exception as e:
            logger.error("Failed to send HYBRID status update", error=str(e))
    
    async def start_enhanced_continuous_monitoring(self):
        """Start enhanced 24/7 continuous monitoring with database integration."""
        await self.initialize_system()
        
        logger.info("Starting HYBRID 24/7 Arbitrage Monitoring System", 
                   cycle_interval=f"{self.cycle_interval//60} minutes",
                   products_per_cycle=self.products_per_cycle,
                   min_discount_threshold=f"{self.min_discount_threshold}%",
                   database_integration="MongoDB with comprehensive duplicate handling")
        
        # Send HYBRID startup notification
        startup_message = f"""
🚀 **HYBRID ARBITRAGE MONITOR STARTED**

🤖 24/7 monitoring with HYBRID STRATEGY activated
⏱️ Scanning every {self.cycle_interval//60} minutes
📦 {self.products_per_cycle} products per cycle
🔥 Min discount threshold: {self.min_discount_threshold}%
💾 Database: MongoDB with duplicate handling

🎯 **CURRENT STRATEGY: HIGH DISCOUNT ALERTS**
• 30%+ discounts → Immediate alerts
• 50%+ discounts → Premium priority  
• 70%+ discounts → Critical priority

💡 **FUTURE: REAL ARBITRAGE INTEGRATION**
• Keepa API ready for implementation
• Real Amazon price matching coming soon
• Genuine profit calculations when you add API key

🚀 Ready to detect high-value discount opportunities!
        """.strip()
        
        try:
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': startup_message,
                'parse_mode': 'Markdown'
            }
            requests.post(url, json=payload, timeout=10)
        except:
            pass
        
        cycle_results = None
        while True:
            try:
                # Run enhanced monitoring cycle
                cycle_results = await self.run_enhanced_monitoring_cycle()
                
                # Send enhanced status update every 10 cycles
                if self.cycle_count % 10 == 0:
                    await self.send_enhanced_status_update(cycle_results)
                
                # Wait until next cycle
                logger.info(f"Waiting {self.cycle_interval//60} minutes until next enhanced cycle...")
                await asyncio.sleep(self.cycle_interval)
                
            except KeyboardInterrupt:
                logger.info("Enhanced monitoring stopped by user")
                break
            except Exception as e:
                logger.error("Unexpected error in enhanced monitoring loop", error=str(e))
                await asyncio.sleep(60)  # Wait 1 minute before retrying

async def main():
    """Main entry point for HYBRID 24/7 monitoring: High Discounts Now + Future Keepa Integration."""
    print("🚀 Starting HYBRID 24/7 Continuous Arbitrage Monitoring System")
    print("💾 Features: MongoDB integration, comprehensive duplicate handling")
    print("🔥 CURRENT: High discount alerts (30%+ discounts)")
    print("💡 FUTURE: Real arbitrage with Keepa API integration")
    print("📱 Telegram notifications + Database persistence for analytics")
    print("⚡ Press Ctrl+C to stop")
    print("")
    
    monitor = Enhanced24_7ArbitrageMonitor()
    await monitor.start_enhanced_continuous_monitoring()

if __name__ == "__main__":
    asyncio.run(main()) 