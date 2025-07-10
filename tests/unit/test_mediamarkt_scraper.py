"""
Unit tests for the MediaMarkt scraper.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from decimal import Decimal

from src.services.scraper.mediamarkt_scraper import MediaMarktScraper
from tests.mocks.mediamarkt_html import (
    MEDIAMARKT_PAGE_1_HTML,
    MEDIAMARKT_PAGE_2_HTML,
    MEDIAMARKT_EMPTY_PAGE_HTML,
    MEDIAMARKT_MALFORMED_HTML
)

@pytest.fixture
def mock_playwright_page():
    """Fixture for a mocked Playwright page object."""
    page = AsyncMock()
    page.content.return_value = MEDIAMARKT_PAGE_1_HTML
    page.goto = AsyncMock()
    page.wait_for_selector = AsyncMock()
    return page

@pytest.fixture
def scraper(mock_playwright_page):
    """Fixture for MediaMarktScraper with a mocked page."""
    scraper = MediaMarktScraper()
    scraper.page = mock_playwright_page
    scraper.base_url = "https://www.mediamarkt.pt"
    return scraper

@pytest.mark.asyncio
async def test_scrape_single_page_success(scraper, mock_playwright_page):
    """Test successful scraping of a single product page."""
    products = await scraper.scrape_products_page("http://mock.url/page1")
    
    assert len(products) == 10
    mock_playwright_page.goto.assert_called_once_with("http://mock.url/page1", wait_until="networkidle", timeout=30000)
    
    # Check first product
    product_1 = products[0]
    assert product_1['title'] == "Apple iPhone 15 Pro (256GB) - Natural Titanium"
    assert product_1['brand'] == "Apple"
    assert product_1['ean'] == "1234567890123"
    assert product_1['current_price'] == Decimal('1199.99')
    assert product_1['original_price'] == Decimal('1399.99')
    assert product_1['discount_percentage'] == 14.29
    assert product_1['stock_status'] == "in_stock"
    assert product_1['url'] == "https://www.mediamarkt.pt/product/apple-iphone-15-pro-256gb-natural-titanium"

    # Check product with no original price
    product_3 = products[2]
    assert product_3['original_price'] is None
    assert product_3['discount_percentage'] is None

    # Check out-of-stock product
    product_8 = products[7]
    assert product_8['stock_status'] == 'out_of_stock'


@pytest.mark.asyncio
async def test_data_extraction_from_html(scraper):
    """Test the extract_product_data method directly."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(MEDIAMARKT_PAGE_1_HTML, 'html.parser')
    product_element = soup.select_one(".product-wrapper")
    
    product_data = await scraper.extract_product_data(product_element, "http://mock.url")
    
    assert product_data is not None
    assert product_data['title'] == "Apple iPhone 15 Pro (256GB) - Natural Titanium"
    assert product_data['brand'] == "Apple"
    assert product_data['ean'] == "1234567890123"
    assert product_data['current_price'] == Decimal('1199.99')
    assert product_data['original_price'] == Decimal('1399.99')
    assert product_data['discount_percentage'] == 14.29
    assert product_data['stock_status'] == "in_stock"
    assert product_data['url'] == "https://www.mediamarkt.pt/product/apple-iphone-15-pro-256gb-natural-titanium"
    assert 'scraped_at' in product_data

@pytest.mark.asyncio
async def test_scrape_empty_page(scraper, mock_playwright_page):
    """Test scraping a page with no products."""
    mock_playwright_page.content.return_value = MEDIAMARKT_EMPTY_PAGE_HTML
    mock_playwright_page.wait_for_selector.side_effect = Exception("No selector found")

    products = await scraper.scrape_products_page("http://mock.url/empty")
    
    assert len(products) == 0

@pytest.mark.asyncio
async def test_scrape_malformed_page(scraper, mock_playwright_page):
    """Test scraping a page with malformed product HTML."""
    mock_playwright_page.content.return_value = MEDIAMARKT_MALFORMED_HTML
    
    products = await scraper.scrape_products_page("http://mock.url/malformed")
    
    # Should skip malformed entries and return valid ones if any, or empty list
    assert isinstance(products, list)
    # Based on the malformed HTML, no products should be successfully parsed
    assert len(products) == 0


@pytest.mark.asyncio
async def test_pagination_logic(scraper, mock_playwright_page):
    """Test the multi-page scraping logic."""
    
    async def side_effect(url, wait_until, timeout):
        if "page=2" in url:
            mock_playwright_page.content.return_value = MEDIAMARKT_PAGE_2_HTML
        else:
            mock_playwright_page.content.return_value = MEDIAMARKT_PAGE_1_HTML
        return AsyncMock()

    mock_playwright_page.goto = AsyncMock(side_effect=side_effect)

    all_products = await scraper.scrape_all_products(max_pages=2)

    assert len(all_products) == 15  # 10 from page 1, 5 from page 2
    assert mock_playwright_page.goto.call_count == 2


@pytest.mark.asyncio
async def test_error_handling_on_navigation(scraper, mock_playwright_page):
    """Test error handling when page navigation fails."""
    mock_playwright_page.goto.side_effect = Exception("Navigation timeout")

    products = await scraper.scrape_products_page("http://mock.url/error")
    
    assert products == []

def test_parse_price():
    """Test the price parsing utility function."""
    scraper = MediaMarktScraper()
    assert scraper.parse_price("€1.199,99") == Decimal("1199.99")
    assert scraper.parse_price("€349,99") == Decimal("349.99")
    assert scraper.parse_price("€1.299,00") == Decimal("1299.00")
    assert scraper.parse_price("€699.99") == Decimal("699.99") # . as separator
    assert scraper.parse_price("Invalid Price") is None
    assert scraper.parse_price("") is None

@pytest.mark.asyncio
async def test_stealth_mode_configuration():
    """Test that the browser is configured with stealth options."""
    with patch('playwright.async_api.async_playwright') as mock_playwright_context:
        mock_playwright = AsyncMock()
        mock_playwright_context.return_value.start.return_value = mock_playwright
        
        mock_browser = AsyncMock()
        mock_playwright.chromium.launch.return_value = mock_browser
        
        mock_context = AsyncMock()
        mock_browser.new_context.return_value = mock_context

        scraper = MediaMarktScraper()
        await scraper.start_browser()

        mock_playwright.chromium.launch.assert_called_once()
        
        # Check that new_context was called with stealth-related arguments
        _, kwargs = mock_browser.new_context.call_args
        assert 'user_agent' in kwargs
        assert 'locale' in kwargs
        assert 'timezone_id' in kwargs

        # Check that the init script for stealth is added
        mock_context.add_init_script.assert_called_once()
        script_content = mock_context.add_init_script.call_args[0][0]
        assert "Object.defineProperty(navigator, 'webdriver'" in script_content
        
        await scraper.close_browser() 