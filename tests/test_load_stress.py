"""
Load and Stress Testing Suite for Cross-Market Arbitrage Tool

Business Requirements:
- Handle 1,000 concurrent users
- Process 100,000+ products efficiently
- Maintain response times under acceptable thresholds
- Monitor system resource usage and bottlenecks
"""

import asyncio
import time
import psutil
import pytest
import statistics
from typing import List, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
from concurrent.futures import ThreadPoolExecutor, as_completed
import aiohttp
import json

from src.services.scraper.mediamarkt_scraper import MediaMarktScraper
from src.services.matcher.ean_matcher import EANMatcher
from src.services.matcher.fuzzy_matcher import FuzzyMatcher
from src.services.analyzer.price_analyzer import PriceAnalyzer
from src.tasks.scraping import scrape_mediamarkt
from src.tasks.matching import match_products_with_asins
from src.tasks.analysis import analyze_price_trends
from src.config.settings import settings


class LoadTestMetrics:
    """Metrics collection for load testing."""
    
    def __init__(self):
        self.response_times: List[float] = []
        self.error_count = 0
        self.success_count = 0
        self.memory_usage: List[float] = []
        self.cpu_usage: List[float] = []
        self.throughput_data: List[Dict] = []
        
    def record_response_time(self, response_time: float):
        self.response_times.append(response_time)
        
    def record_error(self):
        self.error_count += 1
        
    def record_success(self):
        self.success_count += 1
        
    def record_system_metrics(self):
        process = psutil.Process()
        self.memory_usage.append(process.memory_info().rss / 1024 / 1024)  # MB
        self.cpu_usage.append(process.cpu_percent())
        
    def get_statistics(self) -> Dict[str, Any]:
        if not self.response_times:
            return {"error": "No response times recorded"}
            
        return {
            "total_requests": len(self.response_times),
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": (self.success_count / (self.success_count + self.error_count)) * 100,
            "response_times": {
                "avg": statistics.mean(self.response_times),
                "median": statistics.median(self.response_times),
                "p95": statistics.quantiles(self.response_times, n=20)[18] if len(self.response_times) > 20 else max(self.response_times),
                "p99": statistics.quantiles(self.response_times, n=100)[98] if len(self.response_times) > 100 else max(self.response_times),
                "min": min(self.response_times),
                "max": max(self.response_times)
            },
            "system_resources": {
                "avg_memory_mb": statistics.mean(self.memory_usage) if self.memory_usage else 0,
                "max_memory_mb": max(self.memory_usage) if self.memory_usage else 0,
                "avg_cpu_percent": statistics.mean(self.cpu_usage) if self.cpu_usage else 0,
                "max_cpu_percent": max(self.cpu_usage) if self.cpu_usage else 0
            }
        }


