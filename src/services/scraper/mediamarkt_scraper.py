"""
MediaMarkt scraper implementation using Playwright with blazing fast performance.
Enhanced with concurrent processing, smart pagination, and optimized selectors.
Business-grade version for 1000+ product handling.
"""

import asyncio
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timezone
import json
import re
from decimal import Decimal
from urllib.parse import urljoin, urlparse, quote
from concurrent.futures import ThreadPoolExecutor
import hashlib
import aiohttp

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from bs4 import BeautifulSoup
import structlog

from src.config.settings import get_settings

logger = structlog.get_logger(__name__)


class MediaMarktScraper:
    """Enhanced MediaMarkt scraper with business-grade features."""
    
    def __init__(self):
        """Initialize the scraper with enhanced configuration."""
        self.settings = get_settings()
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.settings.SCRAPING_TIMEOUT),
            connector=aiohttp.TCPConnector(limit=self.settings.SCRAPING_CONCURRENT_LIMIT)
        )
        
        # Initialize browser-related attributes
        self.browser = None
        self.contexts = []
        self.pages = []
        self.performance_metrics = {}
        
        # Base URLs for different MediaMarkt domains
        self.base_urls = {
            'pt': 'https://mediamarkt.pt',
            'es': 'https://mediamarkt.es', 
            'de': 'https://mediamarkt.de'
        }
        
        # Enhanced headers for better stealth
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'pt-PT,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
        
        logger.info("MediaMarktScraper initialized with business-grade configuration")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start_browser()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close_browser()
    
    async def start_browser(self):
        """Initialize Playwright browser with business-grade performance settings."""
        try:
            playwright = await async_playwright().start()
            
            # Business-grade browser launch options for maximum performance
            launch_options = {
                "headless": True,
                "args": [
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-accelerated-2d-canvas",
                    "--no-first-run",
                    "--no-zygote",
                    "--disable-gpu",
                    "--disable-features=VizDisplayCompositor",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                    "--disable-extensions",
                    "--disable-plugins",
                    "--disable-images",  # Disable image loading for speed
                    "--disable-javascript-harmony-shipping",
                    "--disable-background-networking",
                    "--disable-default-apps",
                    "--disable-sync",
                    "--no-default-browser-check",
                    "--memory-pressure-off",
                    "--max_old_space_size=4096",  # Increase memory for 1000+ products
                ]
            }
            
            self.browser = await playwright.chromium.launch(**launch_options)
            
            # Create multiple contexts for business-grade concurrent processing
            for i in range(self.settings.MAX_BROWSER_CONTEXTS):
                context = await self.browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="pt-PT",
                timezone_id="Europe/Lisbon",
                    java_script_enabled=True,
                    permissions=[],
                    # Business-grade resource optimization
                    ignore_https_errors=True,
                    bypass_csp=True,
                )
                
                # Create pages for this context
                pages_per_context = self.settings.MAX_CONCURRENT_PAGES // self.settings.MAX_BROWSER_CONTEXTS
                context_pages = []
                for j in range(pages_per_context):
                    page = await context.new_page()
                    
                    # Business-grade performance optimizations
                    await page.route("**/*.{png,jpg,jpeg,gif,svg,webp,ico,woff,woff2,ttf,eot}", lambda route: route.abort())
                    await page.route("**/{google-analytics,googletagmanager,facebook,twitter,linkedin}**", lambda route: route.abort())
                    await page.route("**/ads/**", lambda route: route.abort())
                    
                    # Set aggressive timeouts for business performance
                    page.set_default_timeout(15000)  # 15 second timeout
                    page.set_default_navigation_timeout(20000)  # 20 second navigation
                    
                    context_pages.append(page)
                    
                self.contexts.append(context)
                self.pages.extend(context_pages)
            
            logger.info("Business-grade browser started", 
                       contexts=len(self.contexts), 
                       pages=len(self.pages),
                       max_capacity="1000+ products")
            
        except Exception as e:
            logger.error("Failed to start browser", error=str(e))
            logger.warning("Falling back to HTTP-only mode (limited functionality)")
            # Don't raise the exception, just log it and continue with HTTP-only mode
            self.browser = None
            self.contexts = []
            self.pages = []
    
    async def close_browser(self):
        """Close browser and cleanup resources."""
        try:
            for page in self.pages:
                await page.close()
            for context in self.contexts:
                await context.close()
            if self.browser:
                await self.browser.close()
            logger.info("Browser closed successfully")
        except Exception as e:
            logger.error("Error closing browser", error=str(e))
    
    def generate_product_hash(self, title: str, price: float, ean: Optional[str] = None) -> str:
        """
        Generate a unique hash for product deduplication.
        Business-grade duplicate handling using multiple identifiers.
        """
        # Normalize title for better matching
        normalized_title = re.sub(r'[^\w\s]', '', title.lower().strip())
        normalized_title = re.sub(r'\s+', ' ', normalized_title)
        
        # Create hash from multiple identifiers
        hash_input = f"{normalized_title}_{price}"
        if ean:
            hash_input += f"_{ean}"
        
        return hashlib.md5(hash_input.encode()).hexdigest()
    
    async def scrape_business_grade(self, max_pages: int = 50, max_products: int = 1000) -> List[Dict[str, Any]]:
        """
        Business-grade product scraping for 1000+ products with advanced performance optimization.
        
        Args:
            max_pages: Maximum pages to scrape (default: 50 for business capacity)
            max_products: Maximum products to collect (default: 1000)
            
        Returns:
            List of unique, high-quality product dictionaries
        """
        logger.info("Starting business-grade MediaMarkt scraping", 
                   max_pages=max_pages, 
                   max_products=max_products,
                   concurrent_pages=len(self.pages),
                   capacity="Optimized-level")
        
        self.performance_metrics["start_time"] = datetime.now()
        all_products = []
        
        # Business-grade page detection with caching
        total_available_pages = await self.detect_total_pages_cached()
        actual_max_pages = min(max_pages, total_available_pages)
        
        logger.info("Business-grade page detection complete", 
                   requested_pages=max_pages,
                   available_pages=total_available_pages, 
                   will_scrape=actual_max_pages,
                   estimated_products=actual_max_pages * 20)
        
        # Create optimized page batches for maximum concurrency
        batch_size = len(self.pages)
        page_batches = []
        for i in range(0, actual_max_pages, batch_size):
            batch = list(range(i + 1, min(i + batch_size + 1, actual_max_pages + 1)))
            if batch:
                page_batches.append(batch)
        
        # Process page batches with business-grade error handling
        for batch_idx, page_numbers in enumerate(page_batches):
            if len(all_products) >= max_products:
                logger.info("Reached product limit early", current_products=len(all_products))
                break
                
            logger.info("Processing business batch", 
                       batch=batch_idx + 1, 
                       total_batches=len(page_batches),
                       pages=page_numbers,
                       progress=f"{batch_idx/len(page_batches)*100:.1f}%")
            
            # Create concurrent tasks with error isolation
            tasks = []
            for i, page_num in enumerate(page_numbers):
                if i < len(self.pages):
                    page = self.pages[i]
                    url = f"{self.search_url}&page={page_num}"
                    task = self.scrape_page_business_grade(page, url, page_num)
                    tasks.append(task)
            
            # Execute with business-grade error handling
            if tasks:
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results with advanced deduplication
                for page_num, result in zip(page_numbers[:len(tasks)], batch_results):
                    if isinstance(result, Exception):
                        logger.error("Page scraping failed", 
                                   page=page_num, 
                                   error=str(result),
                                   batch=batch_idx + 1)
                        self.performance_metrics["errors"] += 1
                        continue
                    
                    if result:
                        # Business-grade duplicate filtering
                        new_products = self.filter_duplicates_advanced(result)
                        all_products.extend(new_products)
                        
                        self.performance_metrics["pages_processed"] += 1
                        self.performance_metrics["products_found"] += len(result)
                        self.performance_metrics["duplicates_filtered"] += len(result) - len(new_products)
                        
                        logger.info("Business page processed", 
                                   page=page_num,
                                   found_products=len(result),
                                   new_products=len(new_products),
                                   total_products=len(all_products),
                                   duplicates_filtered=len(result) - len(new_products))
                    
                    # Stop if we have enough products
                    if len(all_products) >= max_products:
                        logger.info("Business target reached", limit=max_products)
                    break
                
            # Business-grade rate limiting (be respectful to MediaMarkt)
            if batch_idx < len(page_batches) - 1:
                await asyncio.sleep(0.2)  # Reduced delay for business speed
        
        # Trim to exact limit and sort by quality
        final_products = self.post_process_products(all_products[:max_products])
        
        # Business metrics logging
        execution_time = (datetime.now() - self.performance_metrics["start_time"]).total_seconds()
        
        logger.info("Business-grade scraping completed", 
                   total_products=len(final_products), 
                   execution_time=f"{execution_time:.2f}s",
                   products_per_second=f"{len(final_products)/execution_time:.1f}",
                   pages_processed=self.performance_metrics["pages_processed"],
                   duplicates_filtered=self.performance_metrics["duplicates_filtered"],
                   error_rate=f"{self.performance_metrics['errors']/max(self.performance_metrics['pages_processed'], 1)*100:.1f}%",
                   quality="Business-grade")
        
        return final_products
    
    def filter_duplicates_advanced(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Advanced duplicate filtering for business-grade quality.
        """
        unique_products = []
        
        for product in products:
            # Generate business-grade hash
            product_hash = self.generate_product_hash(
                product['title'], 
                product['price'], 
                product.get('ean')
            )
            
            if product_hash not in self.seen_products:
                self.seen_products.add(product_hash)
                product['_hash'] = product_hash  # Store hash for tracking
                unique_products.append(product)
        
        return unique_products
    
    def post_process_products(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Business-grade post-processing for product quality enhancement.
        """
        # Sort by business priority: discount percentage, then price
        sorted_products = sorted(products, key=lambda p: (
            -(p.get('discount_percentage') or 0),  # Higher discounts first
            p.get('price', float('inf'))  # Lower prices first
        ))
        
        # Add business-grade metadata
        for i, product in enumerate(sorted_products):
            product['scrape_rank'] = i + 1
            product['business_score'] = self.calculate_business_score(product)
            product['quality_grade'] = self.assign_quality_grade(product)
        
        return sorted_products
    
    def calculate_business_score(self, product: Dict[str, Any]) -> float:
        """Calculate business opportunity score (0-100)."""
        score = 50.0  # Base score
        
        # Discount bonus
        if product.get('discount_percentage'):
            score += min(product['discount_percentage'] * 2, 30)
        
        # Price range bonus (sweet spot for arbitrage)
        price = product.get('price', 0)
        if 50 <= price <= 500:
            score += 10
        elif 20 <= price <= 1000:
            score += 5
        
        # Brand recognition bonus
        if product.get('brand'):
            known_brands = ['SAMSUNG', 'APPLE', 'SONY', 'LG', 'NINTENDO', 'PLAYSTATION']
            if product['brand'].upper() in known_brands:
                score += 10
        
        # EAN availability bonus (better for matching)
        if product.get('ean'):
            score += 5
        
        return min(score, 100.0)
    
    def assign_quality_grade(self, product: Dict[str, Any]) -> str:
        """Assign quality grade based on business score."""
        score = product.get('business_score', 0)
        if score >= 80:
            return 'A+'
        elif score >= 70:
            return 'A'
        elif score >= 60:
            return 'B+'
        elif score >= 50:
            return 'B'
        else:
            return 'C'

    async def detect_total_pages_cached(self) -> int:
        """
        Business-grade page detection with caching.
        """
        try:
            page = self.pages[0]
            await page.goto(self.search_url, wait_until="domcontentloaded", timeout=20000)
            
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Advanced pagination detection
            max_page = 1
            
            # Method 1: Look for pagination links
            pagination_selectors = [
                '.pagination .page-numbers',
                '.pagination a',
                '[class*="page"]',
                'a[href*="page="]'
            ]
            
            for selector in pagination_selectors:
                page_links = soup.select(selector)
                for link in page_links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    page_match = re.search(r'page=(\d+)', href)
                    if page_match:
                        page_num = int(page_match.group(1))
                        max_page = max(max_page, page_num)
                    
                    if text.isdigit():
                        page_num = int(text)
                        max_page = max(max_page, page_num)
            
            # Method 2: Estimate from product count (business heuristic)
            if max_page == 1:
                products_on_page = len(soup.select("li.snize-product"))
                if products_on_page > 0:
                    # Estimate: MediaMarkt typically has 20-30 products per page
                    # For business grade, assume substantial inventory
                    estimated_total_products = 2000  # Conservative business estimate
                    estimated_pages = min(estimated_total_products // 25, 100)  # Cap at 100 pages
                    max_page = estimated_pages
            
            logger.info("Business page detection completed", 
                       total_pages=max_page,
                       method="advanced_heuristic")
            return max_page
            
        except Exception as e:
            logger.warning("Page detection failed, using business default", error=str(e))
            return 50  # Business-grade default
    
    async def scrape_page_business_grade(self, page: Page, url: str, page_num: int) -> List[Dict[str, Any]]:
        """
        Business-grade single page scraping with enhanced error handling.
        """
        try:
            # Navigate with business-grade timeouts
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Business-grade product detection
            try:
                await page.wait_for_selector("li.snize-product", timeout=15000)
            except:
                # Try alternative selectors with business fallbacks
                alternative_selectors = [".product-item", ".product", "[data-product]"]
                for selector in alternative_selectors:
                    try:
                        await page.wait_for_selector(selector, timeout=5000)
                        break
                    except:
                        continue
            
            # Get content efficiently
            content = await page.evaluate("() => document.body.innerHTML")
            soup = BeautifulSoup(content, 'html.parser')
            
            # Use confirmed selectors with fallbacks
            product_elements = soup.select("li.snize-product")
            if not product_elements:
                fallback_selectors = [
                    ".product-item", ".product", "[data-product]", "[class*='product']"
                ]
                for selector in fallback_selectors:
                    product_elements = soup.select(selector)
                    if product_elements:
                        logger.info("Using business fallback selector", 
                                   selector=selector, page=page_num)
                    break
            
            if not product_elements:
                logger.warning("No products found on business page", page=page_num, url=url)
                return []
            
            # Business-grade parallel extraction with increased workers
            with ThreadPoolExecutor(max_workers=8) as executor:
                tasks = [
                    executor.submit(self.extract_product_data_business_grade, element, url) 
                    for element in product_elements
                ]
                
                products = []
                for future in tasks:
                    try:
                        product = future.result(timeout=10)  # Increased timeout for business data
                        if product:
                            products.append(product)
                    except Exception as e:
                        logger.debug("Business product extraction failed", error=str(e))
            
            logger.info("Business page scraping completed", 
                       page=page_num,
                       containers_found=len(product_elements),
                       products_extracted=len(products),
                       extraction_rate=f"{len(products)/len(product_elements)*100:.1f}%",
                       quality="Business-grade")
            
            return products
            
        except Exception as e:
            logger.error("Business page scraping failed", 
                        page=page_num, url=url, error=str(e))
            return []
    
    def extract_product_data_business_grade(self, element, page_url: str) -> Optional[Dict[str, Any]]:
        """
        Business-grade product data extraction with enhanced data quality.
        """
        try:
            # Enhanced title extraction
            title = None
            title_selectors = ["span.snize-title", ".product-title", ".title", "h3", "h4", "h2"]
            for selector in title_selectors:
                title_elem = element.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if title and len(title) > 5:  # Business quality filter
                        break
            
            if not title or len(title) < 5:
                return None
            
            # 🔥 CRITICAL FIX: Extract product URL
            product_url = None
            url_selectors = [
                "a[href*='/products/']", 
                "a[href*='/product/']",
                "span.snize-title a",
                ".product-title a",
                ".title a",
                "h3 a",
                "h4 a", 
                "h2 a",
                "a"  # Fallback to any link within the product element
            ]
            
            for selector in url_selectors:
                url_elem = element.select_one(selector)
                if url_elem:
                    href = url_elem.get('href', '')
                    if href:
                        # Make URL absolute if it's relative
                        if href.startswith('/'):
                            product_url = urljoin(self.base_url, href)
                        elif href.startswith('http'):
                            product_url = href
                        else:
                            product_url = urljoin(page_url, href)
                        
                        # Validate URL contains product identifier
                        if any(identifier in product_url.lower() for identifier in ['/product', '/products', '/p/', '/dp/']):
                            break
                        elif 'mediamarkt' in product_url.lower():
                            break  # Accept any MediaMarkt URL as fallback
            
            # If no valid URL found, construct a fallback URL
            if not product_url:
                # Create a search-based fallback URL
                search_title = title.replace(' ', '+').replace('&', '').replace(',', '')[:50]
                product_url = f"{self.base_url}/search?q={search_title}"
                logger.debug("Using fallback URL for product", title=title[:30], url=product_url)
            
            # Business-grade price extraction
            current_price = None
            price_selectors = ["span.snize-price", ".price", ".current-price", "[class*='price']"]
            for selector in price_selectors:
                price_elem = element.select_one(selector)
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    current_price = self.parse_price_business_grade(price_text)
                    if current_price and current_price > 0:
                        break
            
            if not current_price or current_price <= 0:
                return None
            
            # Enhanced discount detection
            has_discount = bool(element.select('.campaign-sticker, [class*="discount"], [class*="save"], [class*="promo"], [class*="offer"]'))
            discount_percentage = None
            original_price = None
            
            if has_discount:
                # Business-grade discount extraction
                discount_elements = element.select('.campaign-sticker, [class*="discount"], [class*="save"], [class*="promo"]')
                for elem in discount_elements:
                    text = elem.get_text(strip=True)
                    # Look for percentage
                    match = re.search(r'(\d+)%', text)
                    if match:
                        discount_percentage = float(match.group(1))
                        break
                    # Look for "save X" format
                    save_match = re.search(r'poupar?\s*€?\s*(\d+[.,]?\d*)', text.lower())
                    if save_match and current_price:
                        save_amount = float(save_match.group(1).replace(',', '.'))
                        original_price = current_price + save_amount
                        discount_percentage = (save_amount / original_price) * 100
                        break
            
            # Enhanced EAN/SKU extraction
            ean = None
            sku_patterns = [
                "span.snize-sku", "[class*='sku']", "[class*='code']", 
                "[data-sku]", "[data-ean]", "[data-product-id]"
            ]
            for pattern in sku_patterns:
                sku_elem = element.select_one(pattern)
                if sku_elem:
                    sku_text = sku_elem.get_text(strip=True)
                    if re.match(r'^\d{8,13}$', sku_text):
                        ean = sku_text
                        break
            
            # Business-grade availability detection
            availability = "unknown"
            stock_indicators = element.select("[class*='stock'], [class*='availability'], [class*='status']")
            if stock_indicators:
                stock_text = " ".join([elem.get_text(strip=True).lower() for elem in stock_indicators])
                if any(word in stock_text for word in ["indisponível", "esgotado", "sem stock", "out of stock"]):
                    availability = "out_of_stock"
                elif any(word in stock_text for word in ["disponível", "entrega", "stock", "available", "in stock"]):
                    availability = "in_stock"
                elif any(word in stock_text for word in ["limitado", "últimas", "limited"]):
                    availability = "limited_stock"
            
            # Enhanced brand extraction
            brand = None
            # Try to extract from title first
            brand_patterns = [
                r'^([A-Z][a-zA-Z]+)\s',
                r'^([A-Z]{2,})\s',
                r'([A-Z][a-zA-Z]+)\s+[A-Z]',
            ]
            
            for pattern in brand_patterns:
                match = re.search(pattern, title)
                if match:
                    potential_brand = match.group(1)
                    known_brands = [
                        'SAMSUNG', 'APPLE', 'SONY', 'LG', 'HUAWEI', 'XIAOMI', 'LEGO', 
                        'NINTENDO', 'PLAYSTATION', 'PS4', 'PS5', 'XBOX', 'MICROSOFT',
                        'PHILIPS', 'PANASONIC', 'CANON', 'NIKON', 'HP', 'DELL', 'ASUS'
                    ]
                    if potential_brand.upper() in known_brands:
                        brand = potential_brand.upper()
                        break
            
            # Business-grade category determination
            title_lower = title.lower()
            category = "Electronics"  # Default
            
            category_keywords = {
                "Gaming": ['ps4', 'ps5', 'xbox', 'nintendo', 'jogo', 'game', 'gaming', 'console'],
                "Smartphones": ['iphone', 'samsung galaxy', 'smartphone', 'telemóvel', 'phone'],
                "TV & Audio": ['tv', 'televisão', 'smart tv', 'soundbar', 'audio', 'speaker'],
                "Computing": ['laptop', 'computador', 'tablet', 'ipad', 'macbook', 'monitor'],
                "Photography": ['camera', 'câmara', 'fotografia', 'lens', 'nikon', 'canon'],
                "Home Appliances": ['frigorífico', 'máquina', 'forno', 'microondas', 'aspirador']
            }
            
            for cat, keywords in category_keywords.items():
                if any(keyword in title_lower for keyword in keywords):
                    category = cat
                    break
            
            # Calculate business metrics
            profit_potential_score = 0
            if discount_percentage:
                profit_potential_score += min(discount_percentage * 2, 40)
            if current_price >= 50:
                profit_potential_score += 10
            if brand:
                profit_potential_score += 15
            if ean:
                profit_potential_score += 10
            
            return {
                "title": title,
                "price": float(current_price),
                "original_price": float(original_price) if original_price else None,
                "discount_percentage": discount_percentage,
                "ean": ean,
                "brand": brand,
                "category": category,
                "availability": availability,
                "url": product_url,  # 🔥 CRITICAL FIX: Include URL in return
                "scraped_at": datetime.utcnow(),
                "source": "mediamarkt",
                "has_discount": has_discount,
                "profit_potential_score": profit_potential_score,
                "business_grade": True,
                "quality_indicators": {
                    "has_ean": bool(ean),
                    "has_brand": bool(brand),
                    "has_discount": has_discount,
                    "has_url": bool(product_url),
                    "price_range": "high" if current_price >= 100 else "medium" if current_price >= 50 else "low"
                }
            }
            
        except Exception as e:
            return None
    
    def parse_price_business_grade(self, price_text: str) -> Optional[Decimal]:
        """
        Business-grade price parsing with enhanced accuracy.
        """
        try:
            # Remove common currency symbols and text
            cleaned = re.sub(r'[€$£¥PVPpvr\s]', '', price_text)
            
            # Handle different decimal separators
            if ',' in cleaned and '.' in cleaned:
                # Handle format like 1.234,56
                parts = cleaned.split(',')
                if len(parts) == 2 and len(parts[1]) <= 2:
                    cleaned = cleaned.replace('.', '').replace(',', '.')
            elif ',' in cleaned:
                # Handle format like 1234,56
                parts = cleaned.split(',')
                if len(parts) == 2 and len(parts[1]) <= 2:
                    cleaned = cleaned.replace(',', '.')
            
            # Extract price with regex
            price_match = re.search(r'(\d+[.,]?\d*)', cleaned)
            if price_match:
                price_str = price_match.group(1).replace(',', '.')
                return Decimal(price_str)
            return None
        except:
            return None

    async def scrape_products_http_only(self, max_pages: int = 3, max_products: int = 50) -> List[Dict[str, Any]]:
        """
        HTTP-only scraping method that doesn't require Playwright browsers.
        This is a fallback when browser automation is not available.
        """
        logger.info("🔄 Starting HTTP-only scraping (fallback mode)")
        
        products = []
        page = 1
        
        try:
            while page <= max_pages and len(products) < max_products:
                logger.info(f"📄 Scraping page {page} via HTTP")
                
                # Use aiohttp to fetch the page
                url = f"{self.base_url}/search?q=&page={page}"
                
                async with self.session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        html_content = await response.text()
                        
                        # Parse with BeautifulSoup
                        soup = BeautifulSoup(html_content, 'html.parser')
                        
                        # Find product elements (basic selectors)
                        product_elements = soup.find_all(['div', 'article'], class_=lambda x: x and 'product' in x.lower() if x else False)
                        
                        if not product_elements:
                            # Try alternative selectors
                            product_elements = soup.find_all(['div', 'article'], attrs={'data-product': True})
                        
                        logger.info(f"📦 Found {len(product_elements)} product elements on page {page}")
                        
                        for element in product_elements:
                            if len(products) >= max_products:
                                break
                                
                            try:
                                product_data = self.extract_product_data_business_grade(element, url)
                                if product_data:
                                    products.append(product_data)
                            except Exception as e:
                                logger.warning(f"Failed to extract product data: {e}")
                                continue
                        
                        page += 1
                        await asyncio.sleep(1)  # Rate limiting
                    else:
                        logger.error(f"HTTP request failed with status {response.status}")
                        break
                        
        except Exception as e:
            logger.error(f"HTTP-only scraping failed: {e}")
        
        logger.info(f"✅ HTTP-only scraping completed: {len(products)} products found")
        return products

    # Legacy methods for backward compatibility
    async def scrape_all_products_fast(self, max_pages: int = 10, max_products: int = 100) -> List[Dict[str, Any]]:
        """Legacy method - redirects to business-grade scraper."""
        return await self.scrape_business_grade(max_pages, max_products)
    
    async def scrape_all_products(self, max_pages: int = 3, max_products: int = 20) -> List[Dict[str, Any]]:
        """Scrape all products with fallback to HTTP-only mode."""
        try:
            # Try browser-based scraping first
            if self.browser and self.pages:
                logger.info("🔄 Using browser-based scraping")
                return await self.scrape_business_grade(max_pages, max_products)
            else:
                logger.info("🔄 Browser not available, using HTTP-only fallback")
                return await self.scrape_products_http_only(max_pages, max_products)
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            logger.info("🔄 Falling back to HTTP-only mode")
            return await self.scrape_products_http_only(max_pages, max_products)


# Business-grade standalone function
async def scrape_mediamarkt_products_business_grade(max_pages: int = 50, max_products: int = 1000) -> List[Dict[str, Any]]:
    """
    Business-grade MediaMarkt scraping for production use.
    Optimized for 1000+ products with advanced duplicate handling.
    
    Args:
        max_pages: Maximum pages to scrape (default: 50)
        max_products: Maximum products to collect (default: 1000)
        
    Returns:
        List of business-grade scraped products
    """
    async with MediaMarktScraper() as scraper:
        return await scraper.scrape_business_grade(max_pages=max_pages, max_products=max_products)

# Enhanced legacy function
async def scrape_mediamarkt_products_fast(max_pages: int = 10, max_products: int = 100) -> List[Dict[str, Any]]:
    """Enhanced fast scraper - now using business-grade engine."""
    return await scrape_mediamarkt_products_business_grade(max_pages, max_products)

# Legacy function for backward compatibility
async def scrape_mediamarkt_products(max_pages: int = 3, max_products: int = 20) -> List[Dict[str, Any]]:
    """Legacy function - redirects to business-grade scraper."""
    return await scrape_mediamarkt_products_business_grade(max_pages, max_products) 