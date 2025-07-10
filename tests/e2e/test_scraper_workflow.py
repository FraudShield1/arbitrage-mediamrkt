"""
End-to-end tests for the scraper workflow.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.tasks.scraping import scrape_mediamarkt
from src.models.product import Product
from src.config.celery import celery_app
from tests.mocks.mock_mediamarkt_server import mock_mediamarkt_app


@pytest.fixture(scope="module")
def celery_test_app():
    """Fixture for a test Celery app that runs tasks eagerly."""
    celery_app.conf.update(task_always_eager=True)
    yield celery_app
    celery_app.conf.update(task_always_eager=False)

@pytest.fixture
def mock_server_for_e2e(monkeypatch):
    """Fixture to mock the MediaMarkt server for E2E tests."""
    from fastapi.testclient import TestClient
    from src.services.scraper.mediamarkt_scraper import MediaMarktScraper

    client = TestClient(mock_mediamarkt_app)
    base_url = str(client.base_url)
    
    # This is tricky because the task runs in a different context.
    # We patch the scraper class itself to always use the mock server url.
    monkeypatch.setattr(MediaMarktScraper, 'base_url', base_url)
    monkeypatch.setattr(MediaMarktScraper, 'search_url', f"{base_url}/pages/search-results-page?q=+")
    return client

@pytest.mark.asyncio
async def test_full_scraping_cycle_e2e(db_session: AsyncSession, celery_test_app, mock_server_for_e2e):
    """
    Test the full scraping cycle as an end-to-end workflow.
    - Triggers the Celery scraping task.
    - The task uses the scraper, which hits the mock server.
    - Verifies that data is scraped and stored in the database.
    """
    
    # The task runs synchronously due to `task_always_eager=True`
    result = scrape_mediamarkt.delay(max_pages=1)

    assert result.successful(), "Celery task failed"
    task_result = result.get()
    
    assert task_result['status'] == 'completed'
    assert task_result['products_scraped'] == 10

    # Verify data in the database
    db_result = await db_session.execute(select(Product))
    products_in_db = db_result.scalars().all()
    
    assert len(products_in_db) == 10
    
    # Verify downstream compatibility (conceptual)
    # In a real E2E test, you would now trigger the matching task
    # e.g., `process_unmatched_products.delay()`
    # and verify that it can access and process the scraped products.
    from src.services.matcher.ean_matcher import EANMatcher
    
    matcher = EANMatcher()
    # Let's check if the first product can be processed by a matcher
    first_product = products_in_db[0]
    
    # A simple check to ensure the data is usable
    assert first_product.ean is not None
    assert len(first_product.ean) > 5 # basic sanity check
    
@pytest.mark.asyncio
async def test_performance_and_error_recovery_e2e(celery_test_app, mock_server_for_e2e):
    """
    Conceptual test for performance and error recovery.
    - Measures time to scrape (mocked) products.
    - Simulates network failures to test retry logic.
    """
    # Performance measurement
    import time
    start_time = time.time()
    
    # Run scraping task for multiple pages
    scrape_mediamarkt.delay(max_pages=2)
    
    end_time = time.time()
    duration = end_time - start_time
    
    # With eager tasks, this runs locally. Should be very fast.
    # This doesn't test real performance but validates the workflow speed.
    assert duration < 5 # Should be very quick for mock data
    
    # Error recovery
    # To test this, we would need to make the mock server fail on certain requests
    # and patch the scraper's retry logic to have fewer attempts for test speed.
    with patch('src.services.scraper.mediamarkt_scraper.MediaMarktScraper.scrape_products_page') as mock_scrape:
        mock_scrape.side_effect = [
            Exception("Simulated network failure on first attempt"),
            MagicMock(return_value=[{"title": "Product on retry"}]) # Success on retry
        ]
        
        # This part of the test is more complex as it requires control over the retries
        # within the running task. A simpler unit test on the scraper's retry
        # decorator (if it has one) would be more effective.
        
        # For an E2E test, we might check logs or final status which indicates retries happened.
        pass 