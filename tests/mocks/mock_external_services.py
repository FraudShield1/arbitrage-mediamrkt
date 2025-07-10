"""
Mock implementations of external services for testing.
"""

import asyncio
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock


class MockMediaMarktScraper:
    """Mock implementation of MediaMarkt scraper for testing."""
    
    def __init__(self, mock_products: Optional[List[Dict]] = None):
        self.mock_products = mock_products or self._default_mock_products()
        self.browser = None
        self.context = None
        self.page = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    
    async def start_browser(self):
        """Mock browser startup."""
        self.browser = Mock()
        self.context = Mock()
        self.page = Mock()
    
    async def close_browser(self):
        """Mock browser cleanup."""
        self.browser = None
        self.context = None
        self.page = None
    
    async def scrape_products_page(self, search_term: Optional[str] = None) -> List[Dict]:
        """Mock product scraping."""
        await asyncio.sleep(0.1)  # Simulate scraping delay
        
        if search_term:
            # Filter products by search term
            filtered_products = [
                p for p in self.mock_products 
                if search_term.lower() in p['title'].lower()
            ]
            return filtered_products
        
        return self.mock_products
    
    async def scrape_category_products(self, category: str) -> List[Dict]:
        """Mock category scraping."""
        return [
            p for p in self.mock_products 
            if p.get('category', '').lower() == category.lower()
        ]
    
    def _default_mock_products(self) -> List[Dict]:
        """Default mock product data."""
        return [
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
            },
            {
                'title': 'Samsung Galaxy S24 Ultra 256GB Titânio Violeta',
                'brand': 'Samsung',
                'ean': '8806095262',
                'current_price': Decimal('899.99'),
                'original_price': Decimal('1199.99'),
                'discount_percentage': Decimal('25.00'),
                'stock_status': 'in_stock',
                'product_url': 'https://mediamarkt.pt/samsung-galaxy-s24-ultra',
                'category': 'Smartphones',
                'scraped_at': datetime.utcnow()
            },
            {
                'title': 'Sony WH-1000XM5 Wireless Noise Canceling Headphones',
                'brand': 'Sony',
                'ean': '027242919',
                'current_price': Decimal('299.99'),
                'original_price': Decimal('399.99'),
                'discount_percentage': Decimal('25.00'),
                'stock_status': 'in_stock',
                'product_url': 'https://mediamarkt.pt/sony-wh-1000xm5',
                'category': 'Audio',
                'scraped_at': datetime.utcnow()
            }
        ]


class MockKeepaClient:
    """Mock implementation of Keepa API client for testing."""
    
    def __init__(self, mock_data: Optional[Dict] = None):
        self.mock_data = mock_data or self._default_mock_data()
        self.api_key = "mock_api_key"
        self.rate_limit_delay = 0.1
    
    async def get_product_data(self, asin: str) -> Dict[str, Any]:
        """Mock product data retrieval."""
        await asyncio.sleep(self.rate_limit_delay)  # Simulate API delay
        
        if asin in self.mock_data:
            return self.mock_data[asin]
        
        # Return default data structure for unknown ASINs
        return {
            'asin': asin,
            'title': f'Mock Product {asin}',
            'current_price': 999.99,
            'price_history': self._generate_mock_price_history(),
            'avg_price_30d': 999.99,
            'lowest_price_30d': 899.99,
            'highest_price_30d': 1099.99,
            'sales_rank': 100,
            'reviews_count': 500,
            'rating': 4.2
        }
    
    async def get_multiple_products(self, asins: List[str]) -> Dict[str, Dict]:
        """Mock bulk product data retrieval."""
        results = {}
        for asin in asins:
            results[asin] = await self.get_product_data(asin)
            await asyncio.sleep(0.05)  # Simulate staggered requests
        return results
    
    def _default_mock_data(self) -> Dict[str, Dict]:
        """Default mock Keepa data."""
        return {
            'B0CHX2F5QT': {
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
                'highest_price_30d': 1399.00,
                'sales_rank': 15,
                'reviews_count': 1250,
                'rating': 4.5
            },
            'B0CMDRCZBX': {
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
                'highest_price_30d': 1199.00,
                'sales_rank': 25,
                'reviews_count': 890,
                'rating': 4.3
            }
        }
    
    def _generate_mock_price_history(self) -> List[Dict]:
        """Generate realistic mock price history."""
        history = []
        base_price = 999.99
        current_date = datetime.utcnow()
        
        for i in range(30, 0, -1):
            # Simulate price fluctuations
            variation = (i % 7 - 3) * 0.05  # ±15% variation
            price = base_price * (1 + variation)
            history.append({
                'timestamp': current_date - timedelta(days=i),
                'price': round(price, 2)
            })
        
        return history


