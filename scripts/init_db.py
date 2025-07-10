#!/usr/bin/env python3
"""
Database Initialization Script

Sets up the database schema, runs migrations, and creates initial data
for the Cross-Market Arbitrage Tool.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.settings import get_settings
from src.config.database import get_database, close_database
from src.models import Base
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_database_if_not_exists():
    """Create database if it doesn't exist."""
    settings = get_settings()
    
    # Extract database name from URL
    db_name = settings.DATABASE_URL.split('/')[-1]
    
    # Create connection to postgres database (without specific db)
    postgres_url = settings.DATABASE_URL.replace(f'/{db_name}', '/postgres')
    
    engine = create_async_engine(postgres_url, isolation_level="AUTOCOMMIT")
    
    try:
        async with engine.connect() as conn:
            # Check if database exists
            result = await conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                {"db_name": db_name}
            )
            
            if result.fetchone() is None:
                logger.info(f"Creating database: {db_name}")
                await conn.execute(text(f"CREATE DATABASE {db_name}"))
                logger.info(f"Database {db_name} created successfully")
            else:
                logger.info(f"Database {db_name} already exists")
                
    except Exception as e:
        logger.error(f"Error creating database: {str(e)}")
        raise
    finally:
        await engine.dispose()


async def create_extensions():
    """Create required PostgreSQL extensions."""
    logger.info("Creating PostgreSQL extensions...")
    
    try:
        db = await get_database()
        async with db.begin() as conn:
            # Create extensions if they don't exist
            extensions = [
                "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"",
                "CREATE EXTENSION IF NOT EXISTS pg_trgm",
                "CREATE EXTENSION IF NOT EXISTS vector"  # For pgvector if available
            ]
            
            for ext in extensions:
                try:
                    await conn.execute(text(ext))
                    logger.info(f"Extension created: {ext}")
                except Exception as e:
                    logger.warning(f"Could not create extension {ext}: {str(e)}")
                    
    except Exception as e:
        logger.error(f"Error creating extensions: {str(e)}")
        raise


async def create_tables():
    """Create all database tables."""
    logger.info("Creating database tables...")
    
    try:
        settings = get_settings()
        engine = create_async_engine(settings.DATABASE_URL)
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("Database tables created successfully")
        await engine.dispose()
        
    except Exception as e:
        logger.error(f"Error creating tables: {str(e)}")
        raise


async def create_indexes():
    """Create additional indexes for performance."""
    logger.info("Creating additional indexes...")
    
    try:
        db = await get_database()
        async with db.begin() as conn:
            indexes = [
                # Product indexes
                "CREATE INDEX IF NOT EXISTS idx_products_ean ON products(ean) WHERE ean IS NOT NULL",
                "CREATE INDEX IF NOT EXISTS idx_products_brand_category ON products(brand, category)",
                "CREATE INDEX IF NOT EXISTS idx_products_price ON products(current_price)",
                "CREATE INDEX IF NOT EXISTS idx_products_created ON products(created_at)",
                
                # ASIN indexes
                "CREATE INDEX IF NOT EXISTS idx_asins_marketplace ON asins(marketplace)",
                "CREATE INDEX IF NOT EXISTS idx_asins_price ON asins(current_price)",
                "CREATE INDEX IF NOT EXISTS idx_asins_sales_rank ON asins(sales_rank)",
                
                # Alert indexes
                "CREATE INDEX IF NOT EXISTS idx_alerts_status ON price_alerts(status)",
                "CREATE INDEX IF NOT EXISTS idx_alerts_created ON price_alerts(created_at)",
                "CREATE INDEX IF NOT EXISTS idx_alerts_profit ON price_alerts(profit_margin)",
                
                # Match indexes
                "CREATE INDEX IF NOT EXISTS idx_matches_confidence ON product_asin_matches(confidence)",
                "CREATE INDEX IF NOT EXISTS idx_matches_type ON product_asin_matches(match_type)",
                
                # Full-text search indexes
                "CREATE INDEX IF NOT EXISTS idx_products_title_gin ON products USING gin(to_tsvector('english', title))",
                "CREATE INDEX IF NOT EXISTS idx_asins_title_gin ON asins USING gin(to_tsvector('english', title))"
            ]
            
            for index in indexes:
                try:
                    await conn.execute(text(index))
                    logger.info(f"Index created: {index.split()[-3]}")  # Extract index name
                except Exception as e:
                    logger.warning(f"Could not create index: {str(e)}")
                    
    except Exception as e:
        logger.error(f"Error creating indexes: {str(e)}")
        raise


