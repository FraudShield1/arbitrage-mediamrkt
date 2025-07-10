"""
Scraping background tasks.
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import structlog

from src.config.celery import celery_app, CallbackTask, TaskErrorHandler
from src.config.database import get_database_session
from src.models.product import Product
from src.models.alert import ScrapingSession
from src.services.scraper.mediamarkt_scraper import MediaMarktScraper
from src.services.scraper.proxy_manager import ProxyManager
from src.services.scraper.rate_limiter import RateLimiter

logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, base=CallbackTask, name="src.tasks.scraping.scrape_mediamarkt")
def scrape_mediamarkt(
    self,
    max_products: int = 10000,
    max_pages: int = 100
) -> Dict[str, Any]:
    """
    Scrape MediaMarkt products using unified search endpoint.
    
    Args:
        max_products: Maximum number of products to scrape
        max_pages: Maximum number of pages to process
        
    Returns:
        Task result with statistics
    """
    return asyncio.run(_scrape_mediamarkt_async(
        task_id=self.request.id,
        max_products=max_products,
        max_pages=max_pages
    ))


async def _scrape_mediamarkt_async(
    task_id: str,
    max_products: int = 10000,
    max_pages: int = 100
) -> Dict[str, Any]:
    """Async implementation of MediaMarkt scraping using unified search endpoint."""
    session_stats = {
        "task_id": task_id,
        "start_time": datetime.utcnow(),
        "products_found": 0,
        "products_new": 0,
        "products_updated": 0,
        "pages_processed": 0,
        "errors": [],
        "status": "running"
    }
    
    db_session = None
    scraper = None
    scraping_session_id = None
    
    try:
        # Initialize database session
        async for db_session in get_database_session():
            break
        
        # Create scraping session record
        scraping_session = ScrapingSession(
            task_id=task_id,
            source="mediamarkt",
            status="running",
            start_time=datetime.utcnow(),
            max_products=max_products
        )
        db_session.add(scraping_session)
        await db_session.commit()
        await db_session.refresh(scraping_session)
        scraping_session_id = scraping_session.id
        
        logger.info(
            "Starting MediaMarkt scraping session",
            task_id=task_id,
            session_id=scraping_session_id,
            max_products=max_products,
            max_pages=max_pages
        )
        
        # Initialize scraper with proxy and rate limiting
        proxy_manager = ProxyManager()
        rate_limiter = RateLimiter()
        scraper = MediaMarktScraper(
            proxy_manager=proxy_manager,
            rate_limiter=rate_limiter
        )
        
        await scraper.initialize()
        
        # Scrape using unified search endpoint
        page = 1
        products_found = 0
        
        while page <= max_pages and products_found < max_products:
            try:
                logger.info(f"Scraping page {page}")
                
                # Construct URL with pagination
                url = f"{scraper.search_url}&page={page}"
                
                # Scrape page
                page_products = await scraper.scrape_products_page(url)
                
                if not page_products:
                    logger.info(f"No more products found at page {page}")
                    break
                
                session_stats["pages_processed"] += 1
                
                # Process each product
                for product_data in page_products:
                    try:
                        result = await _process_product_data(
                            db_session=db_session,
                            product_data=product_data,
                            scraping_session_id=scraping_session_id
                        )
                        
                        if result["is_new"]:
                            session_stats["products_new"] += 1
                        else:
                            session_stats["products_updated"] += 1
                        
                        session_stats["products_found"] += 1
                        products_found += 1
                        
                        # Check limit
                        if products_found >= max_products:
                            break
                            
                    except Exception as e:
                        error_msg = f"Error processing product: {str(e)}"
                        session_stats["errors"].append(error_msg)
                        logger.error(error_msg, page=page)
                        continue
                
                page += 1
                
                # Check if we've reached the limit
                if products_found >= max_products:
                    logger.info(f"Reached max products limit: {max_products}")
                    break
                    
            except Exception as e:
                error_msg = f"Error scraping page {page}: {str(e)}"
                session_stats["errors"].append(error_msg)
                logger.error(error_msg, page=page)
                TaskErrorHandler.handle_scraping_error(e, task_id, {"page": page})
                break
        
        session_stats["status"] = "completed"
        session_stats["end_time"] = datetime.utcnow()
        session_stats["duration"] = (session_stats["end_time"] - session_stats["start_time"]).total_seconds()
        
        # Update scraping session in database
        scraping_session.status = "completed"
        scraping_session.end_time = session_stats["end_time"]
        scraping_session.products_found = session_stats["products_found"]
        scraping_session.products_new = session_stats["products_new"] 
        scraping_session.products_updated = session_stats["products_updated"]
        scraping_session.pages_processed = session_stats["pages_processed"]
        scraping_session.error_count = len(session_stats["errors"])
        
        await db_session.commit()
        
        logger.info(
            "Completed MediaMarkt scraping session",
            task_id=task_id,
            session_id=scraping_session_id,
            **{k: v for k, v in session_stats.items() if k not in ["errors", "start_time", "end_time"]}
        )
        
        return session_stats
        
    except Exception as e:
        session_stats["status"] = "failed"
        session_stats["end_time"] = datetime.utcnow()
        error_msg = f"Critical error in scraping task: {str(e)}"
        session_stats["errors"].append(error_msg)
        
        logger.error(error_msg, task_id=task_id)
        TaskErrorHandler.handle_scraping_error(e, task_id)
        
        # Update scraping session status
        if db_session and scraping_session_id:
            try:
                result = await db_session.execute(
                    select(ScrapingSession).where(ScrapingSession.id == scraping_session_id)
                )
                scraping_session = result.scalar_one_or_none()
                if scraping_session:
                    scraping_session.status = "failed"
                    scraping_session.end_time = datetime.utcnow()
                    scraping_session.error_count = len(session_stats["errors"])
                    await db_session.commit()
            except Exception as update_error:
                logger.error(f"Failed to update scraping session: {update_error}")
        
        raise
        
    finally:
        # Cleanup
        if scraper:
            await scraper.close()
        if db_session:
            await db_session.close()


async def _process_product_data(
    db_session: AsyncSession,
    product_data: Dict[str, Any],
    scraping_session_id: int
) -> Dict[str, Any]:
    """Process and save product data to database."""
    
    # Check if product already exists
    result = await db_session.execute(
        select(Product).where(
            and_(
                Product.ean == product_data.get("ean"),
                Product.source == "mediamarkt"
            )
        )
    )
    existing_product = result.scalar_one_or_none()
    
    if existing_product:
        # Update existing product
        existing_product.title = product_data.get("title")
        existing_product.price = product_data.get("price")
        existing_product.original_price = product_data.get("original_price")
        existing_product.discount_percentage = product_data.get("discount_percentage")
        existing_product.brand = product_data.get("brand")
        existing_product.category = product_data.get("category")
        existing_product.stock_status = product_data.get("stock_status")
        existing_product.url = product_data.get("url")
        existing_product.asin = product_data.get("asin")  # Rare but possible
        existing_product.last_seen = datetime.utcnow()
        existing_product.last_scraping_session_id = scraping_session_id
        
        await db_session.commit()
        
        return {"is_new": False, "product_id": existing_product.id}
    
    else:
        # Create new product
        new_product = Product(
            ean=product_data.get("ean"),
            title=product_data.get("title"),
            price=product_data.get("price"),
            original_price=product_data.get("original_price"),
            discount_percentage=product_data.get("discount_percentage"),
            brand=product_data.get("brand"),
            category=product_data.get("category"),
            stock_status=product_data.get("stock_status"),
            url=product_data.get("url"),
            asin=product_data.get("asin"),
            source="mediamarkt",
            created_at=datetime.utcnow(),
            last_seen=datetime.utcnow(),
            last_scraping_session_id=scraping_session_id
        )
        
        db_session.add(new_product)
        await db_session.commit()
        await db_session.refresh(new_product)
        
        return {"is_new": True, "product_id": new_product.id}


@celery_app.task(bind=True, base=CallbackTask, name="src.tasks.scraping.scrape_product_updates")
def scrape_product_updates(self, product_ids: List[int]) -> Dict[str, Any]:
    """
    Update specific products by scraping their current data.
    
    Args:
        product_ids: List of product IDs to update
        
    Returns:
        Update statistics
    """
    return asyncio.run(_scrape_product_updates_async(
        task_id=self.request.id,
        product_ids=product_ids
    ))


async def _scrape_product_updates_async(
    task_id: str,
    product_ids: List[int]
) -> Dict[str, Any]:
    """Async implementation of product updates."""
    stats = {
        "task_id": task_id,
        "products_requested": len(product_ids),
        "products_updated": 0,
        "products_failed": 0,
        "errors": []
    }
    
    db_session = None
    scraper = None
    
    try:
        # Initialize database session
        async for db_session in get_database_session():
            break
        
        # Get products to update
        result = await db_session.execute(
            select(Product).where(Product.id.in_(product_ids))
        )
        products = result.scalars().all()
        
        if not products:
            logger.warning(f"No products found for IDs: {product_ids}")
            return stats
        
        # Initialize scraper
        proxy_manager = ProxyManager()
        rate_limiter = RateLimiter()
        scraper = MediaMarktScraper(
            proxy_manager=proxy_manager,
            rate_limiter=rate_limiter
        )
        await scraper.initialize()
        
        # Update each product
        for product in products:
            try:
                updated_data = await scraper.scrape_product_by_url(product.url)
                
                if updated_data:
                    # Update product data
                    product.price = updated_data.get("price", product.price)
                    product.original_price = updated_data.get("original_price", product.original_price)
                    product.discount_percentage = updated_data.get("discount_percentage", product.discount_percentage)
                    product.stock_status = updated_data.get("stock_status", product.stock_status)
                    product.last_seen = datetime.utcnow()
                    
                    stats["products_updated"] += 1
                else:
                    stats["products_failed"] += 1
                    stats["errors"].append(f"Failed to scrape product ID {product.id}")
                    
            except Exception as e:
                stats["products_failed"] += 1
                error_msg = f"Error updating product ID {product.id}: {str(e)}"
                stats["errors"].append(error_msg)
                logger.error(error_msg, task_id=task_id, product_id=product.id)
        
        await db_session.commit()
        
        logger.info(
            "Completed product updates",
            task_id=task_id,
            **{k: v for k, v in stats.items() if k != "errors"}
        )
        
        return stats
        
    except Exception as e:
        error_msg = f"Critical error in product update task: {str(e)}"
        stats["errors"].append(error_msg)
        logger.error(error_msg, task_id=task_id)
        TaskErrorHandler.handle_scraping_error(e, task_id)
        raise
        
    finally:
        if scraper:
            await scraper.close()
        if db_session:
            await db_session.close() 