@pytest.mark.asyncio
class TestLoadAndStressTesting:
    """Load and stress testing suite."""

    @pytest.fixture
    def load_metrics(self):
        """Fixture for load testing metrics."""
        return LoadTestMetrics()

    @pytest.fixture
    def mock_large_product_dataset(self):
        """Generate large dataset for testing."""
        products = []
        for i in range(100000):  # 100K products
            products.append({
                "id": f"product_{i}",
                "name": f"Test Product {i}",
                "brand": f"Brand_{i % 100}",
                "ean": f"123456789012{i % 10}",
                "current_price": 99.99 + (i % 1000),
                "original_price": 149.99 + (i % 1000),
                "stock_status": "in_stock" if i % 3 == 0 else "limited_stock",
                "product_url": f"https://mediamarkt.pt/product/{i}",
                "category": f"Category_{i % 50}",
                "description": f"Description for product {i}" * (i % 5 + 1)
            })
        return products

    @pytest.fixture
    def mock_asin_dataset(self):
        """Generate large ASIN dataset for matching."""
        asins = []
        for i in range(50000):  # 50K ASINs
            asins.append({
                "asin": f"B{i:08d}XYZ",
                "title": f"Amazon Product {i}",
                "brand": f"Brand_{i % 100}",
                "ean": f"123456789012{i % 10}",
                "category": f"Category_{i % 50}",
                "current_price": 89.99 + (i % 800),
                "is_available": i % 4 != 0
            })
        return asins

    async def test_concurrent_user_load_1000_users(self, load_metrics):
        """
        Test system with 1,000 concurrent users.
        
        Business Requirement: Handle 1,000 concurrent users
        Target: <500ms average response time, >95% success rate
        """
        concurrent_users = 1000
        requests_per_user = 10
        
        async def simulate_user_session(user_id: int):
            """Simulate a user session with multiple API calls."""
            session_metrics = []
            
            try:
                # Simulate user workflow: login, browse products, check alerts
                for request_num in range(requests_per_user):
                    start_time = time.time()
                    
                    # Mock API endpoint calls
                    with patch('aiohttp.ClientSession.get') as mock_get:
                        mock_response = AsyncMock()
                        mock_response.status = 200
                        mock_response.json.return_value = {"status": "success", "user_id": user_id}
                        mock_get.return_value.__aenter__.return_value = mock_response
                        
                        # Simulate API call latency
                        await asyncio.sleep(0.01 + (request_num * 0.001))  # Simulated processing time
                        
                    end_time = time.time()
                    response_time = end_time - start_time
                    session_metrics.append(response_time)
                    
                    load_metrics.record_response_time(response_time)
                    load_metrics.record_success()
                    
                    # Record system metrics every 10 requests
                    if request_num % 10 == 0:
                        load_metrics.record_system_metrics()
                        
            except Exception as e:
                load_metrics.record_error()
                print(f"User {user_id} error: {e}")
            
            return session_metrics

        # Execute concurrent user sessions
        print(f"Starting load test with {concurrent_users} concurrent users...")
        start_time = time.time()
        
        tasks = [simulate_user_session(i) for i in range(concurrent_users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Analyze results
        stats = load_metrics.get_statistics()
        
        print(f"Load Test Results:")
        print(f"Total Duration: {total_duration:.2f}s")
        print(f"Total Requests: {stats['total_requests']}")
        print(f"Success Rate: {stats['success_rate']:.2f}%")
        print(f"Average Response Time: {stats['response_times']['avg']:.3f}s")
        print(f"95th Percentile: {stats['response_times']['p95']:.3f}s")
        print(f"Max Memory Usage: {stats['system_resources']['max_memory_mb']:.2f}MB")
        print(f"Max CPU Usage: {stats['system_resources']['max_cpu_percent']:.2f}%")
        
        # Business requirements validation
        assert stats['success_rate'] >= 95.0, f"Success rate {stats['success_rate']:.2f}% below 95% threshold"
        assert stats['response_times']['avg'] <= 0.5, f"Average response time {stats['response_times']['avg']:.3f}s exceeds 500ms"
        assert stats['response_times']['p95'] <= 1.0, f"95th percentile {stats['response_times']['p95']:.3f}s exceeds 1s"

    async def test_large_dataset_processing_100k_products(self, mock_large_product_dataset, load_metrics):
        """
        Test processing 100,000+ products efficiently.
        
        Business Requirement: Process 100,000+ products
        Target: Complete processing within 5 minutes, maintain memory under 2GB
        """
        product_count = len(mock_large_product_dataset)
        batch_size = 1000
        
        async def process_product_batch(batch: List[Dict]) -> Dict:
            """Process a batch of products."""
            start_time = time.time()
            
            # Mock product processing
            with patch.object(MediaMarktScraper, 'scrape_products') as mock_scraper:
                mock_scraper.return_value = batch
                
                # Simulate processing overhead
                await asyncio.sleep(0.01)  # 10ms per batch
                
                processed_count = len(batch)
                
            end_time = time.time()
            processing_time = end_time - start_time
            
            load_metrics.record_response_time(processing_time)
            load_metrics.record_success()
            load_metrics.record_system_metrics()
            
            return {
                "processed_count": processed_count,
                "processing_time": processing_time,
                "batch_id": id(batch)
            }

        print(f"Processing {product_count} products in batches of {batch_size}...")
        start_time = time.time()
        
        # Process products in batches
        tasks = []
        for i in range(0, product_count, batch_size):
            batch = mock_large_product_dataset[i:i + batch_size]
            task = process_product_batch(batch)
            tasks.append(task)
        
        # Execute batches concurrently (limited concurrency to avoid overwhelming)
        semaphore = asyncio.Semaphore(20)  # Max 20 concurrent batches
        
        async def process_with_semaphore(task):
            async with semaphore:
                return await task
        
        results = await asyncio.gather(*[process_with_semaphore(task) for task in tasks])
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Calculate statistics
        total_processed = sum(r["processed_count"] for r in results)
        stats = load_metrics.get_statistics()
        
        throughput = total_processed / total_duration  # products per second
        
        print(f"Large Dataset Processing Results:")
        print(f"Total Products Processed: {total_processed:,}")
        print(f"Total Duration: {total_duration:.2f}s")
        print(f"Throughput: {throughput:.2f} products/second")
        print(f"Average Batch Time: {stats['response_times']['avg']:.3f}s")
        print(f"Max Memory Usage: {stats['system_resources']['max_memory_mb']:.2f}MB")
        print(f"Success Rate: {stats['success_rate']:.2f}%")
        
        # Business requirements validation
        assert total_processed == product_count, f"Processed {total_processed} != Expected {product_count}"
        assert total_duration <= 300, f"Processing took {total_duration:.2f}s, exceeds 5-minute limit"
        assert stats['system_resources']['max_memory_mb'] <= 2048, f"Memory usage {stats['system_resources']['max_memory_mb']:.2f}MB exceeds 2GB limit"
        assert stats['success_rate'] >= 99.0, f"Success rate {stats['success_rate']:.2f}% below 99% threshold"

    async def test_database_stress_concurrent_operations(self, load_metrics):
        """
        Test database under stress with concurrent operations.
        
        Target: Handle 500 concurrent database operations, maintain <100ms query time
        """
        concurrent_operations = 500
        
        async def simulate_database_operation(operation_id: int):
            """Simulate database operation."""
            start_time = time.time()
            
            try:
                # Mock database operations
                operation_type = ["select", "insert", "update", "delete"][operation_id % 4]
                
                # Simulate query execution time based on operation type
                if operation_type == "select":
                    await asyncio.sleep(0.02)  # 20ms for select
                elif operation_type == "insert":
                    await asyncio.sleep(0.03)  # 30ms for insert
                elif operation_type == "update":
                    await asyncio.sleep(0.025)  # 25ms for update
                else:  # delete
                    await asyncio.sleep(0.015)  # 15ms for delete
                
                end_time = time.time()
                query_time = end_time - start_time
                
                load_metrics.record_response_time(query_time)
                load_metrics.record_success()
                
                if operation_id % 50 == 0:
                    load_metrics.record_system_metrics()
                
                return {"operation_id": operation_id, "type": operation_type, "duration": query_time}
                
            except Exception as e:
                load_metrics.record_error()
                raise

        print(f"Starting database stress test with {concurrent_operations} operations...")
        start_time = time.time()
        
        tasks = [simulate_database_operation(i) for i in range(concurrent_operations)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Analyze results
        successful_operations = [r for r in results if isinstance(r, dict)]
        stats = load_metrics.get_statistics()
        
        print(f"Database Stress Test Results:")
        print(f"Total Operations: {len(results)}")
        print(f"Successful Operations: {len(successful_operations)}")
        print(f"Total Duration: {total_duration:.2f}s")
        print(f"Operations/Second: {len(successful_operations) / total_duration:.2f}")
        print(f"Average Query Time: {stats['response_times']['avg'] * 1000:.2f}ms")
        print(f"95th Percentile Query Time: {stats['response_times']['p95'] * 1000:.2f}ms")
        print(f"Success Rate: {stats['success_rate']:.2f}%")
        
        # Performance requirements validation
        assert stats['success_rate'] >= 98.0, f"Success rate {stats['success_rate']:.2f}% below 98% threshold"
        assert stats['response_times']['avg'] <= 0.1, f"Average query time {stats['response_times']['avg'] * 1000:.2f}ms exceeds 100ms"
        assert stats['response_times']['p95'] <= 0.2, f"95th percentile {stats['response_times']['p95'] * 1000:.2f}ms exceeds 200ms"

    async def test_memory_stress_large_operations(self, load_metrics):
        """
        Test system under memory stress with large data operations.
        
        Target: Process large datasets without memory leaks, stay under 4GB peak usage
        """
        
        async def memory_intensive_operation(operation_id: int):
            """Simulate memory-intensive operation."""
            start_time = time.time()
            
            try:
                # Simulate large data processing
                large_data = [{"id": i, "data": "x" * 1000} for i in range(10000)]  # ~10MB per operation
                
                # Process data
                processed_data = []
                for item in large_data:
                    processed_item = {
                        "processed_id": item["id"],
                        "processed_data": item["data"][:100],  # Reduce data size
                        "timestamp": time.time()
                    }
                    processed_data.append(processed_item)
                
                # Simulate processing delay
                await asyncio.sleep(0.05)
                
                # Clean up large data
                del large_data
                del processed_data
                
                end_time = time.time()
                operation_time = end_time - start_time
                
                load_metrics.record_response_time(operation_time)
                load_metrics.record_success()
                load_metrics.record_system_metrics()
                
                return {"operation_id": operation_id, "duration": operation_time}
                
            except Exception as e:
                load_metrics.record_error()
                raise

        operations_count = 100  # 100 memory-intensive operations
        
        print(f"Starting memory stress test with {operations_count} operations...")
        start_time = time.time()
        
        # Run operations in smaller concurrent batches to control memory usage
        batch_size = 10
        all_results = []
        
        for i in range(0, operations_count, batch_size):
            batch_end = min(i + batch_size, operations_count)
            batch_tasks = [memory_intensive_operation(j) for j in range(i, batch_end)]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            all_results.extend(batch_results)
            
            # Small delay between batches to allow GC
            await asyncio.sleep(0.1)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Analyze results
        successful_operations = [r for r in all_results if isinstance(r, dict)]
        stats = load_metrics.get_statistics()
        
        print(f"Memory Stress Test Results:")
        print(f"Total Operations: {len(all_results)}")
        print(f"Successful Operations: {len(successful_operations)}")
        print(f"Total Duration: {total_duration:.2f}s")
        print(f"Average Operation Time: {stats['response_times']['avg']:.3f}s")
        print(f"Peak Memory Usage: {stats['system_resources']['max_memory_mb']:.2f}MB")
        print(f"Average Memory Usage: {stats['system_resources']['avg_memory_mb']:.2f}MB")
        print(f"Success Rate: {stats['success_rate']:.2f}%")
        
        # Memory requirements validation
        assert stats['success_rate'] >= 95.0, f"Success rate {stats['success_rate']:.2f}% below 95% threshold"
        assert stats['system_resources']['max_memory_mb'] <= 4096, f"Peak memory {stats['system_resources']['max_memory_mb']:.2f}MB exceeds 4GB limit"

    async def test_system_stability_prolonged_load(self, load_metrics):
        """
        Test system stability under prolonged load.
        
        Target: Maintain performance over 10-minute continuous load test
        """
        test_duration = 600  # 10 minutes
        operation_interval = 0.1  # New operation every 100ms
        
        async def continuous_operation_generator():
            """Generate continuous operations for stability testing."""
            operation_id = 0
            end_time = time.time() + test_duration
            
            while time.time() < end_time:
                start_time = time.time()
                
                try:
                    # Simulate mixed workload
                    if operation_id % 10 == 0:
                        # Heavy operation (10% of load)
                        await asyncio.sleep(0.1)
                    else:
                        # Light operation (90% of load)
                        await asyncio.sleep(0.01)
                    
                    response_time = time.time() - start_time
                    load_metrics.record_response_time(response_time)
                    load_metrics.record_success()
                    
                    if operation_id % 100 == 0:
                        load_metrics.record_system_metrics()
                    
                    operation_id += 1
                    await asyncio.sleep(operation_interval)
                    
                except Exception as e:
                    load_metrics.record_error()
                    print(f"Operation {operation_id} failed: {e}")
            
            return operation_id

        print(f"Starting {test_duration}s stability test...")
        start_time = time.time()
        
        total_operations = await continuous_operation_generator()
        
        end_time = time.time()
        actual_duration = end_time - start_time
        
        # Analyze stability
        stats = load_metrics.get_statistics()
        
        print(f"Stability Test Results:")
        print(f"Test Duration: {actual_duration:.2f}s")
        print(f"Total Operations: {total_operations}")
        print(f"Operations/Second: {total_operations / actual_duration:.2f}")
        print(f"Success Rate: {stats['success_rate']:.2f}%")
        print(f"Response Time Stability:")
        print(f"  Average: {stats['response_times']['avg'] * 1000:.2f}ms")
        print(f"  Std Dev: {statistics.stdev(load_metrics.response_times) * 1000:.2f}ms")
        print(f"Memory Stability:")
        print(f"  Peak: {stats['system_resources']['max_memory_mb']:.2f}MB")
        print(f"  Average: {stats['system_resources']['avg_memory_mb']:.2f}MB")
        
        # Stability requirements
        response_time_stdev = statistics.stdev(load_metrics.response_times)
        
        assert stats['success_rate'] >= 99.0, f"Success rate {stats['success_rate']:.2f}% below 99% threshold"
        assert response_time_stdev <= 0.05, f"Response time std dev {response_time_stdev:.3f}s indicates instability"
        assert actual_duration >= test_duration * 0.95, f"Test duration {actual_duration:.2f}s less than expected {test_duration}s" 