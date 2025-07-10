"""
Pydantic schemas for API request/response validation.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
from enum import Enum
import uuid

from pydantic import BaseModel, Field, validator, ConfigDict


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class StockStatus(str, Enum):
    """Product stock status."""
    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "out_of_stock"
    LIMITED = "limited"
    UNKNOWN = "unknown"


class ScrapingStatus(str, Enum):
    """Scraping session status."""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MatchMethod(str, Enum):
    """Product matching methods."""
    EAN = "ean"
    FUZZY = "fuzzy"
    SEMANTIC = "semantic"
    MANUAL = "manual"


# Base schemas
class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )


# Product schemas
class ProductBase(BaseSchema):
    """Base product schema."""
    title: str = Field(..., min_length=1, max_length=500)
    price: Decimal = Field(..., gt=0)
    original_price: Optional[Decimal] = Field(None, gt=0)
    discount_percentage: Optional[float] = Field(None, ge=0, le=100)
    ean: Optional[str] = Field(None, max_length=20)
    asin: Optional[str] = Field(None, min_length=10, max_length=10)
    brand: Optional[str] = Field(None, max_length=100)
    category: str = Field(..., min_length=1, max_length=100)
    stock_status: StockStatus
    url: str = Field(..., min_length=1, max_length=1000)
    # Removed images and specifications to optimize performance


class ProductCreate(ProductBase):
    """Schema for creating a product."""
    scraped_at: datetime
    source: str = Field(default="mediamarkt", max_length=50)


class ProductUpdate(BaseSchema):
    """Schema for updating a product."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    price: Optional[Decimal] = Field(None, gt=0)
    original_price: Optional[Decimal] = Field(None, gt=0)
    discount_percentage: Optional[float] = Field(None, ge=0, le=100)
    stock_status: Optional[StockStatus] = None


class ProductResponse(ProductBase):
    """Schema for product API responses."""
    id: uuid.UUID
    scraped_at: datetime
    source: str
    created_at: datetime
    updated_at: datetime


# ASIN schemas
class ASINBase(BaseSchema):
    """Base ASIN schema."""
    title: str = Field(..., min_length=1, max_length=500)
    brand: Optional[str] = Field(None, max_length=100)
    category: str = Field(..., min_length=1, max_length=100)
    marketplace: str = Field(..., min_length=2, max_length=5)


class ASINCreate(ASINBase):
    """Schema for creating an ASIN."""
    asin: str = Field(..., min_length=10, max_length=10)


class ASINResponse(ASINBase):
    """Schema for ASIN API responses."""
    asin: str
    last_updated: datetime
    created_at: datetime


# Product-ASIN Match schemas
class ProductAsinMatchBase(BaseSchema):
    """Base product-ASIN match schema."""
    confidence_score: Decimal = Field(..., ge=0, le=1)
    match_method: MatchMethod


class ProductAsinMatchCreate(ProductAsinMatchBase):
    """Schema for creating a product-ASIN match."""
    product_id: uuid.UUID
    asin: str = Field(..., min_length=10, max_length=10)


class ProductAsinMatchResponse(ProductAsinMatchBase):
    """Schema for product-ASIN match API responses."""
    id: uuid.UUID
    product_id: uuid.UUID
    asin: str
    created_at: datetime


# Price Alert schemas
class PriceAlertBase(BaseSchema):
    """Base price alert schema."""
    current_price: Decimal = Field(..., gt=0)
    average_price: Decimal = Field(..., gt=0)
    discount_percentage: Decimal = Field(..., ge=0)
    profit_potential: Decimal
    confidence_score: Decimal = Field(..., ge=0, le=1)
    severity: AlertSeverity


class PriceAlertCreate(PriceAlertBase):
    """Schema for creating a price alert."""
    product_id: uuid.UUID
    asin: str = Field(..., min_length=10, max_length=10)


class PriceAlertUpdate(BaseSchema):
    """Schema for updating a price alert."""
    processed_at: Optional[datetime] = None


class PriceAlertResponse(PriceAlertBase):
    """Schema for price alert API responses."""
    id: uuid.UUID
    product_id: uuid.UUID
    asin: str
    processed_at: Optional[datetime] = None
    created_at: datetime


# Keepa Data schemas
class KeepaDataBase(BaseSchema):
    """Base Keepa data schema."""
    price_history: Dict[str, Any]
    sales_rank_history: Optional[Dict[str, Any]] = None
    stats: Dict[str, Any]


class KeepaDataCreate(KeepaDataBase):
    """Schema for creating Keepa data."""
    asin: str = Field(..., min_length=10, max_length=10)
    marketplace: str = Field(..., min_length=2, max_length=5)


class KeepaDataResponse(KeepaDataBase):
    """Schema for Keepa data API responses."""
    asin: str
    marketplace: str
    updated_at: datetime


# Scraping Session schemas
class ScrapingSessionBase(BaseSchema):
    """Base scraping session schema."""
    source: str = Field(..., min_length=1, max_length=50)
    products_scraped: int = Field(default=0, ge=0)
    errors_count: int = Field(default=0, ge=0)
    status: ScrapingStatus = ScrapingStatus.RUNNING
    error_details: Optional[Dict[str, Any]] = None


class ScrapingSessionCreate(BaseSchema):
    """Schema for creating a scraping session."""
    source: str = Field(..., min_length=1, max_length=50)
    started_at: datetime


