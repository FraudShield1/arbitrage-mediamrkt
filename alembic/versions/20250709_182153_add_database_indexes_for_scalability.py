"""Add database indexes for scalability

Revision ID: 20250709_182153
Revises: 
Create Date: 2025-01-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20250709_182153'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add database indexes for scalability improvements."""
    
    # Products table indexes for frequently queried fields
    op.create_index('idx_products_ean', 'products', ['ean'])
    op.create_index('idx_products_asin', 'products', ['asin'])
    op.create_index('idx_products_brand', 'products', ['brand'])
    op.create_index('idx_products_category', 'products', ['category'])
    op.create_index('idx_products_price', 'products', ['price'])
    op.create_index('idx_products_discount_percentage', 'products', ['discount_percentage'])
    op.create_index('idx_products_stock_status', 'products', ['stock_status'])
    op.create_index('idx_products_source', 'products', ['source'])
    op.create_index('idx_products_scraped_at', 'products', ['scraped_at'])
    op.create_index('idx_products_created_at', 'products', ['created_at'])
    
    # Composite indexes for common query patterns
    op.create_index('idx_products_category_brand', 'products', ['category', 'brand'])
    op.create_index('idx_products_price_discount', 'products', ['price', 'discount_percentage'])
    op.create_index('idx_products_stock_price', 'products', ['stock_status', 'price'])
    op.create_index('idx_products_ean_asin', 'products', ['ean', 'asin'])
    
    # ASIN table indexes
    op.create_index('idx_asins_brand', 'asins', ['brand'])
    op.create_index('idx_asins_category', 'asins', ['category'])
    op.create_index('idx_asins_marketplace', 'asins', ['marketplace'])
    op.create_index('idx_asins_last_updated', 'asins', ['last_updated'])
    op.create_index('idx_asins_category_marketplace', 'asins', ['category', 'marketplace'])
    
    # Product ASIN matches indexes for join performance
    op.create_index('idx_product_asin_matches_product_id', 'product_asin_matches', ['product_id'])
    op.create_index('idx_product_asin_matches_asin', 'product_asin_matches', ['asin'])
    op.create_index('idx_product_asin_matches_confidence', 'product_asin_matches', ['confidence_score'])
    op.create_index('idx_product_asin_matches_method', 'product_asin_matches', ['match_method'])
    op.create_index('idx_product_asin_matches_created_at', 'product_asin_matches', ['created_at'])
    
    # Price alerts indexes for fast alert retrieval
    op.create_index('idx_price_alerts_product_id', 'price_alerts', ['product_id'])
    op.create_index('idx_price_alerts_asin', 'price_alerts', ['asin'])
    op.create_index('idx_price_alerts_severity', 'price_alerts', ['severity'])
    op.create_index('idx_price_alerts_profit_potential', 'price_alerts', ['profit_potential'])
    op.create_index('idx_price_alerts_confidence_score', 'price_alerts', ['confidence_score'])
    op.create_index('idx_price_alerts_processed_at', 'price_alerts', ['processed_at'])
    op.create_index('idx_price_alerts_created_at', 'price_alerts', ['created_at'])
    
    # Composite indexes for price alerts analysis
    op.create_index('idx_price_alerts_severity_profit', 'price_alerts', ['severity', 'profit_potential'])
    op.create_index('idx_price_alerts_processed_severity', 'price_alerts', ['processed_at', 'severity'])
    
    # Keepa data indexes for price history queries
    op.create_index('idx_keepa_data_asin', 'keepa_data', ['asin'])
    op.create_index('idx_keepa_data_marketplace', 'keepa_data', ['marketplace'])
    op.create_index('idx_keepa_data_updated_at', 'keepa_data', ['updated_at'])
    op.create_index('idx_keepa_data_asin_marketplace', 'keepa_data', ['asin', 'marketplace'])
    
    # Scraping sessions indexes for monitoring
    op.create_index('idx_scraping_sessions_source', 'scraping_sessions', ['source'])
    op.create_index('idx_scraping_sessions_status', 'scraping_sessions', ['status'])
    op.create_index('idx_scraping_sessions_started_at', 'scraping_sessions', ['started_at'])
    op.create_index('idx_scraping_sessions_completed_at', 'scraping_sessions', ['completed_at'])
    op.create_index('idx_scraping_sessions_source_status', 'scraping_sessions', ['source', 'status'])
    
    # System settings index
    op.create_index('idx_system_settings_key', 'system_settings', ['key'])
    op.create_index('idx_system_settings_updated_at', 'system_settings', ['updated_at'])
    
    # Text search indexes for product names and titles
    op.execute("CREATE INDEX idx_products_title_gin ON products USING gin(to_tsvector('english', title))")
    op.execute("CREATE INDEX idx_asins_title_gin ON asins USING gin(to_tsvector('english', title))")


def downgrade() -> None:
    """Remove database indexes."""
    
    # Text search indexes
    op.execute("DROP INDEX IF EXISTS idx_products_title_gin")
    op.execute("DROP INDEX IF EXISTS idx_asins_title_gin")
    
    # System settings indexes
    op.drop_index('idx_system_settings_updated_at')
    op.drop_index('idx_system_settings_key')
    
    # Scraping sessions indexes
    op.drop_index('idx_scraping_sessions_source_status')
    op.drop_index('idx_scraping_sessions_completed_at')
    op.drop_index('idx_scraping_sessions_started_at')
    op.drop_index('idx_scraping_sessions_status')
    op.drop_index('idx_scraping_sessions_source')
    
    # Keepa data indexes
    op.drop_index('idx_keepa_data_asin_marketplace')
    op.drop_index('idx_keepa_data_updated_at')
    op.drop_index('idx_keepa_data_marketplace')
    op.drop_index('idx_keepa_data_asin')
    
    # Price alerts composite indexes
    op.drop_index('idx_price_alerts_processed_severity')
    op.drop_index('idx_price_alerts_severity_profit')
    
    # Price alerts indexes
    op.drop_index('idx_price_alerts_created_at')
    op.drop_index('idx_price_alerts_processed_at')
    op.drop_index('idx_price_alerts_confidence_score')
    op.drop_index('idx_price_alerts_profit_potential')
    op.drop_index('idx_price_alerts_severity')
    op.drop_index('idx_price_alerts_asin')
    op.drop_index('idx_price_alerts_product_id')
    
    # Product ASIN matches indexes
    op.drop_index('idx_product_asin_matches_created_at')
    op.drop_index('idx_product_asin_matches_method')
    op.drop_index('idx_product_asin_matches_confidence')
    op.drop_index('idx_product_asin_matches_asin')
    op.drop_index('idx_product_asin_matches_product_id')
    
    # ASIN table indexes
    op.drop_index('idx_asins_category_marketplace')
    op.drop_index('idx_asins_last_updated')
    op.drop_index('idx_asins_marketplace')
    op.drop_index('idx_asins_category')
    op.drop_index('idx_asins_brand')
    
    # Products composite indexes
    op.drop_index('idx_products_ean_asin')
    op.drop_index('idx_products_stock_price')
    op.drop_index('idx_products_price_discount')
    op.drop_index('idx_products_category_brand')
    
    # Products single column indexes
    op.drop_index('idx_products_created_at')
    op.drop_index('idx_products_scraped_at')
    op.drop_index('idx_products_source')
    op.drop_index('idx_products_stock_status')
    op.drop_index('idx_products_discount_percentage')
    op.drop_index('idx_products_price')
    op.drop_index('idx_products_category')
    op.drop_index('idx_products_brand')
    op.drop_index('idx_products_asin')
    op.drop_index('idx_products_ean') 