class MockTelegramNotifier:
    """Mock Telegram notification service."""
    
    def __init__(self):
        self.bot_token = "mock_bot_token"
        self.chat_id = "mock_chat_id"
        self.sent_messages = []
    
    async def send_alert_notification(self, message: str) -> bool:
        """Mock sending Telegram notification."""
        await asyncio.sleep(0.1)  # Simulate network delay
        
        self.sent_messages.append({
            'message': message,
            'timestamp': datetime.utcnow(),
            'type': 'alert'
        })
        return True
    
    async def send_status_update(self, status: str) -> bool:
        """Mock sending status update."""
        await asyncio.sleep(0.1)
        
        self.sent_messages.append({
            'message': status,
            'timestamp': datetime.utcnow(),
            'type': 'status'
        })
        return True


class MockSlackNotifier:
    """Mock Slack notification service."""
    
    def __init__(self):
        self.webhook_url = "https://hooks.slack.com/mock"
        self.channel = "#arbitrage-alerts"
        self.sent_messages = []
    
    async def send_alert_notification(self, message: str) -> bool:
        """Mock sending Slack notification."""
        await asyncio.sleep(0.1)
        
        self.sent_messages.append({
            'message': message,
            'timestamp': datetime.utcnow(),
            'channel': self.channel,
            'type': 'alert'
        })
        return True
    
    async def send_formatted_alert(self, alert_data: Dict) -> bool:
        """Mock sending formatted Slack alert."""
        formatted_message = self._format_slack_message(alert_data)
        return await self.send_alert_notification(formatted_message)
    
    def _format_slack_message(self, alert_data: Dict) -> str:
        """Format alert data for Slack."""
        return f"""
🚨 *Arbitrage Opportunity*
💰 Profit: €{alert_data.get('profit_amount', 0)}
📊 Margin: {alert_data.get('profit_margin', 0):.1%}
🏪 MediaMarkt: €{alert_data.get('current_price_mm', 0)}
🛒 Amazon: €{alert_data.get('current_price_amazon', 0)}
        """.strip()


class MockEmailNotifier:
    """Mock email notification service."""
    
    def __init__(self):
        self.smtp_host = "smtp.mock.com"
        self.smtp_port = 587
        self.sender_email = "alerts@arbitrage.com"
        self.recipient_email = "user@example.com"
        self.sent_emails = []
    
    async def send_alert_notification(self, subject: str, message: str) -> bool:
        """Mock sending email notification."""
        await asyncio.sleep(0.2)  # Simulate email sending delay
        
        self.sent_emails.append({
            'subject': subject,
            'message': message,
            'recipient': self.recipient_email,
            'timestamp': datetime.utcnow()
        })
        return True
    
    async def send_weekly_report(self, report_data: Dict) -> bool:
        """Mock sending weekly report email."""
        subject = f"Weekly Arbitrage Report - {datetime.utcnow().strftime('%Y-%m-%d')}"
        message = self._format_report_email(report_data)
        return await self.send_alert_notification(subject, message)
    
    def _format_report_email(self, report_data: Dict) -> str:
        """Format report data for email."""
        return f"""
Weekly Arbitrage Report

Total Opportunities: {report_data.get('total_opportunities', 0)}
Total Profit Potential: €{report_data.get('total_profit', 0)}
Average Margin: {report_data.get('avg_margin', 0):.1%}

Top Categories:
{self._format_category_list(report_data.get('top_categories', []))}
        """.strip()
    
    def _format_category_list(self, categories: List[Dict]) -> str:
        """Format category list for email."""
        if not categories:
            return "No data available"
        
        lines = []
        for cat in categories[:5]:  # Top 5
            lines.append(f"- {cat.get('name', 'Unknown')}: {cat.get('count', 0)} opportunities")
        return '\n'.join(lines)


