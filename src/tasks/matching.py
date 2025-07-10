"""
Product matching background tasks.
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
import structlog

from src.config.celery import celery_app, CallbackTask, TaskErrorHandler
from src.config.database import get_database_session
from src.models.product import Product
from src.models.asin import ASIN
from src.models.alert import ProductAsinMatch
from src.services.matcher.ean_matcher import EANMatcher
from src.services.matcher.fuzzy_matcher import FuzzyMatcher
from src.services.matcher.semantic_matcher import SemanticMatcher
from src.integrations.keepa_api import KeepaAPIClient

logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, base=CallbackTask, name="src.tasks.matching.process_unmatched_products")
def process_unmatched_products(
    self,
    limit: int = 1000,
    min_confidence: float = 0.80
) -> Dict[str, Any]:
    """
    Process unmatched products through matching pipeline.
    
    Args:
        limit: Maximum number of products to process
        min_confidence: Minimum confidence score for matches
        
    Returns:
        Matching statistics
    """
    return asyncio.run(_process_unmatched_products_async(
        task_id=self.request.id,
        limit=limit,
        min_confidence=min_confidence
    ))


async def _process_unmatched_products_async(
    task_id: str,
    limit: int = 1000,
    min_confidence: float = 0.80
) -> Dict[str, Any]:
    """Async implementation of unmatched products processing."""
    stats = {
        "task_id": task_id,
        "start_time": datetime.utcnow(),
        "products_processed": 0,
        "ean_matches": 0,
        "fuzzy_matches": 0,
        "semantic_matches": 0,
        "no_matches": 0,
        "errors": [],
        "status": "running"
    }
    
    db_session = None
    
    try:
        # Initialize database session
        async for db_session in get_database_session():
            break
        
        logger.info(
            "Starting unmatched products processing",
            task_id=task_id,
            limit=limit,
            min_confidence=min_confidence
        )
        
        # Get unmatched products
        unmatched_products = await _get_unmatched_products(db_session, limit)
        
        if not unmatched_products:
            logger.info("No unmatched products found")
            stats["status"] = "completed"
            return stats
        
        logger.info(f"Found {len(unmatched_products)} unmatched products")
        
        # Initialize matchers
        ean_matcher = EANMatcher()
        fuzzy_matcher = FuzzyMatcher()
        semantic_matcher = SemanticMatcher()
        
        # Process each product through matching pipeline
        for product in unmatched_products:
            try:
                match_result = await _process_product_matching(
                    product=product,
                    ean_matcher=ean_matcher,
                    fuzzy_matcher=fuzzy_matcher,
                    semantic_matcher=semantic_matcher,
                    min_confidence=min_confidence,
                    db_session=db_session
                )
                
                # Update statistics
                stats["products_processed"] += 1
                if match_result["match_type"] == "ean":
                    stats["ean_matches"] += 1
                elif match_result["match_type"] == "fuzzy":
                    stats["fuzzy_matches"] += 1
                elif match_result["match_type"] == "semantic":
                    stats["semantic_matches"] += 1
                else:
                    stats["no_matches"] += 1
                
                # Commit after each product to avoid long transactions
                await db_session.commit()
                
            except Exception as e:
                error_msg = f"Error processing product ID {product.id}: {str(e)}"
                stats["errors"].append(error_msg)
                logger.error(error_msg, task_id=task_id, product_id=product.id)
                TaskErrorHandler.handle_matching_error(e, task_id, product.id)
                continue
        
        stats["status"] = "completed"
        stats["end_time"] = datetime.utcnow()
        stats["duration"] = (stats["end_time"] - stats["start_time"]).total_seconds()
        
        logger.info(
            "Completed unmatched products processing",
            task_id=task_id,
            **{k: v for k, v in stats.items() if k not in ["errors", "start_time", "end_time"]}
        )
        
        return stats
        
    except Exception as e:
        stats["status"] = "failed"
        stats["end_time"] = datetime.utcnow()
        error_msg = f"Critical error in matching task: {str(e)}"
        stats["errors"].append(error_msg)
        
        logger.error(error_msg, task_id=task_id)
        TaskErrorHandler.handle_matching_error(e, task_id)
        raise
        
    finally:
        if db_session:
            await db_session.close()


async def _get_unmatched_products(
    db_session: AsyncSession,
    limit: int
) -> List[Product]:
    """Get products that don't have ASIN matches."""
    
    # Get products without any ASIN matches
    subquery = select(ProductAsinMatch.product_id).subquery()
    
    result = await db_session.execute(
        select(Product)
        .where(
            and_(
                Product.ean.isnot(None),  # Must have EAN
                Product.id.notin_(select(subquery.c.product_id)),  # No existing matches
                Product.last_seen >= datetime.utcnow() - timedelta(days=30)  # Recent products
            )
        )
        .order_by(Product.created_at.desc())
        .limit(limit)
    )
    
    return result.scalars().all()


