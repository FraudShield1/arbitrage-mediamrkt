"""
Unit tests for the Price Analyzer service.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List, Tuple

from src.services.analyzer.price_analyzer import (
    PriceAnalyzer, 
    PriceAnalysisResult
)
from src.models.product import Product
from src.models.alert import ProductAsinMatch, KeepaData


class TestPriceAnalyzer:
    """Test cases for PriceAnalyzer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = PriceAnalyzer(
            anomaly_threshold=0.50,
            min_confidence=0.70,
            min_price_points=10
        )
    
    def test_initialization(self):
        """Test analyzer initialization with custom parameters."""
        analyzer = PriceAnalyzer(
            anomaly_threshold=0.60,
            min_confidence=0.80,
            min_price_points=15,
            lookback_days=90
        )
        
        assert analyzer.anomaly_threshold == 0.60
        assert analyzer.min_confidence == 0.80
        assert analyzer.min_price_points == 15
        assert analyzer.lookback_days == 90
    
    def test_extract_price_history(self):
        """Test price history extraction from Keepa data."""
        # Create mock Keepa data
        keepa_data = Mock()
        keepa_data.price_data = {
            "timestamp": [1640995200, 1641081600, 1641168000],  # Jan 1, 2, 3 2022
            "price": [2999, 2799, 2599]  # Prices in cents
        }
        
        price_history = self.analyzer._extract_price_history(keepa_data)
        
        assert len(price_history) == 3
        assert price_history[0][1] == 29.99  # Price converted from cents
        assert price_history[1][1] == 27.99
        assert price_history[2][1] == 25.99
        
        # Check timestamps are datetime objects
        assert all(isinstance(timestamp, datetime) for timestamp, _ in price_history)
    
    def test_extract_price_history_invalid_data(self):
        """Test price history extraction with invalid data."""
        # Empty data
        keepa_data = Mock()
        keepa_data.price_data = {"timestamp": [], "price": []}
        
        price_history = self.analyzer._extract_price_history(keepa_data)
        assert price_history == []
        
        # Mismatched lengths
        keepa_data.price_data = {
            "timestamp": [1640995200, 1641081600],
            "price": [2999]
        }
        
        price_history = self.analyzer._extract_price_history(keepa_data)
        assert price_history == []
    
    def test_calculate_price_statistics(self):
        """Test price statistics calculation."""
        # Create test price history
        base_date = datetime.utcnow()
        price_history = [
            (base_date - timedelta(days=150), 100.0),
            (base_date - timedelta(days=120), 90.0),
            (base_date - timedelta(days=90), 95.0),
            (base_date - timedelta(days=60), 85.0),
            (base_date - timedelta(days=30), 88.0),
            (base_date - timedelta(days=15), 92.0),
            (base_date - timedelta(days=5), 89.0),
        ]
        
        current_price = 75.0  # Significant discount
        
        stats = self.analyzer._calculate_price_statistics(price_history, current_price)
        
        # Check that all required statistics are present
        assert 'avg_30d' in stats
        assert 'avg_90d' in stats
        assert 'avg_180d' in stats
        assert 'avg_all' in stats
        assert 'min_all' in stats
        assert 'max_all' in stats
        assert 'median_all' in stats
        assert 'std_all' in stats
        
        # Check discount calculations
        assert 'discount_30d' in stats
        assert 'discount_90d' in stats
        assert 'discount_180d' in stats
        
        # Verify min/max values
        assert stats['min_all'] == 85.0
        assert stats['max_all'] == 100.0
        
        # Discount should be positive for a lower current price
        assert stats['discount_30d'] > 0
        assert stats['discount_90d'] > 0
    
    def test_calculate_anomaly_score(self):
        """Test anomaly score calculation."""
        price_stats = {
            'avg_30d': 90.0,
            'avg_90d': 95.0,
            'avg_180d': 92.0,
            'avg_all': 93.0,
            'std_all': 5.0,
            'discount_30d': 0.55,  # 55% discount
            'discount_90d': 0.52,  # 52% discount
            'discount_180d': 0.54,  # 54% discount
        }
        
        current_price = 40.0  # Significantly below average
        
        anomaly_score, is_anomaly = self.analyzer._calculate_anomaly_score(
            current_price, price_stats
        )
        
        assert anomaly_score > 0.5
        assert is_anomaly is True
        
        # Test with normal price
        normal_price = 92.0
        normal_stats = price_stats.copy()
        normal_stats.update({
            'discount_30d': 0.02,  # 2% discount
            'discount_90d': 0.03,  # 3% discount
            'discount_180d': 0.00,  # No discount
        })
        
        anomaly_score, is_anomaly = self.analyzer._calculate_anomaly_score(
            normal_price, normal_stats
        )
        
        assert anomaly_score < 0.5
        assert is_anomaly is False
    
    def test_calculate_confidence(self):
        """Test confidence calculation."""
        # High quality data - many points, recent, low variance
        high_quality_history = [
            (datetime.utcnow() - timedelta(days=i), 100.0 + (i % 3))
            for i in range(50)
        ]
        
        high_quality_stats = {
            'avg_all': 100.0,
            'std_all': 1.0,  # Low variance
            'count_all': 50
        }
        
        confidence = self.analyzer._calculate_confidence(
            high_quality_history, high_quality_stats
        )
        
        assert confidence > 0.8  # Should be high confidence
        
        # Low quality data - few points, old, high variance
        low_quality_history = [
            (datetime.utcnow() - timedelta(days=90 + i), 100.0 + (i * 10))
            for i in range(5)
        ]
        
        low_quality_stats = {
            'avg_all': 100.0,
            'std_all': 20.0,  # High variance
            'count_all': 5
        }
        
        confidence = self.analyzer._calculate_confidence(
            low_quality_history, low_quality_stats
        )
        
        assert confidence < 0.5  # Should be low confidence
    
    @pytest.mark.asyncio
    async def test_get_keepa_data(self):
        """Test Keepa data retrieval."""
        # Mock database session and Keepa data
        mock_session = AsyncMock()
        mock_keepa_data = Mock()
        mock_keepa_data.asin = "B08N5WRWNW"
        mock_keepa_data.marketplace = "DE"
        mock_keepa_data.price_data = {"timestamp": [1640995200], "price": [2999]}
        
        # Mock database query
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_keepa_data
        mock_session.execute.return_value = mock_result
        
        keepa_data = await self.analyzer._get_keepa_data(
            "B08N5WRWNW", "DE", mock_session
        )
        
        assert keepa_data == mock_keepa_data
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_product_match(self):
        """Test complete product match analysis."""
        # Create mock product match
        product_match = Mock()
        product_match.id = "match-123"
        product_match.product_id = "product-456"
        product_match.asin = "B08N5WRWNW"
        
        # Create mock product
        mock_product = Mock()
        mock_product.id = "product-456"
        mock_product.price = Decimal("75.99")
        mock_product.title = "Test Product"
        
        # Mock database session
        mock_session = AsyncMock()
        
        # Mock product query
        mock_product_result = Mock()
        mock_product_result.scalar_one_or_none.return_value = mock_product
        mock_session.execute.return_value = mock_product_result
        
        # Mock the marketplace analysis method
        mock_analysis = PriceAnalysisResult(
            product_id="product-456",
            asin="B08N5WRWNW",
            current_price=Decimal("75.99"),
            average_price_30d=Decimal("120.00"),
            average_price_90d=Decimal("115.00"),
            average_price_180d=Decimal("118.00"),
            median_price=Decimal("117.00"),
            min_price=Decimal("110.00"),
            max_price=Decimal("125.00"),
            discount_percentage=36.7,
            anomaly_score=0.75,
            is_anomaly=True,
            confidence_score=0.85,
            analysis_details={"marketplace": "DE"}
        )
        
        with patch.object(self.analyzer, '_analyze_single_marketplace', return_value=mock_analysis):
            result = await self.analyzer.analyze_product_match(product_match, mock_session)
        
        assert result is not None
        assert result.product_id == "product-456"
        assert result.asin == "B08N5WRWNW"
        assert result.is_anomaly is True
        assert result.confidence_score == 0.85
    
    @pytest.mark.asyncio
    async def test_batch_analyze_matches(self):
        """Test batch analysis of multiple matches."""
        # Create mock matches
        matches = [Mock() for _ in range(3)]
        for i, match in enumerate(matches):
            match.id = f"match-{i}"
            match.product_id = f"product-{i}"
            match.asin = f"ASIN{i:03d}"
        
        # Mock successful analysis for first two, failure for third
        def mock_analyze_side_effect(match, session):
            if match.id == "match-2":
                raise Exception("Analysis failed")
            
            return PriceAnalysisResult(
                product_id=match.product_id,
                asin=match.asin,
                current_price=Decimal("50.0"),
                average_price_30d=Decimal("100.0"),
                average_price_90d=Decimal("100.0"),
                average_price_180d=Decimal("100.0"),
                median_price=Decimal("100.0"),
                min_price=Decimal("90.0"),
                max_price=Decimal("110.0"),
                discount_percentage=50.0,
                anomaly_score=0.8,
                is_anomaly=True,
                confidence_score=0.85,
                analysis_details={}
            )
        
        with patch.object(self.analyzer, 'analyze_product_match', side_effect=mock_analyze_side_effect):
            results = await self.analyzer.batch_analyze_matches(matches)
        
        # Should return 2 successful analyses (third one failed)
        assert len(results) == 2
        assert all(result.is_anomaly for result in results)
    
    def test_normalize_price_valid(self):
        """Test price normalization with valid inputs."""
        # Test integer
        assert self.analyzer._normalize_price(2999) == 29.99
        
        # Test float
        assert self.analyzer._normalize_price(29.99) == 29.99
        
        # Test string
        assert self.analyzer._normalize_price("2999") == 29.99
        assert self.analyzer._normalize_price("29.99") == 29.99
        
        # Test Decimal
        assert self.analyzer._normalize_price(Decimal("29.99")) == 29.99
    
    def test_normalize_price_invalid(self):
        """Test price normalization with invalid inputs."""
        # Test None
        assert self.analyzer._normalize_price(None) == 0.0
        
        # Test empty string
        assert self.analyzer._normalize_price("") == 0.0
        
        # Test negative
        assert self.analyzer._normalize_price(-100) == 0.0
        
        # Test invalid string
        assert self.analyzer._normalize_price("invalid") == 0.0
    
    def test_filter_recent_data(self):
        """Test filtering of recent price data."""
        base_date = datetime.utcnow()
        price_history = [
            (base_date - timedelta(days=200), 100.0),  # Too old
            (base_date - timedelta(days=150), 95.0),   # Within range
            (base_date - timedelta(days=100), 90.0),   # Within range
            (base_date - timedelta(days=50), 85.0),    # Within range
            (base_date - timedelta(days=10), 80.0),    # Within range
        ]
        
        # Filter to 180 days
        filtered = self.analyzer._filter_recent_data(price_history, 180)
        
        # Should exclude the first entry (200 days old)
        assert len(filtered) == 4
        assert all(
            (base_date - timestamp).days <= 180 
            for timestamp, _ in filtered
        )
    
    def test_detect_outliers(self):
        """Test outlier detection in price data."""
        # Create data with clear outliers
        price_data = [10.0, 12.0, 11.0, 9.0, 50.0, 10.5, 11.5, 100.0, 9.5]
        
        outliers = self.analyzer._detect_outliers(price_data)
        
        # Should detect the obvious outliers (50.0 and 100.0)
        assert 50.0 in outliers
        assert 100.0 in outliers
        assert 10.0 not in outliers
        assert 12.0 not in outliers


