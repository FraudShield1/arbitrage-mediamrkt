"""
Fuzzy String Matcher for product matching.

Uses rapidfuzz for title/brand matching with 85% confidence threshold
as outlined in the matching specifications.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import re

from rapidfuzz import fuzz, process
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from ...models.product import Product
from ...models.asin import ASIN
from ...models.alert import ProductAsinMatch
from ...config.database import get_database_session

logger = logging.getLogger(__name__)


@dataclass
class FuzzyMatchResult:
    """Result of fuzzy matching."""
    asin: str
    title_score: float
    brand_score: float
    combined_score: float
    confidence: float
    match_reason: str


class FuzzyMatcher:
    """Fuzzy string matcher for product matching."""
    
    def __init__(
        self,
        title_threshold: float = 85.0,
        brand_threshold: float = 90.0,
        combined_threshold: float = 85.0,
        title_weight: float = 0.7,
        brand_weight: float = 0.3
    ):
        """
        Initialize fuzzy matcher.
        
        Args:
            title_threshold: Minimum score for title matching
            brand_threshold: Minimum score for brand matching
            combined_threshold: Minimum combined score for matching
            title_weight: Weight for title in combined score
            brand_weight: Weight for brand in combined score
        """
        self.title_threshold = title_threshold
        self.brand_threshold = brand_threshold
        self.combined_threshold = combined_threshold
        self.title_weight = title_weight
        self.brand_weight = brand_weight
        
    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for matching.
        
        Args:
            text: Input text
            
        Returns:
            Normalized text
        """
        if not text:
            return ""
            
        # Convert to lowercase
        text = text.lower().strip()
        
        # Remove special characters and extra spaces
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common stop words that don't affect matching
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'should', 'could', 'can', 'may', 'might', 'must'
        }
        
        words = text.split()
        words = [word for word in words if word not in stop_words]
        
        return ' '.join(words)
    
    def _extract_model_info(self, title: str) -> Dict[str, str]:
        """
        Extract model numbers and key identifiers from title.
        
        Args:
            title: Product title
            
        Returns:
            Dictionary with extracted model info
        """
        info = {}
        
        # Extract model numbers (common patterns)
        model_patterns = [
            r'\b([A-Z]{1,3}\d{3,6}[A-Z]*)\b',  # e.g., RTX3080, MX570
            r'\b(\d{3,4}[A-Z]{1,3})\b',        # e.g., 3080Ti
            r'\b([A-Z]+\s?\d+[A-Z]*)\b',       # e.g., RX 6700XT
        ]
        
        for pattern in model_patterns:
            matches = re.findall(pattern, title.upper())
            if matches:
                info['model'] = matches[0]
                break
                
        # Extract capacity/size info
        capacity_patterns = [
            r'(\d+)\s?(GB|TB|MB)',
            r'(\d+)\s?(inch|"|inches)',
            r'(\d+)\s?(W|watt|watts)',
        ]
        
        for pattern in capacity_patterns:
            matches = re.findall(pattern, title, re.IGNORECASE)
            if matches:
                info['capacity'] = f"{matches[0][0]}{matches[0][1]}"
                break
                
        return info
    
    def _calculate_title_score(self, product_title: str, asin_title: str) -> float:
        """
        Calculate title similarity score.
        
        Args:
            product_title: MediaMarkt product title
            asin_title: Amazon ASIN title
            
        Returns:
            Similarity score (0-100)
        """
        # Normalize titles
        norm_product = self._normalize_text(product_title)
        norm_asin = self._normalize_text(asin_title)
        
        # Calculate different similarity metrics
        token_sort_ratio = fuzz.token_sort_ratio(norm_product, norm_asin)
        token_set_ratio = fuzz.token_set_ratio(norm_product, norm_asin)
        partial_ratio = fuzz.partial_ratio(norm_product, norm_asin)
        
        # Extract model info and compare
        product_model = self._extract_model_info(product_title)
        asin_model = self._extract_model_info(asin_title)
        
        model_bonus = 0
        if product_model.get('model') and asin_model.get('model'):
            if product_model['model'].upper() == asin_model['model'].upper():
                model_bonus = 20
            elif fuzz.ratio(product_model['model'], asin_model['model']) > 80:
                model_bonus = 10
                
        # Capacity bonus
        capacity_bonus = 0
        if product_model.get('capacity') and asin_model.get('capacity'):
            if product_model['capacity'] == asin_model['capacity']:
                capacity_bonus = 10
        
        # Combined score with bonuses
        base_score = max(token_sort_ratio, token_set_ratio, partial_ratio)
        final_score = min(100, base_score + model_bonus + capacity_bonus)
        
        return final_score
    
    def _calculate_brand_score(self, product_brand: str, asin_brand: str) -> float:
        """
        Calculate brand similarity score.
        
        Args:
            product_brand: MediaMarkt product brand
            asin_brand: Amazon ASIN brand
            
        Returns:
            Similarity score (0-100)
        """
        if not product_brand or not asin_brand:
            return 0.0
            
        # Normalize brands
        norm_product = self._normalize_text(product_brand)
        norm_asin = self._normalize_text(asin_brand)
        
        # Exact match bonus
        if norm_product == norm_asin:
            return 100.0
            
        # Calculate fuzzy similarity
        ratio = fuzz.ratio(norm_product, norm_asin)
        
        # Brand aliases mapping
        brand_aliases = {
            'hp': ['hewlett packard', 'hewlett-packard'],
            'asus': ['asustek'],
            'msi': ['micro-star'],
            'lg': ['lg electronics'],
            'samsung': ['samsung electronics'],
        }
        
        # Check brand aliases
        for brand, aliases in brand_aliases.items():
            if (norm_product == brand and norm_asin in aliases) or \
               (norm_asin == brand and norm_product in aliases):
                return 95.0
                
        return ratio
    
    async def _get_candidate_asins(
        self, 
        session: AsyncSession, 
        product: Product,
        limit: int = 100
    ) -> List[ASIN]:
        """
        Get candidate ASINs for matching.
        
        Args:
            session: Database session
            product: Product to match
            limit: Maximum number of candidates
            
        Returns:
            List of candidate ASINs
        """
        query = select(ASIN)
        
        # Filter by category if available
        if product.category:
            # Map MediaMarkt categories to Amazon categories
            category_mapping = {
                'Informática': ['Electronics', 'Computers'],
                'Gaming': ['Video Games', 'Electronics'],
                'Audio': ['Electronics', 'Audio'],
                'TV': ['Electronics', 'TV'],
                'Smartphones': ['Electronics', 'Cell Phones'],
                'Fotografia': ['Electronics', 'Camera'],
            }
            
            amazon_categories = category_mapping.get(product.category, [])
            if amazon_categories:
                query = query.where(ASIN.category.in_(amazon_categories))
        
        # Filter by brand if available
        if product.brand:
            query = query.where(ASIN.brand.ilike(f"%{product.brand}%"))
            
        query = query.limit(limit)
        result = await session.execute(query)
        return result.scalars().all()
    
    async def match_product(
        self, 
        product: Product, 
        session: Optional[AsyncSession] = None
    ) -> Optional[FuzzyMatchResult]:
        """
        Match a product using fuzzy string matching.
        
        Args:
            product: Product to match
            session: Database session (optional)
            
        Returns:
            Best match result or None
        """
        if session is None:
            async with get_database_session() as session:
                return await self.match_product(product, session)
        
        try:
            # Get candidate ASINs
            candidates = await self._get_candidate_asins(session, product)
            
            if not candidates:
                logger.warning(f"No ASIN candidates found for product {product.id}")
                return None
            
            best_match = None
            best_score = 0.0
            
            for asin in candidates:
                # Calculate title score
                title_score = self._calculate_title_score(product.title, asin.title)
                
                # Calculate brand score
                brand_score = self._calculate_brand_score(product.brand, asin.brand)
                
                # Calculate combined score
                combined_score = (
                    title_score * self.title_weight +
                    brand_score * self.brand_weight
                )
                
                # Check if this is a good match
                if (title_score >= self.title_threshold and 
                    brand_score >= self.brand_threshold and
                    combined_score >= self.combined_threshold):
                    
                    if combined_score > best_score:
                        best_score = combined_score
                        best_match = FuzzyMatchResult(
                            asin=asin.asin,
                            title_score=title_score,
                            brand_score=brand_score,
                            combined_score=combined_score,
                            confidence=min(combined_score / 100.0, 0.99),  # Max 99% for fuzzy
                            match_reason=f"Fuzzy match: title={title_score:.1f}, brand={brand_score:.1f}"
                        )
            
            if best_match:
                logger.info(
                    f"Fuzzy match found for product {product.id}: "
                    f"ASIN {best_match.asin} with confidence {best_match.confidence:.2f}"
                )
            else:
                logger.info(f"No fuzzy match found for product {product.id}")
                
            return best_match
            
        except Exception as e:
            logger.error(f"Error in fuzzy matching for product {product.id}: {e}")
            return None
    
    async def match_products_batch(
        self, 
        products: List[Product], 
        session: Optional[AsyncSession] = None
    ) -> Dict[str, FuzzyMatchResult]:
        """
        Match multiple products in batch.
        
        Args:
            products: List of products to match
            session: Database session (optional)
            
        Returns:
            Dictionary mapping product IDs to match results
        """
        if session is None:
            async with get_database_session() as session:
                return await self.match_products_batch(products, session)
        
        results = {}
        
        for product in products:
            try:
                match_result = await self.match_product(product, session)
                if match_result:
                    results[str(product.id)] = match_result
            except Exception as e:
                logger.error(f"Error matching product {product.id}: {e}")
                continue
                
        logger.info(f"Fuzzy matched {len(results)} out of {len(products)} products")
        return results
    
    async def store_match(
        self,
        product_id: str,
        match_result: FuzzyMatchResult,
        session: Optional[AsyncSession] = None
    ) -> Optional[ProductAsinMatch]:
        """
        Store a fuzzy match result in the database.
        
        Args:
            product_id: Product ID
            match_result: Match result to store
            session: Database session (optional)
            
        Returns:
            Created ProductAsinMatch or None
        """
        if session is None:
            async with get_database_session() as session:
                return await self.store_match(product_id, match_result, session)
        
        try:
            # Check if match already exists
            existing_query = select(ProductAsinMatch).where(
                and_(
                    ProductAsinMatch.product_id == product_id,
                    ProductAsinMatch.asin == match_result.asin
                )
            )
            result = await session.execute(existing_query)
            existing = result.scalar_one_or_none()
            
            if existing:
                # Update existing match if confidence is higher
                if match_result.confidence > existing.confidence_score:
                    existing.confidence_score = match_result.confidence
                    existing.match_method = "fuzzy"
                    existing.match_details = {
                        "title_score": match_result.title_score,
                        "brand_score": match_result.brand_score,
                        "combined_score": match_result.combined_score,
                        "match_reason": match_result.match_reason
                    }
                    existing.created_at = datetime.utcnow()
                    await session.commit()
                    return existing
                else:
                    return existing
            
            # Create new match
            match = ProductAsinMatch(
                product_id=product_id,
                asin=match_result.asin,
                confidence_score=match_result.confidence,
                match_method="fuzzy",
                match_details={
                    "title_score": match_result.title_score,
                    "brand_score": match_result.brand_score,
                    "combined_score": match_result.combined_score,
                    "match_reason": match_result.match_reason
                }
            )
            
            session.add(match)
            await session.commit()
            await session.refresh(match)
            
            logger.info(f"Stored fuzzy match: Product {product_id} -> ASIN {match_result.asin}")
            return match
            
        except Exception as e:
            logger.error(f"Error storing fuzzy match: {e}")
            await session.rollback()
            return None


# Convenience function for quick matching
async def match_product_fuzzy(product: Product) -> Optional[FuzzyMatchResult]:
    """
    Quick function to match a single product using fuzzy matching.
    
    Args:
        product: Product to match
        
    Returns:
        Match result or None
    """
    matcher = FuzzyMatcher()
    return await matcher.match_product(product) 