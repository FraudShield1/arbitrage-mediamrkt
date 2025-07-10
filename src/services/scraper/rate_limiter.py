"""
Rate Limiting Service for web scraping.

Implements configurable delays, request throttling, and exponential backoff.
"""

import asyncio
import time
import random
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


@dataclass
class RateLimitRule:
    """Rate limiting rule configuration."""
    max_requests: int  # Maximum requests per time window
    time_window: int   # Time window in seconds
    delay_min: float   # Minimum delay between requests
    delay_max: float   # Maximum delay between requests
    burst_limit: int   # Maximum burst requests allowed


class ExponentialBackoff:
    """Exponential backoff handler."""
    
    def __init__(self, base_delay: float = 1.0, max_delay: float = 300.0, multiplier: float = 2.0):
        """
        Initialize exponential backoff.
        
        Args:
            base_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            multiplier: Backoff multiplier
        """
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.current_delay = base_delay
        self.failure_count = 0

    def get_delay(self) -> float:
        """Get current delay with jitter."""
        # Add jitter (±25% of current delay)
        jitter = random.uniform(-0.25, 0.25) * self.current_delay
        return max(0, self.current_delay + jitter)

    def on_failure(self) -> float:
        """Handle failure and return next delay."""
        self.failure_count += 1
        self.current_delay = min(
            self.max_delay,
            self.base_delay * (self.multiplier ** self.failure_count)
        )
        delay = self.get_delay()
        logger.warning(f"Failure #{self.failure_count}, backing off for {delay:.2f}s")
        return delay

    def on_success(self):
        """Handle success and reset backoff."""
        if self.failure_count > 0:
            logger.info(f"Success after {self.failure_count} failures, resetting backoff")
        self.failure_count = 0
        self.current_delay = self.base_delay

    def reset(self):
        """Reset backoff state."""
        self.failure_count = 0
        self.current_delay = self.base_delay


