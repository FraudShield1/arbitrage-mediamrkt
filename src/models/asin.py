"""
ASIN SQLAlchemy model.
"""

from typing import Dict, Any
from datetime import datetime

from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.orm import relationship

from src.config.database import Base


class ASIN(Base):
    """ASIN model for Amazon product catalog."""
    
    __tablename__ = "asins"
    
    asin = Column(String(10), primary_key=True)
    title = Column(String(500), nullable=False)
    brand = Column(String(100), nullable=True)
    category = Column(String(100), nullable=False)
    marketplace = Column(String(5), nullable=False)
    last_updated = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    product_matches = relationship(
        "ProductAsinMatch",
        back_populates="asin_ref",
        cascade="all, delete-orphan"
    )
    price_alerts = relationship(
        "PriceAlert",
        back_populates="asin_ref",
        cascade="all, delete-orphan"
    )
    keepa_data = relationship(
        "KeepaData",
        back_populates="asin_ref",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<ASIN(asin='{self.asin}', title='{self.title[:50]}...', marketplace='{self.marketplace}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "asin": self.asin,
            "title": self.title,
            "brand": self.brand,
            "category": self.category,
            "marketplace": self.marketplace,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        } 