async def _process_product_matching(
    product: Product,
    ean_matcher: EANMatcher,
    fuzzy_matcher: FuzzyMatcher,
    semantic_matcher: SemanticMatcher,
    min_confidence: float,
    db_session: AsyncSession
) -> Dict[str, Any]:
    """Process a single product through the matching pipeline."""
    
    logger.debug(f"Processing product matching for ID {product.id}")
    
    # Step 1: Try EAN matching (highest confidence)
    if product.ean:
        try:
            ean_matches = await ean_matcher.find_matches(product.ean)
            if ean_matches:
                best_match = max(ean_matches, key=lambda x: x.get("confidence", 0))
                if best_match.get("confidence", 0) >= 0.95:  # High confidence for EAN
                    await _save_product_match(
                        db_session=db_session,
                        product=product,
                        asin=best_match["asin"],
                        confidence=best_match["confidence"],
                        match_type="ean",
                        match_data=best_match
                    )
                    return {"match_type": "ean", "confidence": best_match["confidence"]}
        except Exception as e:
            logger.warning(f"EAN matching failed for product {product.id}: {str(e)}")
    
    # Step 2: Try fuzzy matching if EAN failed
    try:
        fuzzy_matches = await fuzzy_matcher.find_matches(
            title=product.title,
            brand=product.brand,
            category=product.category
        )
        if fuzzy_matches:
            best_match = max(fuzzy_matches, key=lambda x: x.get("confidence", 0))
            if best_match.get("confidence", 0) >= 0.85:  # Lower confidence for fuzzy
                await _save_product_match(
                    db_session=db_session,
                    product=product,
                    asin=best_match["asin"],
                    confidence=best_match["confidence"],
                    match_type="fuzzy",
                    match_data=best_match
                )
                return {"match_type": "fuzzy", "confidence": best_match["confidence"]}
    except Exception as e:
        logger.warning(f"Fuzzy matching failed for product {product.id}: {str(e)}")
    
    # Step 3: Try semantic matching as last resort
    try:
        semantic_matches = await semantic_matcher.find_matches(
            title=product.title,
            brand=product.brand,
            category=product.category
        )
        if semantic_matches:
            best_match = max(semantic_matches, key=lambda x: x.get("confidence", 0))
            if best_match.get("confidence", 0) >= min_confidence:
                await _save_product_match(
                    db_session=db_session,
                    product=product,
                    asin=best_match["asin"],
                    confidence=best_match["confidence"],
                    match_type="semantic",
                    match_data=best_match
                )
                return {"match_type": "semantic", "confidence": best_match["confidence"]}
    except Exception as e:
        logger.warning(f"Semantic matching failed for product {product.id}: {str(e)}")
    
    # No matches found
    logger.debug(f"No matches found for product {product.id}")
    return {"match_type": "none", "confidence": 0.0}


async def _save_product_match(
    db_session: AsyncSession,
    product: Product,
    asin: str,
    confidence: float,
    match_type: str,
    match_data: Dict[str, Any]
) -> None:
    """Save a product-ASIN match to the database."""
    
    # Check if ASIN exists, create if not
    result = await db_session.execute(
        select(ASIN).where(ASIN.asin == asin)
    )
    asin_obj = result.scalar_one_or_none()
    
    if not asin_obj:
        # Fetch ASIN data from Keepa
        try:
            asin_data = await KeepaAPIClient().get_product(asin, marketplace_id=8)  # Germany
            if asin_data:
                asin_obj = ASIN(
                    asin=asin,
                    title=asin_data.get("title"),
                    brand=asin_data.get("brand"),
                    category=asin_data.get("category"),
                    ean=asin_data.get("ean"),
                    marketplace_id=8,
                    created_at=datetime.utcnow(),
                    last_updated=datetime.utcnow()
                )
                db_session.add(asin_obj)
                await db_session.flush()  # Get the ID
        except Exception as e:
            logger.error(f"Failed to fetch ASIN data for {asin}: {str(e)}")
            return
    
    # Create the match record
    match_record = ProductAsinMatch(
        product_id=product.id,
        asin_id=asin_obj.id,
        confidence_score=confidence,
        match_type=match_type,
        match_data=match_data,
        created_at=datetime.utcnow()
    )
    
    db_session.add(match_record)
    
    logger.info(
        f"Saved {match_type} match",
        product_id=product.id,
        asin=asin,
        confidence=confidence
    )


