"""
Amazon Product Advertising API integration.

This module provides integration with Amazon's Product Advertising API
for ASIN lookup, catalog search, and product information retrieval.
"""

import asyncio
import logging
import hmac
import hashlib
import base64
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import quote, urlencode

import aiohttp
from pydantic import BaseModel, Field

from ..config.settings import get_settings


logger = logging.getLogger(__name__)


class AmazonMarketplace(Enum):
    """Amazon marketplace configurations."""
    
    GERMANY = {
        "code": "DE",
        "host": "webservices.amazon.de",
        "region": "eu-west-1",
        "marketplace_id": "A1PA6795UKMFR9"
    }
    FRANCE = {
        "code": "FR",
        "host": "webservices.amazon.fr",
        "region": "eu-west-1",
        "marketplace_id": "A13V1IB3VIYZZH"
    }
    SPAIN = {
        "code": "ES",
        "host": "webservices.amazon.es",
        "region": "eu-west-1",
        "marketplace_id": "A1RKKUPIHCS9HS"
    }
    ITALY = {
        "code": "IT",
        "host": "webservices.amazon.it",
        "region": "eu-west-1",
        "marketplace_id": "APJ6JRA9NG5V4"
    }
    UK = {
        "code": "UK",
        "host": "webservices.amazon.co.uk",
        "region": "eu-west-1",
        "marketplace_id": "A1F83G8C2ARO7P"
    }


@dataclass
class AmazonProduct:
    """Amazon product information from Product Advertising API."""
    
    asin: str
    title: str
    marketplace: str
    
    # Basic product info
    brand: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    part_number: Optional[str] = None
    ean: Optional[str] = None
    upc: Optional[str] = None
    
    # Category information
    browse_node_id: Optional[str] = None
    category: Optional[str] = None
    product_group: Optional[str] = None
    
    # Pricing (when available)
    list_price: Optional[float] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    
    # Availability
    availability: Optional[str] = None
    is_prime_eligible: bool = False
    
    # Images
    small_image_url: Optional[str] = None
    medium_image_url: Optional[str] = None
    large_image_url: Optional[str] = None
    
    # Features and description
    features: List[str] = field(default_factory=list)
    description: Optional[str] = None
    
    # Metadata
    detail_page_url: Optional[str] = None
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SearchRequest:
    """Amazon product search request parameters."""
    
    keywords: Optional[str] = None
    title: Optional[str] = None
    brand: Optional[str] = None
    browse_node_id: Optional[str] = None
    search_index: str = "All"  # Default to all categories
    min_price: Optional[int] = None  # In cents
    max_price: Optional[int] = None  # In cents
    item_page: int = 1
    item_count: int = 10


class AmazonAPIError(Exception):
    """Custom exception for Amazon API related errors."""
    
    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(message)
        self.error_code = error_code


