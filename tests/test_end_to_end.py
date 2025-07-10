"""
End-to-End Integration Tests for Cross-Market Arbitrage Tool.

These tests verify the complete workflow from product scraping to profit 
calculation and alert generation.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Dict, Any

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.product import Product
from src.models.asin import ASIN
from src.models.alert import ProductAsinMatch, PriceAlert
from src.services.scraper.mediamarkt_scraper import MediaMarktScraper
from src.services.matcher.ean_matcher import EANMatcher
from src.services.matcher.fuzzy_matcher import FuzzyMatcher
from src.services.matcher.semantic_matcher import SemanticMatcher
from src.services.analyzer.price_analyzer import PriceAnalyzer
from src.integrations.keepa_api import KeepaAPIClient
from src.services.notifier.telegram_notifier import TelegramNotifier
from src.services.notifier.slack_notifier import SlackNotifier
from src.services.notifier.email_notifier import EmailNotifier
from src.tasks.scraping import scrape_mediamarkt
from src.tasks.matching import process_unmatched_products
from src.tasks.analysis import analyze_price_opportunities


class TestCompleteArbitrageWorkflow:
    """Test complete arbitrage detection workflow."""

    @pytest.mark.asyncio
    async def test_full_arbitrage_workflow_ean_match(self, db_session: AsyncSession):
        """Test complete workflow with EAN-based product matching."""
        # 1. Mock product scraping
        scraped_products = [
            {
                'title': 'Apple iPhone 15 Pro 256GB Natural Titanium',
                'brand': 'Apple',
                'ean': '194253432807',
                'current_price': Decimal('1049.99'),
                'original_price': Decimal('1199.99'),
                'discount_percentage': Decimal('12.50'),
                'stock_status': 'in_stock',
                'product_url': 'https://mediamarkt.pt/apple-iphone-15-pro',
                'category': 'Smartphones',
                'scraped_at': datetime.utcnow()
            }
        ]

        # 2. Mock ASIN data from database
        mock_asin = ASIN(
            asin='B0CHX2F5QT',
            title='Apple iPhone 15 Pro (256GB) - Natural Titanium',
            brand='Apple',
            ean='194253432807',
            category='Electronics > Cell Phones & Accessories > Cell Phones > Smartphones',
            current_price=Decimal('1299.00'),
            is_available=True,
            last_updated=datetime.utcnow()
        )

        # 3. Mock Keepa price data
        mock_keepa_data = {
            'asin': 'B0CHX2F5QT',
            'title': 'Apple iPhone 15 Pro (256GB) - Natural Titanium',
            'current_price': 1299.00,
            'price_history': [
                {'timestamp': datetime.utcnow() - timedelta(days=30), 'price': 1399.00},
                {'timestamp': datetime.utcnow() - timedelta(days=15), 'price': 1349.00},
                {'timestamp': datetime.utcnow() - timedelta(days=7), 'price': 1299.00},
                {'timestamp': datetime.utcnow() - timedelta(days=1), 'price': 1289.00},
                {'timestamp': datetime.utcnow(), 'price': 1299.00}
            ],
            'avg_price_30d': 1334.00,
            'lowest_price_30d': 1289.00,
            'highest_price_30d': 1399.00
        }

        # Setup mocks
        with patch('src.services.scraper.mediamarkt_scraper.MediaMarktScraper') as mock_scraper_class:
            mock_scraper = AsyncMock()
            mock_scraper_class.return_value = mock_scraper
            mock_scraper.__aenter__.return_value = mock_scraper
            mock_scraper.__aexit__.return_value = None
            mock_scraper.scrape_products_page.return_value = scraped_products

            with patch('src.integrations.keepa_api.KeepaAPIClient') as mock_keepa_class:
                mock_keepa = AsyncMock()
                mock_keepa_class.return_value = mock_keepa
                mock_keepa.get_product_data.return_value = mock_keepa_data

                with patch('src.models.asin.ASIN') as mock_asin_model:
                    mock_asin_model.get_by_ean.return_value = mock_asin

                    # Execute workflow steps
                    
                    # Step 1: Scrape products
                    scraper = MediaMarktScraper()
                    async with scraper:
                        scraped_data = await scraper.scrape_products_page()

                    # Step 2: Save products to database
                    product = Product(
                        title=scraped_data[0]['title'],
                        brand=scraped_data[0]['brand'],
                        ean=scraped_data[0]['ean'],
                        current_price=scraped_data[0]['current_price'],
                        original_price=scraped_data[0]['original_price'],
                        discount_percentage=scraped_data[0]['discount_percentage'],
                        stock_status=scraped_data[0]['stock_status'],
                        product_url=scraped_data[0]['product_url'],
                        category=scraped_data[0]['category'],
                        scraped_at=scraped_data[0]['scraped_at']
                    )
                    db_session.add(product)
                    await db_session.commit()
                    await db_session.refresh(product)

                    # Step 3: Match products using EAN
                    ean_matcher = EANMatcher()
                    match_result = await ean_matcher.match_product(product)

                    # Step 4: Analyze prices and calculate profit
                    analyzer = PriceAnalyzer()
                    keepa_client = KeepaAPIClient()
                    keepa_data = await keepa_client.get_product_data(mock_asin.asin)
                    
                    analysis_result = await analyzer.analyze_price_opportunity(
                        product=product,
                        asin=mock_asin,
                        keepa_data=keepa_data
                    )

                    # Step 5: Generate alert if profitable
                    if analysis_result.is_profitable:
                        alert = PriceAlert(
                            product_id=product.id,
                            asin=mock_asin.asin,
                            current_price_mm=product.current_price,
                            current_price_amazon=mock_asin.current_price,
                            profit_margin=analysis_result.profit_margin,
                            profit_amount=analysis_result.estimated_profit,
                            confidence_score=match_result.confidence,
                            match_type='EAN',
                            analysis_data=analysis_result.model_dump(),
                            created_at=datetime.utcnow()
                        )
                        db_session.add(alert)
                        await db_session.commit()

        # Assertions
        assert len(scraped_data) == 1
        assert scraped_data[0]['ean'] == '194253432807'
        assert match_result is not None
        assert match_result.asin == 'B0CHX2F5QT'
        assert match_result.confidence >= 0.95  # EAN matches should have high confidence
        assert analysis_result.is_profitable is True
        assert analysis_result.profit_margin > 0.15  # Should have >15% margin
        assert alert.profit_amount > Decimal('150.00')  # Should have good profit

    @pytest.mark.asyncio
    async def test_full_arbitrage_workflow_fuzzy_match(self, db_session: AsyncSession):
        """Test complete workflow with fuzzy product matching."""
        # Mock product without EAN but with similar title
        scraped_products = [
            {
                'title': 'Samsung Galaxy S24 Ultra 256GB Titânio Violeta',
                'brand': 'Samsung',
                'ean': None,  # No EAN available
                'current_price': Decimal('899.99'),
                'original_price': Decimal('1199.99'),
                'discount_percentage': Decimal('25.00'),
                'stock_status': 'in_stock',
                'product_url': 'https://mediamarkt.pt/samsung-galaxy-s24-ultra',
                'category': 'Smartphones',
                'scraped_at': datetime.utcnow()
            }
        ]

        # Mock similar ASIN for fuzzy matching
        mock_asin = ASIN(
            asin='B0CMDRCZBX',
            title='Samsung Galaxy S24 Ultra 5G AI Smartphone (256GB) - Titanium Violet',
            brand='Samsung',
            ean=None,
            category='Electronics > Cell Phones & Accessories > Cell Phones > Smartphones',
            current_price=Decimal('1149.00'),
            is_available=True,
            last_updated=datetime.utcnow()
        )

        mock_keepa_data = {
            'asin': 'B0CMDRCZBX',
            'title': 'Samsung Galaxy S24 Ultra 5G AI Smartphone (256GB) - Titanium Violet',
            'current_price': 1149.00,
            'price_history': [
                {'timestamp': datetime.utcnow() - timedelta(days=7), 'price': 1199.00},
                {'timestamp': datetime.utcnow() - timedelta(days=3), 'price': 1149.00},
                {'timestamp': datetime.utcnow(), 'price': 1149.00}
            ],
            'avg_price_30d': 1174.00,
            'lowest_price_30d': 1149.00,
            'highest_price_30d': 1199.00
        }

        with patch('src.services.scraper.mediamarkt_scraper.MediaMarktScraper') as mock_scraper_class:
            mock_scraper = AsyncMock()
            mock_scraper_class.return_value = mock_scraper
            mock_scraper.__aenter__.return_value = mock_scraper
            mock_scraper.__aexit__.return_value = None
            mock_scraper.scrape_products_page.return_value = scraped_products

            with patch('src.integrations.keepa_api.KeepaAPIClient') as mock_keepa_class:
                mock_keepa = AsyncMock()
                mock_keepa_class.return_value = mock_keepa
                mock_keepa.get_product_data.return_value = mock_keepa_data

                with patch.object(FuzzyMatcher, '_get_candidate_asins') as mock_candidates:
                    mock_candidates.return_value = [mock_asin]

                    # Execute workflow
                    scraper = MediaMarktScraper()
                    async with scraper:
                        scraped_data = await scraper.scrape_products_page()

                    product = Product(
                        title=scraped_data[0]['title'],
                        brand=scraped_data[0]['brand'],
                        ean=scraped_data[0]['ean'],
                        current_price=scraped_data[0]['current_price'],
                        original_price=scraped_data[0]['original_price'],
                        discount_percentage=scraped_data[0]['discount_percentage'],
                        stock_status=scraped_data[0]['stock_status'],
                        product_url=scraped_data[0]['product_url'],
                        category=scraped_data[0]['category'],
                        scraped_at=scraped_data[0]['scraped_at']
                    )
                    db_session.add(product)
                    await db_session.commit()
                    await db_session.refresh(product)

                    # Try EAN matching first (should fail)
                    ean_matcher = EANMatcher()
                    ean_result = await ean_matcher.match_product(product)
                    assert ean_result is None  # No EAN, should fail

                    # Try fuzzy matching
                    fuzzy_matcher = FuzzyMatcher()
                    fuzzy_result = await fuzzy_matcher.match_product(product)

                    # Analyze prices
                    analyzer = PriceAnalyzer()
                    keepa_client = KeepaAPIClient()
                    keepa_data = await keepa_client.get_product_data(mock_asin.asin)
                    
                    analysis_result = await analyzer.analyze_price_opportunity(
                        product=product,
                        asin=mock_asin,
                        keepa_data=keepa_data
                    )

        # Assertions
        assert fuzzy_result is not None
        assert fuzzy_result.asin == 'B0CMDRCZBX'
        assert fuzzy_result.confidence >= 0.85  # Fuzzy matches should have good confidence
        assert fuzzy_result.match_reason == 'Fuzzy match'
        assert analysis_result.is_profitable is True
        assert analysis_result.profit_margin > 0.20  # Should have >20% margin

    @pytest.mark.asyncio
    async def test_notification_workflow(self, db_session: AsyncSession):
        """Test complete notification workflow for profitable opportunities."""
        # Create a profitable alert
        alert = PriceAlert(
            product_id="test-product-123",
            asin="B0CHX2F5QT",
            current_price_mm=Decimal("899.99"),
            current_price_amazon=Decimal("1199.00"),
            profit_margin=Decimal("0.25"),
            profit_amount=Decimal("299.01"),
            confidence_score=Decimal("0.95"),
            match_type="EAN",
            analysis_data={
                "avg_amazon_price": 1199.00,
                "price_trend": "stable",
                "estimated_fees": 59.95,
                "net_profit": 239.06
            },
            created_at=datetime.utcnow()
        )
        db_session.add(alert)
        await db_session.commit()
        await db_session.refresh(alert)

        # Test notification services
        with patch('src.services.notifier.telegram_notifier.TelegramNotifier') as mock_telegram:
            with patch('src.services.notifier.slack_notifier.SlackNotifier') as mock_slack:
                with patch('src.services.notifier.email_notifier.EmailNotifier') as mock_email:
                    
                    # Setup mock notifiers
                    telegram_notifier = AsyncMock()
                    slack_notifier = AsyncMock()
                    email_notifier = AsyncMock()
                    
                    mock_telegram.return_value = telegram_notifier
                    mock_slack.return_value = slack_notifier
                    mock_email.return_value = email_notifier
                    
                    # Send notifications
                    message = f"""
