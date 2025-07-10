"""
Pytest configuration and shared fixtures for testing.
"""

import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from src.main import app
from src.config.database import get_db_session
from src.config.settings import get_settings
from src.models.base import Base
from src.auth.models import User, UserRole
from src.auth.jwt_handler import hash_password, create_access_token

# Test database URL - using SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
TEST_SYNC_DATABASE_URL = "sqlite:///:memory:"

# Test settings
settings = get_settings()
settings.DATABASE_URL = TEST_DATABASE_URL


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        pool_pre_ping=True
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    TestSessionLocal = sessionmaker(
        test_engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
    
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client with database session override."""
    
    def override_get_db():
        return db_session
    
    app.dependency_overrides[get_db_session] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=hash_password("testpassword"),
        role=UserRole.USER,
        is_active=True,
        is_verified=True
    )
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    return user


@pytest_asyncio.fixture
async def test_admin(db_session: AsyncSession) -> User:
    """Create a test admin user."""
    admin = User(
        username="testadmin",
        email="admin@example.com",
        hashed_password=hash_password("adminpassword"),
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True
    )
    
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)

    return admin


@pytest_asyncio.fixture
async def auth_headers(test_user: User) -> dict:
    """Create authentication headers for test user."""
    token = create_access_token(
        user_id=test_user.id,
        username=test_user.username,
        role=test_user.role
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_headers(test_admin: User) -> dict:
    """Create authentication headers for test admin."""
    token = create_access_token(
        user_id=test_admin.id,
        username=test_admin.username,
        role=test_admin.role
    )
    return {"Authorization": f"Bearer {token}"}


# Mock data fixtures
@pytest.fixture
def sample_product_data():
    """Sample product data for testing."""
    return {
        "name": "Apple iPhone 15 Pro",
        "brand": "Apple",
        "ean": "1234567890123",
        "current_price": 1199.99,
        "original_price": 1399.99,
        "discount_percentage": 14.29,
        "stock_status": "in_stock",
        "product_url": "https://mediamarkt.pt/product/apple-iphone-15-pro",
        "last_scraped": "2024-01-01T12:00:00Z"
    }


@pytest.fixture
def sample_asin_data():
    """Sample ASIN data for testing."""
    return {
        "asin": "B0CHX2F5QT",
        "title": "Apple iPhone 15 Pro (256GB) - Natural Titanium",
        "brand": "Apple",
        "ean": "194253432807",
        "category": "Electronics > Cell Phones & Accessories > Cell Phones > Smartphones",
        "current_price": 1299.00,
        "is_available": True
    }


@pytest.fixture
def sample_keepa_data():
    """Sample Keepa API response data for testing."""
    return {
        "asin": "B0CHX2F5QT",
        "title": "Apple iPhone 15 Pro (256GB) - Natural Titanium",
        "current_price": 1299.00,
        "price_history": [
            {"timestamp": "2024-01-01T00:00:00Z", "price": 1399.00},
            {"timestamp": "2024-01-15T00:00:00Z", "price": 1349.00},
            {"timestamp": "2024-01-30T00:00:00Z", "price": 1299.00}
        ],
        "avg_price_30d": 1349.00,
        "lowest_price_30d": 1299.00,
        "highest_price_30d": 1399.00,
        "sales_rank": 15,
        "reviews_count": 1250,
        "rating": 4.5
    }


@pytest.fixture
def sample_alert_data():
    """Sample alert data for testing."""
    return {
        "product_id": "test-product-123",
        "asin": "B0CHX2F5QT",
        "current_price_mm": 899.99,
        "current_price_amazon": 1199.00,
        "profit_margin": 0.25,
        "profit_amount": 299.01,
        "confidence_score": 0.95,
        "match_type": "EAN",
        "analysis_data": {
            "avg_amazon_price": 1199.00,
            "price_trend": "stable",
            "estimated_fees": 59.95,
            "net_profit": 239.06
        }
    }


# Test environment configuration
@pytest.fixture(scope="session")
def test_settings():
    """Test-specific settings configuration."""
    settings = get_settings()
    settings.DATABASE_URL = TEST_DATABASE_URL
    settings.testing = True
    settings.log_level = "DEBUG"
    return settings


@pytest.fixture
def mock_celery_app():
    """Mock Celery app for testing background tasks."""
    from unittest.mock import Mock
    mock_app = Mock()
    mock_app.task = Mock(return_value=lambda f: f)
    return mock_app


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing caching."""
    from unittest.mock import AsyncMock
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.delete.return_value = True
    return mock_redis


@pytest.fixture
def mock_notification_services():
    """Mock notification services for testing."""
    from unittest.mock import AsyncMock
    
    return {
        "telegram": AsyncMock(),
        "slack": AsyncMock(),
        "email": AsyncMock()
    } 