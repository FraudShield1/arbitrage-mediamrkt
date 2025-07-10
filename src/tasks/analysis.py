"""
Price analysis background tasks.
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, join
import structlog

from src.config.celery import celery_app, CallbackTask, TaskErrorHandler
from src.config.database import get_database_session
from src.models.product import Product
from src.models.asin import ASIN
from src.models.alert import ProductAsinMatch, PriceAlert
from src.services.analyzer.price_analyzer import PriceAnalyzer
from src.services.analyzer.profit_calculator import ProfitCalculator
from src.integrations.keepa_api import KeepaAPIClient
from src.tasks.notifications import send_arbitrage_alert

logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, base=CallbackTask, name="src.tasks.analysis.analyze_price_opportunities")
def analyze_price_opportunities(
    self,
    limit: int = 500,
    min_profit_percentage: float = 30.0
) -> Dict[str, Any]:
    """
    Analyze matched products for arbitrage opportunities.
    
    Args:
        limit: Maximum number of products to analyze
        min_profit_percentage: Minimum profit percentage to trigger alert
        
    Returns:
        Analysis statistics
    """
    return asyncio.run(_analyze_price_opportunities_async(
        task_id=self.request.id,
        limit=limit,
        min_profit_percentage=min_profit_percentage
    ))


async def _analyze_price_opportunities_async(
    task_id: str,
    limit: int = 500,
    min_profit_percentage: float = 30.0
) -> Dict[str, Any]:
    """Async implementation of price opportunity analysis."""
    stats = {
        "task_id": task_id,
        "start_time": datetime.utcnow(),
        "products_analyzed": 0,
        "opportunities_found": 0,
        "alerts_created": 0,
        "total_profit_potential": Decimal("0.00"),
        "errors": [],
        "status": "running"
    }
    
    db_session = None
    
    try:
        # Initialize database session
        async for db_session in get_database_session():
            break
        
        logger.info(
            "Starting price opportunity analysis",
            task_id=task_id,
            limit=limit,
            min_profit_percentage=min_profit_percentage
        )
        
        # Get matched products for analysis
        matched_products = await _get_products_for_analysis(db_session, limit)
        
        if not matched_products:
            logger.info("No matched products found for analysis")
            stats["status"] = "completed"
            return stats
        
        logger.info(f"Found {len(matched_products)} matched products to analyze")
        
        # Initialize analyzers
        price_analyzer = PriceAnalyzer()
        profit_calculator = ProfitCalculator()
        
        # Process each product
        for product_match in matched_products:
            try:
                analysis_result = await _analyze_product_opportunity(
                    product_match=product_match,
                    price_analyzer=price_analyzer,
                    profit_calculator=profit_calculator,
                    min_profit_percentage=min_profit_percentage,
                    db_session=db_session
                )
                
                stats["products_analyzed"] += 1
                
                if analysis_result["is_opportunity"]:
                    stats["opportunities_found"] += 1
                    stats["total_profit_potential"] += analysis_result["profit_potential"]
                    
                    # Create alert if new opportunity
                    if analysis_result["alert_created"]:
                        stats["alerts_created"] += 1
                        
                        # Trigger immediate notification for high-value opportunities
                        if analysis_result["profit_potential"] > 50:
                            send_arbitrage_alert.delay(
                                alert_id=analysis_result["alert_id"],
                                priority="high"
                            )
                
                # Commit after each product to avoid long transactions
                await db_session.commit()
                
            except Exception as e:
                error_msg = f"Error analyzing product ID {product_match['product'].id}: {str(e)}"
                stats["errors"].append(error_msg)
                logger.error(error_msg, task_id=task_id, product_id=product_match['product'].id)
                TaskErrorHandler.handle_analysis_error(e, task_id, product_match['asin'].asin)
                continue
        
        stats["status"] = "completed"
        stats["end_time"] = datetime.utcnow()
        stats["duration"] = (stats["end_time"] - stats["start_time"]).total_seconds()
        
        logger.info(
            "Completed price opportunity analysis",
            task_id=task_id,
            **{k: v for k, v in stats.items() if k not in ["errors", "start_time", "end_time"]}
        )
        
        return stats
        
    except Exception as e:
        stats["status"] = "failed"
        stats["end_time"] = datetime.utcnow()
        error_msg = f"Critical error in analysis task: {str(e)}"
        stats["errors"].append(error_msg)
        
        logger.error(error_msg, task_id=task_id)
        TaskErrorHandler.handle_analysis_error(e, task_id)
        raise
        
    finally:
        if db_session:
            await db_session.close()


async def _get_products_for_analysis(
    db_session: AsyncSession,
    limit: int
) -> List[Dict[str, Any]]:
    """Get matched products that need price analysis."""
    
    # Get products with matches, prioritizing those not analyzed recently
    result = await db_session.execute(
        select(Product, ASIN, ProductAsinMatch)
        .select_from(
            Product
            .join(ProductAsinMatch, Product.id == ProductAsinMatch.product_id)
            .join(ASIN, ProductAsinMatch.asin_id == ASIN.id)
        )
        .where(
            and_(
                Product.price.isnot(None),  # Must have price
                Product.stock_status.in_(["in_stock", "limited_stock"]),  # Must be available
                Product.last_seen >= datetime.utcnow() - timedelta(days=7),  # Recent data
                or_(
                    Product.last_analysis.is_(None),  # Never analyzed
                    Product.last_analysis <= datetime.utcnow() - timedelta(hours=6)  # Not analyzed recently
                )
            )
        )
        .order_by(Product.last_analysis.asc().nullsfirst())
        .limit(limit)
    )
    
    rows = result.all()
    
    return [
        {
            "product": row[0],
            "asin": row[1], 
            "match": row[2]
        }
        for row in rows
    ]


async def _analyze_product_opportunity(
    product_match: Dict[str, Any],
    price_analyzer: PriceAnalyzer,
    profit_calculator: ProfitCalculator,
    min_profit_percentage: float,
    db_session: AsyncSession
) -> Dict[str, Any]:
    """Analyze a single product for arbitrage opportunity."""
    
    product = product_match["product"]
    asin_obj = product_match["asin"]
    match = product_match["match"]
    
    logger.debug(f"Analyzing product {product.id} - ASIN {asin_obj.asin}")
    
    # Update product last analysis timestamp
    product.last_analysis = datetime.utcnow()
    
    try:
        # Fetch fresh Keepa data
        keepa_data = await KeepaAPIClient().get_price_history(
            asin=asin_obj.asin,
            marketplace_id=8,  # Germany
            days=30
        )
        
        if not keepa_data:
            logger.warning(f"No Keepa data available for ASIN {asin_obj.asin}")
            return {"is_opportunity": False}
        
        # Analyze price patterns
        price_analysis = await price_analyzer.analyze_price_history(
            price_history=keepa_data,
            current_mediamarkt_price=float(product.price)
        )
        
        if not price_analysis["is_anomaly"]:
            logger.debug(f"No price anomaly detected for product {product.id}")
            return {"is_opportunity": False}
        
        # Calculate profit potential
        profit_analysis = await profit_calculator.calculate_arbitrage_profit(
            mediamarkt_price=float(product.price),
            amazon_price_stats=price_analysis["price_stats"],
            product_category=product.category,
            weight_estimate=None  # Will be estimated
        )
        
        if profit_analysis["profit_percentage"] < min_profit_percentage:
            logger.debug(
                f"Profit too low for product {product.id}: {profit_analysis['profit_percentage']:.1f}%"
            )
            return {"is_opportunity": False}
        
        # Check if alert already exists
        existing_alert = await db_session.execute(
            select(PriceAlert).where(
                and_(
                    PriceAlert.product_id == product.id,
                    PriceAlert.asin_id == asin_obj.id,
                    PriceAlert.status.in_(["active", "pending"]),
                    PriceAlert.created_at >= datetime.utcnow() - timedelta(days=1)  # Recent alert
                )
            )
        )
        
        if existing_alert.scalar_one_or_none():
            logger.debug(f"Alert already exists for product {product.id}")
            return {
                "is_opportunity": True,
                "profit_potential": Decimal(str(profit_analysis["profit_amount"])),
                "alert_created": False
            }
        
        # Create new alert
        severity = _determine_alert_severity(
            profit_percentage=profit_analysis["profit_percentage"],
            profit_amount=profit_analysis["profit_amount"],
            confidence_score=match.confidence_score
        )
        
        alert = PriceAlert(
            product_id=product.id,
            asin_id=asin_obj.id,
            alert_type="arbitrage_opportunity",
            severity=severity,
            price_difference=Decimal(str(profit_analysis["price_difference"])),
            profit_potential=Decimal(str(profit_analysis["profit_amount"])),
            profit_percentage=Decimal(str(profit_analysis["profit_percentage"])),
            confidence_score=match.confidence_score,
            mediamarkt_price=product.price,
            amazon_average_price=Decimal(str(price_analysis["price_stats"]["average"])),
            analysis_data={
                "price_analysis": price_analysis,
                "profit_analysis": profit_analysis,
                "match_type": match.match_type
            },
            status="active",
            created_at=datetime.utcnow()
        )
        
        db_session.add(alert)
        await db_session.flush()  # Get the alert ID
        
        logger.info(
            f"Created {severity} arbitrage alert",
            product_id=product.id,
            asin=asin_obj.asin,
            profit_percentage=profit_analysis["profit_percentage"],
            profit_amount=profit_analysis["profit_amount"]
        )
        
        return {
            "is_opportunity": True,
            "profit_potential": Decimal(str(profit_analysis["profit_amount"])),
            "alert_created": True,
            "alert_id": alert.id
        }
        
    except Exception as e:
        logger.error(
            f"Failed to analyze product {product.id}",
            error=str(e),
            asin=asin_obj.asin
        )
        return {"is_opportunity": False}


def _determine_alert_severity(
    profit_percentage: float,
    profit_amount: float,
    confidence_score: float
) -> str:
    """Determine alert severity based on profit potential and confidence."""
    
    # Adjust thresholds based on confidence
    confidence_multiplier = confidence_score
    
    adjusted_profit_percentage = profit_percentage * confidence_multiplier
    adjusted_profit_amount = profit_amount * confidence_multiplier
    
    if adjusted_profit_percentage >= 50 or adjusted_profit_amount >= 100:
        return "critical"
    elif adjusted_profit_percentage >= 40 or adjusted_profit_amount >= 50:
        return "high"
    else:
        return "medium"


@celery_app.task(bind=True, base=CallbackTask, name="src.tasks.analysis.analyze_specific_products")
def analyze_specific_products(
    self,
    product_ids: List[int],
    force_analysis: bool = False
) -> Dict[str, Any]:
    """
    Analyze specific products for arbitrage opportunities.
    
    Args:
        product_ids: List of product IDs to analyze
        force_analysis: Whether to analyze even if recently analyzed
        
    Returns:
        Analysis statistics
    """
    return asyncio.run(_analyze_specific_products_async(
        task_id=self.request.id,
        product_ids=product_ids,
        force_analysis=force_analysis
    ))


async def _analyze_specific_products_async(
    task_id: str,
    product_ids: List[int],
    force_analysis: bool = False
) -> Dict[str, Any]:
    """Async implementation of specific product analysis."""
    stats = {
        "task_id": task_id,
        "products_requested": len(product_ids),
        "products_analyzed": 0,
        "opportunities_found": 0,
        "alerts_created": 0,
        "errors": []
    }
    
    db_session = None
    
    try:
        # Initialize database session
        async for db_session in get_database_session():
            break
        
        # Get specific products with matches
        result = await db_session.execute(
            select(Product, ASIN, ProductAsinMatch)
            .select_from(
                Product
                .join(ProductAsinMatch, Product.id == ProductAsinMatch.product_id)
                .join(ASIN, ProductAsinMatch.asin_id == ASIN.id)
            )
            .where(Product.id.in_(product_ids))
        )
        
        product_matches = [
            {
                "product": row[0],
                "asin": row[1],
                "match": row[2]
            }
            for row in result.all()
        ]
        
        if not product_matches:
            logger.warning(f"No matched products found for IDs: {product_ids}")
            return stats
        
        # Initialize analyzers
        price_analyzer = PriceAnalyzer()
        profit_calculator = ProfitCalculator()
        
        for product_match in product_matches:
            try:
                # Check if recently analyzed and force_analysis is False
                if not force_analysis and product_match["product"].last_analysis:
                    if product_match["product"].last_analysis > datetime.utcnow() - timedelta(hours=1):
                        logger.debug(f"Product {product_match['product'].id} recently analyzed, skipping")
                        continue
                
                analysis_result = await _analyze_product_opportunity(
                    product_match=product_match,
                    price_analyzer=price_analyzer,
                    profit_calculator=profit_calculator,
                    min_profit_percentage=30.0,
                    db_session=db_session
                )
                
                stats["products_analyzed"] += 1
                
                if analysis_result["is_opportunity"]:
                    stats["opportunities_found"] += 1
                    
                    if analysis_result.get("alert_created"):
                        stats["alerts_created"] += 1
                
                await db_session.commit()
                
            except Exception as e:
                error_msg = f"Error analyzing product ID {product_match['product'].id}: {str(e)}"
                stats["errors"].append(error_msg)
                logger.error(error_msg, task_id=task_id, product_id=product_match['product'].id)
                continue
        
        logger.info(
            "Completed specific product analysis",
            task_id=task_id,
            **{k: v for k, v in stats.items() if k != "errors"}
        )
        
        return stats
        
    except Exception as e:
        error_msg = f"Critical error in specific analysis task: {str(e)}"
        stats["errors"].append(error_msg)
        logger.error(error_msg, task_id=task_id)
        TaskErrorHandler.handle_analysis_error(e, task_id)
        raise
        
    finally:
        if db_session:
            await db_session.close()


@celery_app.task(bind=True, base=CallbackTask, name="src.tasks.analysis.update_keepa_data")
def update_keepa_data(
    self,
    asin_list: List[str],
    marketplace_id: int = 8
) -> Dict[str, Any]:
    """
    Update Keepa data for specific ASINs.
    
    Args:
        asin_list: List of ASINs to update
        marketplace_id: Keepa marketplace ID (8 = Germany)
        
    Returns:
        Update statistics
    """
    return asyncio.run(_update_keepa_data_async(
        task_id=self.request.id,
        asin_list=asin_list,
        marketplace_id=marketplace_id
    ))


async def _update_keepa_data_async(
    task_id: str,
    asin_list: List[str],
    marketplace_id: int = 8
) -> Dict[str, Any]:
    """Async implementation of Keepa data update."""
    stats = {
        "task_id": task_id,
        "asins_requested": len(asin_list),
        "asins_updated": 0,
        "asins_failed": 0,
        "errors": []
    }
    
    db_session = None
    
    try:
        # Initialize database session
        async for db_session in get_database_session():
            break
        
        # Process ASINs in batches
        batch_size = 10
        for i in range(0, len(asin_list), batch_size):
            batch = asin_list[i:i + batch_size]
            
            try:
                # Fetch batch data from Keepa
                batch_data = await KeepaAPIClient().get_products(
                    asins=batch,
                    marketplace_id=marketplace_id
                )
                
                for asin, data in batch_data.items():
                    try:
                        # Update ASIN record
                        result = await db_session.execute(
                            select(ASIN).where(ASIN.asin == asin)
                        )
                        asin_obj = result.scalar_one_or_none()
                        
                        if asin_obj:
                            asin_obj.title = data.get("title", asin_obj.title)
                            asin_obj.brand = data.get("brand", asin_obj.brand)
                            asin_obj.category = data.get("category", asin_obj.category)
                            asin_obj.last_updated = datetime.utcnow()
                            
                            stats["asins_updated"] += 1
                        else:
                            logger.warning(f"ASIN {asin} not found in database")
                            stats["asins_failed"] += 1
                            
                    except Exception as e:
                        error_msg = f"Error updating ASIN {asin}: {str(e)}"
                        stats["errors"].append(error_msg)
                        stats["asins_failed"] += 1
                        logger.error(error_msg, task_id=task_id, asin=asin)
                
                await db_session.commit()
                
                # Rate limiting between batches
                await asyncio.sleep(1)
                
            except Exception as e:
                error_msg = f"Error processing batch {i//batch_size + 1}: {str(e)}"
                stats["errors"].append(error_msg)
                logger.error(error_msg, task_id=task_id)
                stats["asins_failed"] += len(batch)
        
        logger.info(
            "Completed Keepa data update",
            task_id=task_id,
            **{k: v for k, v in stats.items() if k != "errors"}
        )
        
        return stats
        
    except Exception as e:
        error_msg = f"Critical error in Keepa update task: {str(e)}"
        stats["errors"].append(error_msg)
        logger.error(error_msg, task_id=task_id)
        raise
        
    finally:
        if db_session:
            await db_session.close() 