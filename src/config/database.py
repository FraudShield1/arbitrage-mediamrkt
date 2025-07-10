"""
Database configuration and connection management.
Supports both MongoDB and PostgreSQL based on DATABASE_URL.
"""

from typing import AsyncGenerator, Optional, Any, Dict, Union
import hashlib
import pickle
import json
from functools import wraps
import structlog
import redis.asyncio as redis
import time
from urllib.parse import urlparse

from .settings import settings

logger = structlog.get_logger(__name__)

# Determine database type from URL
def get_database_type() -> str:
    """Determine database type from DATABASE_URL."""
    parsed = urlparse(settings.DATABASE_URL)
    if parsed.scheme.startswith('mongodb'):
        return 'mongodb'
    elif parsed.scheme.startswith('postgresql'):
        return 'postgresql'
    else:
        return 'unknown'

DATABASE_TYPE = get_database_type()
logger.info(f"Database type detected: {DATABASE_TYPE}")

# MongoDB Configuration
if DATABASE_TYPE == 'mongodb':
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        from pymongo import MongoClient
        import ssl
        
        # Create MongoDB client with proper SSL configuration for Atlas
        mongo_client = AsyncIOMotorClient(
            settings.DATABASE_URL,
            tls=True,
            tlsAllowInvalidCertificates=True,  # Temporarily allow for testing
            tlsAllowInvalidHostnames=True,     # Temporarily allow for testing
            retryWrites=True,
            w='majority',
            maxPoolSize=10,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            socketTimeoutMS=10000
        )
        
        # Get database (extract from URL or use default)
        parsed_url = urlparse(settings.DATABASE_URL)
        database_name = parsed_url.path.lstrip('/') if parsed_url.path and len(parsed_url.path) > 1 else 'arbitrage_tool'
        
        database = mongo_client[database_name]
        
        logger.info(f"MongoDB client initialized for database: {database_name}")
        
    except ImportError:
        logger.error("Motor (MongoDB async driver) not installed. Install with: pip install motor")
        raise
    except Exception as e:
        logger.error(f"Failed to initialize MongoDB client: {e}")
        raise

# PostgreSQL Configuration (fallback)
elif DATABASE_TYPE == 'postgresql':
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        create_async_engine,
        async_sessionmaker,
    )
    from sqlalchemy.orm import declarative_base
    from sqlalchemy.pool import NullPool, StaticPool
    from sqlalchemy import text, event
    from sqlalchemy.engine import Engine
    
    # Enhanced async engine with better pooling
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_pre_ping=True,
        pool_recycle=3600,  # Recycle connections every hour
        pool_timeout=30,    # Connection timeout
        poolclass=NullPool if settings.ENVIRONMENT == "testing" else None,
        # Additional performance optimizations
        connect_args={
            "command_timeout": 60,
            "server_settings": {
                "jit": "off",  # Disable JIT for faster startup
                "application_name": "arbitrage_tool",
            }
        } if settings.ENVIRONMENT != "testing" else {},
    )
    
    # Create async session factory with optimizations
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    # Create declarative base
    Base = declarative_base()

else:
    logger.error(f"Unsupported database type: {DATABASE_TYPE}")
    raise ValueError(f"Unsupported database URL: {settings.DATABASE_URL}")

# For MongoDB, create a dummy Base for compatibility
if DATABASE_TYPE == 'mongodb':
    # Create a dummy Base class for MongoDB compatibility
    class Base:
        """Dummy Base class for MongoDB compatibility."""
        pass

# Redis connection for caching
_redis_client: Optional[redis.Redis] = None


