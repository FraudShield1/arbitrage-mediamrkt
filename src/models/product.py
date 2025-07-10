"""
Product SQLAlchemy model.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
import uuid

from sqlalchemy import (
    Column, String, DECIMAL, DateTime, Text, Boolean, Integer,
    func, Text, ARRAY, Float
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.config.database import Base


class Product(Base):
    """Product model for scraped products."""
    
    __tablename__ = "products"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    price = Column(DECIMAL(10, 2), nullable=False)
    original_price = Column(DECIMAL(10, 2), nullable=True)  # Price before discount
    discount_percentage = Column(Float, nullable=True)  # Discount percentage
    ean = Column(String(20), nullable=True)
    asin = Column(String(10), nullable=True)  # ASIN if found during scraping
    brand = Column(String(100), nullable=True)
    category = Column(String(100), nullable=False)
    stock_status = Column(String(20), nullable=False)
    url = Column(String(1000), nullable=False)
    # Removed images field to optimize performance as per requirements
    scraped_at = Column(DateTime(timezone=True), nullable=False)
    source = Column(String(50), nullable=False, default="mediamarkt")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    asin_matches = relationship(
        "ProductAsinMatch",
        back_populates="product",
        cascade="all, delete-orphan"
    )
    price_alerts = relationship(
        "PriceAlert",
        back_populates="product",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Product(id={self.id}, title='{self.title[:50]}...', price={self.price})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": str(self.id),
            "title": self.title,
            "price": float(self.price),
            "original_price": float(self.original_price) if self.original_price else None,
            "discount_percentage": self.discount_percentage,
            "ean": self.ean,
            "asin": self.asin,
            "brand": self.brand,
            "category": self.category,
            "stock_status": self.stock_status,
            "url": self.url,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        } 