class RateLimiter:
    """
    Advanced rate limiter with multiple strategies.
    
    Supports:
    - Per-domain rate limiting
    - Token bucket algorithm
    - Exponential backoff
    - Request queuing
    - Burst handling
    """

    def __init__(self, default_rule: Optional[RateLimitRule] = None):
        """
        Initialize rate limiter.
        
        Args:
            default_rule: Default rate limiting rule
        """
        self.default_rule = default_rule or RateLimitRule(
            max_requests=60,
            time_window=60,
            delay_min=1.0,
            delay_max=5.0,
            burst_limit=10
        )
        
        # Per-domain rules and state
        self.domain_rules: Dict[str, RateLimitRule] = {}
        self.domain_requests: Dict[str, deque] = defaultdict(deque)
        self.domain_tokens: Dict[str, float] = defaultdict(float)
        self.domain_last_request: Dict[str, float] = defaultdict(float)
        self.domain_backoff: Dict[str, ExponentialBackoff] = defaultdict(
            lambda: ExponentialBackoff()
        )
        
        # Global state
        self._locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self.total_requests = 0
        self.total_delays = 0.0

    def add_domain_rule(self, domain: str, rule: RateLimitRule):
        """
        Add rate limiting rule for specific domain.
        
        Args:
            domain: Domain name
            rule: Rate limiting rule
        """
        self.domain_rules[domain] = rule
        logger.info(f"Added rate limit rule for {domain}: {rule}")

    def _get_domain_rule(self, domain: str) -> RateLimitRule:
        """Get rate limiting rule for domain."""
        return self.domain_rules.get(domain, self.default_rule)

    def _update_token_bucket(self, domain: str, rule: RateLimitRule):
        """Update token bucket for domain."""
        now = time.time()
        last_request = self.domain_last_request[domain]
        
        if last_request > 0:
            # Add tokens based on time elapsed
            time_elapsed = now - last_request
            tokens_to_add = time_elapsed * (rule.max_requests / rule.time_window)
            self.domain_tokens[domain] = min(
                rule.burst_limit,
                self.domain_tokens[domain] + tokens_to_add
            )
        else:
            # Initialize with full burst
            self.domain_tokens[domain] = rule.burst_limit
        
        self.domain_last_request[domain] = now

    def _clean_request_history(self, domain: str, rule: RateLimitRule):
        """Clean old requests from history."""
        now = time.time()
        cutoff = now - rule.time_window
        
        requests = self.domain_requests[domain]
        while requests and requests[0] < cutoff:
            requests.popleft()

    def _calculate_delay(self, domain: str, rule: RateLimitRule) -> float:
        """
        Calculate required delay before next request.
        
        Args:
            domain: Domain name
            rule: Rate limiting rule
            
        Returns:
            Delay in seconds
        """
        now = time.time()
        requests = self.domain_requests[domain]
        
        # Check token bucket
        if self.domain_tokens[domain] < 1:
            # No tokens available, calculate wait time
            tokens_needed = 1 - self.domain_tokens[domain]
            token_generation_rate = rule.max_requests / rule.time_window
            token_wait = tokens_needed / token_generation_rate
            
            # Also check minimum delay
            last_request = self.domain_last_request[domain]
            if last_request > 0:
                time_since_last = now - last_request
                min_delay_wait = max(0, rule.delay_min - time_since_last)
                return max(token_wait, min_delay_wait)
            else:
                return token_wait
        
        # Check minimum delay
        last_request = self.domain_last_request[domain]
        if last_request > 0:
            time_since_last = now - last_request
            if time_since_last < rule.delay_min:
                return rule.delay_min - time_since_last
        
        # Check time window limit
        if len(requests) >= rule.max_requests:
            oldest_request = requests[0]
            wait_time = (oldest_request + rule.time_window) - now
            if wait_time > 0:
                return wait_time
        
        return 0

    async def acquire(self, domain: str) -> float:
        """
        Acquire permission to make request to domain.
        
        Args:
            domain: Domain name
            
        Returns:
            Actual delay time waited
        """
        async with self._locks[domain]:
            rule = self._get_domain_rule(domain)
            
            # Update token bucket
            self._update_token_bucket(domain, rule)
            
            # Clean old requests
            self._clean_request_history(domain, rule)
            
            # Calculate delay
            delay = self._calculate_delay(domain, rule)
            
            # Add random jitter to delay
            if delay > 0:
                jitter = random.uniform(0.8, 1.2)
                actual_delay = delay * jitter
                
                logger.debug(f"Rate limiting {domain}: waiting {actual_delay:.2f}s")
                await asyncio.sleep(actual_delay)
                
                self.total_delays += actual_delay
            else:
                actual_delay = 0
            
            # Consume token and record request
            self.domain_tokens[domain] -= 1
            self.domain_requests[domain].append(time.time())
            self.total_requests += 1
            
            return actual_delay

    async def on_request_success(self, domain: str, response_time: float):
        """
        Report successful request.
        
        Args:
            domain: Domain name
            response_time: Response time in seconds
        """
        backoff = self.domain_backoff[domain]
        backoff.on_success()
        
        # Adjust rate limiting based on response time
        rule = self._get_domain_rule(domain)
        if response_time > 10.0:  # Slow response, be more conservative
            rule.delay_min = min(rule.delay_max, rule.delay_min * 1.1)
        elif response_time < 2.0:  # Fast response, can be more aggressive
            rule.delay_min = max(0.5, rule.delay_min * 0.95)

    async def on_request_failure(self, domain: str, error: Exception) -> float:
        """
        Report failed request and get backoff delay.
        
        Args:
            domain: Domain name
            error: Exception that occurred
            
        Returns:
            Backoff delay in seconds
        """
        backoff = self.domain_backoff[domain]
        delay = backoff.on_failure()
        
        # Check for specific error types
        error_str = str(error).lower()
        if any(indicator in error_str for indicator in [
            "rate limit", "too many requests", "429", "503"
        ]):
            # Server is overloaded, increase delays
            rule = self._get_domain_rule(domain)
            rule.delay_min = min(rule.delay_max, rule.delay_min * 2)
            
            # Use longer backoff for rate limit errors
            delay = max(delay, 60.0)
        
        logger.warning(f"Request failed for {domain}, backing off for {delay:.2f}s")
        await asyncio.sleep(delay)
        
        return delay

    def reset_domain(self, domain: str):
        """
        Reset rate limiting state for domain.
        
        Args:
            domain: Domain name
        """
        self.domain_requests[domain].clear()
        self.domain_tokens[domain] = 0
        self.domain_last_request[domain] = 0
        self.domain_backoff[domain].reset()
        logger.info(f"Reset rate limiting state for {domain}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get rate limiting statistics.
        
        Returns:
            Dictionary with statistics
        """
        domain_stats = {}
        for domain in self.domain_requests:
            requests = self.domain_requests[domain]
            rule = self._get_domain_rule(domain)
            backoff = self.domain_backoff[domain]
            
            # Calculate recent request rate
            now = time.time()
            recent_requests = sum(
                1 for req_time in requests 
                if now - req_time <= rule.time_window
            )
            
            domain_stats[domain] = {
                "recent_requests": recent_requests,
                "max_requests": rule.max_requests,
                "current_tokens": self.domain_tokens[domain],
                "failure_count": backoff.failure_count,
                "current_delay": backoff.current_delay,
                "utilization": recent_requests / rule.max_requests
            }
        
        avg_delay = self.total_delays / max(self.total_requests, 1)
        
        return {
            "total_requests": self.total_requests,
            "total_delays": self.total_delays,
            "average_delay": avg_delay,
            "domain_stats": domain_stats
        }

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        pass 