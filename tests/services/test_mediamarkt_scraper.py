"""
Unit tests for the MediaMarkt Scraper service.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from decimal import Decimal

from src.services.scraper.mediamarkt_scraper import MediaMarktScraper


class TestMediaMarktScraper:
    """Test cases for MediaMarktScraper."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.scraper = MediaMarktScraper()
    
    def test_initialization(self):
        """Test scraper initialization."""
        assert self.scraper.base_url == "https://www.mediamarkt.pt"
        assert self.scraper.search_url == "https://mediamarkt.pt/pages/search-results-page?q=+"
        assert self.scraper.browser is None
        assert self.scraper.context is None
        assert self.scraper.page is None
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager functionality."""
        with patch.object(self.scraper, 'start_browser') as mock_start:
            with patch.object(self.scraper, 'close_browser') as mock_close:
                async with self.scraper as scraper:
                    assert scraper == self.scraper
                    mock_start.assert_called_once()
                mock_close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_browser(self):
        """Test browser startup."""
        mock_playwright = AsyncMock()
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        
        with patch('src.services.scraper.mediamarkt_scraper.async_playwright', return_value=mock_playwright):
            await self.scraper.start_browser()
        
        assert self.scraper.browser == mock_browser
        assert self.scraper.context == mock_context
        assert self.scraper.page == mock_page
        
        # Verify browser was launched with correct options
        mock_playwright.chromium.launch.assert_called_once()
        launch_args = mock_playwright.chromium.launch.call_args[1]
        assert launch_args['headless'] is True
        assert 'user_agent' in launch_args
    
    @pytest.mark.asyncio
    async def test_close_browser(self):
        """Test browser cleanup."""
        # Set up mock browser, context, and page
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        
        self.scraper.browser = mock_browser
        self.scraper.context = mock_context
        self.scraper.page = mock_page
        
        await self.scraper.close_browser()
        
        mock_page.close.assert_called_once()
        mock_context.close.assert_called_once()
        mock_browser.close.assert_called_once()
        
        assert self.scraper.browser is None
        assert self.scraper.context is None
        assert self.scraper.page is None
    
    def test_extract_product_info(self):
        """Test product information extraction."""
        # Mock HTML product element
        mock_element = f"""
        <div class="product-item">
            <h3 class="product-title">iPhone 14 Pro Max 256GB Space Black</h3>
            <span class="product-brand">Apple</span>
            <div class="price">
                <span class="current-price">1299.99€</span>
                <span class="original-price">1399.99€</span>
            </div>
            <div class="product-details">
                <span class="ean">1234567890123</span>
                <span class="availability">Em Stock</span>
            </div>
            <a href="/produtos/iphone-14-pro-max" class="product-link">Ver Produto</a>
        </div>
        """
        
        # Mock BeautifulSoup element
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(mock_element, 'html.parser')
        product_element = soup.find('div', class_='product-item')
        
        product_info = self.scraper._extract_product_info(product_element)
        
        assert product_info['title'] == "iPhone 14 Pro Max 256GB Space Black"
        assert product_info['brand'] == "Apple"
        assert product_info['price'] == Decimal('1299.99')
        assert product_info['original_price'] == Decimal('1399.99')
        assert product_info['ean'] == "1234567890123"
        assert product_info['availability'] == "Em Stock"
        assert "iphone-14-pro-max" in product_info['url']
        assert product_info['currency'] == "EUR"
    
    def test_extract_product_info_minimal(self):
        """Test product extraction with minimal information."""
        # Mock minimal HTML
        mock_element = """
        <div class="product-item">
            <h3>Basic Product</h3>
            <span class="price">99.99€</span>
        </div>
        """
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(mock_element, 'html.parser')
        product_element = soup.find('div', class_='product-item')
        
        product_info = self.scraper._extract_product_info(product_element)
        
        assert product_info['title'] == "Basic Product"
        assert product_info['price'] == Decimal('99.99')
        assert product_info['brand'] == ""
        assert product_info['ean'] == ""
        assert product_info['currency'] == "EUR"
    
    def test_clean_text(self):
        """Test text cleaning functionality."""
        # Test normal text
        assert self.scraper._clean_text("  iPhone 14 Pro  ") == "iPhone 14 Pro"
        
        # Test text with special characters
        assert self.scraper._clean_text("Price: 1.299,99€") == "Price: 1.299,99€"
        
        # Test None input
        assert self.scraper._clean_text(None) == ""
        
        # Test empty input
        assert self.scraper._clean_text("") == ""
        
        # Test whitespace-only input
        assert self.scraper._clean_text("   \n\t   ") == ""
    
    def test_parse_price(self):
        """Test price parsing functionality."""
        # Test normal price formats
        assert self.scraper._parse_price("1299.99€") == Decimal('1299.99')
        assert self.scraper._parse_price("1.299,99€") == Decimal('1299.99')
        assert self.scraper._parse_price("€1299.99") == Decimal('1299.99')
        assert self.scraper._parse_price("1299,99 EUR") == Decimal('1299.99')
        
        # Test price without currency symbol
        assert self.scraper._parse_price("1299.99") == Decimal('1299.99')
        assert self.scraper._parse_price("1.299,99") == Decimal('1299.99')
        
        # Test invalid formats
        assert self.scraper._parse_price("") == Decimal('0.00')
        assert self.scraper._parse_price(None) == Decimal('0.00')
        assert self.scraper._parse_price("invalid") == Decimal('0.00')
        assert self.scraper._parse_price("€€€") == Decimal('0.00')
    
    def test_extract_ean(self):
        """Test EAN extraction from various sources."""
        # Mock product element with EAN in different locations
        mock_element = """
        <div class="product">
            <span class="ean">1234567890123</span>
            <div data-ean="1234567890123"></div>
            <script type="application/ld+json">
                {"@type": "Product", "gtin13": "1234567890123"}
            </script>
        </div>
        """
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(mock_element, 'html.parser')
        product_element = soup.find('div', class_='product')
        
        ean = self.scraper._extract_ean(product_element)
        assert ean == "1234567890123"
        
        # Test with no EAN
        mock_element_no_ean = '<div class="product"><span>No EAN here</span></div>'
        soup_no_ean = BeautifulSoup(mock_element_no_ean, 'html.parser')
        product_element_no_ean = soup_no_ean.find('div', class_='product')
        
        ean_empty = self.scraper._extract_ean(product_element_no_ean)
        assert ean_empty == ""
    
    @pytest.mark.asyncio
    async def test_scrape_products_page(self):
        """Test scraping products from a page."""
        # Mock page response
        mock_page = AsyncMock()
        mock_page.content.return_value = """
        <html>
            <body>
                <div class="products-grid">
                    <div class="product-item">
                        <h3>iPhone 14 Pro</h3>
                        <span class="brand">Apple</span>
                        <span class="price">999.99€</span>
                        <span class="ean">1111111111111</span>
                    </div>
                    <div class="product-item">
                        <h3>Galaxy S23</h3>
                        <span class="brand">Samsung</span>
                        <span class="price">799.99€</span>
                        <span class="ean">2222222222222</span>
                    </div>
                </div>
            </body>
        </html>
        """
        
        self.scraper.page = mock_page
        
        # Mock navigation
        mock_page.goto.return_value = None
        mock_page.wait_for_load_state.return_value = None
        
        with patch.object(self.scraper, '_extract_product_info') as mock_extract:
            # Mock extract to return product data
            mock_extract.side_effect = [
                {
                    'title': 'iPhone 14 Pro',
                    'brand': 'Apple',
                    'price': Decimal('999.99'),
                    'ean': '1111111111111'
                },
                {
                    'title': 'Galaxy S23',
                    'brand': 'Samsung',
                    'price': Decimal('799.99'),
                    'ean': '2222222222222'
                }
            ]
            
            products = await self.scraper.scrape_products_page()
        
        assert len(products) == 2
        assert products[0]['title'] == 'iPhone 14 Pro'
        assert products[1]['title'] == 'Galaxy S23'
        
        # Verify page navigation
        mock_page.goto.assert_called_once()
        mock_page.wait_for_load_state.assert_called()
    
    @pytest.mark.asyncio
    async def test_scrape_products_pagination(self):
        """Test scraping with pagination."""
        mock_page = AsyncMock()
        self.scraper.page = mock_page
        
        # Mock first page with next button
        mock_page.content.side_effect = [
            """<html><body>
                <div class="product-item"><h3>Product 1</h3></div>
                <a class="next-page" href="/page/2">Next</a>
            </body></html>""",
            """<html><body>
                <div class="product-item"><h3>Product 2</h3></div>
            </body></html>"""
        ]
        
        # Mock page navigation
        mock_page.goto.return_value = None
        mock_page.wait_for_load_state.return_value = None
        mock_page.click.return_value = None
        
        # Mock has next page detection
        mock_page.query_selector.side_effect = [
            Mock(),  # Next button exists on first page
            None     # No next button on second page
        ]
        
        with patch.object(self.scraper, '_extract_product_info') as mock_extract:
            mock_extract.side_effect = [
                {'title': 'Product 1', 'price': Decimal('10.00')},
                {'title': 'Product 2', 'price': Decimal('20.00')},
            ]
            
            products = await self.scraper.scrape_products_with_pagination(max_pages=2)
        
        assert len(products) == 2
        assert products[0]['title'] == 'Product 1'
        assert products[1]['title'] == 'Product 2'
    
    @pytest.mark.asyncio
    async def test_scrape_error_handling(self):
        """Test error handling during scraping."""
        mock_page = AsyncMock()
        self.scraper.page = mock_page
        
        # Mock page navigation to raise an exception
        mock_page.goto.side_effect = Exception("Network error")
        
        products = await self.scraper.scrape_products_page()
        
        # Should return empty list on error
        assert products == []
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting functionality."""
        mock_page = AsyncMock()
        self.scraper.page = mock_page
        
        # Track timing
        start_time = datetime.now()
        
        with patch('src.services.scraper.mediamarkt_scraper.asyncio.sleep') as mock_sleep:
            mock_sleep.return_value = None
            
            # Mock successful scraping
            mock_page.goto.return_value = None
            mock_page.content.return_value = "<html><body></body></html>"
            
            await self.scraper.scrape_products_page()
            await self.scraper.scrape_products_page()
        
        # Should call sleep for rate limiting
        assert mock_sleep.call_count >= 1
    
    def test_build_search_url(self):
        """Test search URL building."""
        # Test basic query
        url = self.scraper._build_search_url("iphone")
        assert "q=iphone" in url
        
        # Test query with spaces
        url = self.scraper._build_search_url("iphone 14 pro")
        assert "q=iphone%2014%20pro" in url or "q=iphone+14+pro" in url
        
        # Test empty query (should use unified endpoint)
        url = self.scraper._build_search_url("")
        assert url == self.scraper.search_url
        
        # Test None query
        url = self.scraper._build_search_url(None)
        assert url == self.scraper.search_url
    
    @pytest.mark.asyncio
    async def test_scrape_product_details(self):
        """Test scraping detailed product information."""
        mock_page = AsyncMock()
        self.scraper.page = mock_page
        
        # Mock product detail page
        mock_page.content.return_value = """
        <html>
            <body>
                <div class="product-detail">
                    <h1>iPhone 14 Pro Max 256GB</h1>
                    <span class="brand">Apple</span>
                    <div class="price-info">
                        <span class="current-price">1299.99€</span>
                        <span class="original-price">1399.99€</span>
                    </div>
                    <div class="specs">
                        <span class="ean">1234567890123</span>
                        <span class="model">MQ9T3ZD/A</span>
                    </div>
                    <div class="description">
                        <p>High-end smartphone with advanced camera system.</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        mock_page.goto.return_value = None
        mock_page.wait_for_load_state.return_value = None
        
        product_url = "https://www.mediamarkt.pt/produtos/iphone-14-pro-max"
        
        with patch.object(self.scraper, '_extract_detailed_product_info') as mock_extract:
            mock_extract.return_value = {
                'title': 'iPhone 14 Pro Max 256GB',
                'brand': 'Apple',
                'price': Decimal('1299.99'),
                'original_price': Decimal('1399.99'),
                'ean': '1234567890123',
                'model': 'MQ9T3ZD/A',
                'description': 'High-end smartphone with advanced camera system.',
                'url': product_url
            }
            
            product_details = await self.scraper.scrape_product_details(product_url)
        
        assert product_details['title'] == 'iPhone 14 Pro Max 256GB'
        assert product_details['brand'] == 'Apple'
        assert product_details['ean'] == '1234567890123'
        mock_page.goto.assert_called_with(product_url)


@pytest.mark.asyncio
async def test_scraper_full_workflow():
    """Test complete scraper workflow."""
    scraper = MediaMarktScraper()
    
    # Mock the entire browser setup and scraping process
    with patch.object(scraper, 'start_browser') as mock_start:
        with patch.object(scraper, 'close_browser') as mock_close:
            with patch.object(scraper, 'scrape_products_page') as mock_scrape:
                mock_scrape.return_value = [
                    {
                        'title': 'iPhone 14 Pro',
                        'brand': 'Apple',
                        'price': Decimal('999.99'),
                        'ean': '1234567890123',
                        'scraped_at': datetime.now()
                    }
                ]
                
                async with scraper:
                    products = await scraper.scrape_products_page()
                
                assert len(products) == 1
                assert products[0]['title'] == 'iPhone 14 Pro'
                mock_start.assert_called_once()
                mock_close.assert_called_once() 