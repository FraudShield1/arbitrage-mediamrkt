"""
Alert and supporting SQLAlchemy models.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
import uuid

from sqlalchemy import (
    Column, String, DECIMAL, DateTime, func, Integer,
    ForeignKey, UniqueConstraint, Text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.config.database import Base


class ProductAsinMatch(Base):
    """Product-ASIN matching results with confidence scores."""
    
    __tablename__ = "product_asin_matches"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    asin = Column(String(10), ForeignKey("asins.asin", ondelete="CASCADE"), nullable=False)
    confidence_score = Column(DECIMAL(3, 2), nullable=False)
    match_method = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Unique constraint
    __table_args__ = (UniqueConstraint('product_id', 'asin', name='uq_product_asin'),)
    
    # Relationships
    product = relationship("Product", back_populates="asin_matches")
    asin_ref = relationship("ASIN", back_populates="product_matches")
    
    def __repr__(self) -> str:
        return f"<ProductAsinMatch(product_id={self.product_id}, asin='{self.asin}', confidence={self.confidence_score})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": str(self.id),
            "product_id": str(self.product_id),
            "asin": self.asin,
            "confidence_score": float(self.confidence_score),
            "match_method": self.match_method,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PriceAlert(Base):
    """Price alert model for arbitrage opportunities."""
    
    __tablename__ = "price_alerts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    asin = Column(String(10), ForeignKey("asins.asin", ondelete="CASCADE"), nullable=False)
    current_price = Column(DECIMAL(10, 2), nullable=False)
    average_price = Column(DECIMAL(10, 2), nullable=False)
    discount_percentage = Column(DECIMAL(5, 2), nullable=False)
    profit_potential = Column(DECIMAL(10, 2), nullable=False)
    confidence_score = Column(DECIMAL(3, 2), nullable=False)
    severity = Column(String(20), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    product = relationship("Product", back_populates="price_alerts")
    asin_ref = relationship("ASIN", back_populates="price_alerts")
    
    def __repr__(self) -> str:
        return f"<PriceAlert(id={self.id}, severity='{self.severity}', profit={self.profit_potential})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": str(self.id),
            "product_id": str(self.product_id),
            "asin": self.asin,
            "current_price": float(self.current_price),
            "average_price": float(self.average_price),
            "discount_percentage": float(self.discount_percentage),
            "profit_potential": float(self.profit_potential),
            "confidence_score": float(self.confidence_score),
            "severity": self.severity,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class KeepaData(Base):
    """Keepa historical price data."""
    
    __tablename__ = "keepa_data"
    
    asin = Column(String(10), ForeignKey("asins.asin", ondelete="CASCADE"), primary_key=True)
    marketplace = Column(String(5), primary_key=True)
    price_history = Column(JSONB, nullable=False)
    sales_rank_history = Column(JSONB, nullable=True)
    stats = Column(JSONB, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    asin_ref = relationship("ASIN", back_populates="keepa_data")
    
    def __repr__(self) -> str:
        return f"<KeepaData(asin='{self.asin}', marketplace='{self.marketplace}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "asin": self.asin,
            "marketplace": self.marketplace,
            "price_history": self.price_history,
            "sales_rank_history": self.sales_rank_history,
            "stats": self.stats,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ScrapingSession(Base):
    """Scraping session tracking."""
    
    __tablename__ = "scraping_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(String(50), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    products_scraped = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
    status = Column(String(20), nullable=False, default="running")
    error_details = Column(JSONB, nullable=True)
    
    def __repr__(self) -> str:
        return f"<ScrapingSession(id={self.id}, source='{self.source}', status='{self.status}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": str(self.id),
            "source": self.source,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "products_scraped": self.products_scraped,
            "errors_count": self.errors_count,
            "status": self.status,
            "error_details": self.error_details,
        }


class SystemSettings(Base):
    """System configuration settings."""
    
    __tablename__ = "system_settings"
    
    key = Column(String(100), primary_key=True)
    value = Column(JSONB, nullable=False)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self) -> str:
        return f"<SystemSettings(key='{self.key}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "key": self.key,
            "value": self.value,
            "description": self.description,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        } 