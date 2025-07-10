"""
Products API Endpoints

Endpoints for retrieving and managing product data from MediaMarkt scraping.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from src.config.database import get_db_session
from src.models.product import Product
from src.models.schemas import (
    ProductResponse,
    ProductListResponse,
    PaginationResponse
)

# Add logger
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=ProductListResponse)
async def get_products(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by category"),
    brand: Optional[str] = Query(None, description="Filter by brand"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price filter"),
    min_discount: Optional[float] = Query(None, ge=0, le=100, description="Minimum discount percentage"),
    in_stock: Optional[bool] = Query(None, description="Filter by stock availability"),
    has_asin: Optional[bool] = Query(None, description="Filter products with/without ASIN"),
    search: Optional[str] = Query(None, description="Search in product name"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    db: AsyncSession = Depends(get_db_session)
) -> ProductListResponse:
    """
    Get paginated list of products with filtering and sorting options.
    
    Args:
        page: Page number (1-based)
        size: Number of items per page (max 100)
        category: Filter by product category
        brand: Filter by brand name
        min_price: Minimum price filter
        max_price: Maximum price filter  
        min_discount: Minimum discount percentage filter
        in_stock: Filter by stock availability
        has_asin: Filter products with/without ASIN matches
        search: Search term for product names
        sort_by: Field to sort by (created_at, current_price, discount_percentage, name)
        sort_order: Sort direction (asc/desc)
        db: Database session
        
    Returns:
        ProductListResponse with paginated products and metadata
    """
    try:
        # Build base query
        query = select(Product).options(
            selectinload(Product.asin_matches)
        )
        
        # Apply filters
        filters = []
        
        if category:
            filters.append(Product.category.ilike(f"%{category}%"))
            
        if brand:
            filters.append(Product.brand.ilike(f"%{brand}%"))
            
        if min_price is not None:
            filters.append(Product.current_price >= min_price)
            
        if max_price is not None:
            filters.append(Product.current_price <= max_price)
            
        if min_discount is not None:
            filters.append(Product.discount_percentage >= min_discount)
            
        if in_stock is not None:
            filters.append(Product.in_stock == in_stock)
            
        if has_asin is not None:
            if has_asin:
                filters.append(Product.asin.isnot(None))
            else:
                filters.append(Product.asin.is_(None))
                
        if search:
            filters.append(Product.name.ilike(f"%{search}%"))
        
        if filters:
            query = query.where(and_(*filters))
        
        # Count total items
        count_query = select(func.count(Product.id)).where(and_(*filters) if filters else True)
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        # Apply sorting
        valid_sort_fields = {
            "created_at": Product.created_at,
            "current_price": Product.current_price,
            "discount_percentage": Product.discount_percentage,
            "name": Product.name,
            "brand": Product.brand
        }
        
        sort_field = valid_sort_fields.get(sort_by, Product.created_at)
        
        if sort_order == "desc":
            query = query.order_by(sort_field.desc())
        else:
            query = query.order_by(sort_field.asc())
        
        # Apply pagination
        offset = (page - 1) * size
        query = query.offset(offset).limit(size)
        
        # Execute query
        result = await db.execute(query)
        products = result.scalars().all()
        
        # Calculate pagination metadata
        total_pages = (total + size - 1) // size
        has_next = page < total_pages
        has_prev = page > 1
        
        pagination = PaginationResponse(
            page=page,
            size=size,
            total=total,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev
        )
        
        # Convert to response models
        product_responses = [ProductResponse.from_orm(product) for product in products]
        
        return ProductListResponse(
            products=product_responses,
            pagination=pagination
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving products: {str(e)}")


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int = Path(..., description="Product ID"),
    db: AsyncSession = Depends(get_db_session)
) -> ProductResponse:
    """
    Get a specific product by ID with all related data.
    
    Args:
        product_id: The product ID to retrieve
        db: Database session
        
    Returns:
        ProductResponse with complete product data
        
    Raises:
        HTTPException: 404 if product not found
    """
    try:
        # Query with eager loading of relationships
        query = (
            select(Product)
            .options(selectinload(Product.asin_matches))
            .where(Product.id == product_id)
        )
        
        result = await db.execute(query)
        product = result.scalar_one_or_none()
        
        if not product:
            raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found")
        
        return ProductResponse.from_orm(product)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving product: {str(e)}")


@router.get("/{product_id}/history")
async def get_product_price_history(
    product_id: int = Path(..., description="Product ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days of history"),
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Get price history for a specific product.
    
    Args:
        product_id: The product ID
        days: Number of days of price history to retrieve
        db: Database session
        
    Returns:
        Price history data with statistics and trend analysis
        
    Raises:
        HTTPException: 404 if product not found
    """
    try:
        # Get product with ASIN matches
        product_query = (
            select(Product)
            .options(selectinload(Product.asin_matches))
            .where(Product.id == product_id)
        )
        
        result = await db.execute(product_query)
        product = result.scalar_one_or_none()
        
        if not product:
            raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found")
        
        # Try to get price history from Keepa API if ASIN is available
        price_history = []
        has_keepa_data = False
        best_match = None
        
        if product.asin_matches:
            try:
                from src.integrations.keepa_api import KepaAPI
                from src.config.settings import get_settings
                
                settings = get_settings()
                if settings.keepa.api_key:
                    logger.info(f"Fetching Keepa price history for product {product_id}")
                    keepa_client = KepaAPI()
                    
                    # Get the best ASIN match
                    best_match = max(product.asin_matches, key=lambda x: x.confidence_score)
                    
                    # Fetch price history from Keepa
                    keepa_data = await keepa_client.get_price_history(
                        asin=best_match.asin,
                        marketplace="ES",  # MediaMarkt is in Portugal, but Amazon ES is closest
                        days=days
                    )
                    
                    if keepa_data and "price_history" in keepa_data:
                        has_keepa_data = True
                        logger.info(f"Retrieved {len(keepa_data['price_history'])} price points from Keepa")
                        
                        for entry in keepa_data["price_history"]:
                            price_history.append({
                                "timestamp": entry["timestamp"],
                                "price": entry["price"],
                                "source": "amazon_keepa"
                            })
                    else:
                        logger.warning(f"No price history data returned from Keepa for ASIN {best_match.asin}")
                else:
                    logger.warning("Keepa API key not configured - cannot fetch price history")
                    
            except ImportError as e:
                logger.error(f"Keepa API client not properly configured: {e}")
            except Exception as e:
                logger.warning(f"Failed to fetch Keepa price history for product {product_id}: {e}")
        else:
            logger.info(f"No ASIN matches found for product {product_id} - using MediaMarkt data only")
        
        # If no Keepa data, create price points from product data
        if not has_keepa_data:
            # Add current price as most recent data point
            price_history.append({
                "timestamp": product.updated_at.isoformat() if product.updated_at else product.created_at.isoformat(),
                "price": float(product.current_price),
                "source": "mediamarkt_current"
            })
            
            # Add original price as historical point if available
            if product.original_price and product.original_price != product.current_price:
                # Estimate when the discount started (7 days ago as default)
                discount_start = product.created_at - timedelta(days=7)
                price_history.append({
                    "timestamp": discount_start.isoformat(),
                    "price": float(product.original_price),
                    "source": "mediamarkt_original"
                })
        
        # Sort by timestamp
        price_history.sort(key=lambda x: x["timestamp"])
        
        # Calculate price statistics
        prices = [entry["price"] for entry in price_history]
        stats = {
            "min_price": min(prices) if prices else None,
            "max_price": max(prices) if prices else None,
            "avg_price": sum(prices) / len(prices) if prices else None,
            "current_price": float(product.current_price),
            "original_price": float(product.original_price) if product.original_price else None,
            "discount_percentage": float(product.discount_percentage) if product.discount_percentage else None
        }
        
        # Calculate price trend analysis
        trend_analysis = None
        if len(price_history) >= 2:
            recent_price = price_history[-1]["price"]
            older_price = price_history[0]["price"] 
            price_change = recent_price - older_price
            price_change_percent = (price_change / older_price * 100) if older_price > 0 else 0
            
            trend_analysis = {
                "price_change": round(price_change, 2),
                "price_change_percent": round(price_change_percent, 2),
                "trend_direction": "up" if price_change > 0 else "down" if price_change < 0 else "stable",
                "volatility": round(max(prices) - min(prices), 2) if prices else 0
            }
        
        response_data = {
            "product_id": product_id,
            "product_name": product.name,
            "asin": best_match.asin if best_match else None,
            "marketplace": "ES" if has_keepa_data else "PT",
            "days_requested": days,
            "days_available": len(set(entry["timestamp"][:10] for entry in price_history)),
            "has_keepa_data": has_keepa_data,
            "price_history": price_history,
            "statistics": stats,
            "trend_analysis": trend_analysis,
            "total_data_points": len(price_history)
        }
        
        logger.info(f"Successfully generated price history for product {product_id} with {len(price_history)} data points")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving price history for product {product_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving price history: {str(e)}")


@router.get("/{product_id}/matches")
async def get_product_matches(
    product_id: int = Path(..., description="Product ID"),
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Get ASIN matches for a specific product.
    
    Args:
        product_id: The product ID
        db: Database session
        
    Returns:
        Product matches with confidence scores and details
        
    Raises:
        HTTPException: 404 if product not found
    """
    try:
        # Query product with matches
        query = (
            select(Product)
            .options(selectinload(Product.asin_matches))
            .where(Product.id == product_id)
        )
        
        result = await db.execute(query)
        product = result.scalar_one_or_none()
        
        if not product:
            raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found")
        
        matches = []
        for match in product.asin_matches:
            matches.append({
                "asin": match.asin,
                "confidence_score": float(match.confidence_score),
                "match_method": match.match_method,
                "created_at": match.created_at.isoformat()
            })
        
        return {
            "product_id": product_id,
            "product_name": product.name,
            "total_matches": len(matches),
            "matches": matches,
            "best_match": matches[0] if matches else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving product matches: {str(e)}")