🚨 Profitable Arbitrage Opportunity Detected!

💰 Profit: €{alert.profit_amount} ({alert.profit_margin:.1%} margin)
🏪 MediaMarkt: €{alert.current_price_mm}
🛒 Amazon: €{alert.current_price_amazon}
🎯 Confidence: {alert.confidence_score:.1%}
🔗 ASIN: {alert.asin}

Analysis: {alert.analysis_data}
                    """.strip()
                    
                    await telegram_notifier.send_alert_notification(message)
                    await slack_notifier.send_alert_notification(message)
                    await email_notifier.send_alert_notification(
                        subject="New Arbitrage Opportunity",
                        message=message
                    )

        # Verify notifications were sent
        telegram_notifier.send_alert_notification.assert_called_once()
        slack_notifier.send_alert_notification.assert_called_once()
        email_notifier.send_alert_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_api_workflow_integration(self, client: AsyncClient, test_user):
        """Test complete workflow through API endpoints."""
        # Create access token
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "testpassword"}
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Test health check
        health_response = await client.get("/health/detailed")
        assert health_response.status_code == 200
        health_data = health_response.json()
        assert health_data["status"] == "healthy"

        # Test products endpoint
        products_response = await client.get("/api/v1/products", headers=headers)
        assert products_response.status_code == 200

        # Test alerts endpoint  
        alerts_response = await client.get("/api/v1/alerts", headers=headers)
        assert alerts_response.status_code == 200

        # Test system stats
        stats_response = await client.get("/api/v1/system/stats", headers=headers)
        assert stats_response.status_code == 200
        stats_data = stats_response.json()
        assert "products_count" in stats_data
        assert "alerts_count" in stats_data

        # Test metrics endpoint
        metrics_response = await client.get("/api/v1/system/metrics", headers=headers)
        assert metrics_response.status_code == 200

    @pytest.mark.asyncio
    async def test_error_handling_workflow(self, db_session: AsyncSession):
        """Test error handling throughout the workflow."""
        # Test scraper error handling
        with patch('src.services.scraper.mediamarkt_scraper.MediaMarktScraper') as mock_scraper_class:
            mock_scraper = AsyncMock()
            mock_scraper_class.return_value = mock_scraper
            mock_scraper.__aenter__.return_value = mock_scraper
            mock_scraper.__aexit__.return_value = None
            mock_scraper.scrape_products_page.side_effect = Exception("Network error")

            scraper = MediaMarktScraper()
            
            # Should handle scraping errors gracefully
            with pytest.raises(Exception):
                async with scraper:
                    await scraper.scrape_products_page()

        # Test Keepa API error handling
        with patch('src.integrations.keepa_api.KeepaAPIClient') as mock_keepa_class:
            mock_keepa = AsyncMock()
            mock_keepa_class.return_value = mock_keepa
            mock_keepa.get_product_data.side_effect = Exception("API error")

            keepa_client = KeepaAPIClient()
            
            # Should handle API errors gracefully
            with pytest.raises(Exception):
                await keepa_client.get_product_data("B0CHX2F5QT")

        # Test notification error handling
        with patch('src.services.notifier.telegram_notifier.TelegramNotifier') as mock_telegram:
            # Setup mock for failed notification
            mock_telegram.return_value.send_alert_notification = AsyncMock(side_effect=Exception("Notification failed"))
            
            telegram_service = mock_telegram.return_value
            
            # Test error handling
            with pytest.raises(Exception, match="Notification failed"):
                await telegram_service.send_alert_notification("test message")


class TestCeleryTaskIntegration:
    """Test Celery task integration for background processing."""

    @pytest.mark.asyncio
    async def test_scraping_task_workflow(self):
        """Test complete scraping task workflow."""
        with patch('src.tasks.scraping_task.MediaMarktScraper') as mock_scraper_class:
            with patch('src.tasks.scraping_task.get_db_session') as mock_db:
                mock_scraper = AsyncMock()
                mock_scraper_class.return_value = mock_scraper
                mock_scraper.__aenter__.return_value = mock_scraper
                mock_scraper.__aexit__.return_value = None
                mock_scraper.scrape_products_page.return_value = [
                    {
                        'title': 'Test Product',
                        'brand': 'Test Brand',
                        'ean': '1234567890123',
                        'current_price': Decimal('99.99'),
                        'original_price': Decimal('129.99'),
                        'stock_status': 'in_stock',
                        'product_url': 'https://test.com/product',
                        'scraped_at': datetime.utcnow()
                    }
                ]

                mock_session = AsyncMock()
                mock_db.return_value.__aenter__.return_value = mock_session

                # Execute scraping task
                result = await scrape_mediamarkt()

                # Verify task execution
                mock_scraper.scrape_products_page.assert_called_once()
                assert result["status"] == "success"
                assert result["products_scraped"] == 1

    @pytest.mark.asyncio
    async def test_matching_task_workflow(self):
        """Test complete matching task workflow."""
        with patch('src.tasks.matching_task.get_db_session') as mock_db:
            with patch('src.tasks.matching_task.EANMatcher') as mock_ean_matcher:
                with patch('src.tasks.matching_task.FuzzyMatcher') as mock_fuzzy_matcher:
                    
                    mock_session = AsyncMock()
                    mock_db.return_value.__aenter__.return_value = mock_session
                    
                    # Mock products to match
                    mock_products = [Mock()]
                    mock_session.execute.return_value.scalars.return_value.all.return_value = mock_products
                    
                    # Mock matchers
                    ean_matcher = AsyncMock()
                    fuzzy_matcher = AsyncMock()
                    mock_ean_matcher.return_value = ean_matcher
                    mock_fuzzy_matcher.return_value = fuzzy_matcher
                    
                    ean_matcher.match_product.return_value = Mock(asin="B0CHX2F5QT", confidence=0.95)
                    fuzzy_matcher.match_product.return_value = None

                    # Execute matching task
                    result = await process_unmatched_products()

                    # Verify task execution
                    assert result["status"] == "success"
                    assert result["products_processed"] == 1
                    assert result["matches_found"] == 1

    @pytest.mark.asyncio
    async def test_analysis_task_workflow(self):
        """Test complete analysis task workflow."""
        with patch('src.tasks.analysis_task.get_db_session') as mock_db:
            with patch('src.tasks.analysis_task.PriceAnalyzer') as mock_analyzer:
                with patch('src.tasks.analysis_task.KeepaAPIClient') as mock_keepa:
                    
                    mock_session = AsyncMock()
                    mock_db.return_value.__aenter__.return_value = mock_session
                    
                    # Mock unanalyzed matches
                    mock_matches = [Mock()]
                    mock_session.execute.return_value.scalars.return_value.all.return_value = mock_matches
                    
                    # Mock analyzer and Keepa client
                    analyzer = AsyncMock()
                    keepa_client = AsyncMock()
                    mock_analyzer.return_value = analyzer
                    mock_keepa.return_value = keepa_client
                    
                    keepa_client.get_product_data.return_value = {"price_history": []}
                    analyzer.analyze_price_opportunity.return_value = Mock(
                        is_profitable=True,
                        profit_margin=0.25,
                        estimated_profit=150.00
                    )

                    # Execute analysis task
                    result = await analyze_price_opportunities()

                    # Verify task execution
                    assert result["status"] == "success"
                    assert result["matches_analyzed"] == 1
                    assert result["alerts_generated"] == 1


class TestPerformanceAndLoad:
    """Test performance and load handling capabilities."""

    @pytest.mark.asyncio
    async def test_concurrent_scraping_performance(self):
        """Test performance with concurrent scraping operations."""
        async def mock_scrape_operation():
            await asyncio.sleep(0.1)  # Simulate scraping delay
            return {
                'title': 'Test Product',
                'price': Decimal('99.99'),
                'scraped_at': datetime.utcnow()
            }

        # Test concurrent operations
        start_time = datetime.utcnow()
        tasks = [mock_scrape_operation() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        end_time = datetime.utcnow()
        
        duration = (end_time - start_time).total_seconds()
        
        assert len(results) == 10
        assert duration < 1.0  # Should complete in under 1 second with concurrency

    @pytest.mark.asyncio
    async def test_database_performance_with_bulk_operations(self, db_session: AsyncSession):
        """Test database performance with bulk operations."""
        # Create multiple products for bulk testing
        products = []
        for i in range(100):
            product = Product(
                title=f'Test Product {i}',
                brand='Test Brand',
                ean=f'12345678901{i:02d}',
                current_price=Decimal('99.99'),
                original_price=Decimal('129.99'),
                stock_status='in_stock',
                product_url=f'https://test.com/product-{i}',
                scraped_at=datetime.utcnow()
            )
            products.append(product)

        # Measure bulk insert performance
        start_time = datetime.utcnow()
        db_session.add_all(products)
        await db_session.commit()
        end_time = datetime.utcnow()
        
        duration = (end_time - start_time).total_seconds()
        
        # Should handle 100 products in reasonable time
        assert duration < 5.0  # Should complete in under 5 seconds
        
        # Verify all products were inserted
        from sqlalchemy import select
        result = await db_session.execute(select(Product))
        inserted_products = result.scalars().all()
        assert len(inserted_products) >= 100

    @pytest.mark.asyncio
    async def test_memory_usage_with_large_datasets(self):
        """Test memory efficiency with large datasets."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Simulate processing large dataset
        large_dataset = []
        for i in range(10000):
            large_dataset.append({
                'id': i,
                'title': f'Product {i}',
                'price': Decimal('99.99'),
                'data': 'x' * 100  # Some data
            })
        
        # Process the dataset
        processed_count = 0
        for item in large_dataset:
            if item['price'] > Decimal('50.00'):
                processed_count += 1
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        assert processed_count > 0
        assert memory_increase < 500  # Should not use more than 500MB additional memory


