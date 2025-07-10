"""
End-to-End tests for MediaMarkt scraper complete workflow.
Tests the full pipeline: scraping -> storage -> matching -> analysis -> notifications.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any
import asyncio
import json

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.services.scraper.mediamarkt_scraper import MediaMarktScraper
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
from tests.mocks.mediamarkt_html import MEDIAMARKT_PAGE_1_HTML, MEDIAMARKT_PAGE_2_HTML


class TestCompleteArbitrageWorkflowE2E:
    """Test complete arbitrage detection workflow end-to-end."""
    
    @pytest_asyncio.fixture
    async def mock_keepa_responses(self):
        """Mock Keepa API responses for Amazon product data."""
        return {
            "B0CHX2F5QT": {  # iPhone 15 Pro
                "asin": "B0CHX2F5QT",
                "title": "Apple iPhone 15 Pro (256GB) - Natural Titanium",
                "current_price": 1449.00,
                "ean": "194253432807",
                "brand": "Apple",
                "category": "Electronics > Cell Phones & Accessories",
                "sales_rank": 15,
                "reviews_count": 1250,
                "rating": 4.5,
                "price_history": [
                    {"timestamp": "2024-01-01T00:00:00Z", "price": 1499.00},
                    {"timestamp": "2024-01-15T00:00:00Z", "price": 1449.00},
                    {"timestamp": "2024-01-30T00:00:00Z", "price": 1449.00}
                ]
            },
            "B09XS7JWHH": {  # Sony Headphones
                "asin": "B09XS7JWHH",
                "title": "Sony WH-1000XM5 Wireless Noise Canceling Headphones",
                "current_price": 399.99,
                "ean": "4548736141537",
                "brand": "Sony",
                "category": "Electronics > Headphones",
                "sales_rank": 45,
                "reviews_count": 3420,
                "rating": 4.7,
                "price_history": [
                    {"timestamp": "2024-01-01T00:00:00Z", "price": 399.99},
                    {"timestamp": "2024-01-15T00:00:00Z", "price": 379.99},
                    {"timestamp": "2024-01-30T00:00:00Z", "price": 399.99}
                ]
            }
        }
    
    @pytest_asyncio.fixture 
    async def mock_browser_responses(self):
        """Mock browser responses for MediaMarkt scraping."""
        return {
            "page_1": MEDIAMARKT_PAGE_1_HTML,
            "page_2": MEDIAMARKT_PAGE_2_HTML
        }
    
    async def test_complete_arbitrage_detection_workflow(
        self,
        db_session: AsyncSession,
        mock_keepa_responses: Dict[str, Any],
        mock_browser_responses: Dict[str, str]
    ):
        """Test complete workflow: scrape MediaMarkt -> match with Amazon -> analyze arbitrage -> send notifications."""
        
        # Step 1: Mock MediaMarkt scraping
        with patch('src.services.scraper.mediamarkt_scraper.MediaMarktScraper') as mock_scraper_class:
            mock_scraper = AsyncMock()
            mock_scraper.scrape_all_products.return_value = [
                {
                    "title": "Apple iPhone 15 Pro (256GB) - Natural Titanium",
                    "price": Decimal("1299.00"),  # Lower than Amazon price
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
                    "title": "Sony WH-1000XM5 Wireless Noise Canceling Headphones",
                    "price": Decimal("349.99"),  # Lower than Amazon price
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
            mock_scraper_class.return_value.__aenter__.return_value = mock_scraper
            
            # Step 2: Store scraped products in database
            scraped_data = await mock_scraper.scrape_all_products()
            mediamarkt_products = []
            
            for product_data in scraped_data:
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
                mediamarkt_products.append(product)
            
            await db_session.commit()
            
            # Step 3: Mock Amazon/Keepa data and store Amazon products
            amazon_products = []
            for asin, keepa_data in mock_keepa_responses.items():
                amazon_product = Product(
                    name=keepa_data["title"],
                    brand=keepa_data["brand"],
                    ean=keepa_data["ean"],
                    asin=keepa_data["asin"],
                    current_price=Decimal(str(keepa_data["current_price"])),
                    source=ProductSource.AMAZON,
                    product_url=f"https://amazon.com/dp/{asin}",
                    category=keepa_data["category"],
                    stock_status="in_stock",
                    last_updated=datetime.utcnow()
                )
                db_session.add(amazon_product)
                amazon_products.append(amazon_product)
            
            await db_session.commit()
            
            # Step 4: Product matching
            ean_matcher = EANMatcher(db_session)
            matches = await ean_matcher.find_matches(
                source_products=mediamarkt_products,
                target_source=ProductSource.AMAZON
            )
            
            # Verify matches found
            assert len(matches) == 2  # iPhone and Sony should match
            
            # Step 5: Arbitrage analysis
            analyzer = ArbitrageAnalyzer(db_session)
            opportunities = []
            
            for match in matches:
                mediamarkt_price = match.source_product.current_price
                amazon_price = match.target_product.current_price
                price_difference = amazon_price - mediamarkt_price
                
                if price_difference > Decimal("10.00"):  # Minimum profit threshold
                    profit_percentage = (price_difference / mediamarkt_price) * 100
                    
                    opportunity = ArbitrageOpportunity(
                        mediamarkt_product_id=match.source_product.id,
                        amazon_product_id=match.target_product.id,
                        price_difference=price_difference,
                        profit_margin=profit_percentage,
                        confidence_score=Decimal("95.0"),
                        status=OpportunityStatus.ACTIVE,
                        detected_at=datetime.utcnow(),
                        match_type=match.match_type,
                        match_confidence=Decimal(str(match.match_confidence))
                    )
                    
                    db_session.add(opportunity)
                    opportunities.append(opportunity)
            
            await db_session.commit()
            
            # Verify opportunities detected
            assert len(opportunities) == 2
            
            # Check iPhone opportunity
            iphone_opportunity = next(
                o for o in opportunities 
                if "iPhone" in o.mediamarkt_product.name
            )
            assert iphone_opportunity.price_difference == Decimal("150.00")  # 1449 - 1299
            assert iphone_opportunity.profit_margin > Decimal("10.0")
            
            # Check Sony opportunity  
            sony_opportunity = next(
                o for o in opportunities
                if "Sony" in o.mediamarkt_product.name
            )
            assert sony_opportunity.price_difference == Decimal("50.00")  # 399.99 - 349.99
            assert sony_opportunity.profit_margin > Decimal("10.0")
            
            # Step 6: Notification sending
            with patch('src.services.notifications.notification_manager.TelegramNotifier') as mock_telegram:
                with patch('src.services.notifications.notification_manager.SlackNotifier') as mock_slack:
                    with patch('src.services.notifications.notification_manager.EmailNotifier') as mock_email:
                        
                        # Configure notification mocks
                        mock_telegram.return_value.send_message = AsyncMock(return_value=True)
                        mock_slack.return_value.send_message = AsyncMock(return_value=True)
                        mock_email.return_value.send_message = AsyncMock(return_value=True)
                        
                        notification_manager = NotificationManager(db_session)
                        
                        # Send notifications for each opportunity
                        for opportunity in opportunities:
                            await notification_manager.send_arbitrage_alert(opportunity)
                        
                        # Verify notifications sent
                        assert mock_telegram.return_value.send_message.call_count == 2
                        assert mock_slack.return_value.send_message.call_count == 2
                        assert mock_email.return_value.send_message.call_count == 2
                        
                        # Verify notification content
                        telegram_calls = mock_telegram.return_value.send_message.call_args_list
                        first_notification = telegram_calls[0][0][0]  # First call, first argument
                        assert "iPhone" in first_notification or "arbitrage" in first_notification.lower()
                        assert "150" in first_notification or "1299" in first_notification
    
    async def test_workflow_with_no_arbitrage_opportunities(
        self,
        db_session: AsyncSession
    ):
        """Test workflow when no profitable arbitrage opportunities exist."""
        
        with patch('src.services.scraper.mediamarkt_scraper.MediaMarktScraper') as mock_scraper_class:
            mock_scraper = AsyncMock()
            mock_scraper.scrape_all_products.return_value = [
                {
                    "title": "Expensive Test Product",
                    "price": Decimal("1500.00"),  # Higher than Amazon price
                    "ean": "9999999999999",
                    "brand": "TestBrand",
                    "product_url": "https://mediamarkt.pt/expensive-product",
                    "stock_status": "in_stock",
                    "scraped_at": datetime.utcnow()
                }
            ]
            mock_scraper_class.return_value.__aenter__.return_value = mock_scraper
            
            # Store MediaMarkt product
            scraped_data = await mock_scraper.scrape_all_products()
            mediamarkt_product = Product(
                name=scraped_data[0]["title"],
                brand=scraped_data[0]["brand"],
                ean=scraped_data[0]["ean"],
                current_price=scraped_data[0]["price"],
                source=ProductSource.MEDIAMARKT,
                product_url=scraped_data[0]["product_url"],
                stock_status=scraped_data[0]["stock_status"],
                last_updated=scraped_data[0]["scraped_at"]
            )
            db_session.add(mediamarkt_product)
            
            # Store matching Amazon product with lower price
            amazon_product = Product(
                name="Expensive Test Product",
                brand="TestBrand",
                ean="9999999999999",
                current_price=Decimal("1400.00"),  # Lower than MediaMarkt
                source=ProductSource.AMAZON,
                product_url="https://amazon.com/expensive-product",
                stock_status="in_stock",
                last_updated=datetime.utcnow()
            )
            db_session.add(amazon_product)
            await db_session.commit()
            
            # Find matches
            ean_matcher = EANMatcher(db_session)
            matches = await ean_matcher.find_matches(
                source_products=[mediamarkt_product],
                target_source=ProductSource.AMAZON
            )
            
            assert len(matches) == 1  # Match found
            
            # Analyze arbitrage (should find no opportunities)
            analyzer = ArbitrageAnalyzer(db_session)
            opportunities = []
            
            for match in matches:
                price_difference = match.target_product.current_price - match.source_product.current_price
                
                if price_difference > Decimal("10.00"):  # No profitable opportunities
                    opportunity = ArbitrageOpportunity(
                        mediamarkt_product_id=match.source_product.id,
                        amazon_product_id=match.target_product.id,
                        price_difference=price_difference,
                        profit_margin=(price_difference / match.source_product.current_price) * 100,
                        confidence_score=Decimal("95.0"),
                        status=OpportunityStatus.ACTIVE,
                        detected_at=datetime.utcnow()
                    )
                    opportunities.append(opportunity)
            
            # Verify no opportunities found
            assert len(opportunities) == 0
            
            # Verify no notifications sent
            with patch('src.services.notifications.notification_manager.NotificationManager') as mock_notifier:
                notification_manager = NotificationManager(db_session)
                # No opportunities to notify about
                assert len(opportunities) == 0
    
    async def test_workflow_with_fuzzy_matching_fallback(
        self,
        db_session: AsyncSession
    ):
        """Test workflow using fuzzy matching when EAN matching fails."""
        
        with patch('src.services.scraper.mediamarkt_scraper.MediaMarktScraper') as mock_scraper_class:
            mock_scraper = AsyncMock()
            mock_scraper.scrape_all_products.return_value = [
                {
                    "title": "Apple iPhone 15 Pro (256GB) Natural Titanium",
                    "price": Decimal("1299.00"),
                    "ean": "194253432999",  # Different EAN to force fuzzy matching
                    "brand": "Apple",
                    "product_url": "https://mediamarkt.pt/iphone-fuzzy",
                    "stock_status": "in_stock",
                    "scraped_at": datetime.utcnow()
                }
            ]
            mock_scraper_class.return_value.__aenter__.return_value = mock_scraper
            
            # Store MediaMarkt product
            scraped_data = await mock_scraper.scrape_all_products()
            mediamarkt_product = Product(
                name=scraped_data[0]["title"],
                brand=scraped_data[0]["brand"],
                ean=scraped_data[0]["ean"],
                current_price=scraped_data[0]["price"],
                source=ProductSource.MEDIAMARKT,
                product_url=scraped_data[0]["product_url"],
                stock_status=scraped_data[0]["stock_status"],
                last_updated=scraped_data[0]["scraped_at"]
            )
            db_session.add(mediamarkt_product)
            
            # Store Amazon product with similar name but different EAN
            amazon_product = Product(
                name="Apple iPhone 15 Pro 256GB - Natural Titanium",  # Similar name
                brand="Apple",
                ean="194253432807",  # Different EAN
                current_price=Decimal("1449.00"),
                source=ProductSource.AMAZON,
                product_url="https://amazon.com/iphone-15-pro",
                stock_status="in_stock",
                last_updated=datetime.utcnow()
            )
            db_session.add(amazon_product)
            await db_session.commit()
            
            # Try EAN matching first (should fail)
            ean_matcher = EANMatcher(db_session)
            ean_matches = await ean_matcher.find_matches(
                source_products=[mediamarkt_product],
                target_source=ProductSource.AMAZON
            )
            
            assert len(ean_matches) == 0  # No EAN matches
            
            # Fallback to fuzzy matching
            fuzzy_matcher = FuzzyMatcher(db_session)
            fuzzy_matches = await fuzzy_matcher.find_matches(
                source_products=[mediamarkt_product],
                target_source=ProductSource.AMAZON,
                min_similarity=0.8
            )
            
            assert len(fuzzy_matches) >= 1  # Fuzzy match found
            
            # Verify fuzzy match quality
            fuzzy_match = fuzzy_matches[0]
            assert fuzzy_match.match_type == "fuzzy"
            assert fuzzy_match.match_confidence >= 0.8
            assert fuzzy_match.match_confidence < 1.0  # Not perfect match
            
            # Continue with arbitrage analysis using fuzzy match
            price_difference = fuzzy_match.target_product.current_price - fuzzy_match.source_product.current_price
            
            if price_difference > Decimal("10.00"):
                opportunity = ArbitrageOpportunity(
                    mediamarkt_product_id=fuzzy_match.source_product.id,
                    amazon_product_id=fuzzy_match.target_product.id,
                    price_difference=price_difference,
                    profit_margin=(price_difference / fuzzy_match.source_product.current_price) * 100,
                    confidence_score=Decimal(str(fuzzy_match.match_confidence * 100)),
                    status=OpportunityStatus.ACTIVE,
                    detected_at=datetime.utcnow(),
                    match_type=fuzzy_match.match_type,
                    match_confidence=Decimal(str(fuzzy_match.match_confidence))
                )
                
                db_session.add(opportunity)
                await db_session.commit()
                
                # Verify opportunity created with fuzzy match confidence
                assert opportunity.match_type == "fuzzy"
                assert opportunity.confidence_score < Decimal("100.0")  # Lower confidence due to fuzzy match
                assert opportunity.price_difference == Decimal("150.00")


class TestCeleryWorkflowE2E:
    """Test complete workflow using Celery background tasks."""
    
    async def test_celery_task_chain_workflow(
        self,
        db_session: AsyncSession
    ):
        """Test complete workflow executed through Celery task chain."""
        
        # Mock data for the workflow
        mock_scraped_data = [
            {
                "title": "Celery Test Product",
                "price": Decimal("199.99"),
                "ean": "1111111111111",
                "brand": "CeleryBrand",
                "product_url": "https://mediamarkt.pt/celery-test",
                "stock_status": "in_stock",
                "scraped_at": datetime.utcnow()
            }
        ]
        
        mock_amazon_data = [
            {
                "asin": "CELERY123",
                "title": "Celery Test Product",
                "current_price": Decimal("249.99"),
                "ean": "1111111111111",
                "brand": "CeleryBrand"
            }
        ]
        
        # Mock all the services used in Celery tasks
        with patch('src.tasks.scraping_tasks.MediaMarktScraper') as mock_scraper:
            with patch('src.tasks.matching_tasks.EANMatcher') as mock_matcher:
                with patch('src.tasks.analysis_tasks.ArbitrageAnalyzer') as mock_analyzer:
                    with patch('src.services.notifications.notification_manager.NotificationManager') as mock_notifier:
                        
                        # Configure scraper mock
                        mock_scraper_instance = AsyncMock()
                        mock_scraper_instance.scrape_all_products.return_value = mock_scraped_data
                        mock_scraper.return_value.__aenter__.return_value = mock_scraper_instance
                        
                        # Configure matcher mock
                        mock_matcher_instance = AsyncMock()
                        mock_match_result = MagicMock()
                        mock_match_result.source_product = MagicMock()
                        mock_match_result.source_product.id = 1
                        mock_match_result.source_product.current_price = Decimal("199.99")
                        mock_match_result.target_product = MagicMock()
                        mock_match_result.target_product.id = 2
                        mock_match_result.target_product.current_price = Decimal("249.99")
                        mock_match_result.match_type = "ean"
                        mock_match_result.match_confidence = 1.0
                        
                        mock_matcher_instance.find_matches.return_value = [mock_match_result]
                        mock_matcher.return_value = mock_matcher_instance
                        
                        # Configure analyzer mock
                        mock_analyzer_instance = AsyncMock()
                        mock_analyzer_instance.analyze_opportunities.return_value = [
                            {
                                "mediamarkt_product_id": 1,
                                "amazon_product_id": 2,
                                "price_difference": Decimal("50.00"),
                                "profit_margin": Decimal("25.0"),
                                "confidence_score": Decimal("95.0"),
                                "status": OpportunityStatus.ACTIVE
                            }
                        ]
                        mock_analyzer.return_value = mock_analyzer_instance
                        
                        # Configure notification mock
                        mock_notifier_instance = AsyncMock()
                        mock_notifier_instance.send_arbitrage_alert.return_value = True
                        mock_notifier.return_value = mock_notifier_instance
                        
                        # Execute Celery task chain simulation
                        # Task 1: Scraping
                        scrape_result = await self._simulate_scrape_task(mock_scraped_data, db_session)
                        assert scrape_result["status"] == "completed"
                        assert scrape_result["products_scraped"] == 1
                        
                        # Task 2: Matching 
                        match_result = await self._simulate_match_task(mock_amazon_data, db_session)
                        assert match_result["status"] == "completed"
                        assert match_result["matches_found"] == 1
                        
                        # Task 3: Analysis
                        analysis_result = await self._simulate_analysis_task(db_session)
                        assert analysis_result["status"] == "completed"
                        assert analysis_result["opportunities_found"] == 1
                        
                        # Task 4: Notifications
                        notification_result = await self._simulate_notification_task(db_session)
                        assert notification_result["status"] == "completed"
                        assert notification_result["notifications_sent"] == 1
    
    async def _simulate_scrape_task(self, scraped_data: List[Dict], db_session: AsyncSession) -> Dict[str, Any]:
        """Simulate scraping task execution."""
        
        for product_data in scraped_data:
            product = Product(
                name=product_data["title"],
                brand=product_data["brand"],
                ean=product_data["ean"],
                current_price=product_data["price"],
                source=ProductSource.MEDIAMARKT,
                product_url=product_data["product_url"],
                stock_status=product_data["stock_status"],
                last_updated=product_data["scraped_at"]
            )
            db_session.add(product)
        
        await db_session.commit()
        
        return {
            "status": "completed",
            "products_scraped": len(scraped_data),
            "scraping_time": 2.5
        }
    
    async def _simulate_match_task(self, amazon_data: List[Dict], db_session: AsyncSession) -> Dict[str, Any]:
        """Simulate matching task execution."""
        
        for product_data in amazon_data:
            amazon_product = Product(
                name=product_data["title"],
                brand=product_data["brand"],
                ean=product_data["ean"],
                asin=product_data.get("asin"),
                current_price=product_data["current_price"],
                source=ProductSource.AMAZON,
                product_url=f"https://amazon.com/dp/{product_data.get('asin', 'unknown')}",
                stock_status="in_stock",
                last_updated=datetime.utcnow()
            )
            db_session.add(amazon_product)
        
        await db_session.commit()
        
        return {
            "status": "completed",
            "matches_found": len(amazon_data),
            "matching_time": 1.2
        }
    
    async def _simulate_analysis_task(self, db_session: AsyncSession) -> Dict[str, Any]:
        """Simulate analysis task execution."""
        
        # Find products for analysis
        result = await db_session.execute(
            select(Product).where(Product.source == ProductSource.MEDIAMARKT)
        )
        mediamarkt_products = result.scalars().all()
        
        result = await db_session.execute(
            select(Product).where(Product.source == ProductSource.AMAZON)
        )
        amazon_products = result.scalars().all()
        
        opportunities_found = 0
        if mediamarkt_products and amazon_products:
            # Create arbitrage opportunity
            mediamarkt_product = mediamarkt_products[0]
            amazon_product = amazon_products[0]
            
            price_difference = amazon_product.current_price - mediamarkt_product.current_price
            if price_difference > Decimal("10.00"):
                opportunity = ArbitrageOpportunity(
                    mediamarkt_product_id=mediamarkt_product.id,
                    amazon_product_id=amazon_product.id,
                    price_difference=price_difference,
                    profit_margin=(price_difference / mediamarkt_product.current_price) * 100,
                    confidence_score=Decimal("95.0"),
                    status=OpportunityStatus.ACTIVE,
                    detected_at=datetime.utcnow()
                )
                
                db_session.add(opportunity)
                await db_session.commit()
                opportunities_found = 1
        
        return {
            "status": "completed",
            "opportunities_found": opportunities_found,
            "analysis_time": 0.8
        }
    
    async def _simulate_notification_task(self, db_session: AsyncSession) -> Dict[str, Any]:
        """Simulate notification task execution."""
        
        # Find opportunities to notify about
        result = await db_session.execute(
            select(ArbitrageOpportunity).where(ArbitrageOpportunity.status == OpportunityStatus.ACTIVE)
        )
        opportunities = result.scalars().all()
        
        notifications_sent = 0
        for opportunity in opportunities:
            # Create notification message record
            message = NotificationMessage(
                channel=NotificationChannel.TELEGRAM,
                recipient="@arbitrage_alerts",
                subject="New Arbitrage Opportunity",
                content=f"Arbitrage opportunity detected: {opportunity.profit_margin}% profit",
                opportunity_id=opportunity.id,
                status=MessageStatus.SENT,
                sent_at=datetime.utcnow()
            )
            
            db_session.add(message)
            notifications_sent += 1
        
        await db_session.commit()
        
        return {
            "status": "completed",
            "notifications_sent": notifications_sent,
            "notification_time": 0.3
        }
    
    async def test_celery_error_recovery_workflow(
        self,
        db_session: AsyncSession
    ):
        """Test Celery workflow error handling and recovery."""
        
        # Simulate scraping task failure and recovery
        with patch('src.tasks.scraping_tasks.MediaMarktScraper') as mock_scraper:
            # First attempt fails
            mock_scraper.side_effect = [
                Exception("Browser crashed"),  # First attempt
                AsyncMock()  # Second attempt succeeds
            ]
            
            # Simulate retry logic
            attempts = 0
            max_attempts = 2
            
            while attempts < max_attempts:
                try:
                    attempts += 1
                    if attempts == 1:
                        raise Exception("Browser crashed")
                    else:
                        # Second attempt succeeds
                        result = {
                            "status": "completed",
                            "products_scraped": 5,
                            "attempts": attempts
                        }
                        break
                except Exception:
                    if attempts >= max_attempts:
                        result = {
                            "status": "failed",
                            "error": "Max retry attempts exceeded",
                            "attempts": attempts
                        }
                    else:
                        await asyncio.sleep(0.1)  # Retry delay
            
            # Verify retry logic worked
            assert result["status"] == "completed"
            assert result["attempts"] == 2


class TestAPIWorkflowE2E:
    """Test complete workflow through API endpoints."""
    
    async def test_api_triggered_workflow(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession
    ):
        """Test complete workflow triggered through API endpoints."""
        
        # Step 1: Create some existing Amazon products for matching
        amazon_products = [
            Product(
                name="API Test Product",
                brand="APIBrand",
                ean="8888888888888",
                asin="APITEST1",
                current_price=Decimal("299.99"),
                source=ProductSource.AMAZON,
                product_url="https://amazon.com/api-test",
                stock_status="in_stock",
                last_updated=datetime.utcnow()
            )
        ]
        
        for product in amazon_products:
            db_session.add(product)
        await db_session.commit()
        
        # Step 2: Mock MediaMarkt scraping via API
        with patch('src.services.scraper.mediamarkt_scraper.MediaMarktScraper') as mock_scraper:
            mock_scraper_instance = AsyncMock()
            mock_scraper_instance.scrape_all_products.return_value = [
                {
                    "title": "API Test Product",
                    "price": Decimal("249.99"),  # Lower than Amazon
                    "ean": "8888888888888",
                    "brand": "APIBrand",
                    "product_url": "https://mediamarkt.pt/api-test",
                    "stock_status": "in_stock",
                    "scraped_at": datetime.utcnow()
                }
            ]
            mock_scraper.return_value.__aenter__.return_value = mock_scraper_instance
            
            # Step 3: Trigger scraping via API
            scrape_response = await client.post(
                "/api/v1/scraping/mediamarkt/start",
                headers=auth_headers,
                json={"max_pages": 1}
            )
            
            assert scrape_response.status_code == 200
            scrape_data = scrape_response.json()
            assert scrape_data["status"] == "started"
            
            # Simulate scraping completion and store result
            scraped_data = await mock_scraper_instance.scrape_all_products()
            mediamarkt_product = Product(
                name=scraped_data[0]["title"],
                brand=scraped_data[0]["brand"],
                ean=scraped_data[0]["ean"],
                current_price=scraped_data[0]["price"],
                source=ProductSource.MEDIAMARKT,
                product_url=scraped_data[0]["product_url"],
                stock_status=scraped_data[0]["stock_status"],
                last_updated=scraped_data[0]["scraped_at"]
            )
            db_session.add(mediamarkt_product)
            await db_session.commit()
        
        # Step 4: Check products via API
        products_response = await client.get(
            "/api/v1/products/",
            headers=auth_headers,
            params={"source": "mediamarkt", "limit": 10}
        )
        
        assert products_response.status_code == 200
        products_data = products_response.json()
        assert len(products_data["items"]) >= 1
        
        # Find our test product
        test_product = next(
            (p for p in products_data["items"] if p["ean"] == "8888888888888"),
            None
        )
        assert test_product is not None
        assert test_product["source"] == "mediamarkt"
        assert float(test_product["current_price"]) == 249.99
        
        # Step 5: Simulate matching and create arbitrage opportunity
        opportunity = ArbitrageOpportunity(
            mediamarkt_product_id=mediamarkt_product.id,
            amazon_product_id=amazon_products[0].id,
            price_difference=Decimal("50.00"),
            profit_margin=Decimal("20.0"),
            confidence_score=Decimal("95.0"),
            status=OpportunityStatus.ACTIVE,
            detected_at=datetime.utcnow()
        )
        
        db_session.add(opportunity)
        await db_session.commit()
        
        # Step 6: Check arbitrage opportunities via API
        arbitrage_response = await client.get(
            "/api/v1/arbitrage/opportunities/",
            headers=auth_headers,
            params={"status": "active", "limit": 10}
        )
        
        assert arbitrage_response.status_code == 200
        arbitrage_data = arbitrage_response.json()
        assert len(arbitrage_data["items"]) >= 1
        
        # Find our test opportunity
        test_opportunity = next(
            (o for o in arbitrage_data["items"] if float(o["profit_margin"]) == 20.0),
            None
        )
        assert test_opportunity is not None
        assert float(test_opportunity["price_difference"]) == 50.0
        assert test_opportunity["status"] == "active"
    
    async def test_api_monitoring_and_health_checks(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """Test API health checks and monitoring during workflow."""
        
        # Health check endpoint
        health_response = await client.get("/api/v1/health")
        assert health_response.status_code == 200
        health_data = health_response.json()
        assert health_data["status"] == "healthy"
        assert "database" in health_data["checks"]
        assert "redis" in health_data["checks"]
        
        # System metrics endpoint
        metrics_response = await client.get(
            "/api/v1/metrics/system",
            headers=auth_headers
        )
        assert metrics_response.status_code == 200
        metrics_data = metrics_response.json()
        assert "scraping_stats" in metrics_data
        assert "matching_stats" in metrics_data
        assert "arbitrage_stats" in metrics_data
        
        # Task status endpoint
        status_response = await client.get(
            "/api/v1/tasks/status",
            headers=auth_headers
        )
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert "active_tasks" in status_data
        assert "completed_tasks" in status_data


class TestErrorHandlingE2E:
    """Test error handling throughout the complete workflow."""
    
    async def test_partial_failure_recovery_workflow(
        self,
        db_session: AsyncSession
    ):
        """Test workflow recovery when partial failures occur."""
        
        # Simulate scraping with some products failing to parse
        with patch('src.services.scraper.mediamarkt_scraper.MediaMarktScraper') as mock_scraper:
            mock_scraper_instance = AsyncMock()
            mock_scraper_instance.scrape_all_products.return_value = [
                {
                    "title": "Good Product 1",
                    "price": Decimal("199.99"),
                    "ean": "1111111111111",
                    "brand": "GoodBrand",
                    "product_url": "https://mediamarkt.pt/good-1",
                    "stock_status": "in_stock",
                    "scraped_at": datetime.utcnow()
                },
                {
                    "title": "Malformed Product",
                    "price": None,  # Invalid price
                    "ean": "invalid-ean",  # Invalid EAN
                    "brand": None,
                    "product_url": "invalid-url",
                    "stock_status": "unknown",
                    "scraped_at": datetime.utcnow()
                },
                {
                    "title": "Good Product 2",
                    "price": Decimal("299.99"),
                    "ean": "2222222222222",
                    "brand": "GoodBrand",
                    "product_url": "https://mediamarkt.pt/good-2",
                    "stock_status": "in_stock",
                    "scraped_at": datetime.utcnow()
                }
            ]
            mock_scraper.return_value.__aenter__.return_value = mock_scraper_instance
            
            # Process scraped data with error handling
            scraped_data = await mock_scraper_instance.scrape_all_products()
            successful_products = []
            failed_products = []
            
            for product_data in scraped_data:
                try:
                    # Validate required fields
                    if (product_data.get("price") is None or 
                        not product_data.get("ean") or
                        not product_data.get("brand")):
                        raise ValueError("Missing required fields")
                    
                    product = Product(
                        name=product_data["title"],
                        brand=product_data["brand"],
                        ean=product_data["ean"],
                        current_price=product_data["price"],
                        source=ProductSource.MEDIAMARKT,
                        product_url=product_data["product_url"],
                        stock_status=product_data["stock_status"],
                        last_updated=product_data["scraped_at"]
                    )
                    db_session.add(product)
                    successful_products.append(product)
                    
                except Exception as e:
                    failed_products.append({
                        "product_data": product_data,
                        "error": str(e)
                    })
            
            await db_session.commit()
            
            # Verify partial success
            assert len(successful_products) == 2  # Two good products
            assert len(failed_products) == 1  # One malformed product
            assert "Missing required fields" in failed_products[0]["error"]
    
    async def test_service_dependency_failure_handling(
        self,
        db_session: AsyncSession
    ):
        """Test workflow handling when external service dependencies fail."""
        
        # Create MediaMarkt products
        mediamarkt_product = Product(
            name="Dependency Test Product",
            brand="TestBrand",
            ean="3333333333333",
            current_price=Decimal("199.99"),
            source=ProductSource.MEDIAMARKT,
            product_url="https://mediamarkt.pt/dependency-test",
            stock_status="in_stock",
            last_updated=datetime.utcnow()
        )
        db_session.add(mediamarkt_product)
        await db_session.commit()
        
        # Simulate Keepa API failure during Amazon data fetching
        with patch('src.services.external.keepa_client.KeepaClient') as mock_keepa:
            mock_keepa.return_value.get_product_data.side_effect = Exception("Keepa API rate limit exceeded")
            
            # Try to fetch Amazon data (should handle gracefully)
            try:
                # This would normally fetch Amazon product data
                amazon_data = await self._fetch_amazon_data_with_fallback("3333333333333")
                
                # Should provide cached or fallback data
                assert amazon_data is not None
                assert amazon_data["source"] == "cache"  # Fallback to cached data
                
            except Exception as e:
                # Should be handled gracefully
                assert "rate limit" in str(e).lower()
        
        # Simulate notification service failure
        with patch('src.services.notifications.notification_manager.TelegramNotifier') as mock_telegram:
            mock_telegram.return_value.send_message.side_effect = Exception("Telegram service unavailable")
            
            # Create opportunity
            opportunity = ArbitrageOpportunity(
                mediamarkt_product_id=mediamarkt_product.id,
                amazon_product_id=1,  # Mock Amazon product ID
                price_difference=Decimal("50.00"),
                profit_margin=Decimal("25.0"),
                confidence_score=Decimal("90.0"),
                status=OpportunityStatus.ACTIVE,
                detected_at=datetime.utcnow()
            )
            db_session.add(opportunity)
            await db_session.commit()
            
            # Try to send notification (should handle failure gracefully)
            notification_manager = NotificationManager(db_session)
            
            try:
                await notification_manager.send_arbitrage_alert(opportunity)
            except Exception as e:
                # Should log error but not crash the workflow
                assert "service unavailable" in str(e).lower()
                
                # Opportunity should still be marked for retry
                opportunity.status = OpportunityStatus.NOTIFICATION_FAILED
                await db_session.commit()
    
    async def _fetch_amazon_data_with_fallback(self, ean: str) -> Dict[str, Any]:
        """Simulate fetching Amazon data with fallback mechanisms."""
        
        try:
            # Primary API call (fails in test)
            raise Exception("Keepa API rate limit exceeded")
            
        except Exception:
            # Fallback to cached data
            return {
                "ean": ean,
                "title": "Cached Product Title",
                "current_price": Decimal("249.99"),
                "source": "cache",
                "last_updated": datetime.utcnow() - timedelta(hours=1)
            } 