class ScrapingSessionUpdate(BaseSchema):
    """Schema for updating a scraping session."""
    completed_at: Optional[datetime] = None
    products_scraped: Optional[int] = Field(None, ge=0)
    errors_count: Optional[int] = Field(None, ge=0)
    status: Optional[ScrapingStatus] = None
    error_details: Optional[Dict[str, Any]] = None


class ScrapingSessionResponse(ScrapingSessionBase):
    """Schema for scraping session API responses."""
    id: uuid.UUID
    started_at: datetime
    completed_at: Optional[datetime] = None


# System Settings schemas
class SystemSettingsBase(BaseSchema):
    """Base system settings schema."""
    value: Dict[str, Any]
    description: Optional[str] = None


class SystemSettingsCreate(SystemSettingsBase):
    """Schema for creating system settings."""
    key: str = Field(..., min_length=1, max_length=100)


class SystemSettingsUpdate(BaseSchema):
    """Schema for updating system settings."""
    value: Optional[Dict[str, Any]] = None
    description: Optional[str] = None


class SystemSettingsResponse(SystemSettingsBase):
    """Schema for system settings API responses."""
    key: str
    updated_at: datetime


# Filter schemas
class ProductFilter(BaseSchema):
    """Schema for filtering products."""
    category: Optional[str] = None
    brand: Optional[str] = None
    min_price: Optional[Decimal] = Field(None, gt=0)
    max_price: Optional[Decimal] = Field(None, gt=0)
    stock_status: Optional[StockStatus] = None
    source: Optional[str] = None
    ean: Optional[str] = None
    
    @validator('max_price')
    def validate_price_range(cls, v, values):
        if v is not None and 'min_price' in values and values['min_price'] is not None:
            if v <= values['min_price']:
                raise ValueError('max_price must be greater than min_price')
        return v


class AlertFilter(BaseSchema):
    """Schema for filtering alerts."""
    severity: Optional[AlertSeverity] = None
    processed: Optional[bool] = None
    min_profit: Optional[Decimal] = Field(None, gt=0)
    max_profit: Optional[Decimal] = Field(None, gt=0)
    min_discount: Optional[Decimal] = Field(None, ge=0)
    max_discount: Optional[Decimal] = Field(None, ge=0)
    
    @validator('max_profit')
    def validate_profit_range(cls, v, values):
        if v is not None and 'min_profit' in values and values['min_profit'] is not None:
            if v <= values['min_profit']:
                raise ValueError('max_profit must be greater than min_profit')
        return v


# Pagination schema
class PaginationParams(BaseSchema):
    """Schema for pagination parameters."""
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseSchema):
    """Schema for paginated API responses."""
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int


# Statistics schemas
class SystemStats(BaseSchema):
    """Schema for system statistics."""
    active_alerts: int = Field(..., ge=0)
    total_profit_potential: Decimal
    products_scraped_today: int = Field(..., ge=0)
    success_rate: Decimal = Field(..., ge=0, le=100)
    alerts_generated_today: int = Field(..., ge=0)
    average_processing_time: Decimal = Field(..., ge=0)


# Error schemas
class ErrorResponse(BaseSchema):
    """Schema for error responses."""
    error: str
    details: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Additional API Response schemas
class PaginationResponse(BaseSchema):
    """Schema for pagination metadata."""
    page: int = Field(..., ge=1)
    size: int = Field(..., ge=1)
    total: int = Field(..., ge=0)
    total_pages: int = Field(..., ge=0)
    has_next: bool
    has_prev: bool


class ProductListResponse(BaseSchema):
    """Schema for paginated product list responses."""
    products: List[ProductResponse]
    pagination: PaginationResponse


class AlertResponse(BaseSchema):
    """Schema for alert API responses with product details."""
    id: int
    product_id: int
    asin: str
    amazon_price: Decimal = Field(..., gt=0)
    profit_amount: Decimal
    profit_margin: Decimal = Field(..., ge=0)
    severity: AlertSeverity
    status: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    product: Optional[ProductResponse] = None

    class Config:
        from_attributes = True


class AlertListResponse(BaseSchema):
    """Schema for paginated alert list responses."""
    alerts: List[AlertResponse]
    pagination: PaginationResponse


class AlertProcessRequest(BaseSchema):
    """Schema for processing alert requests."""
    status: str = Field(..., pattern="^(pending|processed|dismissed)$")
    notes: Optional[str] = Field(None, max_length=1000)


class AlertCreateRequest(BaseSchema):
    """Schema for creating alert requests."""
    product_id: str = Field(..., min_length=1)
    asin: str = Field(..., min_length=10, max_length=10)
    threshold_price: Optional[Decimal] = Field(None, gt=0)
    notes: Optional[str] = Field(None, max_length=1000)


class AlertUpdateRequest(BaseSchema):
    """Schema for updating alert requests."""
    status: Optional[str] = Field(None, pattern="^(pending|processed|dismissed)$")
    notes: Optional[str] = Field(None, max_length=1000)
    processed_at: Optional[datetime] = None


# Product matching schemas
class ProductMatch(BaseSchema):
    """Schema for product match results."""
    product_id: str
    asin: str
    confidence_score: Decimal = Field(..., ge=0, le=1)
    match_method: MatchMethod
    match_data: Optional[Dict[str, Any]] = None


class MatchResult(BaseSchema):
    """Schema for matching operation results."""
    matches: List[ProductMatch]
    total_processed: int = Field(..., ge=0)
    successful_matches: int = Field(..., ge=0)
    failed_matches: int = Field(..., ge=0)
    processing_time: float = Field(..., ge=0)
    errors: Optional[List[str]] = None 