@pytest.mark.asyncio
async def test_analyze_product_price_convenience_function():
    """Test the convenience function for quick analysis."""
    from src.services.analyzer.price_analyzer import analyze_product_price
    
    # Create mock product
    mock_product = Mock()
    mock_product.id = "product-123"
    mock_product.title = "Test Product"
    mock_product.price = Decimal("75.99")
    
    with patch('src.services.analyzer.price_analyzer.PriceAnalyzer') as mock_analyzer_class:
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer
        
        mock_result = PriceAnalysisResult(
            product_id="product-123",
            asin="B08N5WRWNW",
            current_price=Decimal("75.99"),
            average_price_30d=Decimal("120.00"),
            average_price_90d=Decimal("115.00"),
            average_price_180d=Decimal("118.00"),
            median_price=Decimal("117.00"),
            min_price=Decimal("110.00"),
            max_price=Decimal("125.00"),
            discount_percentage=36.7,
            anomaly_score=0.75,
            is_anomaly=True,
            confidence_score=0.85,
            analysis_details={}
        )
        
        mock_analyzer.analyze_product_match.return_value = mock_result
        
        result = await analyze_product_price(mock_product, "B08N5WRWNW")
        
        assert result == mock_result
        mock_analyzer.analyze_product_match.assert_called_once() 