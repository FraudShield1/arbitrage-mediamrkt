"""
EAN-based Product Matcher for Amazon catalog.

Provides exact EAN matching with high confidence scoring.
"""

import logging
import asyncio
from typing import List, Optional, Dict, Any, Set
from datetime import datetime
import re

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...models.product import Product
from ...models.asin import ASIN
from ...models.alert import ProductAsinMatch
from ...integrations.amazon_api import AmazonAPIClient
from ...config.database import get_database_session

logger = logging.getLogger(__name__)


class EANMatcher:
    """
    EAN-based product matcher for Amazon catalog.
    
    Provides exact EAN matching with 95% confidence for valid EANs.
    """

    def __init__(self, amazon_client: Optional[AmazonAPIClient] = None):
        """
        Initialize EAN matcher.
        
        Args:
            amazon_client: Amazon API client instance
        """
        self.amazon_client = amazon_client
        self.confidence_threshold = 0.95
        self.cache: Dict[str, List[Dict[str, Any]]] = {}
        self.cache_size_limit = 1000
        
        # EAN validation patterns
        self.ean13_pattern = re.compile(r'^\d{13}$')
        self.ean8_pattern = re.compile(r'^\d{8}$')
        self.upc_pattern = re.compile(r'^\d{12}$')

    def validate_ean(self, ean: str) -> bool:
        """
        Validate EAN format and checksum.
        
        Args:
            ean: EAN code to validate
            
        Returns:
            True if EAN is valid
        """
        if not ean or not isinstance(ean, str):
            return False
        
        # Remove any whitespace and convert to string
        ean = str(ean).strip().replace(' ', '').replace('-', '')
        
        # Check format
        if not (self.ean13_pattern.match(ean) or 
                self.ean8_pattern.match(ean) or 
                self.upc_pattern.match(ean)):
            return False
        
        # Validate checksum
        return self._validate_checksum(ean)

    def _validate_checksum(self, ean: str) -> bool:
        """
        Validate EAN checksum.
        
        Args:
            ean: EAN code
            
        Returns:
            True if checksum is valid
        """
        try:
            if len(ean) == 13:  # EAN-13
                # Calculate checksum
                odd_sum = sum(int(ean[i]) for i in range(0, 12, 2))
                even_sum = sum(int(ean[i]) for i in range(1, 12, 2))
                checksum = (10 - ((odd_sum + even_sum * 3) % 10)) % 10
                return checksum == int(ean[12])
            
            elif len(ean) == 12:  # UPC-A
                # Calculate checksum
                odd_sum = sum(int(ean[i]) for i in range(0, 11, 2))
                even_sum = sum(int(ean[i]) for i in range(1, 11, 2))
                checksum = (10 - ((odd_sum * 3 + even_sum) % 10)) % 10
                return checksum == int(ean[11])
            
            elif len(ean) == 8:  # EAN-8
                # Calculate checksum
                odd_sum = sum(int(ean[i]) for i in range(0, 7, 2))
                even_sum = sum(int(ean[i]) for i in range(1, 7, 2))
                checksum = (10 - ((odd_sum + even_sum * 3) % 10)) % 10
                return checksum == int(ean[7])
            
            return False
        except (ValueError, IndexError):
            return False

    def normalize_ean(self, ean: str) -> Optional[str]:
        """
        Normalize EAN code.
        
        Args:
            ean: Raw EAN code
            
        Returns:
            Normalized EAN or None if invalid
        """
        if not ean:
            return None
        
        # Clean the EAN
        normalized = str(ean).strip().replace(' ', '').replace('-', '').zfill(13)
        
        # Convert UPC to EAN-13 by padding with zero
        if len(normalized) == 12:
            normalized = '0' + normalized
        
        # Validate
        if self.validate_ean(normalized):
            return normalized
        
        return None

    async def search_amazon_by_ean(self, ean: str) -> List[Dict[str, Any]]:
        """
        Search Amazon catalog by EAN.
        
        Args:
            ean: EAN code to search
            
        Returns:
            List of matching Amazon products
        """
        normalized_ean = self.normalize_ean(ean)
        if not normalized_ean:
            logger.warning(f"Invalid EAN format: {ean}")
            return []
        
        # Check cache first
        if normalized_ean in self.cache:
            logger.debug(f"EAN cache hit for {normalized_ean}")
            return self.cache[normalized_ean]
        
        if not self.amazon_client:
            logger.error("Amazon API client not configured")
            return []
        
        try:
            # Search by EAN
            results = await self.amazon_client.search_products(
                query=normalized_ean,
                search_index="All",
                item_count=10
            )
            
            # Filter for exact EAN matches
            exact_matches = []
            for item in results:
                item_eans = item.get('eans', [])
                if any(self.normalize_ean(item_ean) == normalized_ean for item_ean in item_eans):
                    exact_matches.append(item)
            
            # Cache results
            if len(self.cache) >= self.cache_size_limit:
                # Remove oldest entry
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
            
            self.cache[normalized_ean] = exact_matches
            
            logger.info(f"Found {len(exact_matches)} exact EAN matches for {normalized_ean}")
            return exact_matches
            
        except Exception as e:
            logger.error(f"Error searching Amazon by EAN {normalized_ean}: {e}")
            return []

    async def match_product(self, product: Product) -> List[ProductAsinMatch]:
        """
        Match product to Amazon ASINs by EAN.
        
        Args:
            product: Product to match
            
        Returns:
            List of product-ASIN matches
        """
        matches = []
        
        if not product.ean:
            logger.debug(f"Product {product.id} has no EAN")
            return matches
        
        try:
            # Search Amazon by EAN
            amazon_results = await self.search_amazon_by_ean(product.ean)
            
            if not amazon_results:
                logger.debug(f"No Amazon matches found for EAN {product.ean}")
                return matches
            
            # Create matches for each result
            for result in amazon_results:
                asin = result.get('asin')
                if not asin:
                    continue
                
                # Calculate confidence score
                confidence = self._calculate_confidence(product, result)
                
                if confidence >= self.confidence_threshold:
                    match = ProductAsinMatch(
                        product_id=product.id,
                        asin=asin,
                        match_type="ean",
                        confidence_score=confidence,
                        match_data={
                            "ean": product.ean,
                            "amazon_eans": result.get('eans', []),
                            "title_similarity": self._calculate_title_similarity(
                                product.title, result.get('title', '')
                            ),
                            "brand_match": product.brand and product.brand.lower() == 
                                         result.get('brand', '').lower(),
                            "price_amazon": result.get('price'),
                            "price_mediamarkt": float(product.price) if product.price else None
                        },
                        created_at=datetime.utcnow()
                    )
                    matches.append(match)
            
            logger.info(f"EAN matcher found {len(matches)} high-confidence matches for product {product.id}")
            
        except Exception as e:
            logger.error(f"Error matching product {product.id} by EAN: {e}")
        
        return matches

    def _calculate_confidence(self, product: Product, amazon_result: Dict[str, Any]) -> float:
        """
        Calculate confidence score for EAN match.
        
        Args:
            product: MediaMarkt product
            amazon_result: Amazon search result
            
        Returns:
            Confidence score between 0 and 1
        """
        # Start with high confidence for exact EAN match
        confidence = 0.95
        
        # Additional validation factors
        factors = []
        
        # Brand match
        if product.brand and amazon_result.get('brand'):
            brand_match = product.brand.lower() == amazon_result['brand'].lower()
            factors.append(("brand_match", 0.05 if brand_match else -0.1))
        
        # Title similarity
        title_sim = self._calculate_title_similarity(
            product.title, amazon_result.get('title', '')
        )
        if title_sim >= 0.8:
            factors.append(("title_similarity", 0.02))
        elif title_sim < 0.4:
            factors.append(("title_similarity", -0.05))
        
        # Category consistency
        if product.category and amazon_result.get('category'):
            # Simple category matching
            product_cat = product.category.lower()
            amazon_cat = amazon_result['category'].lower()
            if any(word in amazon_cat for word in product_cat.split()):
                factors.append(("category_match", 0.02))
        
        # Apply factors
        for factor_name, adjustment in factors:
            confidence += adjustment
            logger.debug(f"Applied factor {factor_name}: {adjustment}")
        
        # Ensure confidence stays within bounds
        return max(0.0, min(1.0, confidence))

    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """
        Calculate basic title similarity.
        
        Args:
            title1: First title
            title2: Second title
            
        Returns:
            Similarity score between 0 and 1
        """
        if not title1 or not title2:
            return 0.0
        
        # Simple word-based similarity
        words1 = set(title1.lower().split())
        words2 = set(title2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0

    async def batch_match_products(self, products: List[Product]) -> List[ProductAsinMatch]:
        """
        Match multiple products by EAN in batch.
        
        Args:
            products: List of products to match
            
        Returns:
            List of all matches found
        """
        all_matches = []
        
        # Group products by EAN to avoid duplicate API calls
        ean_to_products = {}
        for product in products:
            if product.ean:
                normalized_ean = self.normalize_ean(product.ean)
                if normalized_ean:
                    if normalized_ean not in ean_to_products:
                        ean_to_products[normalized_ean] = []
                    ean_to_products[normalized_ean].append(product)
        
        logger.info(f"Batch matching {len(products)} products with {len(ean_to_products)} unique EANs")
        
        # Process each unique EAN
        for ean, ean_products in ean_to_products.items():
            try:
                # Search Amazon once per EAN
                amazon_results = await self.search_amazon_by_ean(ean)
                
                # Match all products with this EAN
                for product in ean_products:
                    for result in amazon_results:
                        asin = result.get('asin')
                        if not asin:
                            continue
                        
                        confidence = self._calculate_confidence(product, result)
                        
                        if confidence >= self.confidence_threshold:
                            match = ProductAsinMatch(
                                product_id=product.id,
                                asin=asin,
                                match_type="ean",
                                confidence_score=confidence,
                                match_data={
                                    "ean": ean,
                                    "amazon_eans": result.get('eans', []),
                                    "title_similarity": self._calculate_title_similarity(
                                        product.title, result.get('title', '')
                                    ),
                                    "brand_match": product.brand and product.brand.lower() == 
                                                 result.get('brand', '').lower(),
                                    "price_amazon": result.get('price'),
                                    "price_mediamarkt": float(product.price) if product.price else None
                                },
                                created_at=datetime.utcnow()
                            )
                            all_matches.append(match)
                
                # Add delay between EAN searches to respect rate limits
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error in batch matching for EAN {ean}: {e}")
        
        logger.info(f"Batch EAN matching completed: {len(all_matches)} matches found")
        return all_matches

    def get_stats(self) -> Dict[str, Any]:
        """
        Get EAN matcher statistics.
        
        Returns:
            Dictionary with statistics
        """
        return {
            "cache_size": len(self.cache),
            "cache_limit": self.cache_size_limit,
            "confidence_threshold": self.confidence_threshold,
            "supported_formats": ["EAN-13", "EAN-8", "UPC-A"]
        } 