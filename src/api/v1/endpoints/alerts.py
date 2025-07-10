"""
Alerts API Endpoints

Endpoints for managing arbitrage alerts and opportunities.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from src.config.database import get_db_session
from src.models.alert import PriceAlert
from src.models.product import Product
from src.models.schemas import (
    AlertResponse,
    AlertListResponse,
    AlertCreateRequest,
    AlertUpdateRequest,
    PaginationResponse
)

router = APIRouter()


@router.get("/", response_model=AlertListResponse)
async def get_alerts(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by alert status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    min_profit: Optional[float] = Query(None, ge=0, description="Minimum profit amount"),
    category: Optional[str] = Query(None, description="Filter by product category"),
    created_after: Optional[datetime] = Query(None, description="Filter alerts created after date"),
    created_before: Optional[datetime] = Query(None, description="Filter alerts created before date"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    db: AsyncSession = Depends(get_db_session)
) -> AlertListResponse:
    """
    Get paginated list of price alerts with filtering and sorting options.
    
    Args:
        page: Page number (1-based)
        size: Number of items per page (max 100)
        status: Filter by alert status (pending, processed, dismissed)
        severity: Filter by severity (critical, high, medium, low)
        min_profit: Minimum profit amount filter
        category: Filter by product category
        created_after: Filter alerts created after this date
        created_before: Filter alerts created before this date
        sort_by: Field to sort by (created_at, profit_amount, severity)
        sort_order: Sort direction (asc/desc)
        db: Database session
        
    Returns:
        AlertListResponse with paginated alerts and metadata
    """
    try:
        # Build base query with product relationship
        query = (
            select(PriceAlert)
            .options(selectinload(PriceAlert.product))
            .join(Product)
        )
        
        # Apply filters
        filters = []
        
        if status:
            filters.append(PriceAlert.status == status)
            
        if severity:
            filters.append(PriceAlert.severity == severity)
            
        if min_profit is not None:
            filters.append(PriceAlert.profit_amount >= min_profit)
            
        if category:
            filters.append(Product.category.ilike(f"%{category}%"))
            
        if created_after:
            filters.append(PriceAlert.created_at >= created_after)
            
        if created_before:
            filters.append(PriceAlert.created_at <= created_before)
        
        if filters:
            query = query.where(and_(*filters))
        
        # Count total items
        count_query = (
            select(func.count(PriceAlert.id))
            .join(Product)
            .where(and_(*filters) if filters else True)
        )
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        # Apply sorting
        valid_sort_fields = {
            "created_at": PriceAlert.created_at,
            "profit_amount": PriceAlert.profit_amount,
            "severity": PriceAlert.severity,
            "status": PriceAlert.status
        }
        
        sort_field = valid_sort_fields.get(sort_by, PriceAlert.created_at)
        
        if sort_order == "desc":
            query = query.order_by(sort_field.desc())
        else:
            query = query.order_by(sort_field.asc())
        
        # Apply pagination
        offset = (page - 1) * size
        query = query.offset(offset).limit(size)
        
        # Execute query
        result = await db.execute(query)
        alerts = result.scalars().all()
        
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
        alert_responses = [AlertResponse.from_orm(alert) for alert in alerts]
        
        return AlertListResponse(
            alerts=alert_responses,
            pagination=pagination
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving alerts: {str(e)}")


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: int = Path(..., description="Alert ID"),
    db: AsyncSession = Depends(get_db_session)
) -> AlertResponse:
    """
    Get a specific alert by ID with all related data.
    
    Args:
        alert_id: The alert ID to retrieve
        db: Database session
        
    Returns:
        AlertResponse with complete alert data
        
    Raises:
        HTTPException: 404 if alert not found
    """
    try:
        # Query with eager loading of relationships
        query = (
            select(PriceAlert)
            .options(selectinload(PriceAlert.product))
            .where(PriceAlert.id == alert_id)
        )
        
        result = await db.execute(query)
        alert = result.scalar_one_or_none()
        
        if not alert:
            raise HTTPException(status_code=404, detail=f"Alert with ID {alert_id} not found")
        
        return AlertResponse.from_orm(alert)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving alert: {str(e)}")


@router.post("/{alert_id}/process")
async def process_alert(
    request: AlertUpdateRequest,
    alert_id: int = Path(..., description="Alert ID"),
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Process or update the status of a specific alert.
    
    Args:
        alert_id: The alert ID to process
        request: Processing request with new status and optional notes
        db: Database session
        
    Returns:
        Updated alert information
        
    Raises:
        HTTPException: 404 if alert not found, 400 for invalid status
    """
    try:
        # Check if alert exists
        query = select(PriceAlert).where(PriceAlert.id == alert_id)
        result = await db.execute(query)
        alert = result.scalar_one_or_none()
        
        if not alert:
            raise HTTPException(status_code=404, detail=f"Alert with ID {alert_id} not found")
        
        # Validate status transition
        valid_statuses = ["pending", "processed", "dismissed"]
        if request.status not in valid_statuses:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid status '{request.status}'. Must be one of: {valid_statuses}"
            )
        
        # Update alert
        update_data = {
            "status": request.status,
            "updated_at": datetime.utcnow()
        }
        
        if request.notes:
            update_data["notes"] = request.notes
        
        if request.status == "processed":
            update_data["processed_at"] = datetime.utcnow()
        
        # Execute update
        update_query = (
            update(PriceAlert)
            .where(PriceAlert.id == alert_id)
            .values(**update_data)
        )
        
        await db.execute(update_query)
        await db.commit()
        
        # Fetch updated alert
        updated_query = (
            select(PriceAlert)
            .options(selectinload(PriceAlert.product))
            .where(PriceAlert.id == alert_id)
        )
        
        result = await db.execute(updated_query)
        updated_alert = result.scalar_one()
        
        return {
            "message": f"Alert {alert_id} status updated to '{request.status}'",
            "alert": AlertResponse.from_orm(updated_alert).dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing alert: {str(e)}")


@router.post("/{alert_id}/dismiss")
async def dismiss_alert(
    alert_id: int = Path(..., description="Alert ID"),
    notes: Optional[str] = Query(None, description="Optional dismissal notes"),
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Dismiss a specific alert (convenience endpoint).
    
    Args:
        alert_id: The alert ID to dismiss
        notes: Optional dismissal notes
        db: Database session
        
    Returns:
        Dismissal confirmation
        
    Raises:
        HTTPException: 404 if alert not found
    """
    try:
        # Use the process_alert function
        request = AlertUpdateRequest(status="dismissed", notes=notes)
        return await process_alert(alert_id, request, db)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error dismissing alert: {str(e)}")


@router.get("/stats/summary")
async def get_alert_stats(
    days: int = Query(7, ge=1, le=365, description="Number of days for statistics"),
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Get alert statistics summary.
    
    Args:
        days: Number of days to include in statistics
        db: Database session
        
    Returns:
        Alert statistics and metrics
    """
    try:
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0) - \
                    timedelta(days=days - 1)
        
        # Base query for date range
        base_query = select(PriceAlert).where(
            PriceAlert.created_at >= start_date
        )
        
        # Total alerts
        total_result = await db.execute(
            select(func.count(PriceAlert.id)).where(
                PriceAlert.created_at >= start_date
            )
        )
        total_alerts = total_result.scalar()
        
        # Alerts by status
        status_query = (
            select(PriceAlert.status, func.count(PriceAlert.id))
            .where(PriceAlert.created_at >= start_date)
            .group_by(PriceAlert.status)
        )
        status_result = await db.execute(status_query)
        status_counts = {status: count for status, count in status_result.fetchall()}
        
        # Alerts by severity
        severity_query = (
            select(PriceAlert.severity, func.count(PriceAlert.id))
            .where(PriceAlert.created_at >= start_date)
            .group_by(PriceAlert.severity)
        )
        severity_result = await db.execute(severity_query)
        severity_counts = {severity: count for severity, count in severity_result.fetchall()}
        
        # Profit statistics
        profit_query = (
            select(
                func.sum(PriceAlert.profit_amount),
                func.avg(PriceAlert.profit_amount),
                func.max(PriceAlert.profit_amount),
                func.min(PriceAlert.profit_amount)
            )
            .where(PriceAlert.created_at >= start_date)
        )
        profit_result = await db.execute(profit_query)
        profit_stats = profit_result.fetchone()
        
        return {
            "period": {
                "days": days,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "totals": {
                "total_alerts": total_alerts,
                "by_status": status_counts,
                "by_severity": severity_counts
            },
            "profit_metrics": {
                "total_profit_potential": float(profit_stats[0]) if profit_stats[0] else 0.0,
                "average_profit": float(profit_stats[1]) if profit_stats[1] else 0.0,
                "max_profit": float(profit_stats[2]) if profit_stats[2] else 0.0,
                "min_profit": float(profit_stats[3]) if profit_stats[3] else 0.0
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving alert statistics: {str(e)}")


@router.get("/top-opportunities")
async def get_top_opportunities(
    limit: int = Query(10, ge=1, le=50, description="Number of top opportunities"),
    min_profit: Optional[float] = Query(50.0, ge=0, description="Minimum profit threshold"),
    status: str = Query("pending", description="Alert status filter"),
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Get top arbitrage opportunities by profit potential.
    
    Args:
        limit: Maximum number of opportunities to return
        min_profit: Minimum profit threshold
        status: Alert status filter
        db: Database session
        
    Returns:
        List of top opportunities sorted by profit
    """
    try:
        # Query top opportunities
        query = (
            select(PriceAlert)
            .options(selectinload(PriceAlert.product))
            .where(
                and_(
                    PriceAlert.profit_amount >= min_profit,
                    PriceAlert.status == status
                )
            )
            .order_by(PriceAlert.profit_amount.desc())
            .limit(limit)
        )
        
        result = await db.execute(query)
        opportunities = result.scalars().all()
        
        # Format response
        formatted_opportunities = []
        for alert in opportunities:
            formatted_opportunities.append({
                "alert_id": alert.id,
                "product_name": alert.product.name,
                "brand": alert.product.brand,
                "category": alert.product.category,
                "mediamarkt_price": float(alert.product.current_price),
                "amazon_price": float(alert.amazon_price),
                "profit_amount": float(alert.profit_amount),
                "profit_margin": float(alert.profit_margin),
                "severity": alert.severity,
                "created_at": alert.created_at.isoformat(),
                "product_url": alert.product.url,
                "asin": alert.product.asin
            })
        
        return {
            "top_opportunities": formatted_opportunities,
            "filters": {
                "limit": limit,
                "min_profit": min_profit,
                "status": status
            },
            "total_found": len(formatted_opportunities)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving top opportunities: {str(e)}") 