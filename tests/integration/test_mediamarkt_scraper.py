"""
Integration tests for the MediaMarkt scraper.
"""

import pytest
from unittest.mock import patch, AsyncMock
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.services.scraper.mediamarkt_scraper import MediaMarktScraper
from src.models.product import Product
from tests.mocks.mock_mediamarkt_server import mock_mediamarkt_app

@pytest.fixture
def mock_server(monkeypatch):
    """Fixture to mock the MediaMarkt server."""
    from fastapi.testclient import TestClient
    
    client = TestClient(mock_mediamarkt_app)
    
    # Use monkeypatch to override the scraper's base URL
    base_url = client.base_url
    monkeypatch.setattr(MediaMarktScraper, 'base_url', str(base_url))
    monkeypatch.setattr(MediaMarktScraper, 'search_url', f"{base_url}/pages/search-results-page?q=+")
    
    return client

@pytest.mark.asyncio
async def test_scraper_database_integration(db_session: AsyncSession, mock_server):
    """
    Test the full scraping process and integration with the database.
    - Scrapes mock data from the mock server.
    - Stores the data in the test database.
    - Verifies the data is correctly stored.
    """
    scraper = MediaMarktScraper()
    
    # We need to manually override the URLs for the test server
    scraper.base_url = str(mock_server.base_url)
    scraper.search_url = f"{scraper.base_url}/pages/search-results-page?q=+"

    async with scraper:
        # Scrape products (the mock server will provide the HTML)
        scraped_products = await scraper.scrape_all_products(max_pages=1)

    # Assert that products were scraped
    assert len(scraped_products) > 0
    assert len(scraped_products) == 10 # As defined in mock server

    # Save products to the database
    products_to_save = []
    for p_data in scraped_products:
        # Convert to Product model, handling potential None values
        product = Product(
            title=p_data.get('title'),
            current_price=p_data.get('price'),
            original_price=p_data.get('original_price'),
            discount_percentage=p_data.get('discount_percentage'),
            ean=p_data.get('ean'),
            brand=p_data.get('brand'),
            category=p_data.get('category'),
            stock_status=p_data.get('stock_status'),
            url=p_data.get('url'),
            scraped_at=p_data.get('scraped_at'),
            source=p_data.get('source')
        )
        products_to_save.append(product)
    
    db_session.add_all(products_to_save)
    await db_session.commit()

    # Verify data was stored correctly
    result = await db_session.execute(select(Product))
    stored_products = result.scalars().all()

    assert len(stored_products) == len(scraped_products)
    
    # Check one product in detail
    first_scraped = scraped_products[0]
    first_stored = await db_session.get(Product, stored_products[0].id)
    
    assert first_stored is not None
    assert first_stored.title == first_scraped.get('title')
    assert first_stored.ean == first_scraped.get('ean')
    assert first_stored.current_price == first_scraped.get('price')

@pytest.mark.asyncio
async def test_proxy_and_rate_limit_integration(mock_server):
    """
    Test integration with proxy management and rate limiting logic.
    This is a conceptual test, as true proxy/rate limit tests are complex.
    We will simulate the behavior with mocks.
    """
    with patch('src.services.scraper.mediamarkt_scraper.settings') as mock_settings:
        mock_settings.scraping.proxy_rotation = True
        mock_settings.scraping.request_delay = 0.1 # Small delay for test speed

        scraper = MediaMarktScraper()
        
        # Mock the proxy manager and rate limiter if they were separate components
        # For now, we simulate this by observing delays
        
        # In a real scenario, you'd patch 'playwright.chromium.launch' to include
        # proxy settings and verify they are used.
        # e.g. launch_options['proxy'] = {'server': 'http://mockproxy:8080'}

        # Simulate a rate-limited response by having the mock server return 429
        # This requires modifying the mock server or adding a specific endpoint for it.
        # For this test, we'll assume the delay setting is our rate limit stand-in.
        
        import time
        start_time = time.time()
        
        async with scraper:
            await scraper.scrape_all_products(max_pages=2)
            
        end_time = time.time()
        
        # Check if delays were respected (2 pages = 1 delay between them)
        assert (end_time - start_time) >= mock_settings.scraping.request_delay
        
@pytest.mark.asyncio
async def test_data_validation_with_pydantic(mock_server):
    """
    Test that scraped data conforms to Pydantic schemas.
    This test ensures that the data extracted by the scraper can be
    validated and used by other parts of the system that rely on these schemas.
    """
    from src.models.schemas import ProductCreate # Assuming a Pydantic model for creation

    scraper = MediaMarktScraper()
    scraper.base_url = str(mock_server.base_url)
    scraper.search_url = f"{scraper.base_url}/pages/search-results-page?q=+"
    
    async with scraper:
        scraped_products = await scraper.scrape_products_page("http://mock.url/page1")
    
    for product_data in scraped_products:
        try:
            # Pydantic model expects 'price' but scraper provides 'current_price'
            # We need to align these. Let's assume the schema is flexible or we adapt.
            adapted_data = {
                "title": product_data.get('title'),
                "price": product_data.get('price'), # Renaming for schema
                "original_price": product_data.get('original_price'),
                "discount_percentage": product_data.get('discount_percentage'),
                "ean": product_data.get('ean'),
                "brand": product_data.get('brand'),
                "category": product_data.get('category'),
                "stock_status": product_data.get('stock_status'),
                "url": product_data.get('url'),
                "scraped_at": product_data.get('scraped_at'),
                "source": product_data.get('source'),
                "asin": product_data.get('asin')
            }
            ProductCreate.model_validate(adapted_data)
        except Exception as e:
            pytest.fail(f"Pydantic validation failed for product {product_data.get('title')}: {e}") 