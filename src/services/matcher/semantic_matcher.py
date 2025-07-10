"""
Semantic Product Matcher

Uses sentence transformers to find similar products between MediaMarkt and Amazon
based on semantic text similarity of product titles and descriptions.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import numpy as np

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from src.config.settings import get_settings
from src.models.schemas import ProductMatch, MatchResult
from src.integrations.keepa_api import KeepaAPIClient

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class SemanticFeatures:
    """Features extracted for semantic matching."""
    title: str
    brand: str
    category: str
    combined_text: str
    embedding: Optional[np.ndarray] = None


class SemanticMatcher:
    """
    Semantic product matcher using sentence transformers.
    Provides 80% confidence matching for products without EAN codes.
    """
    
    def __init__(self):
        """Initialize semantic matcher with transformer model."""
        # Use multilingual model for better Portuguese/English matching
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        self.keepa_api = KeepaAPIClient()
        self.confidence_threshold = 0.80
        self.similarity_threshold = 0.70  # Cosine similarity threshold
        
    async def match_product(
        self,
        mediamarkt_product: Dict[str, Any],
        search_limit: int = 50
    ) -> List[MatchResult]:
        """
        Find semantically similar products for a MediaMarkt product.
        
        Args:
            mediamarkt_product: Product data from MediaMarkt
            search_limit: Maximum number of Amazon products to search
            
        Returns:
            List of match results with confidence scores
        """
        try:
            # Extract features from MediaMarkt product
            mm_features = self._extract_features(mediamarkt_product)
            if not mm_features.combined_text.strip():
                logger.warning(f"No text content for product {mediamarkt_product.get('id')}")
                return []
            
            # Generate embedding for MediaMarkt product
            mm_embedding = self._generate_embedding(mm_features.combined_text)
            
            # Search Amazon products
            amazon_products = await self._search_amazon_products(
                mm_features, search_limit
            )
            
            if not amazon_products:
                logger.info(f"No Amazon products found for search: {mm_features.title[:50]}")
                return []
            
            # Find best matches
            matches = await self._find_semantic_matches(
                mm_features, mm_embedding, amazon_products
            )
            
            # Filter by confidence threshold and sort by similarity
            valid_matches = [
                match for match in matches 
                if match.confidence >= self.confidence_threshold
            ]
            
            valid_matches.sort(key=lambda x: x.similarity_score, reverse=True)
            
            logger.info(
                f"Found {len(valid_matches)} semantic matches for product {mediamarkt_product.get('id')} "
                f"(searched {len(amazon_products)} Amazon products)"
            )
            
            return valid_matches[:10]  # Return top 10 matches
            
        except Exception as e:
            logger.error(f"Error in semantic matching: {str(e)}", exc_info=True)
            return []
    
    def _extract_features(self, product: Dict[str, Any]) -> SemanticFeatures:
        """Extract text features for semantic analysis."""
        title = product.get('title', '').strip()
        brand = product.get('brand', '').strip()
        category = product.get('category', '').strip()
        
        # Combine all text for better semantic understanding
        text_parts = []
        if title:
            text_parts.append(title)
        if brand:
            text_parts.append(f"Brand: {brand}")
        if category:
            text_parts.append(f"Category: {category}")
            
        combined_text = " ".join(text_parts)
        
        return SemanticFeatures(
            title=title,
            brand=brand,
            category=category,
            combined_text=combined_text
        )
    
    def _generate_embedding(self, text: str) -> np.ndarray:
        """Generate sentence embedding for text."""
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            return np.zeros(384)  # Default embedding size for MiniLM
    
    async def _search_amazon_products(
        self, 
        features: SemanticFeatures, 
        limit: int
    ) -> List[Dict[str, Any]]:
        """Search Amazon products using Keepa API."""
        try:
            # Create search query from product features
            search_terms = []
            
            # Use brand and key words from title
            if features.brand:
                search_terms.append(features.brand)
            
            # Extract key terms from title (remove common words)
            stop_words = {'de', 'da', 'do', 'para', 'com', 'and', 'the', 'in', 'on', 'at'}
            title_words = features.title.lower().split()
            key_words = [word for word in title_words if len(word) > 3 and word not in stop_words]
            search_terms.extend(key_words[:3])  # Use top 3 key words
            
            search_query = " ".join(search_terms)
            
            # Search using Keepa API
            amazon_products = await self.keepa_api.search_products(
                query=search_query,
                domain=1,  # Amazon.de
                limit=limit
            )
            
            return amazon_products
            
        except Exception as e:
            logger.error(f"Error searching Amazon products: {str(e)}")
            return []
    
    async def _find_semantic_matches(
        self,
        mm_features: SemanticFeatures,
        mm_embedding: np.ndarray,
        amazon_products: List[Dict[str, Any]]
    ) -> List[MatchResult]:
        """Find semantic matches between MediaMarkt and Amazon products."""
        matches = []
        
        for amazon_product in amazon_products:
            try:
                # Extract Amazon product features
                amazon_features = self._extract_amazon_features(amazon_product)
                
                # Generate embedding for Amazon product
                amazon_embedding = self._generate_embedding(amazon_features.combined_text)
                
                # Calculate similarity
                similarity = self._calculate_similarity(mm_embedding, amazon_embedding)
                
                # Calculate confidence based on multiple factors
                confidence = self._calculate_confidence(
                    mm_features, amazon_features, similarity
                )
                
                if similarity >= self.similarity_threshold:
                    match = MatchResult(
                        mediamarkt_product_id=mm_features.title,  # Will be updated with actual ID
                        amazon_asin=amazon_product.get('asin', ''),
                        match_type='semantic',
                        confidence=confidence,
                        similarity_score=similarity,
                        match_details={
                            'semantic_similarity': float(similarity),
                            'brand_match': mm_features.brand.lower() == amazon_features.brand.lower(),
                            'category_match': mm_features.category.lower() == amazon_features.category.lower(),
                            'title_overlap': self._calculate_title_overlap(
                                mm_features.title, amazon_features.title
                            )
                        },
                        created_at=datetime.utcnow()
                    )
                    matches.append(match)
                    
            except Exception as e:
                logger.error(f"Error matching product {amazon_product.get('asin', 'unknown')}: {str(e)}")
                continue
        
        return matches
    
    def _extract_amazon_features(self, product: Dict[str, Any]) -> SemanticFeatures:
        """Extract features from Amazon product."""
        title = product.get('title', '').strip()
        brand = product.get('brand', '').strip()
        category = product.get('category', [''])[0] if product.get('category') else ''
        
        # Combine text for Amazon product
        text_parts = []
        if title:
            text_parts.append(title)
        if brand:
            text_parts.append(f"Brand: {brand}")
        if category:
            text_parts.append(f"Category: {category}")
            
        combined_text = " ".join(text_parts)
        
        return SemanticFeatures(
            title=title,
            brand=brand,
            category=category,
            combined_text=combined_text
        )
    
    def _calculate_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate cosine similarity between two embeddings."""
        try:
            # Reshape for sklearn
            emb1 = embedding1.reshape(1, -1)
            emb2 = embedding2.reshape(1, -1)
            
            similarity = cosine_similarity(emb1, emb2)[0][0]
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Error calculating similarity: {str(e)}")
            return 0.0
    
    def _calculate_confidence(
        self,
        mm_features: SemanticFeatures,
        amazon_features: SemanticFeatures,
        similarity: float
    ) -> float:
        """Calculate confidence score based on multiple factors."""
        confidence = similarity * 0.6  # Base confidence from semantic similarity
        
        # Brand matching bonus
        if mm_features.brand and amazon_features.brand:
            if mm_features.brand.lower() == amazon_features.brand.lower():
                confidence += 0.15
            elif mm_features.brand.lower() in amazon_features.brand.lower() or \
                 amazon_features.brand.lower() in mm_features.brand.lower():
                confidence += 0.10
        
        # Category matching bonus
        if mm_features.category and amazon_features.category:
            if mm_features.category.lower() == amazon_features.category.lower():
                confidence += 0.10
            elif mm_features.category.lower() in amazon_features.category.lower() or \
                 amazon_features.category.lower() in mm_features.category.lower():
                confidence += 0.05
        
        # Title overlap bonus
        title_overlap = self._calculate_title_overlap(mm_features.title, amazon_features.title)
        confidence += title_overlap * 0.15
        
        return min(confidence, 0.99)  # Cap at 99%
    
    def _calculate_title_overlap(self, title1: str, title2: str) -> float:
        """Calculate word overlap between two titles."""
        if not title1 or not title2:
            return 0.0
        
        # Normalize titles
        words1 = set(title1.lower().split())
        words2 = set(title2.lower().split())
        
        # Remove stop words
        stop_words = {'de', 'da', 'do', 'para', 'com', 'and', 'the', 'in', 'on', 'at', 'with', 'for'}
        words1 = {w for w in words1 if len(w) > 2 and w not in stop_words}
        words2 = {w for w in words2 if len(w) > 2 and w not in stop_words}
        
        if not words1 or not words2:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    async def batch_match(
        self,
        products: List[Dict[str, Any]],
        batch_size: int = 10
    ) -> Dict[str, List[MatchResult]]:
        """Process multiple products in batches."""
        results = {}
        
        for i in range(0, len(products), batch_size):
            batch = products[i:i + batch_size]
            batch_tasks = []
            
            for product in batch:
                task = self.match_product(product)
                batch_tasks.append(task)
            
            # Process batch concurrently
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for product, matches in zip(batch, batch_results):
                if isinstance(matches, Exception):
                    logger.error(f"Error processing product {product.get('id')}: {matches}")
                    results[product.get('id', 'unknown')] = []
                else:
                    results[product.get('id', 'unknown')] = matches
        
        return results


# Export main class
__all__ = ['SemanticMatcher', 'SemanticFeatures'] 