async def create_initial_settings():
    """Create initial system settings."""
    logger.info("Creating initial system settings...")
    
    try:
        from src.models.schemas import SystemSettingsCreate
        
        db = await get_database()
        
        # Check if settings already exist
        result = await db.execute(text("SELECT COUNT(*) FROM system_settings"))
        count = result.scalar()
        
        if count > 0:
            logger.info("System settings already exist")
            return
        
        # Create default settings
        default_settings = {
            'scraping_interval': 1800,  # 30 minutes
            'max_pages_per_session': 10,
            'request_delay': 2.0,
            'ean_confidence_threshold': 0.95,
            'fuzzy_confidence_threshold': 0.85,
            'semantic_confidence_threshold': 0.80,
            'profit_threshold': 0.30,
            'alert_frequency': 'immediate',
            'max_alerts_per_hour': 20,
            'email_enabled': True,
            'telegram_enabled': True,
            'slack_enabled': True
        }
        
        # Insert settings
        for key, value in default_settings.items():
            await db.execute(
                text("""
                INSERT INTO system_settings (key, value, created_at, updated_at)
                VALUES (:key, :value, NOW(), NOW())
                """),
                {"key": key, "value": str(value)}
            )
        
        await db.commit()
        logger.info("Initial system settings created")
        
    except Exception as e:
        logger.error(f"Error creating initial settings: {str(e)}")
        raise


async def run_alembic_upgrade():
    """Run Alembic migrations."""
    logger.info("Running Alembic migrations...")
    
    try:
        import subprocess
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=project_root,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info("Alembic migrations completed successfully")
            if result.stdout:
                logger.info(f"Alembic output: {result.stdout}")
        else:
            logger.error(f"Alembic migration failed: {result.stderr}")
            
    except Exception as e:
        logger.warning(f"Could not run Alembic migrations: {str(e)}")


async def verify_database():
    """Verify database setup is correct."""
    logger.info("Verifying database setup...")
    
    try:
        db = await get_database()
        
        # Check tables exist
        tables = [
            'products', 'asins', 'price_alerts', 'product_asin_matches',
            'keepa_data', 'scraping_sessions', 'system_settings', 'users'
        ]
        
        for table in tables:
            result = await db.execute(
                text("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = :table"),
                {"table": table}
            )
            
            if result.scalar() == 0:
                logger.error(f"Table {table} does not exist!")
            else:
                logger.info(f"✓ Table {table} exists")
        
        # Test basic operations
        await db.execute(text("SELECT 1"))
        logger.info("✓ Database connection working")
        
        logger.info("Database verification completed successfully")
        
    except Exception as e:
        logger.error(f"Database verification failed: {str(e)}")
        raise


async def main():
    """Main initialization function."""
    logger.info("Starting database initialization...")
    
    try:
        # Step 1: Create database if needed
        await create_database_if_not_exists()
        
        # Step 2: Create extensions
        await create_extensions()
        
        # Step 3: Create tables
        await create_tables()
        
        # Step 4: Run migrations
        await run_alembic_upgrade()
        
        # Step 5: Create indexes
        await create_indexes()
        
        # Step 6: Create initial settings
        await create_initial_settings()
        
        # Step 7: Verify setup
        await verify_database()
        
        logger.info("🎉 Database initialization completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {str(e)}")
        sys.exit(1)
    
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(main()) 