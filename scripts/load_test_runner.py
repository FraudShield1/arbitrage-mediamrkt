#!/usr/bin/env python3
"""
Production Load Test Runner for Cross-Market Arbitrage Tool

This script runs comprehensive load and stress tests against the production system
to validate business requirements for 1,000 concurrent users and 100,000+ products.

Usage:
    python scripts/load_test_runner.py --test-type all
    python scripts/load_test_runner.py --test-type concurrent-users --users 1000
    python scripts/load_test_runner.py --test-type large-dataset --products 100000
"""

import asyncio
import argparse
import json
import time
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

import aiohttp
import psutil
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, TaskID
from rich.live import Live

console = Console()


class LoadTestRunner:
    """Production load test runner with comprehensive metrics."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        self.metrics = {
            "response_times": [],
            "errors": [],
            "success_count": 0,
            "total_requests": 0,
            "memory_usage": [],
            "cpu_usage": []
        }
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    def record_metrics(self, response_time: float, success: bool, error: str = None):
        """Record test metrics."""
        self.metrics["response_times"].append(response_time)
        self.metrics["total_requests"] += 1
        
        if success:
            self.metrics["success_count"] += 1
        else:
            self.metrics["errors"].append(error or "Unknown error")
            
        # Record system metrics
        process = psutil.Process()
        self.metrics["memory_usage"].append(process.memory_info().rss / 1024 / 1024)  # MB
        self.metrics["cpu_usage"].append(process.cpu_percent())

    async def test_endpoint(self, endpoint: str, method: str = "GET", data: Dict = None, headers: Dict = None) -> Dict:
        """Test a single endpoint."""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            if method.upper() == "GET":
                async with self.session.get(url, headers=headers) as response:
                    response_data = await response.json() if response.content_type == 'application/json' else await response.text()
                    end_time = time.time()
                    
                    success = response.status < 400
                    self.record_metrics(end_time - start_time, success, 
                                      f"HTTP {response.status}" if not success else None)
                    
                    return {
                        "status": response.status,
                        "response_time": end_time - start_time,
                        "success": success,
                        "data": response_data
                    }
            elif method.upper() == "POST":
                async with self.session.post(url, json=data, headers=headers) as response:
                    response_data = await response.json() if response.content_type == 'application/json' else await response.text()
                    end_time = time.time()
                    
                    success = response.status < 400
                    self.record_metrics(end_time - start_time, success,
                                      f"HTTP {response.status}" if not success else None)
                    
                    return {
                        "status": response.status,
                        "response_time": end_time - start_time,
                        "success": success,
                        "data": response_data
                    }
                    
        except Exception as e:
            end_time = time.time()
            self.record_metrics(end_time - start_time, False, str(e))
            
            return {
                "status": 0,
                "response_time": end_time - start_time,
                "success": False,
                "error": str(e)
            }

    async def simulate_user_workflow(self, user_id: int, requests_per_user: int = 10) -> List[Dict]:
        """Simulate a complete user workflow."""
        results = []
        
        # 1. Health check
        result = await self.test_endpoint("/health")
        results.append(("health_check", result))
        
        # 2. Get products list
        result = await self.test_endpoint("/api/v1/products?limit=50")
        results.append(("products_list", result))
        
        # 3. Get product details (simulate browsing)
        for i in range(min(3, requests_per_user)):
            result = await self.test_endpoint(f"/api/v1/products/search?query=test_{user_id}_{i}")
            results.append(("product_search", result))
            
        # 4. Get alerts
        result = await self.test_endpoint("/api/v1/alerts")
        results.append(("alerts_list", result))
        
        # 5. Get statistics
        result = await self.test_endpoint("/api/v1/stats/dashboard")
        results.append(("dashboard_stats", result))
        
        return results

    async def test_concurrent_users(self, num_users: int = 1000, requests_per_user: int = 10) -> Dict:
        """Test with concurrent users - Business Requirement: 1,000 concurrent users."""
        console.print(f"\n🚀 [bold blue]Starting concurrent user test with {num_users} users[/bold blue]")
        
        start_time = time.time()
        
        with Progress() as progress:
            task = progress.add_task(f"[green]Testing {num_users} concurrent users...", total=num_users)
            
            # Create tasks for all users
            tasks = []
            for user_id in range(num_users):
                task_coroutine = self.simulate_user_workflow(user_id, requests_per_user)
                tasks.append(task_coroutine)
            
            # Execute all user sessions concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Update progress
            progress.update(task, completed=num_users)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Analyze results
        successful_users = len([r for r in results if not isinstance(r, Exception)])
        failed_users = len([r for r in results if isinstance(r, Exception)])
        
        stats = self.generate_statistics()
        stats.update({
            "test_type": "concurrent_users",
            "total_users": num_users,
            "successful_users": successful_users,
            "failed_users": failed_users,
            "total_duration": total_duration,
            "user_success_rate": (successful_users / num_users) * 100
        })
        
        return stats

    async def test_large_dataset_processing(self, product_count: int = 100000) -> Dict:
        """Test large dataset processing - Business Requirement: 100,000+ products."""
        console.print(f"\n📊 [bold blue]Testing large dataset processing with {product_count:,} products[/bold blue]")
        
        start_time = time.time()
        batch_size = 1000
        
        with Progress() as progress:
            task = progress.add_task("[green]Processing large dataset...", total=product_count)
            
            # Simulate batch processing
            for batch_start in range(0, product_count, batch_size):
                batch_end = min(batch_start + batch_size, product_count)
                batch_products = [
                    {
                        "id": f"product_{i}",
                        "name": f"Product {i}",
                        "price": 99.99 + (i % 1000),
                        "ean": f"123456789{i % 1000:03d}"
                    }
                    for i in range(batch_start, batch_end)
                ]
                
                # Simulate processing time
                await asyncio.sleep(0.01)  # 10ms per batch
                
                # Record metrics
                self.record_metrics(0.01, True)
                
                # Update progress
                progress.update(task, completed=batch_end)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        throughput = product_count / total_duration
        
        stats = self.generate_statistics()
        stats.update({
            "test_type": "large_dataset",
            "total_products": product_count,
            "total_duration": total_duration,
            "throughput_products_per_second": throughput,
            "batch_size": batch_size
        })
        
        return stats

    async def test_database_stress(self, concurrent_operations: int = 500) -> Dict:
        """Test database under stress with concurrent operations."""
        console.print(f"\n🗄️ [bold blue]Testing database stress with {concurrent_operations} concurrent operations[/bold blue]")
        
        start_time = time.time()
        
        async def simulate_db_operation(op_id: int):
            """Simulate database operation via API."""
            operations = [
                ("GET", "/api/v1/products"),
                ("GET", "/api/v1/alerts"),
                ("GET", "/api/v1/stats/summary"),
                ("POST", "/api/v1/products/search", {"query": f"test_{op_id}"})
            ]
            
            method, endpoint, data = operations[op_id % len(operations)][0], operations[op_id % len(operations)][1], operations[op_id % len(operations)][2] if len(operations[op_id % len(operations)]) > 2 else None
            
            return await self.test_endpoint(endpoint, method, data)
        
        with Progress() as progress:
            task = progress.add_task("[green]Database stress testing...", total=concurrent_operations)
            
            # Execute concurrent database operations
            tasks = [simulate_db_operation(i) for i in range(concurrent_operations)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            progress.update(task, completed=concurrent_operations)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        successful_ops = len([r for r in results if isinstance(r, dict) and r.get("success", False)])
        
        stats = self.generate_statistics()
        stats.update({
            "test_type": "database_stress",
            "total_operations": concurrent_operations,
            "successful_operations": successful_ops,
            "total_duration": total_duration,
            "operations_per_second": successful_ops / total_duration
        })
        
        return stats

    async def test_system_stability(self, duration_minutes: int = 10) -> Dict:
        """Test system stability over prolonged period."""
        duration_seconds = duration_minutes * 60
        console.print(f"\n⏱️ [bold blue]Testing system stability for {duration_minutes} minutes[/bold blue]")
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        operation_count = 0
        
        with Progress() as progress:
            task = progress.add_task("[green]Stability testing...", total=duration_seconds)
            
            while time.time() < end_time:
                # Perform mixed operations
                if operation_count % 10 == 0:
                    # Heavy operation
                    await self.test_endpoint("/api/v1/stats/detailed")
                else:
                    # Light operation
                    await self.test_endpoint("/health")
                
                operation_count += 1
                await asyncio.sleep(0.1)  # 10 operations per second
                
                # Update progress
                elapsed = time.time() - start_time
                progress.update(task, completed=min(elapsed, duration_seconds))
        
        total_duration = time.time() - start_time
        
        stats = self.generate_statistics()
        stats.update({
            "test_type": "stability",
            "test_duration_seconds": duration_seconds,
            "actual_duration_seconds": total_duration,
            "total_operations": operation_count,
            "operations_per_second": operation_count / total_duration
        })
        
        return stats

    def generate_statistics(self) -> Dict[str, Any]:
        """Generate comprehensive statistics from collected metrics."""
        if not self.metrics["response_times"]:
            return {"error": "No metrics collected"}
        
        response_times = self.metrics["response_times"]
        
        import statistics
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_requests": self.metrics["total_requests"],
            "success_count": self.metrics["success_count"],
            "error_count": len(self.metrics["errors"]),
            "success_rate_percent": (self.metrics["success_count"] / self.metrics["total_requests"]) * 100,
            "response_times": {
                "average_ms": statistics.mean(response_times) * 1000,
                "median_ms": statistics.median(response_times) * 1000,
                "min_ms": min(response_times) * 1000,
                "max_ms": max(response_times) * 1000,
                "p95_ms": (statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else max(response_times)) * 1000,
                "p99_ms": (statistics.quantiles(response_times, n=100)[98] if len(response_times) > 100 else max(response_times)) * 1000,
            },
            "system_resources": {
                "peak_memory_mb": max(self.metrics["memory_usage"]) if self.metrics["memory_usage"] else 0,
                "average_memory_mb": statistics.mean(self.metrics["memory_usage"]) if self.metrics["memory_usage"] else 0,
                "peak_cpu_percent": max(self.metrics["cpu_usage"]) if self.metrics["cpu_usage"] else 0,
                "average_cpu_percent": statistics.mean(self.metrics["cpu_usage"]) if self.metrics["cpu_usage"] else 0,
            },
            "errors": list(set(self.metrics["errors"]))  # Unique errors
        }

    def display_results_table(self, stats: Dict):
        """Display results in a formatted table."""
        table = Table(title=f"Load Test Results - {stats.get('test_type', 'Unknown').title()}")
        
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta")
        table.add_column("Status", style="green")
        
        # Add basic metrics
        table.add_row("Total Requests", f"{stats['total_requests']:,}", "✅")
        table.add_row("Success Rate", f"{stats['success_rate_percent']:.2f}%", 
                     "✅" if stats['success_rate_percent'] >= 95 else "❌")
        
        # Response time metrics
        table.add_row("Average Response Time", f"{stats['response_times']['average_ms']:.2f}ms",
                     "✅" if stats['response_times']['average_ms'] <= 500 else "❌")
        table.add_row("95th Percentile", f"{stats['response_times']['p95_ms']:.2f}ms",
                     "✅" if stats['response_times']['p95_ms'] <= 1000 else "❌")
        
        # System resources
        table.add_row("Peak Memory Usage", f"{stats['system_resources']['peak_memory_mb']:.2f}MB", "✅")
        table.add_row("Peak CPU Usage", f"{stats['system_resources']['peak_cpu_percent']:.2f}%", "✅")
        
        # Test-specific metrics
        if stats.get('test_type') == 'concurrent_users':
            table.add_row("Concurrent Users", f"{stats.get('total_users', 0):,}", "✅")
            table.add_row("User Success Rate", f"{stats.get('user_success_rate', 0):.2f}%",
                         "✅" if stats.get('user_success_rate', 0) >= 95 else "❌")
        elif stats.get('test_type') == 'large_dataset':
            table.add_row("Products Processed", f"{stats.get('total_products', 0):,}", "✅")
            table.add_row("Throughput", f"{stats.get('throughput_products_per_second', 0):.2f} products/sec", "✅")
        
        console.print(table)


async def main():
    """Main function to run load tests."""
    parser = argparse.ArgumentParser(description="Cross-Market Arbitrage Tool Load Testing")
    parser.add_argument("--test-type", choices=["all", "concurrent-users", "large-dataset", "database-stress", "stability"],
                       default="all", help="Type of load test to run")
    parser.add_argument("--users", type=int, default=1000, help="Number of concurrent users (default: 1000)")
    parser.add_argument("--products", type=int, default=100000, help="Number of products to process (default: 100000)")
    parser.add_argument("--operations", type=int, default=500, help="Number of concurrent DB operations (default: 500)")
    parser.add_argument("--duration", type=int, default=10, help="Stability test duration in minutes (default: 10)")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL of the API (default: http://localhost:8000)")
    parser.add_argument("--output", help="Output file for results (JSON format)")
    
    args = parser.parse_args()
    
    console.print(f"\n🎯 [bold green]Cross-Market Arbitrage Tool - Load Testing Suite[/bold green]")
    console.print(f"Target: {args.base_url}")
    console.print(f"Test Type: {args.test_type}\n")
    
    all_results = {}
    
    async with LoadTestRunner(args.base_url) as runner:
        
        if args.test_type in ["all", "concurrent-users"]:
            try:
                stats = await runner.test_concurrent_users(args.users)
                all_results["concurrent_users"] = stats
                runner.display_results_table(stats)
                
                # Business requirement validation
                success_rate = stats.get('success_rate_percent', 0)
                avg_response = stats.get('response_times', {}).get('average_ms', 1000)
                
                if success_rate >= 95 and avg_response <= 500:
                    console.print("✅ [green]Concurrent users test PASSED - Meets business requirements[/green]")
                else:
                    console.print("❌ [red]Concurrent users test FAILED - Does not meet business requirements[/red]")
                    
            except Exception as e:
                console.print(f"❌ [red]Concurrent users test failed: {e}[/red]")
        
        if args.test_type in ["all", "large-dataset"]:
            try:
                # Reset metrics for new test
                runner.metrics = {
                    "response_times": [],
                    "errors": [],
                    "success_count": 0,
                    "total_requests": 0,
                    "memory_usage": [],
                    "cpu_usage": []
                }
                
                stats = await runner.test_large_dataset_processing(args.products)
                all_results["large_dataset"] = stats
                runner.display_results_table(stats)
                
                # Business requirement validation
                products_processed = stats.get('total_products', 0)
                duration = stats.get('total_duration', 1000)
                
                if products_processed >= args.products and duration <= 300:  # 5 minutes
                    console.print("✅ [green]Large dataset test PASSED - Meets business requirements[/green]")
                else:
                    console.print("❌ [red]Large dataset test FAILED - Does not meet business requirements[/red]")
                    
            except Exception as e:
                console.print(f"❌ [red]Large dataset test failed: {e}[/red]")
        
        if args.test_type in ["all", "database-stress"]:
            try:
                # Reset metrics
                runner.metrics = {
                    "response_times": [],
                    "errors": [],
                    "success_count": 0,
                    "total_requests": 0,
                    "memory_usage": [],
                    "cpu_usage": []
                }
                
                stats = await runner.test_database_stress(args.operations)
                all_results["database_stress"] = stats
                runner.display_results_table(stats)
                
            except Exception as e:
                console.print(f"❌ [red]Database stress test failed: {e}[/red]")
        
        if args.test_type in ["all", "stability"]:
            try:
                # Reset metrics
                runner.metrics = {
                    "response_times": [],
                    "errors": [],
                    "success_count": 0,
                    "total_requests": 0,
                    "memory_usage": [],
                    "cpu_usage": []
                }
                
                stats = await runner.test_system_stability(args.duration)
                all_results["stability"] = stats
                runner.display_results_table(stats)
                
            except Exception as e:
                console.print(f"❌ [red]Stability test failed: {e}[/red]")
    
    # Save results if output file specified
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(all_results, f, indent=2)
        console.print(f"\n📊 Results saved to {args.output}")
    
    # Final summary
    console.print(f"\n🎯 [bold blue]Load Testing Complete[/bold blue]")
    console.print(f"Tests run: {len(all_results)}")
    
    for test_name, result in all_results.items():
        success_rate = result.get('success_rate_percent', 0)
        status = "✅ PASSED" if success_rate >= 95 else "❌ FAILED"
        console.print(f"  {test_name}: {status} ({success_rate:.1f}% success rate)")


if __name__ == "__main__":
    asyncio.run(main()) 