class MockRedisClient:
    """Mock Redis client for testing caching."""
    
    def __init__(self):
        self._data = {}
        self._ttl = {}
    
    async def get(self, key: str) -> Optional[str]:
        """Mock Redis GET operation."""
        if key in self._data:
            # Check TTL
            if key in self._ttl and datetime.utcnow() > self._ttl[key]:
                del self._data[key]
                del self._ttl[key]
                return None
            return self._data[key]
        return None
    
    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Mock Redis SET operation."""
        self._data[key] = value
        if ex:
            self._ttl[key] = datetime.utcnow() + timedelta(seconds=ex)
        return True
    
    async def delete(self, key: str) -> int:
        """Mock Redis DELETE operation."""
        if key in self._data:
            del self._data[key]
            if key in self._ttl:
                del self._ttl[key]
            return 1
        return 0
    
    async def exists(self, key: str) -> bool:
        """Mock Redis EXISTS operation."""
        return key in self._data
    
    async def flushall(self) -> bool:
        """Mock Redis FLUSHALL operation."""
        self._data.clear()
        self._ttl.clear()
        return True


class MockCeleryApp:
    """Mock Celery application for testing background tasks."""
    
    def __init__(self):
        self.tasks = {}
        self.task_results = {}
        self.task_history = []
    
    def task(self, name: Optional[str] = None, **kwargs):
        """Mock task decorator."""
        def decorator(func):
            task_name = name or f"{func.__module__}.{func.__name__}"
            self.tasks[task_name] = func
            
            # Create mock task object
            mock_task = AsyncMock()
            mock_task.delay = AsyncMock(return_value=self._create_mock_result(task_name))
            mock_task.apply_async = AsyncMock(return_value=self._create_mock_result(task_name))
            mock_task.name = task_name
            
            return mock_task
        return decorator
    
    def _create_mock_result(self, task_name: str):
        """Create mock task result."""
        result_id = f"mock-task-{len(self.task_history)}"
        
        mock_result = Mock()
        mock_result.id = result_id
        mock_result.status = "SUCCESS"
        mock_result.result = {"status": "success", "task": task_name}
        mock_result.ready = Mock(return_value=True)
        mock_result.successful = Mock(return_value=True)
        mock_result.get = Mock(return_value=mock_result.result)
        
        self.task_history.append({
            'id': result_id,
            'task': task_name,
            'status': 'SUCCESS',
            'timestamp': datetime.utcnow()
        })
        
        return mock_result
    
    def send_task(self, task_name: str, args=None, kwargs=None):
        """Mock sending task."""
        return self._create_mock_result(task_name)


class MockPrometheusMetrics:
    """Mock Prometheus metrics collector."""
    
    def __init__(self):
        self.counters = {}
        self.gauges = {}
        self.histograms = {}
    
    def Counter(self, name: str, documentation: str, labelnames=None):
        """Mock Prometheus Counter."""
        counter = MockCounter(name, labelnames or [])
        self.counters[name] = counter
        return counter
    
    def Gauge(self, name: str, documentation: str, labelnames=None):
        """Mock Prometheus Gauge."""
        gauge = MockGauge(name, labelnames or [])
        self.gauges[name] = gauge
        return gauge
    
    def Histogram(self, name: str, documentation: str, labelnames=None, buckets=None):
        """Mock Prometheus Histogram."""
        histogram = MockHistogram(name, labelnames or [], buckets or [])
        self.histograms[name] = histogram
        return histogram


class MockCounter:
    """Mock Prometheus Counter metric."""
    
    def __init__(self, name: str, labelnames: List[str]):
        self.name = name
        self.labelnames = labelnames
        self._value = 0
        self._labels = {}
    
    def inc(self, amount: float = 1):
        """Increment counter."""
        self._value += amount
    
    def labels(self, **kwargs):
        """Add labels to counter."""
        label_key = tuple(sorted(kwargs.items()))
        if label_key not in self._labels:
            self._labels[label_key] = MockCounter(f"{self.name}_{label_key}", [])
        return self._labels[label_key]


class MockGauge:
    """Mock Prometheus Gauge metric."""
    
    def __init__(self, name: str, labelnames: List[str]):
        self.name = name
        self.labelnames = labelnames
        self._value = 0
        self._labels = {}
    
    def set(self, value: float):
        """Set gauge value."""
        self._value = value
    
    def inc(self, amount: float = 1):
        """Increment gauge."""
        self._value += amount
    
    def dec(self, amount: float = 1):
        """Decrement gauge."""
        self._value -= amount
    
    def labels(self, **kwargs):
        """Add labels to gauge."""
        label_key = tuple(sorted(kwargs.items()))
        if label_key not in self._labels:
            self._labels[label_key] = MockGauge(f"{self.name}_{label_key}", [])
        return self._labels[label_key]


class MockHistogram:
    """Mock Prometheus Histogram metric."""
    
    def __init__(self, name: str, labelnames: List[str], buckets: List[float]):
        self.name = name
        self.labelnames = labelnames
        self.buckets = buckets
        self._observations = []
        self._labels = {}
    
    def observe(self, amount: float):
        """Observe value in histogram."""
        self._observations.append(amount)
    
    def time(self):
        """Context manager for timing operations."""
        return MockTimer(self)
    
    def labels(self, **kwargs):
        """Add labels to histogram."""
        label_key = tuple(sorted(kwargs.items()))
        if label_key not in self._labels:
            self._labels[label_key] = MockHistogram(f"{self.name}_{label_key}", [], self.buckets)
        return self._labels[label_key]


class MockTimer:
    """Mock timer context manager for histograms."""
    
    def __init__(self, histogram):
        self.histogram = histogram
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.utcnow()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = (datetime.utcnow() - self.start_time).total_seconds()
            self.histogram.observe(duration) 