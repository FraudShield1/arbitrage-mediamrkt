"""
Unit tests for the Fuzzy Matcher service.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from src.services.matcher.fuzzy_matcher import (
    FuzzyMatcher, 
    FuzzyMatchResult
)
from src.models.product import Product
from src.models.asin import ASIN


class TestFuzzyMatcher:
    """Test cases for FuzzyMatcher."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.matcher = FuzzyMatcher(
            title_threshold=85.0,
            brand_threshold=90.0,
            combined_threshold=85.0,
            title_weight=0.7,
            brand_weight=0.3
        )
    
    def test_initialization(self):
        """Test matcher initialization with custom parameters."""
        matcher = FuzzyMatcher(
            title_threshold=80.0,
            brand_threshold=85.0,
            combined_threshold=82.0,
            title_weight=0.6,
            brand_weight=0.4
        )
        
        assert matcher.title_threshold == 80.0
        assert matcher.brand_threshold == 85.0
        assert matcher.combined_threshold == 82.0
        assert matcher.title_weight == 0.6
        assert matcher.brand_weight == 0.4
    
    def test_normalize_text(self):
        """Test text normalization."""
        # Test basic normalization
        text = "  iPhone 14 Pro Max (256GB) - Space Black  "
        normalized = self.matcher._normalize_text(text)
        assert normalized == "iphone 14 pro max 256gb space black"
        
        # Test special character removal
        text = "Samsung Galaxy S23+ [128GB] - Phantom Black!"
        normalized = self.matcher._normalize_text(text)
        assert normalized == "samsung galaxy s23 128gb phantom black"
        
        # Test stop words removal
        text = "The amazing Apple iPhone with a great camera"
        normalized = self.matcher._normalize_text(text)
        # Should remove common stop words
        assert "the" not in normalized
        assert "with" not in normalized
        assert "apple" in normalized
        assert "iphone" in normalized
        
        # Test empty/None input
        assert self.matcher._normalize_text(None) == ""
        assert self.matcher._normalize_text("") == ""
        assert self.matcher._normalize_text("   ") == ""
    
    def test_extract_model_info(self):
        """Test model information extraction."""
        # Test iPhone model extraction
        title = "Apple iPhone 14 Pro Max 256GB Space Black"
        model_info = self.matcher._extract_model_info(title)
        assert "iphone" in model_info.get("model", "").lower()
        assert model_info.get("capacity") == "256GB"
        
        # Test Samsung model extraction
        title = "Samsung Galaxy S23 Ultra 512GB Phantom Black"
        model_info = self.matcher._extract_model_info(title)
        assert "galaxy" in model_info.get("model", "").lower()
        assert "s23" in model_info.get("model", "").lower()
        assert model_info.get("capacity") == "512GB"
        
        # Test laptop model extraction
        title = "MacBook Pro 16-inch 1TB SSD Apple M2 Pro"
        model_info = self.matcher._extract_model_info(title)
        assert "macbook" in model_info.get("model", "").lower()
        assert model_info.get("capacity") in ["1TB", "1000GB"]
        
        # Test no model found
        title = "Generic Product Without Model"
        model_info = self.matcher._extract_model_info(title)
        assert model_info.get("model") is None or model_info.get("model") == ""
    
    def test_calculate_title_score(self):
        """Test title similarity scoring."""
        # Test exact match
        title1 = "iPhone 14 Pro Max 256GB Space Black"
        title2 = "iPhone 14 Pro Max 256GB Space Black"
        score = self.matcher._calculate_title_score(title1, title2)
        assert score == 100.0
        
        # Test similar titles
        title1 = "iPhone 14 Pro Max 256GB Space Black"
        title2 = "Apple iPhone 14 Pro Max (256GB) - Space Black"
        score = self.matcher._calculate_title_score(title1, title2)
        assert score > 90.0  # Should be very high
        
        # Test different models of same brand
        title1 = "iPhone 14 Pro Max 256GB"
        title2 = "iPhone 13 Pro Max 256GB"
        score = self.matcher._calculate_title_score(title1, title2)
        assert 60.0 < score < 90.0  # Should be moderate
        
        # Test completely different products
        title1 = "iPhone 14 Pro Max"
        title2 = "Samsung Galaxy S23"
        score = self.matcher._calculate_title_score(title1, title2)
        assert score < 50.0  # Should be low
        
        # Test empty/None titles
        score = self.matcher._calculate_title_score("", "iPhone 14")
        assert score == 0.0
        
        score = self.matcher._calculate_title_score(None, "iPhone 14")
        assert score == 0.0
    
    def test_calculate_brand_score(self):
        """Test brand similarity scoring."""
        # Test exact match
        score = self.matcher._calculate_brand_score("Apple", "Apple")
        assert score == 100.0
        
        # Test case insensitive match
        score = self.matcher._calculate_brand_score("apple", "APPLE")
        assert score == 100.0
        
        # Test similar brands
        score = self.matcher._calculate_brand_score("Samsung", "Samsung Electronics")
        assert score > 80.0
        
        # Test different brands
        score = self.matcher._calculate_brand_score("Apple", "Samsung")
        assert score < 30.0
        
        # Test empty/None brands
        score = self.matcher._calculate_brand_score("", "Apple")
        assert score == 0.0
        
        score = self.matcher._calculate_brand_score(None, "Apple")
        assert score == 0.0
    
    @pytest.mark.asyncio
    async def test_get_candidate_asins(self):
        """Test ASIN candidate retrieval."""
        # Create mock product
        product = Mock()
        product.brand = "Apple"
        product.category = "Electronics"
        
        # Create mock ASINs
        mock_asins = [
            Mock(asin="B08N5WRWNW", brand="Apple", title="iPhone 14 Pro"),
            Mock(asin="B08N5WRWNY", brand="Apple", title="iPhone 14"),
            Mock(asin="B08N5WRWNZ", brand="Samsung", title="Galaxy S23"),
        ]
        
        # Mock database session
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_asins
        mock_session.execute.return_value = mock_result
        
        candidates = await self.matcher._get_candidate_asins(product, mock_session)
        
        assert len(candidates) == 3
        assert all(isinstance(asin, Mock) for asin in candidates)
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_match_product_success(self):
        """Test successful product matching."""
        # Create mock product
        product = Mock()
        product.id = "product-123"
        product.title = "Apple iPhone 14 Pro Max 256GB Space Black"
        product.brand = "Apple"
        product.category = "Electronics"
        
        # Create mock ASIN that should match well
        matching_asin = Mock()
        matching_asin.asin = "B08N5WRWNW"
        matching_asin.title = "iPhone 14 Pro Max (256GB) - Space Black"
        matching_asin.brand = "Apple"
        
        # Mock the candidate retrieval
        with patch.object(self.matcher, '_get_candidate_asins', return_value=[matching_asin]):
            # Mock the scoring methods to return high scores
            with patch.object(self.matcher, '_calculate_title_score', return_value=95.0):
                with patch.object(self.matcher, '_calculate_brand_score', return_value=100.0):
                    result = await self.matcher.match_product(product)
        
        assert result is not None
        assert isinstance(result, FuzzyMatchResult)
        assert result.asin == "B08N5WRWNW"
        assert result.title_score == 95.0
        assert result.brand_score == 100.0
        assert result.combined_score == 96.5  # 95.0 * 0.7 + 100.0 * 0.3
        assert result.confidence > 0.9  # High confidence
        assert "Fuzzy match" in result.match_reason
    
    @pytest.mark.asyncio
    async def test_match_product_no_match(self):
        """Test product matching with no suitable candidates."""
        # Create mock product
        product = Mock()
        product.id = "product-123"
        product.title = "Apple iPhone 14 Pro Max"
        product.brand = "Apple"
        product.category = "Electronics"
        
        # Create mock ASIN that doesn't match well
        non_matching_asin = Mock()
        non_matching_asin.asin = "B08N5WRWNW"
        non_matching_asin.title = "Samsung Galaxy S23"
        non_matching_asin.brand = "Samsung"
        
        # Mock the candidate retrieval
        with patch.object(self.matcher, '_get_candidate_asins', return_value=[non_matching_asin]):
            # Mock the scoring methods to return low scores
            with patch.object(self.matcher, '_calculate_title_score', return_value=30.0):
                with patch.object(self.matcher, '_calculate_brand_score', return_value=10.0):
                    result = await self.matcher.match_product(product)
        
        assert result is None  # No match found
    
    @pytest.mark.asyncio
    async def test_match_product_threshold_filtering(self):
        """Test that matches below threshold are filtered out."""
        # Create mock product
        product = Mock()
        product.id = "product-123"
        product.title = "Apple iPhone 14 Pro Max"
        product.brand = "Apple"
        
        # Create mock ASIN with moderate scores
        moderate_asin = Mock()
        moderate_asin.asin = "B08N5WRWNW"
        moderate_asin.title = "iPhone 13 Pro Max"
        moderate_asin.brand = "Apple"
        
        # Mock the candidate retrieval
        with patch.object(self.matcher, '_get_candidate_asins', return_value=[moderate_asin]):
            # Mock scores that are below threshold
            with patch.object(self.matcher, '_calculate_title_score', return_value=80.0):  # Below 85
                with patch.object(self.matcher, '_calculate_brand_score', return_value=100.0):
                    result = await self.matcher.match_product(product)
        
        assert result is None  # Should be filtered out due to low title score
    
    @pytest.mark.asyncio
    async def test_match_product_best_candidate_selection(self):
        """Test that the best candidate is selected from multiple options."""
        # Create mock product
        product = Mock()
        product.id = "product-123"
        product.title = "Apple iPhone 14 Pro Max"
        product.brand = "Apple"
        
        # Create multiple mock ASINs with different scores
        good_asin = Mock()
        good_asin.asin = "B08N5WRWNG"
        good_asin.title = "iPhone 14 Pro Max Space Black"
        good_asin.brand = "Apple"
        
        better_asin = Mock()
        better_asin.asin = "B08N5WRWNB"
        better_asin.title = "Apple iPhone 14 Pro Max (256GB)"
        better_asin.brand = "Apple"
        
        # Mock the candidate retrieval
        with patch.object(self.matcher, '_get_candidate_asins', return_value=[good_asin, better_asin]):
            # Mock different scores for each ASIN
            def mock_title_score(product_title, asin_title):
                if "Apple iPhone 14 Pro Max (256GB)" in asin_title:
                    return 95.0  # Better match
                else:
                    return 88.0  # Good match
            
            with patch.object(self.matcher, '_calculate_title_score', side_effect=mock_title_score):
                with patch.object(self.matcher, '_calculate_brand_score', return_value=100.0):
                    result = await self.matcher.match_product(product)
        
        assert result is not None
        assert result.asin == "B08N5WRWNB"  # Should select the better match
        assert result.title_score == 95.0
    
    @pytest.mark.asyncio
    async def test_match_product_exception_handling(self):
        """Test exception handling in product matching."""
        # Create mock product
        product = Mock()
        product.id = "product-123"
        product.title = "Apple iPhone 14 Pro Max"
        product.brand = "Apple"
        
        # Mock the candidate retrieval to raise an exception
        with patch.object(self.matcher, '_get_candidate_asins', side_effect=Exception("Database error")):
            result = await self.matcher.match_product(product)
        
        assert result is None  # Should handle exception gracefully
    
    def test_combined_score_calculation(self):
        """Test combined score calculation with different weights."""
        # Test with default weights (0.7 title, 0.3 brand)
        title_score = 90.0
        brand_score = 80.0
        
        combined = title_score * self.matcher.title_weight + brand_score * self.matcher.brand_weight
        expected = 90.0 * 0.7 + 80.0 * 0.3  # 63 + 24 = 87
        
        assert combined == expected
        
        # Test with custom weights
        custom_matcher = FuzzyMatcher(title_weight=0.8, brand_weight=0.2)
        combined = title_score * custom_matcher.title_weight + brand_score * custom_matcher.brand_weight
        expected = 90.0 * 0.8 + 80.0 * 0.2  # 72 + 16 = 88
        
        assert combined == expected
    
    def test_confidence_calculation(self):
        """Test confidence score calculation."""
        # High combined score should give high confidence
        high_score = 95.0
        confidence = min(high_score / 100.0, 0.99)
        assert confidence == 0.95
        
        # Test confidence cap at 99%
        perfect_score = 100.0
        confidence = min(perfect_score / 100.0, 0.99)
        assert confidence == 0.99  # Capped at 99% for fuzzy matching
        
        # Low score should give low confidence
        low_score = 60.0
        confidence = min(low_score / 100.0, 0.99)
        assert confidence == 0.60