@celery_app.task(bind=True, base=CallbackTask, name="src.tasks.matching.rematch_products")
def rematch_products(
    self,
    product_ids: List[int],
    force_rematch: bool = False
) -> Dict[str, Any]:
    """
    Rematch specific products.
    
    Args:
        product_ids: List of product IDs to rematch
        force_rematch: Whether to rematch even if already matched
        
    Returns:
        Rematch statistics
    """
    return asyncio.run(_rematch_products_async(
        task_id=self.request.id,
        product_ids=product_ids,
        force_rematch=force_rematch
    ))


async def _rematch_products_async(
    task_id: str,
    product_ids: List[int],
    force_rematch: bool = False
) -> Dict[str, Any]:
    """Async implementation of product rematching."""
    stats = {
        "task_id": task_id,
        "products_requested": len(product_ids),
        "products_processed": 0,
        "matches_found": 0,
        "matches_updated": 0,
        "errors": []
    }
    
    db_session = None
    
    try:
        # Initialize database session
        async for db_session in get_database_session():
            break
        
        # Get products to rematch
        result = await db_session.execute(
            select(Product).where(Product.id.in_(product_ids))
        )
        products = result.scalars().all()
        
        if not products:
            logger.warning(f"No products found for IDs: {product_ids}")
            return stats
        
        # Initialize matchers
        ean_matcher = EANMatcher()
        fuzzy_matcher = FuzzyMatcher()
        semantic_matcher = SemanticMatcher()
        
        for product in products:
            try:
                # Check if already matched and force_rematch is False
                if not force_rematch:
                    existing_match = await db_session.execute(
                        select(ProductAsinMatch).where(
                            ProductAsinMatch.product_id == product.id
                        )
                    )
                    if existing_match.scalar_one_or_none():
                        logger.debug(f"Product {product.id} already matched, skipping")
                        continue
                
                # Remove existing matches if force_rematch
                if force_rematch:
                    await db_session.execute(
                        select(ProductAsinMatch).where(
                            ProductAsinMatch.product_id == product.id
                        ).delete()
                    )
                
                # Process matching
                match_result = await _process_product_matching(
                    product=product,
                    ean_matcher=ean_matcher,
                    fuzzy_matcher=fuzzy_matcher,
                    semantic_matcher=semantic_matcher,
                    min_confidence=0.80,
                    db_session=db_session
                )
                
                stats["products_processed"] += 1
                
                if match_result["match_type"] != "none":
                    if force_rematch:
                        stats["matches_updated"] += 1
                    else:
                        stats["matches_found"] += 1
                
                await db_session.commit()
                
            except Exception as e:
                error_msg = f"Error rematching product ID {product.id}: {str(e)}"
                stats["errors"].append(error_msg)
                logger.error(error_msg, task_id=task_id, product_id=product.id)
                continue
        
        logger.info(
            "Completed product rematching",
            task_id=task_id,
            **{k: v for k, v in stats.items() if k != "errors"}
        )
        
        return stats
        
    except Exception as e:
        error_msg = f"Critical error in rematching task: {str(e)}"
        stats["errors"].append(error_msg)
        logger.error(error_msg, task_id=task_id)
        TaskErrorHandler.handle_matching_error(e, task_id)
        raise
        
    finally:
        if db_session:
            await db_session.close()


@celery_app.task(bind=True, base=CallbackTask, name="src.tasks.matching.cleanup_poor_matches")
def cleanup_poor_matches(
    self,
    min_confidence: float = 0.70
) -> Dict[str, Any]:
    """
    Remove matches with poor confidence scores.
    
    Args:
        min_confidence: Minimum confidence score to keep
        
    Returns:
        Cleanup statistics
    """
    return asyncio.run(_cleanup_poor_matches_async(
        task_id=self.request.id,
        min_confidence=min_confidence
    ))


async def _cleanup_poor_matches_async(
    task_id: str,
    min_confidence: float = 0.70
) -> Dict[str, Any]:
    """Async implementation of poor matches cleanup."""
    stats = {
        "task_id": task_id,
        "matches_removed": 0,
        "errors": []
    }
    
    db_session = None
    
    try:
        # Initialize database session
        async for db_session in get_database_session():
            break
        
        # Find poor matches
        result = await db_session.execute(
            select(ProductAsinMatch).where(
                ProductAsinMatch.confidence_score < min_confidence
            )
        )
        poor_matches = result.scalars().all()
        
        # Remove poor matches
        for match in poor_matches:
            await db_session.delete(match)
            stats["matches_removed"] += 1
        
        await db_session.commit()
        
        logger.info(
            "Completed poor matches cleanup",
            task_id=task_id,
            matches_removed=stats["matches_removed"],
            min_confidence=min_confidence
        )
        
        return stats
        
    except Exception as e:
        error_msg = f"Critical error in cleanup task: {str(e)}"
        stats["errors"].append(error_msg)
        logger.error(error_msg, task_id=task_id)
        raise
        
    finally:
        if db_session:
            await db_session.close() 