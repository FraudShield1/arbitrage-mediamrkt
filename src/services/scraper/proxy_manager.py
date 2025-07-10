"""
Proxy Management System for MediaMarkt scraper.

Handles proxy rotation, health checking, and IP ban detection/recovery.
"""

import asyncio
import aiohttp
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import time
import random
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ProxyStatus(Enum):
    """Proxy status enumeration."""
    ACTIVE = "active"
    FAILED = "failed"
    BANNED = "banned"
    ROTATING = "rotating"


@dataclass
class ProxyInfo:
    """Proxy information container."""
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    status: ProxyStatus = ProxyStatus.ACTIVE
    last_used: Optional[datetime] = None
    failure_count: int = 0
    ban_detected_at: Optional[datetime] = None
    success_count: int = 0
    response_time: Optional[float] = None

    @property
    def url(self) -> str:
        """Get proxy URL."""
        if self.username and self.password:
            return f"http://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"http://{self.host}:{self.port}"

    @property
    def is_available(self) -> bool:
        """Check if proxy is available for use."""
        if self.status == ProxyStatus.BANNED:
            # Check if ban cooldown period has passed (24 hours)
            if self.ban_detected_at:
                return datetime.now() - self.ban_detected_at > timedelta(hours=24)
        return self.status in [ProxyStatus.ACTIVE, ProxyStatus.ROTATING]

    def mark_success(self, response_time: float):
        """Mark proxy as successful."""
        self.status = ProxyStatus.ACTIVE
        self.last_used = datetime.now()
        self.success_count += 1
        self.response_time = response_time
        self.failure_count = 0  # Reset failure count on success

    def mark_failure(self):
        """Mark proxy as failed."""
        self.failure_count += 1
        self.last_used = datetime.now()
        
        if self.failure_count >= 3:
            self.status = ProxyStatus.FAILED
        
    def mark_banned(self):
        """Mark proxy as banned."""
        self.status = ProxyStatus.BANNED
        self.ban_detected_at = datetime.now()
        self.failure_count += 1


class ProxyManager:
    """
    Manages proxy rotation, health checking, and ban detection.
    """

    def __init__(self, proxies: List[Dict[str, Any]], max_failures: int = 3):
        """
        Initialize proxy manager.
        
        Args:
            proxies: List of proxy configurations
            max_failures: Maximum failures before marking proxy as failed
        """
        self.proxies = [ProxyInfo(**proxy) for proxy in proxies]
        self.max_failures = max_failures
        self.current_proxy_index = 0
        self._lock = asyncio.Lock()
        
        # Health check settings
        self.health_check_url = "https://httpbin.org/ip"
        self.health_check_timeout = 10
        self.health_check_interval = 300  # 5 minutes
        
        # Ban detection patterns
        self.ban_indicators = [
            "access denied",
            "blocked",
            "forbidden",
            "rate limit",
            "too many requests",
            "captcha",
            "security check"
        ]

    async def get_proxy(self) -> Optional[ProxyInfo]:
        """
        Get next available proxy with rotation.
        
        Returns:
            ProxyInfo or None if no proxies available
        """
        async with self._lock:
            available_proxies = [p for p in self.proxies if p.is_available]
            
            if not available_proxies:
                logger.warning("No available proxies found")
                return None
            
            # Sort by success rate and response time
            available_proxies.sort(
                key=lambda p: (p.success_count / max(p.success_count + p.failure_count, 1), 
                              -(p.response_time or 0))
            )
            
            # Use weighted random selection favoring better proxies
            weights = [max(1, p.success_count - p.failure_count) for p in available_proxies]
            proxy = random.choices(available_proxies, weights=weights)[0]
            
            proxy.status = ProxyStatus.ROTATING
            return proxy

    async def report_success(self, proxy: ProxyInfo, response_time: float):
        """
        Report successful proxy usage.
        
        Args:
            proxy: Proxy that was used successfully
            response_time: Response time in seconds
        """
        async with self._lock:
            proxy.mark_success(response_time)
            logger.debug(f"Proxy {proxy.host}:{proxy.port} reported success")

    async def report_failure(self, proxy: ProxyInfo, error: Exception):
        """
        Report proxy failure.
        
        Args:
            proxy: Proxy that failed
            error: Exception that occurred
        """
        async with self._lock:
            error_str = str(error).lower()
            
            # Check for ban indicators
            if any(indicator in error_str for indicator in self.ban_indicators):
                proxy.mark_banned()
                logger.warning(f"Proxy {proxy.host}:{proxy.port} appears to be banned: {error}")
            else:
                proxy.mark_failure()
                logger.warning(f"Proxy {proxy.host}:{proxy.port} failed: {error}")

    async def health_check(self, proxy: ProxyInfo) -> bool:
        """
        Perform health check on a proxy.
        
        Args:
            proxy: Proxy to check
            
        Returns:
            True if proxy is healthy
        """
        try:
            start_time = time.time()
            
            connector = aiohttp.TCPConnector()
            timeout = aiohttp.ClientTimeout(total=self.health_check_timeout)
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            ) as session:
                async with session.get(
                    self.health_check_url,
                    proxy=proxy.url
                ) as response:
                    response_time = time.time() - start_time
                    
                    if response.status == 200:
                        await self.report_success(proxy, response_time)
                        return True
                    else:
                        await self.report_failure(proxy, Exception(f"HTTP {response.status}"))
                        return False
                        
        except Exception as e:
            await self.report_failure(proxy, e)
            return False

    async def health_check_all(self):
        """Perform health check on all proxies."""
        tasks = []
        for proxy in self.proxies:
            if proxy.status != ProxyStatus.BANNED:
                tasks.append(self.health_check(proxy))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            healthy_count = sum(1 for result in results if result is True)
            logger.info(f"Health check completed: {healthy_count}/{len(tasks)} proxies healthy")

    async def start_health_monitoring(self):
        """Start periodic health monitoring."""
        while True:
            try:
                await self.health_check_all()
                await asyncio.sleep(self.health_check_interval)
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error

    def get_proxy_stats(self) -> Dict[str, Any]:
        """
        Get proxy statistics.
        
        Returns:
            Dictionary with proxy statistics
        """
        total_proxies = len(self.proxies)
        active_proxies = len([p for p in self.proxies if p.status == ProxyStatus.ACTIVE])
        banned_proxies = len([p for p in self.proxies if p.status == ProxyStatus.BANNED])
        failed_proxies = len([p for p in self.proxies if p.status == ProxyStatus.FAILED])
        
        avg_response_time = None
        if self.proxies:
            response_times = [p.response_time for p in self.proxies if p.response_time]
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
        
        return {
            "total_proxies": total_proxies,
            "active_proxies": active_proxies,
            "banned_proxies": banned_proxies,
            "failed_proxies": failed_proxies,
            "availability_rate": active_proxies / total_proxies if total_proxies > 0 else 0,
            "average_response_time": avg_response_time
        }

    async def reset_failed_proxies(self):
        """Reset failed proxies after cooldown period."""
        async with self._lock:
            for proxy in self.proxies:
                if (proxy.status == ProxyStatus.FAILED and 
                    proxy.last_used and 
                    datetime.now() - proxy.last_used > timedelta(hours=1)):
                    proxy.status = ProxyStatus.ACTIVE
                    proxy.failure_count = 0
                    logger.info(f"Reset failed proxy {proxy.host}:{proxy.port}")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        pass 