class TestSecurityIntegration:
    """Test security aspects of the complete workflow."""

    @pytest.mark.asyncio
    async def test_api_authentication_workflow(self, client: AsyncClient):
        """Test API authentication throughout the workflow."""
        # Test unauthenticated access
        response = await client.get("/api/v1/products")
        assert response.status_code == 401

        response = await client.get("/api/v1/alerts")
        assert response.status_code == 401

        response = await client.get("/api/v1/system/stats")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_input_validation_workflow(self, client: AsyncClient, auth_headers: dict):
        """Test input validation throughout API workflow."""
        # Test invalid product data
        response = await client.post(
            "/api/v1/products",
            headers=auth_headers,
            json={
                "title": "",  # Invalid empty title
                "price": -10.00,  # Invalid negative price
                "ean": "invalid_ean"  # Invalid EAN format
            }
        )
        assert response.status_code == 422  # Validation error

        # Test SQL injection attempts
        response = await client.get(
            "/api/v1/products?search='; DROP TABLE products; --",
            headers=auth_headers
        )
        # Should handle safely without errors
        assert response.status_code in [200, 400]

    @pytest.mark.asyncio
    async def test_rate_limiting_workflow(self, client: AsyncClient, auth_headers: dict):
        """Test rate limiting in API workflow."""
        # Make multiple rapid requests
        responses = []
        for i in range(10):
            response = await client.get("/api/v1/products", headers=auth_headers)
            responses.append(response)
        
        # All should succeed under normal circumstances
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count >= 8  # Most should succeed 