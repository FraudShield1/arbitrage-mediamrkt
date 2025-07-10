"""
Business-grade arbitrage opportunity detection and notification system.
Analyzes scraped products for profit potential and sends automated alerts.
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import re

import structlog
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.config.database import get_db_session
from src.services.notifications import send_telegram_notification
from src.config.settings import get_settings

logger = structlog.get_logger(__name__)


class ArbitrageDetector:
    """Enhanced arbitrage detection service with configurable parameters."""
    
    def __init__(self):
        """Initialize the arbitrage detector with settings."""
        self.settings = get_settings()
        self.min_profit_margin = self.settings.MIN_PROFIT_MARGIN
        self.min_profit_amount = self.settings.MIN_PROFIT_AMOUNT
        
        # Amazon fee structure (configurable)
        self.amazon_referral_fee = 0.08  # 8% average
        self.amazon_closing_fee = 1.35   # €1.35 average
        self.shipping_cost = 4.99        # €4.99 standard shipping
        
        logger.info(f"ArbitrageDetector initialized with min profit margin: {self.min_profit_margin}")

    async def analyze_products_for_opportunities(
        self, 
        products: List[Dict[str, Any]],
        db: Optional[AsyncIOMotorDatabase] = None
    ) -> List[Dict[str, Any]]:
        """
        Analyze scraped products for arbitrage opportunities.
        Business-grade analysis with multiple profit indicators.
        
        Args:
            products: List of scraped products
            db: Database connection (optional)
            
        Returns:
            List of opportunities with profit analysis
        """
        if not db:
            db = await get_db_session()
        
        logger.info("Starting business-grade opportunity analysis", 
                   products_count=len(products))
        
        opportunities = []
        high_value_opportunities = []
        
        for product in products:
            try:
                opportunity = await self.analyze_single_product(product, db)
                if opportunity:
                    opportunities.append(opportunity)
                    
                    # Check for high-value opportunities
                    if self.is_high_value_opportunity(opportunity):
                        high_value_opportunities.append(opportunity)
                        
            except Exception as e:
                logger.error("Product analysis failed", 
                           product_title=product.get('title', 'Unknown'),
                           error=str(e))
        
        # Sort opportunities by profit potential
        opportunities.sort(key=lambda x: x.get('estimated_profit', 0), reverse=True)
        
        logger.info("Business opportunity analysis completed",
                   total_opportunities=len(opportunities),
                   high_value_opportunities=len(high_value_opportunities),
                   top_profit=opportunities[0].get('estimated_profit', 0) if opportunities else 0)
        
        # Send notifications for high-value opportunities
        if high_value_opportunities:
            await self.notify_high_value_opportunities(high_value_opportunities)
        
        return opportunities
    
    async def analyze_single_product(
        self, 
        product: Dict[str, Any], 
        db: AsyncIOMotorDatabase
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze a single product for arbitrage potential.
        Business-grade analysis with multiple profit calculation methods.
        """
        try:
            # Basic product validation
            if not product.get('price') or product['price'] <= 0:
                return None
            
            # Calculate discount-based opportunity
            discount_opportunity = self.calculate_discount_opportunity(product)
            
            # Calculate brand premium opportunity
            brand_opportunity = self.calculate_brand_premium_opportunity(product)
            
            # Calculate category-based opportunity
            category_opportunity = self.calculate_category_opportunity(product)
            
            # Calculate historical price opportunity (simulated for now)
            historical_opportunity = self.calculate_historical_opportunity(product)
            
            # Combine all opportunity scores
            total_opportunity_score = (
                discount_opportunity.get('score', 0) +
                brand_opportunity.get('score', 0) +
                category_opportunity.get('score', 0) +
                historical_opportunity.get('score', 0)
            )
            
            # Calculate estimated profit
            estimated_profit = self.calculate_estimated_profit(product, total_opportunity_score)
            
            # Only return if it meets minimum thresholds
            if (estimated_profit >= self.min_profit_amount and 
                total_opportunity_score >= 60):  # Business threshold
                
                opportunity = {
                    "product_id": product.get('_hash', product.get('title', '')[:50]),
                    "title": product['title'],
                    "price": product['price'],
                    "original_price": product.get('original_price'),
                    "discount_percentage": product.get('discount_percentage'),
                    "brand": product.get('brand'),
                    "category": product.get('category'),
                    "ean": product.get('ean'),
                    "availability": product.get('availability'),
                    "estimated_profit": estimated_profit,
                    "opportunity_score": total_opportunity_score,
                    "profit_margin": (estimated_profit / product['price']) * 100,
                    "opportunity_breakdown": {
                        "discount": discount_opportunity,
                        "brand": brand_opportunity,
                        "category": category_opportunity,
                        "historical": historical_opportunity
                    },
                    "analysis_timestamp": datetime.utcnow(),
                    "business_grade": True,
                    "quality_grade": product.get('quality_grade', 'B'),
                    "urgency": self.calculate_urgency(product, estimated_profit)
                }
                
                # Store opportunity in database
                await self.store_opportunity(opportunity, db)
                
                return opportunity
            
            return None
            
        except Exception as e:
            logger.error("Single product analysis failed", 
                        product_title=product.get('title', 'Unknown'),
                        error=str(e))
            return None
    
    def calculate_discount_opportunity(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate opportunity based on current discounts."""
        discount_percentage = product.get('discount_percentage', 0)
        
        if discount_percentage >= 50:
            score = 30
            grade = "Excellent"
        elif discount_percentage >= 30:
            score = 20
            grade = "Good"
        elif discount_percentage >= 15:
            score = 10
            grade = "Fair"
        else:
            score = 0
            grade = "Poor"
        
        return {
            "score": score,
            "grade": grade,
            "discount_percentage": discount_percentage,
            "analysis": f"{discount_percentage}% discount opportunity"
        }
    
    def calculate_brand_premium_opportunity(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate opportunity based on brand recognition and premium potential."""
        brand = product.get('brand', '').upper()
        
        premium_brands = {
            'APPLE': 25,
            'SAMSUNG': 20,
            'SONY': 18,
            'NINTENDO': 22,
            'PLAYSTATION': 20,
            'XBOX': 18,
            'LG': 15,
            'CANON': 17,
            'NIKON': 17,
            'PHILIPS': 12
        }
        
        score = premium_brands.get(brand, 5)  # 5 points for any recognized brand
        
        if score >= 20:
            grade = "Premium"
        elif score >= 15:
            grade = "Good"
        elif score >= 10:
            grade = "Fair"
        else:
            grade = "Standard"
        
        return {
            "score": score,
            "grade": grade,
            "brand": brand,
            "analysis": f"{brand} brand premium opportunity"
        }
    
    def calculate_category_opportunity(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate opportunity based on product category demand."""
        category = product.get('category', 'Electronics')
        price = product.get('price', 0)
        
        # Category multipliers based on arbitrage potential
        category_scores = {
            'Gaming': 20,
            'Smartphones': 18,
            'Computing': 15,
            'Photography': 17,
            'TV & Audio': 12,
            'Home Appliances': 10,
            'Electronics': 8
        }
        
        base_score = category_scores.get(category, 5)
        
        # Price range bonus
        if 100 <= price <= 500:  # Sweet spot for arbitrage
            price_bonus = 10
        elif 50 <= price <= 1000:
            price_bonus = 5
        else:
            price_bonus = 0
        
        total_score = base_score + price_bonus
        
        if total_score >= 25:
            grade = "High Demand"
        elif total_score >= 15:
            grade = "Good Demand"
        else:
            grade = "Standard"
        
        return {
            "score": total_score,
            "grade": grade,
            "category": category,
            "price_range": "optimal" if price_bonus == 10 else "good" if price_bonus == 5 else "standard",
            "analysis": f"{category} category with {grade.lower()}"
        }
    
    def calculate_historical_opportunity(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate opportunity based on historical pricing patterns (simulated)."""
        # This would integrate with Keepa API in production
        # For now, simulate based on product characteristics
        
        price = product.get('price', 0)
        has_discount = product.get('has_discount', False)
        
        # Simulate historical analysis
        if has_discount and price >= 100:
            score = 15
            grade = "Strong Historical Value"
        elif has_discount:
            score = 10
            grade = "Good Historical Value"
        elif price >= 200:
            score = 8
            grade = "Fair Historical Value"
        else:
            score = 3
            grade = "Limited Historical Data"
        
        return {
            "score": score,
            "grade": grade,
            "analysis": f"Historical pricing indicates {grade.lower()}"
        }
    
    def calculate_estimated_profit(self, product: Dict[str, Any], opportunity_score: float) -> float:
        """
        Calculate estimated profit based on opportunity score and product characteristics.
        Business-grade profit estimation with multiple factors.
        """
        base_price = product.get('price', 0)
        discount_percentage = product.get('discount_percentage', 0)
        
        # Base profit calculation
        if discount_percentage > 0:
            # Use discount as primary profit indicator
            base_profit = base_price * (discount_percentage / 100) * 0.7  # 70% of discount as profit
        else:
            # Use opportunity score for profit estimation
            profit_rate = min(opportunity_score / 100 * 0.3, 0.4)  # Max 40% profit rate
            base_profit = base_price * profit_rate
        
        # Apply business-grade adjustments
        if product.get('brand') in ['APPLE', 'SAMSUNG', 'NINTENDO']:
            base_profit *= 1.2  # 20% premium for high-demand brands
        
        if product.get('category') in ['Gaming', 'Smartphones']:
            base_profit *= 1.15  # 15% bonus for high-velocity categories
        
        # Ensure minimum profit amount
        return max(base_profit, self.min_profit_amount if base_profit > 5 else 0)
    
    def calculate_urgency(self, product: Dict[str, Any], estimated_profit: float) -> str:
        """Calculate urgency level for the opportunity."""
        discount_percentage = product.get('discount_percentage', 0)
        availability = product.get('availability', 'unknown')
        
        if estimated_profit >= 100 and discount_percentage >= 40:
            return "CRITICAL"
        elif estimated_profit >= 50 and discount_percentage >= 25:
            return "HIGH"
        elif estimated_profit >= 25:
            return "MEDIUM"
        else:
            return "LOW"
    
    def is_high_value_opportunity(self, opportunity: Dict[str, Any]) -> bool:
        """Check if this is a high-value opportunity worthy of immediate notification."""
        return (
            opportunity.get('estimated_profit', 0) >= 50 and
            opportunity.get('opportunity_score', 0) >= 75 and
            opportunity.get('urgency') in ['HIGH', 'CRITICAL']
        )
    
    async def notify_high_value_opportunities(self, opportunities: List[Dict[str, Any]]):
        """Send Telegram notifications for high-value opportunities."""
        try:
            # Sort by profit and take top 3 to avoid spam
            top_opportunities = sorted(
                opportunities, 
                key=lambda x: x.get('estimated_profit', 0), 
                reverse=True
            )[:3]
            
            for opportunity in top_opportunities:
                # Check if we already notified about this product recently
                cache_key = f"{opportunity['product_id']}_{opportunity['estimated_profit']:.0f}"
                
                if cache_key not in self.notification_sent_cache:
                    await self.send_opportunity_notification(opportunity)
                    self.notification_sent_cache.add(cache_key)
                    
                    # Clean old cache entries (keep last 100)
                    if len(self.notification_sent_cache) > 100:
                        old_items = list(self.notification_sent_cache)[:50]
                        self.notification_sent_cache -= set(old_items)
        
        except Exception as e:
            logger.error("Failed to send high-value notifications", error=str(e))
    
    async def send_opportunity_notification(self, opportunity: Dict[str, Any]):
        """Send a formatted Telegram notification for a business opportunity."""
        try:
            title = opportunity['title'][:50] + "..." if len(opportunity['title']) > 50 else opportunity['title']
            price = opportunity['price']
            estimated_profit = opportunity['estimated_profit']
            profit_margin = opportunity['profit_margin']
            urgency = opportunity['urgency']
            quality_grade = opportunity.get('quality_grade', 'B')
            discount = opportunity.get('discount_percentage', 0)
            
            # Create urgency emoji
            urgency_emoji = {
                'CRITICAL': '🚨',
                'HIGH': '⚡',
                'MEDIUM': '📈',
                'LOW': '📊'
            }
            
            # Create notification message
            message_title = f"{urgency_emoji.get(urgency, '📊')} ARBITRAGE OPPORTUNITY - {urgency}"
            
            message_body = f"""
**{title}**

💰 **Price**: €{price:.2f}
💎 **Estimated Profit**: €{estimated_profit:.2f}
📊 **Profit Margin**: {profit_margin:.1f}%
⭐ **Quality Grade**: {quality_grade}
{f"🏷️ **Discount**: {discount:.0f}%" if discount > 0 else ""}

🏪 **Source**: MediaMarkt.pt
⏰ **Detected**: {datetime.now().strftime('%H:%M:%S')}

**Opportunity Breakdown**:
• Brand: {opportunity['opportunity_breakdown']['brand']['grade']}
• Category: {opportunity['opportunity_breakdown']['category']['grade']}
• Discount: {opportunity['opportunity_breakdown']['discount']['grade']}

**Urgency**: {urgency} - Act fast for maximum profit!
"""
            
            success = await send_telegram_notification(message_title, message_body)
            
            if success:
                logger.info("Business opportunity notification sent", 
                           title=title,
                           profit=estimated_profit,
                           urgency=urgency)
            else:
                logger.error("Failed to send opportunity notification", 
                            title=title)
                
        except Exception as e:
            logger.error("Error sending opportunity notification", 
                        opportunity_id=opportunity.get('product_id'),
                        error=str(e))
    
    async def store_opportunity(self, opportunity: Dict[str, Any], db: AsyncIOMotorDatabase):
        """Store the opportunity in the database for tracking."""
        try:
            # Prepare opportunity for storage
            opportunity_doc = {
                **opportunity,
                "created_at": datetime.utcnow(),
                "status": "active",
                "notifications_sent": 1 if self.is_high_value_opportunity(opportunity) else 0
            }
            
            # Upsert the opportunity
            await db.price_alerts.replace_one(
                {"product_id": opportunity['product_id']},
                opportunity_doc,
                upsert=True
            )
            
            logger.debug("Business opportunity stored", 
                        product_id=opportunity['product_id'],
                        profit=opportunity['estimated_profit'])
            
        except Exception as e:
            logger.error("Failed to store opportunity", 
                        product_id=opportunity.get('product_id'),
                        error=str(e))


# Business-grade convenience functions
async def analyze_scraped_products_for_arbitrage(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Analyze scraped products for arbitrage opportunities and send notifications.
    Business-grade wrapper function for easy integration.
    
    Args:
        products: List of scraped products from MediaMarkt
        
    Returns:
        List of arbitrage opportunities
    """
    detector = ArbitrageDetector()
    return await detector.analyze_products_for_opportunities(products)


async def run_business_arbitrage_analysis(max_pages: int = 20, max_products: int = 500) -> Dict[str, Any]:
    """
    Complete business-grade arbitrage analysis workflow.
    Scrapes products and analyzes them for opportunities.
    
    Args:
        max_pages: Maximum pages to scrape
        max_products: Maximum products to analyze
        
    Returns:
        Analysis results with opportunities and metrics
    """
    from src.services.scraper.mediamarkt_scraper import scrape_mediamarkt_products_business_grade
    
    start_time = datetime.now()
    
    try:
        logger.info("Starting complete business arbitrage analysis",
                   max_pages=max_pages,
                   max_products=max_products)
        
        # Step 1: Scrape products
        products = await scrape_mediamarkt_products_business_grade(
            max_pages=max_pages, 
            max_products=max_products
        )
        
        # Step 2: Analyze for opportunities
        opportunities = await analyze_scraped_products_for_arbitrage(products)
        
        # Step 3: Calculate metrics
        execution_time = (datetime.now() - start_time).total_seconds()
        
        high_value_opportunities = [
            opp for opp in opportunities 
            if opp.get('urgency') in ['HIGH', 'CRITICAL']
        ]
        
        total_profit_potential = sum(opp.get('estimated_profit', 0) for opp in opportunities)
        
        results = {
            "execution_time": execution_time,
            "products_scraped": len(products),
            "opportunities_found": len(opportunities),
            "high_value_opportunities": len(high_value_opportunities),
            "total_profit_potential": total_profit_potential,
            "average_profit_per_opportunity": total_profit_potential / len(opportunities) if opportunities else 0,
            "top_opportunities": opportunities[:10],  # Top 10 opportunities
            "analysis_timestamp": datetime.utcnow(),
            "business_grade": True
        }
        
        logger.info("Business arbitrage analysis completed",
                   **{k: v for k, v in results.items() if k != 'top_opportunities'})
        
        return results
        
    except Exception as e:
        logger.error("Business arbitrage analysis failed", error=str(e))
        return {
            "error": str(e),
            "execution_time": (datetime.now() - start_time).total_seconds(),
            "business_grade": False
        } 