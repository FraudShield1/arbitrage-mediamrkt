"""
Keepa API Integration for price history data retrieval.

This module provides async integration with Keepa API for fetching
Amazon product price history and statistics across different time periods.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, field
from enum import Enum

import aiohttp
from pydantic import BaseModel, Field

from ..config.settings import get_settings


logger = logging.getLogger(__name__)


class MarketplaceId(Enum):
    """Amazon marketplace identifiers for Keepa API."""
    
    GERMANY = 3      # amazon.de
    FRANCE = 8       # amazon.fr  
    SPAIN = 5        # amazon.es
    ITALY = 4        # amazon.it
    UK = 2           # amazon.co.uk


class HistoryPeriod(Enum):
    """Supported history periods for price analysis."""
    
    THIRTY_DAYS = 30
    NINETY_DAYS = 90
    ONE_HUNDRED_EIGHTY_DAYS = 180


@dataclass
class PricePoint:
    """Represents a single price point in time."""
    
    timestamp: datetime
    price: Optional[float]
    is_available: bool = True


@dataclass
class PriceStatistics:
    """Statistical analysis of price data over a period."""
    
    period_days: int
    average_price: Optional[float] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    current_price: Optional[float] = None
    price_drop_percentage: Optional[float] = None
    data_points: int = 0
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class KeepaProductData:
    """Complete Keepa product data with price history."""
    
    asin: str
    marketplace: MarketplaceId
    title: str
    brand: Optional[str] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    
    # Price history by period
    price_history_30d: List[PricePoint] = field(default_factory=list)
    price_history_90d: List[PricePoint] = field(default_factory=list)
    price_history_180d: List[PricePoint] = field(default_factory=list)
    
    # Statistical analysis
    statistics_30d: Optional[PriceStatistics] = None
    statistics_90d: Optional[PriceStatistics] = None
    statistics_180d: Optional[PriceStatistics] = None
    
    last_updated: datetime = field(default_factory=datetime.utcnow)


class KeepaAPIError(Exception):
    """Custom exception for Keepa API related errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class KeepaRateLimiter:
    """Rate limiter for Keepa API requests."""
    
    def __init__(self, requests_per_minute: int = 100):
        self.requests_per_minute = requests_per_minute
        self.requests: List[datetime] = []
        self.lock = asyncio.Lock()
    
    async def acquire(self) -> None:
        """Wait until a request can be made according to rate limits."""
        async with self.lock:
            now = datetime.utcnow()
            # Remove requests older than 1 minute
            self.requests = [req_time for req_time in self.requests 
                           if now - req_time < timedelta(minutes=1)]
            
            if len(self.requests) >= self.requests_per_minute:
                # Wait until we can make another request
                oldest_request = min(self.requests)
                wait_time = 60 - (now - oldest_request).total_seconds()
                if wait_time > 0:
                    logger.info(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                    await asyncio.sleep(wait_time)
            
            self.requests.append(now)


class KeepaAPIClient:
    """
    Async client for Keepa API integration.
    
    Provides methods to fetch Amazon product price history and statistics
    with proper rate limiting and error handling.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.settings = get_settings()
        self.api_key = api_key or self.settings.keepa_api_key
        self.base_url = "https://api.keepa.com"
        self.rate_limiter = KeepaRateLimiter(requests_per_minute=100)
        self.session: Optional[aiohttp.ClientSession] = None
        
        if not self.api_key:
            raise ValueError("Keepa API key is required")
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                "User-Agent": "ArbitrageBot/1.0",
                "Accept": "application/json"
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def _make_request(
        self, 
        endpoint: str, 
        params: Dict[str, Any],
        retries: int = 3
    ) -> Dict[str, Any]:
        """Make an API request with rate limiting and retry logic."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        await self.rate_limiter.acquire()
        
        # Add API key to parameters
        params["key"] = self.api_key
        
        url = f"{self.base_url}/{endpoint}"
        
        for attempt in range(retries + 1):
            try:
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    elif response.status == 429:
                        # Rate limited, wait and retry
                        wait_time = 2 ** attempt
                        logger.warning(f"Rate limited, waiting {wait_time} seconds")
                        await asyncio.sleep(wait_time)
                        continue
                    elif response.status == 400:
                        error_text = await response.text()
                        raise KeepaAPIError(f"Bad request: {error_text}", response.status)
                    elif response.status == 401:
                        raise KeepaAPIError("Invalid API key", response.status)
                    else:
                        error_text = await response.text()
                        raise KeepaAPIError(f"API error: {error_text}", response.status)
                        
            except aiohttp.ClientError as e:
                if attempt == retries:
                    raise KeepaAPIError(f"Network error: {str(e)}")
                
                wait_time = 2 ** attempt
                logger.warning(f"Network error, retrying in {wait_time} seconds: {e}")
                await asyncio.sleep(wait_time)
        
        raise KeepaAPIError("Max retries exceeded")
    
    async def get_product_data(
        self, 
        asin: str, 
        marketplace: MarketplaceId,
        history_period: HistoryPeriod = HistoryPeriod.ONE_HUNDRED_EIGHTY_DAYS
    ) -> Optional[KeepaProductData]:
        """
        Fetch complete product data including price history.
        
        Args:
            asin: Amazon Standard Identification Number
            marketplace: Target marketplace
            history_period: How far back to fetch price history
            
        Returns:
            KeepaProductData with price history and statistics
        """
        try:
            # Calculate days parameter for API
            days = history_period.value
            
            params = {
                "domain": marketplace.value,
                "asin": asin,
                "stats": days,  # Include statistics
                "history": 1,   # Include price history
                "days": days    # History period
            }
            
            logger.info(f"Fetching Keepa data for ASIN {asin} in marketplace {marketplace.name}")
            
            response_data = await self._make_request("product", params)
            
            if not response_data or "products" not in response_data:
                logger.warning(f"No product data returned for ASIN {asin}")
                return None
            
            products = response_data["products"]
            if not products:
                logger.warning(f"Empty products list for ASIN {asin}")
                return None
            
            product = products[0]
            return self._parse_product_data(product, marketplace, history_period)
            
        except KeepaAPIError as e:
            logger.error(f"Keepa API error for ASIN {asin}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching ASIN {asin}: {e}")
            return None
    
    def _parse_product_data(
        self, 
        product: Dict[str, Any], 
        marketplace: MarketplaceId,
        history_period: HistoryPeriod
    ) -> KeepaProductData:
        """Parse Keepa API response into structured data."""
        asin = product.get("asin", "")
        title = product.get("title", "")
        brand = product.get("brand", "")
        category = product.get("categoryTree", [{}])[-1].get("name") if product.get("categoryTree") else None
        image_url = product.get("imagesCSV", "").split(",")[0] if product.get("imagesCSV") else None
        
        # Parse price history
        price_history = []
        if "csv" in product and product["csv"]:
            price_history = self._parse_price_history(product["csv"])
        
        # Calculate statistics for different periods
        statistics_30d = self._calculate_statistics(price_history, 30)
        statistics_90d = self._calculate_statistics(price_history, 90)
        statistics_180d = self._calculate_statistics(price_history, 180)
        
        # Filter history by periods
        history_30d = self._filter_history_by_period(price_history, 30)
        history_90d = self._filter_history_by_period(price_history, 90)
        history_180d = self._filter_history_by_period(price_history, 180)
        
        return KeepaProductData(
            asin=asin,
            marketplace=marketplace,
            title=title,
            brand=brand,
            category=category,
            image_url=image_url,
            price_history_30d=history_30d,
            price_history_90d=history_90d,
            price_history_180d=history_180d,
            statistics_30d=statistics_30d,
            statistics_90d=statistics_90d,
            statistics_180d=statistics_180d
        )
    
    def _parse_price_history(self, csv_data: List[int]) -> List[PricePoint]:
        """Parse Keepa CSV format price history."""
        if not csv_data or len(csv_data) < 2:
            return []
        
        price_points = []
        
        # Keepa CSV format: [timestamp1, price1, timestamp2, price2, ...]
        # Timestamps are in Keepa time (minutes since epoch + offset)
        # Prices are in microcents (price * 100 * 1000)
        
        for i in range(0, len(csv_data), 2):
            if i + 1 >= len(csv_data):
                break
                
            keepa_time = csv_data[i]
            price_microcents = csv_data[i + 1]
            
            # Convert Keepa time to datetime
            # Keepa time is minutes since epoch (Jan 1, 2011, 00:00 UTC)
            epoch_start = datetime(2011, 1, 1)
            timestamp = epoch_start + timedelta(minutes=keepa_time)
            
            # Convert price from microcents to euros
            price = None
            is_available = True
            
            if price_microcents == -1:
                # Product not available
                is_available = False
            elif price_microcents > 0:
                price = price_microcents / (100 * 1000)  # Convert microcents to currency
            
            price_points.append(PricePoint(
                timestamp=timestamp,
                price=price,
                is_available=is_available
            ))
        
        return sorted(price_points, key=lambda x: x.timestamp)
    
    def _filter_history_by_period(
        self, 
        price_history: List[PricePoint], 
        days: int
    ) -> List[PricePoint]:
        """Filter price history to specified number of days."""
        if not price_history:
            return []
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return [point for point in price_history if point.timestamp >= cutoff_date]
    
    def _calculate_statistics(
        self, 
        price_history: List[PricePoint], 
        period_days: int
    ) -> PriceStatistics:
        """Calculate price statistics for a given period."""
        filtered_history = self._filter_history_by_period(price_history, period_days)
        
        # Filter out unavailable products and get valid prices
        valid_prices = [
            point.price for point in filtered_history 
            if point.is_available and point.price is not None and point.price > 0
        ]
        
        if not valid_prices:
            return PriceStatistics(period_days=period_days, data_points=0)
        
        # Calculate statistics
        average_price = sum(valid_prices) / len(valid_prices)
        min_price = min(valid_prices)
        max_price = max(valid_prices)
        
        # Get current price (most recent valid price)
        current_price = None
        for point in reversed(filtered_history):
            if point.is_available and point.price is not None and point.price > 0:
                current_price = point.price
                break
        
        # Calculate price drop percentage
        price_drop_percentage = None
        if current_price and average_price > 0:
            price_drop_percentage = ((average_price - current_price) / average_price) * 100
        
        return PriceStatistics(
            period_days=period_days,
            average_price=average_price,
            min_price=min_price,
            max_price=max_price,
            current_price=current_price,
            price_drop_percentage=price_drop_percentage,
            data_points=len(valid_prices)
        )
    
    async def get_multiple_products(
        self,
        asins: List[str],
        marketplace: MarketplaceId,
        history_period: HistoryPeriod = HistoryPeriod.ONE_HUNDRED_EIGHTY_DAYS
    ) -> Dict[str, KeepaProductData]:
        """
        Fetch data for multiple ASINs efficiently.
        
        Args:
            asins: List of ASINs to fetch
            marketplace: Target marketplace
            history_period: History period to fetch
            
        Returns:
            Dictionary mapping ASIN to KeepaProductData
        """
        results = {}
        
        # Process in batches to respect rate limits
        batch_size = 10  # Keepa allows up to 100 ASINs per request, but we'll be conservative
        
        for i in range(0, len(asins), batch_size):
            batch = asins[i:i + batch_size]
            
            try:
                # For multiple ASINs, join them with comma
                asin_string = ",".join(batch)
                
                params = {
                    "domain": marketplace.value,
                    "asin": asin_string,
                    "stats": history_period.value,
                    "history": 1,
                    "days": history_period.value
                }
                
                logger.info(f"Fetching Keepa data for {len(batch)} ASINs")
                
                response_data = await self._make_request("product", params)
                
                if response_data and "products" in response_data:
                    for product in response_data["products"]:
                        if "asin" in product:
                            asin = product["asin"]
                            product_data = self._parse_product_data(
                                product, marketplace, history_period
                            )
                            results[asin] = product_data
                
                # Small delay between batches
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error fetching batch {i//batch_size + 1}: {e}")
                continue
        
        return results
    
    async def check_api_status(self) -> Dict[str, Any]:
        """Check API status and remaining tokens."""
        try:
            response_data = await self._make_request("token", {})
            return {
                "tokens_left": response_data.get("tokensLeft", 0),
                "tokens_consumed": response_data.get("tokensConsumed", 0),
                "subscription_type": response_data.get("subscription", "unknown"),
                "status": "ok"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            } 