"""
Price Analyzer Engine for detecting arbitrage opportunities.

Processes Keepa data to detect price anomalies (>50% below average)
as specified in docs/appflow.md.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
import statistics
import numpy as np

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from ...models.product import Product
from ...models.asin import ASIN
from ...models.alert import ProductAsinMatch, PriceAlert, KeepaData
from ...config.database import get_database_session
from ...integrations.keepa_api import KeepaAPIClient

logger = logging.getLogger(__name__)


@dataclass
class PriceAnalysisResult:
    """Result of price analysis."""
    product_id: str
    asin: str
    current_price: Decimal
    average_price_30d: Decimal
    average_price_90d: Decimal
    average_price_180d: Decimal
    median_price: Decimal
    min_price: Decimal
    max_price: Decimal
    discount_percentage: float
    anomaly_score: float
    is_anomaly: bool
    confidence_score: float
    analysis_details: Dict[str, Any]


@dataclass
class MarketplacePrice:
    """Price information for a marketplace."""
    marketplace: str
    current_price: Optional[Decimal]
    average_price: Optional[Decimal]
    min_price: Optional[Decimal]
    max_price: Optional[Decimal]
    availability: bool


class PriceAnalyzer:
    """Price analyzer for detecting arbitrage opportunities."""
    
    def __init__(
        self,
        anomaly_threshold: float = 0.50,  # 50% below average
        min_confidence: float = 0.70,
        min_price_points: int = 10,
        lookback_days: int = 180
    ):
        """
        Initialize price analyzer.
        
        Args:
            anomaly_threshold: Minimum discount percentage to consider anomaly
            min_confidence: Minimum confidence for price analysis
            min_price_points: Minimum number of price points for analysis
            lookback_days: Days to look back for price history
        """
        self.anomaly_threshold = anomaly_threshold
        self.min_confidence = min_confidence
        self.min_price_points = min_price_points
        self.lookback_days = lookback_days
        self.keepa_client = KeepaAPIClient()
        
    async def _get_keepa_data(
        self, 
        asin: str, 
        marketplace: str,
        session: AsyncSession
    ) -> Optional[KeepaData]:
        """
        Get Keepa data for ASIN and marketplace.
        
        Args:
            asin: Amazon ASIN
            marketplace: Marketplace code (e.g., 'DE', 'FR')
            session: Database session
            
        Returns:
            KeepaData or None
        """
        try:
            # Check if we have recent data
            query = select(KeepaData).where(
                and_(
                    KeepaData.asin == asin,
                    KeepaData.marketplace == marketplace,
                    KeepaData.updated_at >= datetime.utcnow() - timedelta(hours=6)
                )
            )
            result = await session.execute(query)
            keepa_data = result.scalar_one_or_none()
            
            if keepa_data:
                return keepa_data
            
            # Fetch fresh data from Keepa
            logger.info(f"Fetching fresh Keepa data for {asin} in {marketplace}")
            fresh_data = await self.keepa_client.get_product_data(asin, marketplace)
            
            if fresh_data:
                # Store in database
                keepa_data = KeepaData(
                    asin=asin,
                    marketplace=marketplace,
                    price_history=fresh_data.get('price_history', {}),
                    sales_rank_history=fresh_data.get('sales_rank_history', {}),
                    stats=fresh_data.get('stats', {})
                )
                session.add(keepa_data)
                await session.commit()
                await session.refresh(keepa_data)
                return keepa_data
                
            return None
            
        except Exception as e:
            logger.error(f"Error getting Keepa data for {asin}: {e}")
            return None
    
    def _extract_price_history(self, keepa_data: KeepaData) -> List[Tuple[datetime, float]]:
        """
        Extract price history from Keepa data.
        
        Args:
            keepa_data: Keepa data object
            
        Returns:
            List of (timestamp, price) tuples
        """
        try:
            price_history = keepa_data.price_history
            if not price_history or 'csv' not in price_history:
                return []
            
            # Parse Keepa CSV format
            csv_data = price_history['csv']
            if not csv_data or len(csv_data) < 2:
                return []
            
            prices = []
            for i in range(0, len(csv_data), 2):
                if i + 1 < len(csv_data):
                    # Keepa timestamp is in minutes since epoch
                    timestamp = datetime.fromtimestamp(csv_data[i] * 60)
                    # Price is in cents, convert to euros
                    price = csv_data[i + 1] / 100.0 if csv_data[i + 1] > 0 else None
                    
                    if price is not None and price > 0:
                        prices.append((timestamp, price))
            
            # Sort by timestamp
            prices.sort(key=lambda x: x[0])
            return prices
            
        except Exception as e:
            logger.error(f"Error extracting price history: {e}")
            return []
    
    def _calculate_price_statistics(
        self, 
        price_history: List[Tuple[datetime, float]],
        current_price: float
    ) -> Dict[str, Any]:
        """
        Calculate price statistics from history.
        
        Args:
            price_history: List of (timestamp, price) tuples
            current_price: Current MediaMarkt price
            
        Returns:
            Dictionary with price statistics
        """
        if not price_history:
            return {}
        
        cutoff_30d = datetime.utcnow() - timedelta(days=30)
        cutoff_90d = datetime.utcnow() - timedelta(days=90)
        cutoff_180d = datetime.utcnow() - timedelta(days=180)
        
        prices_30d = [p for t, p in price_history if t >= cutoff_30d]
        prices_90d = [p for t, p in price_history if t >= cutoff_90d]
        prices_180d = [p for t, p in price_history if t >= cutoff_180d]
        all_prices = [p for t, p in price_history]
        
        stats = {}
        
        # Calculate averages
        if prices_30d:
            stats['avg_30d'] = statistics.mean(prices_30d)
            stats['median_30d'] = statistics.median(prices_30d)
        
        if prices_90d:
            stats['avg_90d'] = statistics.mean(prices_90d)
            stats['median_90d'] = statistics.median(prices_90d)
            
        if prices_180d:
            stats['avg_180d'] = statistics.mean(prices_180d)
            stats['median_180d'] = statistics.median(prices_180d)
        
        if all_prices:
            stats['avg_all'] = statistics.mean(all_prices)
            stats['median_all'] = statistics.median(all_prices)
            stats['min_all'] = min(all_prices)
            stats['max_all'] = max(all_prices)
            stats['std_all'] = statistics.stdev(all_prices) if len(all_prices) > 1 else 0
        
        # Calculate discount percentages
        for period in ['30d', '90d', '180d', 'all']:
            avg_key = f'avg_{period}'
            if avg_key in stats and stats[avg_key] > 0:
                discount = (stats[avg_key] - current_price) / stats[avg_key]
                stats[f'discount_{period}'] = max(0, discount)
        
        return stats
    
    def _calculate_anomaly_score(
        self, 
        current_price: float,
        price_stats: Dict[str, Any]
    ) -> Tuple[float, bool]:
        """
        Calculate anomaly score for current price.
        
        Args:
            current_price: Current MediaMarkt price
            price_stats: Price statistics
            
        Returns:
            Tuple of (anomaly_score, is_anomaly)
        """
        if not price_stats:
            return 0.0, False
        
        anomaly_scores = []
        
        # Check discount against different periods
        for period in ['30d', '90d', '180d']:
            discount_key = f'discount_{period}'
            if discount_key in price_stats:
                discount = price_stats[discount_key]
                if discount >= self.anomaly_threshold:
                    # Higher score for higher discounts
                    score = min(1.0, discount / 0.8)  # Cap at 80% discount
                    anomaly_scores.append(score)
        
        # Check against statistical outliers
        if 'avg_all' in price_stats and 'std_all' in price_stats:
            avg = price_stats['avg_all']
            std = price_stats['std_all']
            if std > 0:
                z_score = abs((current_price - avg) / std)
                if z_score > 2:  # More than 2 standard deviations
                    stat_score = min(1.0, (z_score - 2) / 3)  # Normalize
                    anomaly_scores.append(stat_score)
        
        if not anomaly_scores:
            return 0.0, False
        
        # Use maximum anomaly score
        anomaly_score = max(anomaly_scores)
        is_anomaly = anomaly_score >= 0.5  # 50% threshold for anomaly
        
        return anomaly_score, is_anomaly
    
    async def analyze_product_match(
        self, 
        product_match: ProductAsinMatch,
        session: Optional[AsyncSession] = None
    ) -> Optional[PriceAnalysisResult]:
        """
        Analyze a product-ASIN match for price anomalies.
        
        Args:
            product_match: Product-ASIN match to analyze
            session: Database session (optional)
            
        Returns:
            Price analysis result or None
        """
        if session is None:
            async with get_database_session() as session:
                return await self.analyze_product_match(product_match, session)
        
        try:
            # Get product and ASIN data
            product_query = select(Product).where(Product.id == product_match.product_id)
            product_result = await session.execute(product_query)
            product = product_result.scalar_one_or_none()
            
            if not product:
                logger.warning(f"Product {product_match.product_id} not found")
                return None
            
            # Analyze against multiple EU marketplaces
            marketplaces = ['DE', 'FR', 'ES', 'IT', 'UK']
            best_analysis = None
            best_discount = 0.0
            
            for marketplace in marketplaces:
                analysis = await self._analyze_single_marketplace(
                    product, product_match.asin, marketplace, session
                )
                
                if analysis and analysis.discount_percentage > best_discount:
                    best_discount = analysis.discount_percentage
                    best_analysis = analysis
            
            return best_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing product match {product_match.id}: {e}")
            return None
    
    async def _analyze_single_marketplace(
        self,
        product: Product,
        asin: str,
        marketplace: str,
        session: AsyncSession
    ) -> Optional[PriceAnalysisResult]:
        """
        Analyze price for a single marketplace.
        
        Args:
            product: MediaMarkt product
            asin: Amazon ASIN
            marketplace: Marketplace code
            session: Database session
            
        Returns:
            Price analysis result or None
        """
        try:
            # Get Keepa data
            keepa_data = await self._get_keepa_data(asin, marketplace, session)
            if not keepa_data:
                return None
            
            # Extract price history
            price_history = self._extract_price_history(keepa_data)
            if len(price_history) < self.min_price_points:
                logger.warning(f"Insufficient price history for {asin} in {marketplace}")
                return None
            
            current_price = float(product.price)
            
            # Calculate statistics
            price_stats = self._calculate_price_statistics(price_history, current_price)
            if not price_stats:
                return None
            
            # Calculate anomaly score
            anomaly_score, is_anomaly = self._calculate_anomaly_score(
                current_price, price_stats
            )
            
            # Calculate confidence based on data quality
            confidence = self._calculate_confidence(price_history, price_stats)
            
            if confidence < self.min_confidence:
                return None
            
            # Determine best comparison price (prefer 90-day average)
            avg_price = (
                price_stats.get('avg_90d') or 
                price_stats.get('avg_30d') or 
                price_stats.get('avg_180d') or 
                price_stats.get('avg_all')
            )
            
            if not avg_price or avg_price <= 0:
                return None
            
            discount_percentage = (avg_price - current_price) / avg_price
            
            return PriceAnalysisResult(
                product_id=str(product.id),
                asin=asin,
                current_price=Decimal(str(current_price)),
                average_price_30d=Decimal(str(price_stats.get('avg_30d', 0))),
                average_price_90d=Decimal(str(price_stats.get('avg_90d', 0))),
                average_price_180d=Decimal(str(price_stats.get('avg_180d', 0))),
                median_price=Decimal(str(price_stats.get('median_90d', 0))),
                min_price=Decimal(str(price_stats.get('min_all', 0))),
                max_price=Decimal(str(price_stats.get('max_all', 0))),
                discount_percentage=discount_percentage,
                anomaly_score=anomaly_score,
                is_anomaly=is_anomaly,
                confidence_score=confidence,
                analysis_details={
                    'marketplace': marketplace,
                    'price_stats': price_stats,
                    'price_points': len(price_history),
                    'analysis_timestamp': datetime.utcnow().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error analyzing marketplace {marketplace}: {e}")
            return None
    
    def _calculate_confidence(
        self, 
        price_history: List[Tuple[datetime, float]],
        price_stats: Dict[str, Any]
    ) -> float:
        """
        Calculate confidence score for price analysis.
        
        Args:
            price_history: Price history data
            price_stats: Calculated price statistics
            
        Returns:
            Confidence score (0-1)
        """
        confidence_factors = []
        
        # Data recency (more recent data = higher confidence)
        if price_history:
            latest_date = max(t for t, p in price_history)
            days_old = (datetime.utcnow() - latest_date).days
            recency_score = max(0, 1 - (days_old / 30))  # Decay over 30 days
            confidence_factors.append(recency_score * 0.3)
        
        # Data volume (more data points = higher confidence)
        volume_score = min(1.0, len(price_history) / 50)  # Normalize to 50 points
        confidence_factors.append(volume_score * 0.3)
        
        # Price stability (lower variance = higher confidence)
        if 'std_all' in price_stats and 'avg_all' in price_stats:
            avg = price_stats['avg_all']
            std = price_stats['std_all']
            if avg > 0:
                cv = std / avg  # Coefficient of variation
                stability_score = max(0, 1 - cv)  # Lower CV = higher stability
                confidence_factors.append(stability_score * 0.2)
        
        # Temporal coverage (data spread over time = higher confidence)
        if len(price_history) > 1:
            time_span = (price_history[-1][0] - price_history[0][0]).days
            coverage_score = min(1.0, time_span / 90)  # Normalize to 90 days
            confidence_factors.append(coverage_score * 0.2)
        
        return sum(confidence_factors) if confidence_factors else 0.0
    
    async def batch_analyze_matches(
        self,
        matches: List[ProductAsinMatch],
        session: Optional[AsyncSession] = None
    ) -> List[PriceAnalysisResult]:
        """
        Analyze multiple product matches in batch.
        
        Args:
            matches: List of product-ASIN matches
            session: Database session (optional)
            
        Returns:
            List of price analysis results
        """
        if session is None:
            async with get_database_session() as session:
                return await self.batch_analyze_matches(matches, session)
        
        results = []
        
        for match in matches:
            try:
                analysis = await self.analyze_product_match(match, session)
                if analysis and analysis.is_anomaly:
                    results.append(analysis)
            except Exception as e:
                logger.error(f"Error analyzing match {match.id}: {e}")
                continue
        
        logger.info(f"Found {len(results)} price anomalies out of {len(matches)} matches")
        return results


# Convenience function for quick analysis
async def analyze_product_price(
    product: Product, 
    asin: str
) -> Optional[PriceAnalysisResult]:
    """
    Quick function to analyze price for a product-ASIN pair.
    
    Args:
        product: MediaMarkt product
        asin: Amazon ASIN
        
    Returns:
        Price analysis result or None
    """
    analyzer = PriceAnalyzer()
    
    # Create temporary match object
    from uuid import uuid4
    temp_match = ProductAsinMatch(
        id=uuid4(),
        product_id=str(product.id),
        asin=asin,
        confidence_score=1.0,
        match_method="temp"
    )
    
    return await analyzer.analyze_product_match(temp_match) 