@pytest.mark.asyncio
async def test_fuzzy_matcher_integration():
    """Test fuzzy matcher with realistic data."""
    matcher = FuzzyMatcher()
    
    # Create realistic product data
    product = Mock()
    product.id = "mm-12345"
    product.title = "Apple iPhone 14 Pro Max 256GB Roxo Profundo"
    product.brand = "Apple"
    product.category = "Smartphones"
    
    # Create realistic ASIN data
    matching_asin = Mock()
    matching_asin.asin = "B0BDJQ8GF8"
    matching_asin.title = "Apple iPhone 14 Pro Max (256GB) - Deep Purple"
    matching_asin.brand = "Apple"
    
    similar_asin = Mock()
    similar_asin.asin = "B0BDJQ8GF9"
    similar_asin.title = "Apple iPhone 14 Pro (256GB) - Deep Purple"
    similar_asin.brand = "Apple"
    
    different_asin = Mock()
    different_asin.asin = "B0BDJQ8GF0"
    different_asin.title = "Samsung Galaxy S23 Ultra 256GB Phantom Black"
    different_asin.brand = "Samsung"
    
    # Mock database session and candidate retrieval
    with patch.object(matcher, '_get_candidate_asins', return_value=[matching_asin, similar_asin, different_asin]):
        result = await matcher.match_product(product)
    
    # Should find a match (the exact iPhone model)
    assert result is not None
    assert result.asin == "B0BDJQ8GF8"  # Should match the exact model
    assert result.confidence > 0.85  # Should have high confidence
    assert "Fuzzy match" in result.match_reason 