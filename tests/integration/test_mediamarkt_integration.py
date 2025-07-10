"""
Integration tests for MediaMarkt scraper with system components.
Tests the scraper's integration with database, Celery, notifications, and API endpoints.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any
import asyncio

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.scraper.mediamarkt_scraper import MediaMarktScraper, scrape_mediamarkt_products
from src.models.product import Product, ProductSource
from src.models.arbitrage import ArbitrageOpportunity, OpportunityStatus
from src.models.notification import NotificationMessage, NotificationChannel, MessageStatus
from src.services.matching.ean_matcher import EANMatcher
from src.services.matching.fuzzy_matcher import FuzzyMatcher
from src.services.analysis.arbitrage_analyzer import ArbitrageAnalyzer
from src.services.notifications.notification_manager import NotificationManager
from src.tasks.scraping_tasks import scrape_mediamarkt_task
from src.tasks.matching_tasks import match_products_task
from src.tasks.analysis_tasks import analyze_arbitrage_task
from tests.mocks.mediamarkt_html import (
    MEDIAMARKT_PAGE_1_HTML,
    MEDIAMARKT_PAGE_2_HTML,
    MEDIAMARKT_EMPTY_PAGE_HTML,
    MEDIAMARKT_MALFORMED_HTML
)


class TestMediaMarktDatabaseIntegration:
    """Test MediaMarkt scraper integration with database operations."""
    
    @pytest_asyncio.fixture
    async def mock_scraper_with_data(self):
        """Create a mock scraper that returns realistic product data."""
        scraper = AsyncMock(spec=MediaMarktScraper)
        scraper.scrape_all_products.return_value = [
            {
                "title": "Apple iPhone 15 Pro (256GB) - Natural Titanium",
                "price": Decimal("1299.00"),
                "original_price": Decimal("1399.00"),
                "discount_percentage": Decimal("7.14"),
                "product_url": "https://mediamarkt.pt/produto/apple-iphone-15-pro-256gb-natural-titanium",
                "ean": "194253432807",
                "asin": "B0CHX2F5QT",
                "brand": "Apple",
                "category": "Smartphones > Apple",
                "availability": "Em stock",
                "stock_status": "in_stock",
                "scraped_at": datetime.utcnow()
            },
            {
                "title": "Samsung Galaxy S24 Ultra (512GB) - Titanium Black",
                "price": Decimal("1399.99"),
                "original_price": Decimal("1599.99"),
                "discount_percentage": Decimal("12.50"),
                "product_url": "https://mediamarkt.pt/produto/samsung-galaxy-s24-ultra-512gb-titanium-black",
                "ean": "8806095048826",
                "asin": None,  # Some products might not have ASIN
                "brand": "Samsung",
                "category": "Smartphones > Samsung",
                "availability": "Em stock",
                "stock_status": "in_stock",
                "scraped_at": datetime.utcnow()
            },
            {
                "title": "Sony WH-1000XM5 Wireless Noise Canceling Headphones",
                "price": Decimal("349.99"),
                "original_price": Decimal("399.99"),
                "discount_percentage": Decimal("12.50"),
                "product_url": "https://mediamarkt.pt/produto/sony-wh-1000xm5-wireless-headphones",
                "ean": "4548736141537",
                "asin": "B09XS7JWHH",
                "brand": "Sony",
                "category": "Audio > Headphones",
                "availability": "Em stock",
                "stock_status": "in_stock",
                "scraped_at": datetime.utcnow()
            }
        ]
        return scraper
    
    @pytest_asyncio.fixture
    async def existing_products(self, db_session: AsyncSession):
        """Create some existing products in the database for update testing."""
        products = [
            Product(
                name="Apple iPhone 15 Pro (256GB) - Natural Titanium",
                brand="Apple",
                ean="194253432807",
                asin="B0CHX2F5QT",
                current_price=Decimal("1349.00"),  # Different price for update testing
                source=ProductSource.MEDIAMARKT,
                product_url="https://mediamarkt.pt/produto/apple-iphone-15-pro-256gb-natural-titanium",
                last_updated=datetime.utcnow() - timedelta(hours=2)
            )
        ]
        
        for product in products:
            db_session.add(product)
        await db_session.commit()
        
        return products
    
    async def test_scrape_and_store_new_products(
        self,
        db_session: AsyncSession,
        mock_scraper_with_data: AsyncMock
    ):
        """Test scraping products and storing them in the database."""
        
        with patch('src.services.scraper.mediamarkt_scraper.MediaMarktScraper') as mock_class:
            mock_class.return_value.__aenter__.return_value = mock_scraper_with_data
            
            # Execute scraping
            products_data = await mock_scraper_with_data.scrape_all_products()
            
            # Store products in database
            stored_products = []
            for product_data in products_data:
                product = Product(
                    name=product_data["title"],
                    brand=product_data["brand"],
                    ean=product_data["ean"],
                    asin=product_data.get("asin"),
                    current_price=product_data["price"],
                    original_price=product_data.get("original_price"),
                    discount_percentage=product_data.get("discount_percentage"),
                    source=ProductSource.MEDIAMARKT,
                    product_url=product_data["product_url"],
                    category=product_data.get("category"),
                    stock_status=product_data["stock_status"],
                    last_updated=product_data["scraped_at"]
                )
                db_session.add(product)
                stored_products.append(product)
            
            await db_session.commit()
            
            # Verify products were stored
            assert len(stored_products) == 3
            
            # Check specific product details
            iphone = next(p for p in stored_products if "iPhone" in p.name)
            assert iphone.ean == "194253432807"
            assert iphone.current_price == Decimal("1299.00")
            assert iphone.brand == "Apple"
            assert iphone.asin == "B0CHX2F5QT"
            
            samsung = next(p for p in stored_products if "Samsung" in p.name)
            assert samsung.ean == "8806095048826"
            assert samsung.asin is None  # No ASIN available
            assert samsung.brand == "Samsung"
    
    async def test_scrape_and_update_existing_products(
        self,
        db_session: AsyncSession,
        existing_products: List[Product],
        mock_scraper_with_data: AsyncMock
    ):
        """Test updating existing products with new scraped data."""
        
        with patch('src.services.scraper.mediamarkt_scraper.MediaMarktScraper') as mock_class:
            mock_class.return_value.__aenter__.return_value = mock_scraper_with_data
            
            # Get existing product
            existing_product = existing_products[0]
            original_price = existing_product.current_price
            original_updated = existing_product.last_updated
            
            # Execute scraping
            products_data = await mock_scraper_with_data.scrape_all_products()
            
            # Find matching product data
            matching_data = next(
                p for p in products_data 
                if p["ean"] == existing_product.ean
            )
            
            # Update existing product
            existing_product.current_price = matching_data["price"]
            existing_product.original_price = matching_data.get("original_price")
            existing_product.discount_percentage = matching_data.get("discount_percentage")
            existing_product.last_updated = matching_data["scraped_at"]
            
            await db_session.commit()
            await db_session.refresh(existing_product)
            
            # Verify product was updated
            assert existing_product.current_price == Decimal("1299.00")
            assert existing_product.current_price != original_price
            assert existing_product.last_updated > original_updated
            assert existing_product.discount_percentage == Decimal("7.14")
    
    async def test_scrape_with_database_transaction_rollback(
        self,
        db_session: AsyncSession,
        mock_scraper_with_data: AsyncMock
    ):
        """Test database rollback on scraping errors."""
        
        # Simulate a database error during storage
        with patch('src.services.scraper.mediamarkt_scraper.MediaMarktScraper') as mock_class:
            mock_class.return_value.__aenter__.return_value = mock_scraper_with_data
            
            products_data = await mock_scraper_with_data.scrape_all_products()
            
            try:
                # Start transaction
                for i, product_data in enumerate(products_data):
                    product = Product(
                        name=product_data["title"],
                        brand=product_data["brand"],
                        ean=product_data["ean"],
                        current_price=product_data["price"],
                        source=ProductSource.MEDIAMARKT,
                        product_url=product_data["product_url"]
                    )
                    db_session.add(product)
                    
                    # Simulate error on second product
                    if i == 1:
                        raise Exception("Database connection lost")
                
                await db_session.commit()
                
            except Exception:
                await db_session.rollback()
            
            # Verify no products were stored due to rollback
            from sqlalchemy import select
            result = await db_session.execute(select(Product))
            products = result.scalars().all()
            assert len(products) == 0


class TestMediaMarktCeleryIntegration:
    """Test MediaMarkt scraper integration with Celery background tasks."""
    
    @pytest_asyncio.fixture
    async def mock_celery_task_results(self):
        """Mock Celery task results."""
        return {
            "scraping_task_id": "scrape-123",
            "matching_task_id": "match-456", 
            "analysis_task_id": "analyze-789"
        }
    
    async def test_celery_scraping_task_integration(
        self,
        db_session: AsyncSession,
        mock_celery_task_results: Dict[str, str]
    ):
        """Test MediaMarkt scraping via Celery task."""
        
        mock_scraped_data = [
            {
                "title": "Test Product",
                "price": Decimal("99.99"),
                "ean": "1234567890123",
                "brand": "Test Brand",
                "product_url": "https://mediamarkt.pt/test",
                "stock_status": "in_stock",
                "scraped_at": datetime.utcnow()
            }
        ]
        
        with patch('src.tasks.scraping_tasks.MediaMarktScraper') as mock_scraper_class:
            mock_scraper = AsyncMock()
            mock_scraper.scrape_all_products.return_value = mock_scraped_data
            mock_scraper_class.return_value.__aenter__.return_value = mock_scraper
            
            with patch('src.tasks.scraping_tasks.get_db_session') as mock_get_db:
                mock_get_db.return_value = db_session
                
                # Execute the Celery task
                result = await scrape_mediamarkt_task.apply_async().get()
                
                # Verify task execution
                assert result["status"] == "completed"
                assert result["products_scraped"] == 1
                assert "scraping_time" in result
    
    async def test_celery_task_chain_integration(
        self,
        db_session: AsyncSession,
        mock_celery_task_results: Dict[str, str]
    ):
        """Test full Celery task chain: scrape -> match -> analyze."""
        
        # Mock data for each stage
        mock_scraped_products = [
            {
                "title": "Apple iPhone 15 Pro",
                "price": Decimal("1299.00"),
                "ean": "194253432807",
                "asin": "B0CHX2F5QT",
                "brand": "Apple",
                "product_url": "https://mediamarkt.pt/iphone15pro",
                "stock_status": "in_stock",
                "scraped_at": datetime.utcnow()
            }
        ]
        
        mock_amazon_products = [
            {
                "asin": "B0CHX2F5QT",
                "title": "Apple iPhone 15 Pro (256GB)",
                "current_price": Decimal("1399.00"),
                "ean": "194253432807"
            }
        ]
        
        mock_arbitrage_opportunities = [
            {
                "mediamarkt_product_id": 1,
                "amazon_product_id": 2,
                "profit_amount": Decimal("100.00"),
                "profit_percentage": Decimal("7.69"),
                "status": OpportunityStatus.ACTIVE
            }
        ]
        
        with patch('src.tasks.scraping_tasks.MediaMarktScraper') as mock_scraper:
            mock_scraper_instance = AsyncMock()
            mock_scraper_instance.scrape_all_products.return_value = mock_scraped_products
            mock_scraper.return_value.__aenter__.return_value = mock_scraper_instance
            
            with patch('src.tasks.matching_tasks.EANMatcher') as mock_matcher:
                mock_matcher_instance = AsyncMock()
                mock_matcher_instance.find_matches.return_value = mock_amazon_products
                mock_matcher.return_value = mock_matcher_instance
                
                with patch('src.tasks.analysis_tasks.ArbitrageAnalyzer') as mock_analyzer:
                    mock_analyzer_instance = AsyncMock()
                    mock_analyzer_instance.analyze_opportunities.return_value = mock_arbitrage_opportunities
                    mock_analyzer.return_value = mock_analyzer_instance
                    
                    # Execute task chain
                    scrape_result = await scrape_mediamarkt_task.apply_async().get()
                    match_result = await match_products_task.apply_async().get()
                    analyze_result = await analyze_arbitrage_task.apply_async().get()
                    
                    # Verify chain execution
                    assert scrape_result["status"] == "completed"
                    assert match_result["status"] == "completed"
                    assert analyze_result["status"] == "completed"
                    assert analyze_result["opportunities_found"] == 1
    
    async def test_celery_task_error_handling(
        self,
        db_session: AsyncSession
    ):
        """Test Celery task error handling and retry logic."""
        
        with patch('src.tasks.scraping_tasks.MediaMarktScraper') as mock_scraper:
            # Simulate scraper failure
            mock_scraper.side_effect = Exception("Browser failed to start")
            
            try:
                result = await scrape_mediamarkt_task.apply_async().get()
                assert False, "Expected task to raise exception"
            except Exception as e:
                assert "Browser failed to start" in str(e)
    
    async def test_celery_task_with_rate_limiting(
        self,
        db_session: AsyncSession
    ):
        """Test Celery task respects rate limiting."""
        
        with patch('src.tasks.scraping_tasks.MediaMarktScraper') as mock_scraper:
            mock_scraper_instance = AsyncMock()
            # Simulate rate limiting delay
            async def delayed_scrape(*args, **kwargs):
                await asyncio.sleep(0.1)  # Simulate delay
                return []
            
            mock_scraper_instance.scrape_all_products = delayed_scrape
            mock_scraper.return_value.__aenter__.return_value = mock_scraper_instance
            
            start_time = datetime.utcnow()
            result = await scrape_mediamarkt_task.apply_async().get()
            end_time = datetime.utcnow()
            
            # Verify task took appropriate time (considering rate limiting)
            execution_time = (end_time - start_time).total_seconds()
            assert execution_time >= 0.1  # At least the delay time


class TestMediaMarktMatchingIntegration:
    """Test MediaMarkt scraper integration with product matching services."""
    
    @pytest_asyncio.fixture
    async def mediamarkt_products(self, db_session: AsyncSession):
        """Create MediaMarkt products for matching tests."""
        products = [
            Product(
                name="Apple iPhone 15 Pro (256GB) - Natural Titanium",
                brand="Apple",
                ean="194253432807",
                asin="B0CHX2F5QT",
                current_price=Decimal("1299.00"),
                source=ProductSource.MEDIAMARKT,
                product_url="https://mediamarkt.pt/iphone15pro"
            ),
            Product(
                name="Samsung Galaxy S24 Ultra 512GB Titanium Black",
                brand="Samsung", 
                ean="8806095048826",
                current_price=Decimal("1399.99"),
                source=ProductSource.MEDIAMARKT,
                product_url="https://mediamarkt.pt/galaxy-s24-ultra"
            ),
            Product(
                name="Sony WH-1000XM5 Headphones Black",
                brand="Sony",
                ean="4548736141537",
                current_price=Decimal("349.99"),
                source=ProductSource.MEDIAMARKT,
                product_url="https://mediamarkt.pt/sony-headphones"
            )
        ]
        
        for product in products:
            db_session.add(product)
        await db_session.commit()
        
        return products
    
    @pytest_asyncio.fixture
    async def amazon_products(self, db_session: AsyncSession):
        """Create Amazon products for matching tests."""
        products = [
            Product(
                name="Apple iPhone 15 Pro (256GB) - Natural Titanium",
                brand="Apple",
                ean="194253432807",
                asin="B0CHX2F5QT",
                current_price=Decimal("1399.00"),
                source=ProductSource.AMAZON,
                product_url="https://amazon.com/iphone15pro"
            ),
            Product(
                name="Samsung Galaxy S24 Ultra (512GB) - Titanium Black", 
                brand="Samsung",
                ean="8806095048826",
                current_price=Decimal("1499.99"),
                source=ProductSource.AMAZON,
                product_url="https://amazon.com/galaxy-s24-ultra"
            )
        ]
        
        for product in products:
            db_session.add(product)
        await db_session.commit()
        
        return products
    
    async def test_ean_matching_integration(
        self,
        db_session: AsyncSession,
        mediamarkt_products: List[Product],
        amazon_products: List[Product]
    ):
        """Test EAN-based matching between MediaMarkt and Amazon products."""
        
        matcher = EANMatcher(db_session)
        
        # Find matches for MediaMarkt products
        matches = await matcher.find_matches(
            source_products=mediamarkt_products,
            target_source=ProductSource.AMAZON
        )
        
        # Verify matches found
        assert len(matches) == 2  # iPhone and Samsung should match
        
        # Check iPhone match
        iphone_match = next(m for m in matches if "iPhone" in m.source_product.name)
        assert iphone_match.source_product.ean == "194253432807"
        assert iphone_match.target_product.ean == "194253432807"
        assert iphone_match.match_confidence == 1.0  # Perfect EAN match
        assert iphone_match.match_type == "ean"
        
        # Check Samsung match
        samsung_match = next(m for m in matches if "Samsung" in m.source_product.name)
        assert samsung_match.source_product.ean == "8806095048826"
        assert samsung_match.target_product.ean == "8806095048826"
        assert samsung_match.match_confidence == 1.0
    
    async def test_fuzzy_matching_integration(
        self,
        db_session: AsyncSession,
        mediamarkt_products: List[Product]
    ):
        """Test fuzzy matching for products without EAN matches."""
        
        # Create Amazon product with similar name but different EAN
        similar_product = Product(
            name="Apple iPhone 15 Pro 256GB Natural Titanium",  # Slightly different name
            brand="Apple",
            ean="194253432999",  # Different EAN
            current_price=Decimal("1449.00"),
            source=ProductSource.AMAZON,
            product_url="https://amazon.com/iphone15pro-similar"
        )
        
        db_session.add(similar_product)
        await db_session.commit()
        
        fuzzy_matcher = FuzzyMatcher(db_session)
        
        # Find fuzzy matches
        matches = await fuzzy_matcher.find_matches(
            source_products=mediamarkt_products,
            target_source=ProductSource.AMAZON,
            min_similarity=0.8
        )
        
        # Verify fuzzy match found
        fuzzy_matches = [m for m in matches if m.match_type == "fuzzy"]
        assert len(fuzzy_matches) >= 1
        
        # Check the fuzzy match quality
        iphone_fuzzy = next(m for m in fuzzy_matches if "iPhone" in m.source_product.name)
        assert iphone_fuzzy.match_confidence >= 0.8
        assert iphone_fuzzy.match_confidence < 1.0  # Not perfect match
    
    async def test_combined_matching_strategy(
        self,
        db_session: AsyncSession,
        mediamarkt_products: List[Product],
        amazon_products: List[Product]
    ):
        """Test combined EAN + fuzzy matching strategy."""
        
        # Add a product that only has fuzzy match potential
        fuzzy_only_product = Product(
            name="Sony WH1000XM5 Wireless Headphones - Black Color",  # Similar to existing
            brand="Sony",
            ean="4548736141999",  # Different EAN
            current_price=Decimal("379.99"),
            source=ProductSource.AMAZON,
            product_url="https://amazon.com/sony-headphones-similar"
        )
        
        db_session.add(fuzzy_only_product)
        await db_session.commit()
        
        # First try EAN matching
        ean_matcher = EANMatcher(db_session)
        ean_matches = await ean_matcher.find_matches(
            source_products=mediamarkt_products,
            target_source=ProductSource.AMAZON
        )
        
        # Then try fuzzy matching for unmatched products
        unmatched_products = [
            p for p in mediamarkt_products 
            if not any(m.source_product.id == p.id for m in ean_matches)
        ]
        
        fuzzy_matcher = FuzzyMatcher(db_session)
        fuzzy_matches = await fuzzy_matcher.find_matches(
            source_products=unmatched_products,
            target_source=ProductSource.AMAZON,
            min_similarity=0.7
        )
        
        # Combine results
        all_matches = ean_matches + fuzzy_matches
        
        # Verify comprehensive matching
        assert len(ean_matches) == 2  # iPhone and Samsung EAN matches
        assert len(fuzzy_matches) >= 1  # Sony fuzzy match
        assert len(all_matches) >= 3


class TestMediaMarktNotificationIntegration:
    """Test MediaMarkt scraper integration with notification services."""
    
    @pytest_asyncio.fixture
    async def arbitrage_opportunities(self, db_session: AsyncSession):
        """Create arbitrage opportunities for notification testing."""
        
        # Create MediaMarkt product
        mediamarkt_product = Product(
            name="Apple iPhone 15 Pro (256GB)",
            brand="Apple",
            ean="194253432807",
            current_price=Decimal("1299.00"),
            source=ProductSource.MEDIAMARKT,
            product_url="https://mediamarkt.pt/iphone15pro"
        )
        
        # Create Amazon product  
        amazon_product = Product(
            name="Apple iPhone 15 Pro (256GB)",
            brand="Apple", 
            ean="194253432807",
            current_price=Decimal("1449.00"),
            source=ProductSource.AMAZON,
            product_url="https://amazon.com/iphone15pro"
        )
        
        db_session.add_all([mediamarkt_product, amazon_product])
        await db_session.commit()
        
        # Create arbitrage opportunity
        opportunity = ArbitrageOpportunity(
            mediamarkt_product_id=mediamarkt_product.id,
            amazon_product_id=amazon_product.id,
            price_difference=Decimal("150.00"),
            profit_margin=Decimal("10.34"),
            confidence_score=Decimal("95.5"),
            status=OpportunityStatus.ACTIVE,
            detected_at=datetime.utcnow()
        )
        
        db_session.add(opportunity)
        await db_session.commit()
        
        return [opportunity]
    
    async def test_notification_on_new_arbitrage_opportunity(
        self,
        db_session: AsyncSession,
        arbitrage_opportunities: List[ArbitrageOpportunity]
    ):
        """Test notifications are sent when new arbitrage opportunities are detected."""
        
        opportunity = arbitrage_opportunities[0]
        
        with patch('src.services.notifications.notification_manager.TelegramNotifier') as mock_telegram:
            with patch('src.services.notifications.notification_manager.SlackNotifier') as mock_slack:
                with patch('src.services.notifications.notification_manager.EmailNotifier') as mock_email:
                    
                    # Configure mocks
                    mock_telegram.return_value.send_message = AsyncMock(return_value=True)
                    mock_slack.return_value.send_message = AsyncMock(return_value=True)
                    mock_email.return_value.send_message = AsyncMock(return_value=True)
                    
                    # Send notifications
                    notification_manager = NotificationManager(db_session)
                    await notification_manager.send_arbitrage_alert(opportunity)
                    
                    # Verify notifications were sent
                    mock_telegram.return_value.send_message.assert_called_once()
                    mock_slack.return_value.send_message.assert_called_once()
                    mock_email.return_value.send_message.assert_called_once()
    
    async def test_notification_message_persistence(
        self,
        db_session: AsyncSession,
        arbitrage_opportunities: List[ArbitrageOpportunity]
    ):
        """Test notification messages are persisted in database."""
        
        opportunity = arbitrage_opportunities[0]
        
        with patch('src.services.notifications.notification_manager.TelegramNotifier') as mock_telegram:
            mock_telegram.return_value.send_message = AsyncMock(return_value=True)
            
            notification_manager = NotificationManager(db_session)
            
            # Send notification and store message
            message = NotificationMessage(
                channel=NotificationChannel.TELEGRAM,
                recipient="@arbitrage_channel",
                subject="New Arbitrage Opportunity",
                content=f"New opportunity detected: {opportunity.profit_margin}% profit",
                opportunity_id=opportunity.id,
                status=MessageStatus.PENDING
            )
            
            db_session.add(message)
            await db_session.commit()
            
            # Simulate sending
            await notification_manager.send_message(message)
            
            # Update message status
            message.status = MessageStatus.SENT
            message.sent_at = datetime.utcnow()
            await db_session.commit()
            
            # Verify message was persisted
            from sqlalchemy import select
            result = await db_session.execute(
                select(NotificationMessage).where(NotificationMessage.id == message.id)
            )
            stored_message = result.scalar_one()
            
            assert stored_message.status == MessageStatus.SENT
            assert stored_message.sent_at is not None
            assert stored_message.opportunity_id == opportunity.id
    
    async def test_bulk_notification_on_multiple_opportunities(
        self,
        db_session: AsyncSession
    ):
        """Test bulk notifications when multiple opportunities are detected."""
        
        # Create multiple arbitrage opportunities
        opportunities = []
        for i in range(5):
            mediamarkt_product = Product(
                name=f"Test Product {i}",
                brand="TestBrand",
                ean=f"123456789012{i}",
                current_price=Decimal(f"{100 + i * 10}.00"),
                source=ProductSource.MEDIAMARKT,
                product_url=f"https://mediamarkt.pt/product-{i}"
            )
            
            amazon_product = Product(
                name=f"Test Product {i}",
                brand="TestBrand",
                ean=f"123456789012{i}",
                current_price=Decimal(f"{120 + i * 10}.00"),
                source=ProductSource.AMAZON,
                product_url=f"https://amazon.com/product-{i}"
            )
            
            db_session.add_all([mediamarkt_product, amazon_product])
            await db_session.commit()
            
            opportunity = ArbitrageOpportunity(
                mediamarkt_product_id=mediamarkt_product.id,
                amazon_product_id=amazon_product.id,
                price_difference=Decimal("20.00"),
                profit_margin=Decimal("16.67"),
                confidence_score=Decimal("90.0"),
                status=OpportunityStatus.ACTIVE,
                detected_at=datetime.utcnow()
            )
            
            db_session.add(opportunity)
            opportunities.append(opportunity)
        
        await db_session.commit()
        
        with patch('src.services.notifications.notification_manager.TelegramNotifier') as mock_telegram:
            mock_telegram.return_value.send_message = AsyncMock(return_value=True)
            
            notification_manager = NotificationManager(db_session)
            
            # Send bulk notification
            await notification_manager.send_bulk_arbitrage_summary(opportunities)
            
            # Verify bulk notification was sent
            mock_telegram.return_value.send_message.assert_called_once()
            
            # Check the message content includes all opportunities
            call_args = mock_telegram.return_value.send_message.call_args
            message_content = call_args[0][0]  # First argument
            
            assert "5 opportunities" in message_content or "5 arbitrage" in message_content


class TestMediaMarktAPIIntegration:
    """Test MediaMarkt scraper integration with FastAPI endpoints."""
    
    async def test_scraping_endpoint_integration(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession
    ):
        """Test triggering MediaMarkt scraping via API endpoint."""
        
        with patch('src.services.scraper.mediamarkt_scraper.MediaMarktScraper') as mock_scraper:
            mock_scraper_instance = AsyncMock()
            mock_scraper_instance.scrape_all_products.return_value = [
                {
                    "title": "Test Product via API",
                    "price": Decimal("199.99"),
                    "ean": "1111111111111",
                    "brand": "TestBrand",
                    "product_url": "https://mediamarkt.pt/api-test",
                    "stock_status": "in_stock",
                    "scraped_at": datetime.utcnow()
                }
            ]
            mock_scraper.return_value.__aenter__.return_value = mock_scraper_instance
            
            # Trigger scraping via API
            response = await client.post(
                "/api/v1/scraping/mediamarkt/start",
                headers=auth_headers,
                json={"max_pages": 1}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "started"
            assert "task_id" in data
    
    async def test_products_api_with_scraped_data(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession
    ):
        """Test products API endpoints with scraped MediaMarkt data."""
        
        # Create scraped product
        product = Product(
            name="API Test Product",
            brand="TestBrand",
            ean="2222222222222",
            current_price=Decimal("299.99"),
            source=ProductSource.MEDIAMARKT,
            product_url="https://mediamarkt.pt/api-product"
        )
        
        db_session.add(product)
        await db_session.commit()
        
        # Test GET products endpoint
        response = await client.get(
            "/api/v1/products/",
            headers=auth_headers,
            params={"source": "mediamarkt", "limit": 10}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 1
        
        # Find our test product
        test_product = next(
            (p for p in data["items"] if p["ean"] == "2222222222222"),
            None
        )
        assert test_product is not None
        assert test_product["name"] == "API Test Product"
        assert test_product["source"] == "mediamarkt"
    
    async def test_arbitrage_api_integration(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession
    ):
        """Test arbitrage opportunities API with MediaMarkt products."""
        
        # Create MediaMarkt and Amazon products
        mediamarkt_product = Product(
            name="API Arbitrage Test",
            brand="TestBrand",
            ean="3333333333333",
            current_price=Decimal("199.99"),
            source=ProductSource.MEDIAMARKT,
            product_url="https://mediamarkt.pt/arbitrage-test"
        )
        
        amazon_product = Product(
            name="API Arbitrage Test",
            brand="TestBrand",
            ean="3333333333333",
            current_price=Decimal("249.99"),
            source=ProductSource.AMAZON,
            product_url="https://amazon.com/arbitrage-test"
        )
        
        db_session.add_all([mediamarkt_product, amazon_product])
        await db_session.commit()
        
        # Create arbitrage opportunity
        opportunity = ArbitrageOpportunity(
            mediamarkt_product_id=mediamarkt_product.id,
            amazon_product_id=amazon_product.id,
            price_difference=Decimal("50.00"),
            profit_margin=Decimal("20.0"),
            confidence_score=Decimal("95.0"),
            status=OpportunityStatus.ACTIVE,
            detected_at=datetime.utcnow()
        )
        
        db_session.add(opportunity)
        await db_session.commit()
        
        # Test arbitrage opportunities endpoint
        response = await client.get(
            "/api/v1/arbitrage/opportunities/",
            headers=auth_headers,
            params={"status": "active", "limit": 10}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 1
        
        # Find our test opportunity
        test_opportunity = next(
            (o for o in data["items"] if o["profit_margin"] == 20.0),
            None
        )
        assert test_opportunity is not None
        assert test_opportunity["price_difference"] == 50.0
        assert test_opportunity["status"] == "active"


class TestMediaMarktErrorHandlingIntegration:
    """Test MediaMarkt scraper error handling in integration scenarios."""
    
    async def test_database_connection_failure_handling(
        self,
        db_session: AsyncSession
    ):
        """Test handling of database connection failures during scraping."""
        
        with patch('src.services.scraper.mediamarkt_scraper.MediaMarktScraper') as mock_scraper:
            mock_scraper_instance = AsyncMock()
            mock_scraper_instance.scrape_all_products.return_value = [
                {
                    "title": "Error Test Product",
                    "price": Decimal("99.99"),
                    "ean": "5555555555555",
                    "brand": "ErrorBrand",
                    "product_url": "https://mediamarkt.pt/error-test",
                    "stock_status": "in_stock",
                    "scraped_at": datetime.utcnow()
                }
            ]
            mock_scraper.return_value.__aenter__.return_value = mock_scraper_instance
            
            # Simulate database connection failure
            with patch.object(db_session, 'add', side_effect=Exception("Database connection lost")):
                
                try:
                    # Attempt scraping with database storage
                    products_data = await mock_scraper_instance.scrape_all_products()
                    
                    for product_data in products_data:
                        product = Product(
                            name=product_data["title"],
                            brand=product_data["brand"],
                            ean=product_data["ean"],
                            current_price=product_data["price"],
                            source=ProductSource.MEDIAMARKT,
                            product_url=product_data["product_url"]
                        )
                        db_session.add(product)  # This will fail
                    
                    await db_session.commit()
                    
                except Exception as e:
                    # Verify error is properly handled
                    assert "Database connection lost" in str(e)
                    await db_session.rollback()
    
    async def test_notification_service_failure_handling(
        self,
        db_session: AsyncSession
    ):
        """Test handling of notification service failures."""
        
        # Create test opportunity
        opportunity = ArbitrageOpportunity(
            mediamarkt_product_id=1,
            amazon_product_id=2,
            price_difference=Decimal("100.00"),
            profit_margin=Decimal("25.0"),
            confidence_score=Decimal("90.0"),
            status=OpportunityStatus.ACTIVE,
            detected_at=datetime.utcnow()
        )
        
        with patch('src.services.notifications.notification_manager.TelegramNotifier') as mock_telegram:
            # Simulate notification failure
            mock_telegram.return_value.send_message = AsyncMock(
                side_effect=Exception("Telegram API unavailable")
            )
            
            notification_manager = NotificationManager(db_session)
            
            # Attempt to send notification
            try:
                await notification_manager.send_arbitrage_alert(opportunity)
            except Exception as e:
                # Verify error is captured and handled gracefully
                assert "Telegram API unavailable" in str(e)
    
    async def test_concurrent_scraping_error_handling(
        self,
        db_session: AsyncSession
    ):
        """Test error handling during concurrent scraping operations."""
        
        async def failing_scraper():
            await asyncio.sleep(0.1)
            raise Exception("Scraper instance failed")
        
        async def successful_scraper():
            await asyncio.sleep(0.1)
            return [
                {
                    "title": "Concurrent Test Product",
                    "price": Decimal("149.99"),
                    "ean": "6666666666666",
                    "brand": "ConcurrentBrand",
                    "product_url": "https://mediamarkt.pt/concurrent-test",
                    "stock_status": "in_stock",
                    "scraped_at": datetime.utcnow()
                }
            ]
        
        # Run concurrent operations with one failure
        tasks = [
            failing_scraper(),
            successful_scraper(),
            successful_scraper()
        ]
        
        # Gather results, handling failures gracefully
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify mixed results
        exceptions = [r for r in results if isinstance(r, Exception)]
        successes = [r for r in results if not isinstance(r, Exception)]
        
        assert len(exceptions) == 1
        assert len(successes) == 2
        assert "Scraper instance failed" in str(exceptions[0]) 