class AmazonAPIClient:
    """
    Amazon Product Advertising API client.
    
    Provides methods for ASIN lookup, product search, and catalog queries
    with proper authentication and error handling.
    """
    
    def __init__(
        self,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        partner_tag: Optional[str] = None
    ):
        self.settings = get_settings()
        self.access_key = access_key or self.settings.amazon_access_key
        self.secret_key = secret_key or self.settings.amazon_secret_key
        self.partner_tag = partner_tag or self.settings.amazon_partner_tag
        
        self.service = "ProductAdvertisingAPI"
        self.version = "paapi5"
        
        self.session: Optional[aiohttp.ClientSession] = None
        
        if not all([self.access_key, self.secret_key, self.partner_tag]):
            raise ValueError("Amazon API credentials are required")
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                "User-Agent": "ArbitrageBot/1.0",
                "Content-Type": "application/json; charset=UTF-8"
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def _generate_signature(
        self,
        method: str,
        host: str,
        path: str,
        query_string: str,
        payload: str,
        timestamp: str,
        region: str
    ) -> str:
        """Generate AWS Signature Version 4 for API authentication."""
        
        # Step 1: Create canonical request
        canonical_headers = f"host:{host}\nx-amz-date:{timestamp}\n"
        signed_headers = "host;x-amz-date"
        
        # Hash the payload
        payload_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()
        
        canonical_request = f"{method}\n{path}\n{query_string}\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
        
        # Step 2: Create string to sign
        algorithm = "AWS4-HMAC-SHA256"
        credential_scope = f"{timestamp[:8]}/{region}/{self.service}/aws4_request"
        string_to_sign = f"{algorithm}\n{timestamp}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        
        # Step 3: Calculate signature
        def sign(key: bytes, msg: str) -> bytes:
            return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()
        
        k_date = sign(f"AWS4{self.secret_key}".encode('utf-8'), timestamp[:8])
        k_region = sign(k_date, region)
        k_service = sign(k_region, self.service)
        k_signing = sign(k_service, "aws4_request")
        
        signature = hmac.new(k_signing, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
        
        return signature
    
    def _create_auth_headers(
        self,
        method: str,
        host: str,
        path: str,
        payload: str,
        region: str
    ) -> Dict[str, str]:
        """Create authentication headers for Amazon API request."""
        
        timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        date_stamp = timestamp[:8]
        
        signature = self._generate_signature(
            method, host, path, "", payload, timestamp, region
        )
        
        credential_scope = f"{date_stamp}/{region}/{self.service}/aws4_request"
        authorization_header = (
            f"AWS4-HMAC-SHA256 "
            f"Credential={self.access_key}/{credential_scope}, "
            f"SignedHeaders=host;x-amz-date, "
            f"Signature={signature}"
        )
        
        return {
            "Authorization": authorization_header,
            "X-Amz-Date": timestamp,
            "X-Amz-Target": f"com.amazon.paapi5.v1.ProductAdvertisingAPIv1.{method}"
        }
    
    async def _make_request(
        self,
        marketplace: AmazonMarketplace,
        operation: str,
        payload: Dict[str, Any],
        retries: int = 3
    ) -> Dict[str, Any]:
        """Make authenticated request to Amazon Product Advertising API."""
        
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        marketplace_config = marketplace.value
        host = marketplace_config["host"]
        region = marketplace_config["region"]
        path = f"/paapi5/{operation.lower()}"
        
        # Add partner tag to payload
        payload["PartnerTag"] = self.partner_tag
        payload["PartnerType"] = "Associates"
        payload["Marketplace"] = marketplace_config["marketplace_id"]
        
        json_payload = str(payload).replace("'", '"')  # Simple JSON conversion
        
        # Generate authentication headers
        auth_headers = self._create_auth_headers(
            "POST", host, path, json_payload, region
        )
        
        url = f"https://{host}{path}"
        
        for attempt in range(retries + 1):
            try:
                async with self.session.post(
                    url,
                    json=payload,
                    headers=auth_headers
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        return data
                    elif response.status == 429:
                        # Rate limited
                        wait_time = 2 ** attempt
                        logger.warning(f"Amazon API rate limited, waiting {wait_time} seconds")
                        await asyncio.sleep(wait_time)
                        continue
                    elif response.status == 400:
                        error_text = await response.text()
                        raise AmazonAPIError(f"Bad request: {error_text}")
                    elif response.status == 403:
                        raise AmazonAPIError("Access denied - check API credentials")
                    else:
                        error_text = await response.text()
                        raise AmazonAPIError(f"API error: {error_text}")
                        
            except aiohttp.ClientError as e:
                if attempt == retries:
                    raise AmazonAPIError(f"Network error: {str(e)}")
                
                wait_time = 2 ** attempt
                logger.warning(f"Network error, retrying in {wait_time} seconds: {e}")
                await asyncio.sleep(wait_time)
        
        raise AmazonAPIError("Max retries exceeded")
    
    async def get_items_by_asin(
        self,
        asins: List[str],
        marketplace: AmazonMarketplace,
        resources: Optional[List[str]] = None
    ) -> Dict[str, Optional[AmazonProduct]]:
        """
        Get product information by ASIN(s).
        
        Args:
            asins: List of ASINs to lookup
            marketplace: Target marketplace
            resources: Specific data resources to include
            
        Returns:
            Dictionary mapping ASIN to product data
        """
        
        if not resources:
            resources = [
                "ItemInfo.Title",
                "ItemInfo.Features",
                "ItemInfo.ProductInfo",
                "ItemInfo.ManufactureInfo",
                "Images.Primary.Large",
                "Images.Primary.Medium",
                "Images.Primary.Small",
                "Offers.Listings.Price",
                "Offers.Listings.Availability.Message",
                "Offers.Listings.DeliveryInfo.IsPrimeEligible",
                "BrowseNodeInfo.BrowseNodes"
            ]
        
        # Limit to 10 ASINs per request as per API limits
        batch_size = 10
        results = {}
        
        for i in range(0, len(asins), batch_size):
            batch = asins[i:i + batch_size]
            
            payload = {
                "ItemIds": batch,
                "Resources": resources
            }
            
            try:
                logger.info(f"Looking up {len(batch)} ASINs in {marketplace.name}")
                
                response_data = await self._make_request(
                    marketplace, "GetItems", payload
                )
                
                # Parse response
                if "ItemsResult" in response_data:
                    items_result = response_data["ItemsResult"]
                    
                    # Process successful items
                    if "Items" in items_result:
                        for item in items_result["Items"]:
                            asin = item.get("ASIN")
                            if asin:
                                product = self._parse_item_data(item, marketplace.value["code"])
                                results[asin] = product
                    
                    # Handle errors for individual items
                    if "Errors" in items_result:
                        for error in items_result["Errors"]:
                            if "ItemIds" in error:
                                for failed_asin in error["ItemIds"]:
                                    results[failed_asin] = None
                                    logger.warning(f"ASIN {failed_asin} lookup failed: {error.get('Message', 'Unknown error')}")
                
                # Small delay between batches
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error looking up ASIN batch: {e}")
                # Mark all ASINs in failed batch as None
                for asin in batch:
                    results[asin] = None
        
        return results
    
    async def search_items(
        self,
        search_request: SearchRequest,
        marketplace: AmazonMarketplace,
        resources: Optional[List[str]] = None
    ) -> List[AmazonProduct]:
        """
        Search for items in Amazon catalog.
        
        Args:
            search_request: Search parameters
            marketplace: Target marketplace
            resources: Specific data resources to include
            
        Returns:
            List of matching products
        """
        
        if not resources:
            resources = [
                "ItemInfo.Title",
                "ItemInfo.Features",
                "ItemInfo.ProductInfo",
                "Images.Primary.Medium",
                "Offers.Listings.Price",
                "BrowseNodeInfo.BrowseNodes"
            ]
        
        payload = {
            "SearchIndex": search_request.search_index,
            "Resources": resources,
            "ItemPage": search_request.item_page,
            "ItemCount": min(search_request.item_count, 10)  # API limit
        }
        
        # Add search criteria
        if search_request.keywords:
            payload["Keywords"] = search_request.keywords
        if search_request.title:
            payload["Title"] = search_request.title
        if search_request.brand:
            payload["Brand"] = search_request.brand
        if search_request.browse_node_id:
            payload["BrowseNodeId"] = search_request.browse_node_id
        if search_request.min_price:
            payload["MinPrice"] = search_request.min_price
        if search_request.max_price:
            payload["MaxPrice"] = search_request.max_price
        
        try:
            logger.info(f"Searching Amazon catalog: {search_request.keywords or search_request.title}")
            
            response_data = await self._make_request(
                marketplace, "SearchItems", payload
            )
            
            products = []
            
            if "SearchResult" in response_data and "Items" in response_data["SearchResult"]:
                for item in response_data["SearchResult"]["Items"]:
                    product = self._parse_item_data(item, marketplace.value["code"])
                    products.append(product)
            
            logger.info(f"Found {len(products)} products in search")
            return products
            
        except Exception as e:
            logger.error(f"Error searching Amazon catalog: {e}")
            return []
    
    def _parse_item_data(self, item: Dict[str, Any], marketplace_code: str) -> AmazonProduct:
        """Parse Amazon API item data into AmazonProduct object."""
        
        asin = item.get("ASIN", "")
        
        # Extract title
        title = ""
        if "ItemInfo" in item and "Title" in item["ItemInfo"]:
            title = item["ItemInfo"]["Title"].get("DisplayValue", "")
        
        # Extract brand and manufacturer
        brand = None
        manufacturer = None
        model = None
        part_number = None
        
        if "ItemInfo" in item:
            if "ByLineInfo" in item["ItemInfo"] and "Brand" in item["ItemInfo"]["ByLineInfo"]:
                brand = item["ItemInfo"]["ByLineInfo"]["Brand"].get("DisplayValue")
            
            if "ManufactureInfo" in item["ItemInfo"]:
                if "Brand" in item["ItemInfo"]["ManufactureInfo"]:
                    manufacturer = item["ItemInfo"]["ManufactureInfo"]["Brand"].get("DisplayValue")
                if "Model" in item["ItemInfo"]["ManufactureInfo"]:
                    model = item["ItemInfo"]["ManufactureInfo"]["Model"].get("DisplayValue")
                if "PartNumber" in item["ItemInfo"]["ManufactureInfo"]:
                    part_number = item["ItemInfo"]["ManufactureInfo"]["PartNumber"].get("DisplayValue")
            
            # Extract EAN/UPC from product info
            ean = None
            upc = None
            if "ProductInfo" in item["ItemInfo"]:
                if "EANs" in item["ItemInfo"]["ProductInfo"]:
                    ean_list = item["ItemInfo"]["ProductInfo"]["EANs"].get("DisplayValues", [])
                    ean = ean_list[0] if ean_list else None
                if "UPCs" in item["ItemInfo"]["ProductInfo"]:
                    upc_list = item["ItemInfo"]["ProductInfo"]["UPCs"].get("DisplayValues", [])
                    upc = upc_list[0] if upc_list else None
        
        # Extract category information
        browse_node_id = None
        category = None
        product_group = None
        
        if "BrowseNodeInfo" in item and "BrowseNodes" in item["BrowseNodeInfo"]:
            browse_nodes = item["BrowseNodeInfo"]["BrowseNodes"]
            if browse_nodes:
                # Use the first browse node
                browse_node = browse_nodes[0]
                browse_node_id = browse_node.get("Id")
                category = browse_node.get("DisplayName")
        
        # Extract pricing information
        list_price = None
        price = None
        currency = None
        availability = None
        is_prime_eligible = False
        
        if "Offers" in item and "Listings" in item["Offers"]:
            listings = item["Offers"]["Listings"]
            if listings:
                listing = listings[0]  # Use first listing
                
                if "Price" in listing:
                    if "DisplayAmount" in listing["Price"]:
                        price_str = listing["Price"]["DisplayAmount"]
                        # Extract numeric price (removing currency symbols)
                        import re
                        price_match = re.search(r'[\d,]+\.?\d*', price_str.replace(',', ''))
                        if price_match:
                            price = float(price_match.group().replace(',', ''))
                    
                    currency = listing["Price"].get("Currency")
                
                if "Availability" in listing:
                    availability = listing["Availability"].get("Message")
                
                if "DeliveryInfo" in listing:
                    is_prime_eligible = listing["DeliveryInfo"].get("IsPrimeEligible", False)
        
        # Extract images
        small_image_url = None
        medium_image_url = None
        large_image_url = None
        
        if "Images" in item and "Primary" in item["Images"]:
            primary_images = item["Images"]["Primary"]
            if "Small" in primary_images:
                small_image_url = primary_images["Small"].get("URL")
            if "Medium" in primary_images:
                medium_image_url = primary_images["Medium"].get("URL")
            if "Large" in primary_images:
                large_image_url = primary_images["Large"].get("URL")
        
        # Extract features
        features = []
        if "ItemInfo" in item and "Features" in item["ItemInfo"]:
            features = item["ItemInfo"]["Features"].get("DisplayValues", [])
        
        # Detail page URL
        detail_page_url = item.get("DetailPageURL")
        
        return AmazonProduct(
            asin=asin,
            title=title,
            marketplace=marketplace_code,
            brand=brand,
            manufacturer=manufacturer,
            model=model,
            part_number=part_number,
            ean=ean,
            upc=upc,
            browse_node_id=browse_node_id,
            category=category,
            product_group=product_group,
            list_price=list_price,
            price=price,
            currency=currency,
            availability=availability,
            is_prime_eligible=is_prime_eligible,
            small_image_url=small_image_url,
            medium_image_url=medium_image_url,
            large_image_url=large_image_url,
            features=features,
            detail_page_url=detail_page_url
        )
    
    async def search_by_ean(
        self,
        ean: str,
        marketplace: AmazonMarketplace
    ) -> List[AmazonProduct]:
        """
        Search for products by EAN/UPC code.
        
        Args:
            ean: EAN or UPC code
            marketplace: Target marketplace
            
        Returns:
            List of matching products
        """
        
        # Try searching with EAN as keywords first
        search_request = SearchRequest(keywords=ean, item_count=10)
        products = await self.search_items(search_request, marketplace)
        
        # Filter results to only include exact EAN matches
        exact_matches = []
        for product in products:
            if product.ean == ean or product.upc == ean:
                exact_matches.append(product)
        
        return exact_matches
    
    async def get_browse_node_info(
        self,
        browse_node_ids: List[str],
        marketplace: AmazonMarketplace
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get browse node information (categories).
        
        Args:
            browse_node_ids: List of browse node IDs
            marketplace: Target marketplace
            
        Returns:
            Dictionary mapping browse node ID to node info
        """
        
        payload = {
            "BrowseNodeIds": browse_node_ids,
            "Resources": [
                "BrowseNodeInfo.BrowseNodes",
                "BrowseNodeInfo.BrowseNodes.Ancestor",
                "BrowseNodeInfo.BrowseNodes.Children"
            ]
        }
        
        try:
            response_data = await self._make_request(
                marketplace, "GetBrowseNodes", payload
            )
            
            results = {}
            
            if "BrowseNodesResult" in response_data and "BrowseNodes" in response_data["BrowseNodesResult"]:
                for node in response_data["BrowseNodesResult"]["BrowseNodes"]:
                    node_id = node.get("Id")
                    if node_id:
                        results[node_id] = {
                            "id": node_id,
                            "name": node.get("DisplayName"),
                            "context_free_name": node.get("ContextFreeName"),
                            "is_root": node.get("IsRoot", False),
                            "ancestors": node.get("Ancestor", []),
                            "children": node.get("Children", [])
                        }
            
            return results
            
        except Exception as e:
            logger.error(f"Error fetching browse node info: {e}")
            return {}


# Convenience functions
async def lookup_asin(
    asin: str,
    marketplace: AmazonMarketplace = AmazonMarketplace.GERMANY
) -> Optional[AmazonProduct]:
    """
    Quick function to lookup a single ASIN.
    
    Args:
        asin: Amazon ASIN
        marketplace: Target marketplace
        
    Returns:
        Product data or None
    """
    async with AmazonAPIClient() as client:
        results = await client.get_items_by_asin([asin], marketplace)
        return results.get(asin)


async def search_amazon_catalog(
    keywords: str,
    marketplace: AmazonMarketplace = AmazonMarketplace.GERMANY,
    max_results: int = 10
) -> List[AmazonProduct]:
    """
    Quick function to search Amazon catalog.
    
    Args:
        keywords: Search keywords
        marketplace: Target marketplace
        max_results: Maximum number of results
        
    Returns:
        List of matching products
    """
    async with AmazonAPIClient() as client:
        search_request = SearchRequest(keywords=keywords, item_count=max_results)
        return await client.search_items(search_request, marketplace) 