async def get_redis_client() -> Optional[redis.Redis]:
    """
    Get Redis client for caching.
    
    Returns:
        Redis client or None if not configured
    """
    global _redis_client
    
    if _redis_client is None and settings.REDIS_URL:
        try:
            _redis_client = redis.from_url(
                str(settings.REDIS_URL),
                decode_responses=False,  # Keep binary for pickle
                max_connections=settings.REDIS_CONNECTION_POOL_SIZE,
                retry_on_timeout=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            # Test connection
            await _redis_client.ping()
            logger.info("Redis connection established for caching")
        except Exception as e:
            logger.warning(f"Redis connection failed, caching disabled: {e}")
            _redis_client = None
    
    return _redis_client


def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """
    Generate a cache key from function arguments.
    
    Args:
        prefix: Cache key prefix
        *args: Function arguments
        **kwargs: Function keyword arguments
        
    Returns:
        Generated cache key
    """
    # Create a string representation of arguments
    key_data = f"{prefix}:{str(args)}:{str(sorted(kwargs.items()))}"
    # Hash for consistent length
    return f"cache:{hashlib.md5(key_data.encode()).hexdigest()}"


def cached_query(ttl: int = 300, prefix: str = "query"):
    """
    Decorator for caching database queries with Redis.
    
    Args:
        ttl: Time to live in seconds
        prefix: Cache key prefix
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            redis_client = await get_redis_client()
            
            if redis_client is None:
                # No caching, execute directly
                return await func(*args, **kwargs)
            
            # Generate cache key
            cache_key = generate_cache_key(prefix, *args, **kwargs)
            
            try:
                # Try to get from cache
                cached_result = await redis_client.get(cache_key)
                if cached_result:
                    logger.debug(f"Cache hit for key: {cache_key}")
                    return pickle.loads(cached_result)
                
                # Cache miss, execute query
                result = await func(*args, **kwargs)
                
                # Store in cache
                await redis_client.setex(
                    cache_key,
                    ttl,
                    pickle.dumps(result)
                )
                logger.debug(f"Cache stored for key: {cache_key}")
                
                return result
                
            except Exception as e:
                logger.warning(f"Cache error for key {cache_key}: {e}")
                # Fallback to direct execution
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator


async def invalidate_cache_pattern(pattern: str) -> int:
    """
    Invalidate cache entries matching a pattern.
    
    Args:
        pattern: Redis pattern to match keys
        
    Returns:
        Number of keys deleted
    """
    redis_client = await get_redis_client()
    if redis_client is None:
        return 0
    
    try:
        keys = await redis_client.keys(pattern)
        if keys:
            deleted = await redis_client.delete(*keys)
            logger.info(f"Invalidated {deleted} cache entries matching pattern: {pattern}")
            return deleted
        return 0
    except Exception as e:
        logger.error(f"Failed to invalidate cache pattern {pattern}: {e}")
        return 0


# Database session management (MongoDB or PostgreSQL)
def get_database_session():
    """
    Get database session/connection based on database type.
    
    Returns:
        Database session or connection (not async generator for MongoDB)
    """
    if DATABASE_TYPE == 'mongodb':
        return database
    elif DATABASE_TYPE == 'postgresql':
        # Return the session factory for PostgreSQL
        return AsyncSessionLocal

async def get_database_session_async():
    """
    Get database session/connection as async generator.
    
    Yields:
        Database session or connection
    """
    if DATABASE_TYPE == 'mongodb':
        yield database
    elif DATABASE_TYPE == 'postgresql':
        async with AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()


async def create_database_tables():
    """Create database tables/collections."""
    if DATABASE_TYPE == 'mongodb':
        # MongoDB collections are created automatically when data is inserted
        # Create indexes for better performance
        try:
            # Products collection indexes
            # FIX: Make ASIN index sparse to allow multiple null values
            await database.products.create_index(
                "asin", 
                unique=True, 
                partialFilterExpression={"asin": {"$exists": True, "$type": "string"}}  # Only index non-null string ASINs
            )
            await database.products.create_index("ean")
            await database.products.create_index("title")
            await database.products.create_index([("category", 1), ("subcategory", 1)])
            
            # Price alerts collection indexes
            await database.price_alerts.create_index("user_id")
            await database.price_alerts.create_index("product_id")
            await database.price_alerts.create_index([("is_active", 1), ("created_at", -1)])
            
            # Keepa data collection indexes
            await database.keepa_data.create_index("asin")
            await database.keepa_data.create_index("timestamp")
            
            # Scraping sessions collection indexes
            await database.scraping_sessions.create_index("session_id", unique=True)
            await database.scraping_sessions.create_index("status")
            await database.scraping_sessions.create_index("created_at")
            
            logger.info("MongoDB indexes created successfully")
        except Exception as e:
            logger.error(f"Failed to create MongoDB indexes: {e}")
    
    elif DATABASE_TYPE == 'postgresql':
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("PostgreSQL tables created")


async def drop_database_tables():
    """Drop all database tables/collections."""
    if DATABASE_TYPE == 'mongodb':
        # Drop all collections
        collections = await database.list_collection_names()
        for collection_name in collections:
            await database.drop_collection(collection_name)
        logger.info("MongoDB collections dropped")
    
    elif DATABASE_TYPE == 'postgresql':
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("PostgreSQL tables dropped")


async def check_database_connection() -> bool:
    """
    Check if database connection is working.
    
    Returns:
        bool: True if connection is working, False otherwise
    """
    try:
        if DATABASE_TYPE == 'mongodb':
            # Ping the database
            await mongo_client.admin.command('ping')
            logger.info("MongoDB connection check successful")
            return True
        
        elif DATABASE_TYPE == 'postgresql':
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("PostgreSQL connection check successful")
            return True
            
    except Exception as e:
        logger.error("Database connection check failed", error=str(e))
        return False


async def close_database_connection():
    """Close database connection pool."""
    try:
        if DATABASE_TYPE == 'mongodb':
            mongo_client.close()
            logger.info("MongoDB connection closed")
        
        elif DATABASE_TYPE == 'postgresql':
            await engine.dispose()
            logger.info("PostgreSQL connection pool closed")
            
    except Exception as e:
        logger.error(f"Error closing database connection: {e}")


# Additional dependency functions for FastAPI
async def get_db_session():
    """
    FastAPI dependency function to get database session.
    
    Yields:
        Database session for API endpoints
    """
    if DATABASE_TYPE == 'mongodb':
        yield database
    
    elif DATABASE_TYPE == 'postgresql':
        async with AsyncSessionLocal() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()


async def get_database():
    """Initialize database connection (for app startup)."""
    await check_database_connection()
    # Initialize Redis cache
    await get_redis_client()
    # Create database tables/indexes
    await create_database_tables()
    logger.info("Database initialized for application startup")


async def close_database():
    """Close database connections (for app shutdown)."""
    global _redis_client
    
    await close_database_connection()
    
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis connection closed")


async def get_db_stats() -> Dict[str, Any]:
    """
    Get database connection statistics.
    
    Returns:
        Dictionary with database stats
    """
    if DATABASE_TYPE == 'mongodb':
        try:
            server_info = await mongo_client.server_info()
            db_stats = await database.command("dbStats")
            return {
                "database_type": "mongodb",
                "server_version": server_info.get("version"),
                "database_name": database.name,
                "collections": db_stats.get("collections", 0),
                "data_size": db_stats.get("dataSize", 0),
                "storage_size": db_stats.get("storageSize", 0),
                "indexes": db_stats.get("indexes", 0),
            }
        except Exception as e:
            logger.error(f"Failed to get MongoDB stats: {e}")
            return {"database_type": "mongodb", "error": str(e)}
    
    elif DATABASE_TYPE == 'postgresql':
        pool = engine.pool
        return {
            "database_type": "postgresql",
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "total": pool.size() + pool.overflow(),
            "invalid": pool.invalid(),
        }


# MongoDB helper functions
if DATABASE_TYPE == 'mongodb':
    def get_collection(name: str):
        """Get MongoDB collection by name."""
        return database[name]
    
    async def find_one(collection_name: str, query: dict) -> Optional[dict]:
        """Find one document in collection."""
        collection = get_collection(collection_name)
        return await collection.find_one(query)
    
    async def find_many(collection_name: str, query: dict, limit: int = 100) -> list:
        """Find multiple documents in collection."""
        collection = get_collection(collection_name)
        cursor = collection.find(query).limit(limit)
        return await cursor.to_list(length=limit)
    
    async def insert_one(collection_name: str, document: dict) -> str:
        """Insert one document into collection."""
        collection = get_collection(collection_name)
        result = await collection.insert_one(document)
        return str(result.inserted_id)
    
    async def update_one(collection_name: str, query: dict, update: dict) -> bool:
        """Update one document in collection."""
        collection = get_collection(collection_name)
        result = await collection.update_one(query, {"$set": update})
        return result.modified_count > 0
    
    async def delete_one(collection_name: str, query: dict) -> bool:
        """Delete one document from collection."""
        collection = get_collection(collection_name)
        result = await collection.delete_one(query)
        return result.deleted_count > 0


# PostgreSQL compatibility (if still needed)
if DATABASE_TYPE == 'postgresql':
    # Keep existing PostgreSQL code for backward compatibility
    Base = Base  # Already defined above
    
    # Event listeners for query logging in development
    if settings.ENVIRONMENT == "development":
        @event.listens_for(Engine, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            context._query_start_time = time.time()

        @event.listens_for(Engine, "after_cursor_execute")
        def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            total = time.time() - context._query_start_time
            if total > 1.0:  # Log slow queries
                logger.warning(f"Slow query detected: {total:.2f}s - {statement[:100]}...") 