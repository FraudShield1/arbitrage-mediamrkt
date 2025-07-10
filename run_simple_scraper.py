#!/usr/bin/env python3
"""
Enhanced Business-Grade MediaMarkt Scraper with MongoDB Integration
- Handles all duplicate scenarios
- Comprehensive database saving
- Business-grade error handling
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List
import hashlib
import structlog

from src.services.scraper.mediamarkt_scraper import scrape_mediamarkt_products_business_grade
from src.config.database import get_database_session, DATABASE_TYPE

logger = structlog.get_logger(__name__)

class ProductDatabaseManager:
    """Handles all database operations for scraped products with comprehensive duplicate handling."""
    
    def __init__(self):
        self.db = None
        self.stats = {
            "total_scraped": 0,
            "new_products": 0,
            "updated_products": 0,
            "duplicates_skipped": 0,
            "errors": 0
        }
    
    async def initialize_database(self):
        """Initialize database connection."""
        if DATABASE_TYPE == 'mongodb':
            self.db = get_database_session()  # Remove await - this returns database directly for MongoDB
            logger.info("MongoDB connection initialized for product storage")
        else:
            logger.error("Only MongoDB supported for this scraper version")
            raise Exception("MongoDB required for enhanced scraper")
    
    def generate_product_fingerprint(self, product: Dict[str, Any]) -> str:
        """Generate unique fingerprint for duplicate detection using multiple fields."""
        # Create fingerprint from title + price + EAN (if available)
        fingerprint_data = f"{product.get('title', '').lower().strip()}"
        fingerprint_data += f"_{product.get('price', 0)}"
        
        # Add EAN if available for better uniqueness
        if product.get('ean'):
            fingerprint_data += f"_{product.get('ean')}"
        
        # Add brand if available
        if product.get('brand'):
            fingerprint_data += f"_{product.get('brand').lower()}"
        
        return hashlib.md5(fingerprint_data.encode()).hexdigest()
    
    async def check_for_duplicates(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Comprehensive duplicate checking using multiple strategies:
        1. EAN-based matching (most reliable)
        2. Title + price matching
        3. Product fingerprint matching
        """
        ean = product.get('ean')
        title = product.get('title', '').strip()
        price = product.get('price', 0)
        fingerprint = self.generate_product_fingerprint(product)
        
        # Strategy 1: EAN-based duplicate detection (most reliable)
        if ean:
            existing_ean = await self.db.products.find_one({
                "ean": ean,
                "source": "mediamarkt"
            })
            if existing_ean:
                return {
                    "is_duplicate": True,
                    "duplicate_type": "ean_match",
                    "existing_id": str(existing_ean["_id"]),
                    "should_update": abs(existing_ean.get("price", 0) - price) > 0.01
                }
        
        # Strategy 2: Title + price exact match
        if title:
            existing_title_price = await self.db.products.find_one({
                "title": title,
                "price": price,
                "source": "mediamarkt"
            })
            if existing_title_price:
                return {
                    "is_duplicate": True,
                    "duplicate_type": "title_price_match",
                    "existing_id": str(existing_title_price["_id"]),
                    "should_update": False  # Exact match, no update needed
                }
        
        # Strategy 3: Fingerprint-based matching (fuzzy duplicates)
        existing_fingerprint = await self.db.products.find_one({
            "product_fingerprint": fingerprint,
            "source": "mediamarkt"
        })
        if existing_fingerprint:
            return {
                "is_duplicate": True,
                "duplicate_type": "fingerprint_match",
                "existing_id": str(existing_fingerprint["_id"]),
                "should_update": abs(existing_fingerprint.get("price", 0) - price) > 0.01
            }
        
        # Strategy 4: Similar title matching (fuzzy)
        if title and len(title) > 10:
            # Use regex for similar titles (same first 20 characters)
            title_prefix = title[:20].lower()
            similar_title = await self.db.products.find_one({
                "title": {"$regex": f"^{title_prefix}", "$options": "i"},
                "source": "mediamarkt",
                "price": {"$gte": price * 0.95, "$lte": price * 1.05}  # Within 5% price range
            })
            if similar_title:
                return {
                    "is_duplicate": True,
                    "duplicate_type": "similar_title_match",
                    "existing_id": str(similar_title["_id"]),
                    "should_update": True  # Update with more recent data
                }
        
        return {"is_duplicate": False}
    
    async def save_product_to_database(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save product to MongoDB with comprehensive duplicate handling.
        Handles all scenarios: new products, exact duplicates, price updates, etc.
        """
        try:
            # Check for duplicates
            duplicate_check = await self.check_for_duplicates(product)
            
            if duplicate_check["is_duplicate"]:
                if duplicate_check.get("should_update", False):
                    # Update existing product with new data
                    result = await self.update_existing_product(
                        duplicate_check["existing_id"], 
                        product, 
                        duplicate_check["duplicate_type"]
                    )
                    self.stats["updated_products"] += 1
                    return result
                else:
                    # Skip exact duplicate
                    self.stats["duplicates_skipped"] += 1
                    logger.debug("Skipping exact duplicate", 
                               title=product.get('title', '')[:50],
                               duplicate_type=duplicate_check["duplicate_type"])
                    return {
                        "action": "skipped",
                        "reason": f"exact_duplicate_{duplicate_check['duplicate_type']}",
                        "existing_id": duplicate_check["existing_id"]
                    }
            
            # Insert new product
            result = await self.insert_new_product(product)
            self.stats["new_products"] += 1
            return result
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error("Failed to save product to database", 
                        error=str(e), 
                        title=product.get('title', '')[:50])
            return {
                "action": "error",
                "error": str(e)
            }
    
    async def insert_new_product(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a new product into the database."""
        # Prepare product document for MongoDB
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
            "scraping_session": {
                "timestamp": datetime.utcnow(),
                "scraper_version": "business_grade_v2"
            }
        }
        
        # Add optional fields if available
        if product.get('url'):
            product_doc['url'] = product['url']
        
        if product.get('quality_indicators'):
            product_doc['quality_indicators'] = product['quality_indicators']
        
        # Insert into MongoDB
        result = await self.db.products.insert_one(product_doc)
        
        logger.debug("New product inserted", 
                    title=product.get('title', '')[:50],
                    price=product.get('price'),
                    product_id=str(result.inserted_id))
        
        return {
            "action": "inserted",
            "product_id": str(result.inserted_id),
            "title": product.get('title', '')[:50]
        }
    
    async def update_existing_product(self, existing_id: str, product: Dict[str, Any], duplicate_type: str) -> Dict[str, Any]:
        """Update an existing product with new data."""
        from bson import ObjectId
        
        update_data = {
            "price": float(product.get('price', 0)),
            "discount_percentage": product.get('discount_percentage'),
            "availability": product.get('availability', 'unknown'),
            "has_discount": product.get('has_discount', False),
            "last_updated": datetime.utcnow(),
            "quality_grade": product.get('quality_grade', 'B'),
            "profit_potential_score": product.get('profit_potential_score', 0)
        }
        
        # Update original price if it's different
        if product.get('original_price'):
            update_data['original_price'] = float(product['original_price'])
        
        # Update title if it's more detailed (longer)
        if product.get('title') and len(product['title']) > 20:
            update_data['title'] = product['title']
        
        result = await self.db.products.update_one(
            {"_id": ObjectId(existing_id)},
            {"$set": update_data}
        )
        
        logger.debug("Product updated", 
                    product_id=existing_id,
                    duplicate_type=duplicate_type,
                    modified_count=result.modified_count)
        
        return {
            "action": "updated",
            "product_id": existing_id,
            "duplicate_type": duplicate_type,
            "modified_count": result.modified_count
        }
    
    async def bulk_save_products(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process and save multiple products with comprehensive duplicate handling."""
        logger.info("Starting bulk product save", total_products=len(products))
        
        self.stats["total_scraped"] = len(products)
        
        for i, product in enumerate(products):
            if i % 100 == 0 and i > 0:
                logger.info("Bulk save progress", 
                           processed=i, 
                           total=len(products),
                           progress=f"{i/len(products)*100:.1f}%")
            
            await self.save_product_to_database(product)
        
        # Generate summary
        summary = {
            "total_processed": self.stats["total_scraped"],
            "new_products": self.stats["new_products"],
            "updated_products": self.stats["updated_products"],
            "duplicates_skipped": self.stats["duplicates_skipped"],
            "errors": self.stats["errors"],
            "success_rate": ((self.stats["new_products"] + self.stats["updated_products"]) / self.stats["total_scraped"] * 100) if self.stats["total_scraped"] > 0 else 0
        }
        
        logger.info("Bulk save completed", **summary)
        return summary

async def main():
    print('🚀 Starting Enhanced Business-Grade MediaMarkt Scraper with MongoDB Integration')
    print('🔥 Features: Duplicate handling, MongoDB storage, comprehensive error handling')
    print('📊 Processing up to 1000 products with database persistence')
    print('')
    
    start_time = datetime.now()
    
    try:
        # Initialize database manager
        db_manager = ProductDatabaseManager()
        await db_manager.initialize_database()
        print('✅ Database connection established')
        
        # Run business-grade scraper
        print('🕷️ Starting MediaMarkt scraping...')
        products = await scrape_mediamarkt_products_business_grade(
            max_pages=50,  # Business-grade page coverage  
            max_products=1000  # Target 1000 products
        )
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        print('')
        print('📊 SCRAPING RESULTS:')
        print('=' * 60)
        print(f'⏱️  Scraping Time: {execution_time:.2f} seconds')
        print(f'📦 Products Scraped: {len(products)}')
        print(f'⚡ Products per Second: {len(products)/execution_time:.2f}')
        print(f'🎯 Success Rate: {len(products)/1000*100:.1f}% of target')
        print('')
        
        # Save to database with comprehensive duplicate handling
        print('💾 Saving products to MongoDB with duplicate handling...')
        db_start_time = datetime.now()
        
        db_summary = await db_manager.bulk_save_products(products)
        
        db_execution_time = (datetime.now() - db_start_time).total_seconds()
        
        print('')
        print('📊 DATABASE SAVE RESULTS:')
        print('=' * 60)
        print(f'⏱️  Database Save Time: {db_execution_time:.2f} seconds')
        print(f'📊 Total Processed: {db_summary["total_processed"]}')
        print(f'🆕 New Products: {db_summary["new_products"]}')
        print(f'🔄 Updated Products: {db_summary["updated_products"]}')
        print(f'🔍 Duplicates Skipped: {db_summary["duplicates_skipped"]}')
        print(f'❌ Errors: {db_summary["errors"]}')
        print(f'✅ Success Rate: {db_summary["success_rate"]:.1f}%')
        print('')
        
        # Analyze product data for insights
        total_discounts = sum(1 for p in products if p.get('has_discount'))
        brands_found = len(set(p.get('brand') for p in products if p.get('brand')))
        categories = {}
        price_ranges = {'<50': 0, '50-200': 0, '200-500': 0, '>500': 0}
        
        for product in products:
            # Count categories
            category = product.get('category', 'Unknown')
            categories[category] = categories.get(category, 0) + 1
            
            # Count price ranges
            price = product.get('price', 0)
            if price < 50:
                price_ranges['<50'] += 1
            elif price < 200:
                price_ranges['50-200'] += 1
            elif price < 500:
                price_ranges['200-500'] += 1
            else:
                price_ranges['>500'] += 1
        
        print('📈 DATA ANALYSIS:')
        print('-' * 40)
        print(f'🏷️  Products with Discounts: {total_discounts} ({total_discounts/len(products)*100:.1f}%)')
        print(f'🏭 Unique Brands Found: {brands_found}')
        print('')
        
        print('📊 Categories Distribution:')
        for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            percentage = count/len(products)*100
            print(f'   {category}: {count} products ({percentage:.1f}%)')
        print('')
        
        print('💰 Price Distribution:')
        for range_name, count in price_ranges.items():
            percentage = count/len(products)*100
            print(f'   €{range_name}: {count} products ({percentage:.1f}%)')
        print('')
        
        # Show top discounted products (from database perspective)
        if db_summary["new_products"] > 0 or db_summary["updated_products"] > 0:
            print('🔥 TOP OPPORTUNITIES SAVED TO DATABASE:')
            print('-' * 60)
            
            # Query top opportunities from database
            top_opportunities = await db_manager.db.products.find({
                "source": "mediamarkt",
                "has_discount": True,
                "profit_potential_score": {"$gt": 50}
            }).sort("profit_potential_score", -1).limit(5).to_list(5)
            
            for i, opportunity in enumerate(top_opportunities, 1):
                title = opportunity['title'][:50] + "..." if len(opportunity['title']) > 50 else opportunity['title']
                print(f'{i}. {title}')
                print(f'   💰 Price: €{opportunity["price"]:.2f}')
                if opportunity.get('discount_percentage'):
                    print(f'   🏷️ Discount: {opportunity["discount_percentage"]:.0f}%')
                print(f'   🏭 Brand: {opportunity.get("brand", "Unknown")}')
                print(f'   ⭐ Grade: {opportunity.get("quality_grade", "B")}')
                print(f'   📊 Opportunity Score: {opportunity.get("profit_potential_score", 0):.1f}')
                print('')
        
        # Save results to file as backup
        results_file = f'enhanced_scraping_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        results_data = {
            "scraping_summary": {
                "products_scraped": len(products),
                "execution_time_seconds": execution_time,
                "scraping_timestamp": start_time.isoformat()
            },
            "database_summary": db_summary,
            "total_execution_time": (datetime.now() - start_time).total_seconds()
        }
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, default=str, ensure_ascii=False)
        
        print(f'💾 Results summary saved to: {results_file}')
        print('')
        print('✅ Enhanced business-grade scraping with MongoDB integration completed!')
        print(f'🎯 Database now contains products ready for arbitrage analysis')
        print(f'⚡ Total execution time: {(datetime.now() - start_time).total_seconds():.2f} seconds')
        
    except Exception as e:
        print(f'❌ Error during enhanced scraping: {str(e)}')
        logger.error("Enhanced scraping failed", error=str(e))
        raise

if __name__ == '__main__':
    asyncio.run(main()) 