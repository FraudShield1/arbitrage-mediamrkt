"""
Circuit Breaker implementation for improved system reliability.

Provides automatic failure detection and recovery mechanisms for external services
and critical system components.
"""

import asyncio
import time
from enum import Enum
from typing import Any, Callable, Optional, Dict, List
from dataclasses import dataclass, field
from functools import wraps
import structlog
from threading import Lock
import statistics

logger = structlog.get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"        # Normal operation
    OPEN = "open"           # Failure state - calls rejected
    HALF_OPEN = "half_open" # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 5          # Number of failures to trigger open state
    recovery_timeout: int = 60          # Seconds before attempting recovery
    success_threshold: int = 3          # Successful calls needed to close circuit
    timeout: float = 30.0               # Call timeout in seconds
    expected_exception: tuple = (Exception,)  # Exceptions that count as failures
    
    # Advanced configuration
    minimum_calls: int = 10             # Minimum calls before evaluating failure rate
    failure_rate_threshold: float = 0.5 # Percentage of failures to trigger open (0.0-1.0)
    sliding_window_size: int = 100      # Size of call history window
    half_open_max_calls: int = 5        # Maximum calls allowed in half-open state


@dataclass
class CallResult:
    """Result of a circuit breaker protected call."""
    timestamp: float
    success: bool
    duration: float
    exception: Optional[Exception] = None


class CircuitBreakerStats:
    """Statistics tracking for circuit breaker."""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.calls: List[CallResult] = []
        self.lock = Lock()
    
    def record_call(self, result: CallResult):
        """Record a call result."""
        with self.lock:
            self.calls.append(result)
            # Maintain sliding window
            if len(self.calls) > self.window_size:
                self.calls = self.calls[-self.window_size:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics."""
        with self.lock:
            if not self.calls:
                return {
                    "total_calls": 0,
                    "success_rate": 0.0,
                    "failure_rate": 0.0,
                    "average_duration": 0.0,
                    "recent_failures": 0,
                }
            
            total_calls = len(self.calls)
            successful_calls = sum(1 for call in self.calls if call.success)
            failed_calls = total_calls - successful_calls
            
            # Recent failures (last 10 calls)
            recent_calls = self.calls[-10:] if len(self.calls) >= 10 else self.calls
            recent_failures = sum(1 for call in recent_calls if not call.success)
            
            # Duration statistics
            durations = [call.duration for call in self.calls]
            avg_duration = statistics.mean(durations) if durations else 0.0
            
            return {
                "total_calls": total_calls,
                "successful_calls": successful_calls,
                "failed_calls": failed_calls,
                "success_rate": successful_calls / total_calls,
                "failure_rate": failed_calls / total_calls,
                "average_duration": avg_duration,
                "recent_failures": recent_failures,
                "window_size": self.window_size,
            }
    
    def get_failure_rate(self) -> float:
        """Get current failure rate."""
        stats = self.get_stats()
        return stats["failure_rate"]
    
    def get_recent_failures(self, count: int = 5) -> int:
        """Get number of recent failures."""
        with self.lock:
            if not self.calls:
                return 0
            
            recent_calls = self.calls[-count:] if len(self.calls) >= count else self.calls
            return sum(1 for call in recent_calls if not call.success)


class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is in open state."""
    pass


class CircuitBreakerTimeoutException(Exception):
    """Exception raised when call times out."""
    pass


class CircuitBreaker:
    """
    Circuit breaker implementation with advanced features.
    
    Provides automatic failure detection, recovery mechanisms, and comprehensive
    statistics tracking for improved system reliability.
    """
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.stats = CircuitBreakerStats(self.config.sliding_window_size)
        
        # State management
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0
        self.state_changed_time = time.time()
        self.half_open_calls = 0
        
        # Thread safety
        self.lock = Lock()
        
        logger.info(f"Circuit breaker '{name}' initialized", 
                   config=self.config.__dict__)
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator to wrap functions with circuit breaker protection."""
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await self.call_async(func, *args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return self.call_sync(func, *args, **kwargs)
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with circuit breaker protection."""
        self._check_state()
        
        start_time = time.time()
        try:
            # Apply timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.timeout
            )
            
            duration = time.time() - start_time
            self._record_success(duration)
            return result
            
        except asyncio.TimeoutError as e:
            duration = time.time() - start_time
            timeout_exc = CircuitBreakerTimeoutException(
                f"Call timed out after {self.config.timeout}s"
            )
            self._record_failure(duration, timeout_exc)
            raise timeout_exc from e
            
        except self.config.expected_exception as e:
            duration = time.time() - start_time
            self._record_failure(duration, e)
            raise
    
    def call_sync(self, func: Callable, *args, **kwargs) -> Any:
        """Execute sync function with circuit breaker protection."""
        self._check_state()
        
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            self._record_success(duration)
            return result
            
        except self.config.expected_exception as e:
            duration = time.time() - start_time
            self._record_failure(duration, e)
            raise
    
    def _check_state(self):
        """Check current state and potentially transition states."""
        with self.lock:
            if self.state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                if time.time() - self.last_failure_time >= self.config.recovery_timeout:
                    self._transition_to_half_open()
                else:
                    raise CircuitBreakerOpenException(
                        f"Circuit breaker '{self.name}' is OPEN. "
                        f"Retry after {self.config.recovery_timeout}s"
                    )
            
            elif self.state == CircuitState.HALF_OPEN:
                # Limit calls in half-open state
                if self.half_open_calls >= self.config.half_open_max_calls:
                    raise CircuitBreakerOpenException(
                        f"Circuit breaker '{self.name}' is HALF_OPEN with max calls reached"
                    )
    
    def _record_success(self, duration: float):
        """Record successful call."""
        with self.lock:
            # Record in statistics
            result = CallResult(
                timestamp=time.time(),
                success=True,
                duration=duration
            )
            self.stats.record_call(result)
            
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                self.half_open_calls += 1
                
                # Check if we can close the circuit
                if self.success_count >= self.config.success_threshold:
                    self._transition_to_closed()
            
            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success
                self.failure_count = 0
        
        logger.debug(f"Circuit breaker '{self.name}' recorded success",
                    duration=duration, state=self.state.value)
    
    def _record_failure(self, duration: float, exception: Exception):
        """Record failed call."""
        with self.lock:
            # Record in statistics
            result = CallResult(
                timestamp=time.time(),
                success=False,
                duration=duration,
                exception=exception
            )
            self.stats.record_call(result)
            
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.state == CircuitState.HALF_OPEN:
                self.half_open_calls += 1
                # Any failure in half-open state goes back to open
                self._transition_to_open()
            
            elif self.state == CircuitState.CLOSED:
                # Check if we should open the circuit
                if self._should_open_circuit():
                    self._transition_to_open()
        
        logger.warning(f"Circuit breaker '{self.name}' recorded failure",
                      duration=duration, exception=str(exception), 
                      state=self.state.value, failure_count=self.failure_count)
    
    def _should_open_circuit(self) -> bool:
        """Determine if circuit should be opened based on failure criteria."""
        stats = self.stats.get_stats()
        
        # Need minimum number of calls to evaluate
        if stats["total_calls"] < self.config.minimum_calls:
            return False
        
        # Check failure rate threshold
        if stats["failure_rate"] >= self.config.failure_rate_threshold:
            return True
        
        # Check consecutive failures threshold
        if self.failure_count >= self.config.failure_threshold:
            return True
        
        return False
    
    def _transition_to_open(self):
        """Transition circuit to OPEN state."""
        previous_state = self.state
        self.state = CircuitState.OPEN
        self.state_changed_time = time.time()
        self.half_open_calls = 0
        
        logger.error(f"Circuit breaker '{self.name}' transitioned to OPEN",
                    previous_state=previous_state.value,
                    failure_count=self.failure_count,
                    stats=self.stats.get_stats())
    
    def _transition_to_half_open(self):
        """Transition circuit to HALF_OPEN state."""
        previous_state = self.state
        self.state = CircuitState.HALF_OPEN
        self.state_changed_time = time.time()
        self.success_count = 0
        self.half_open_calls = 0
        
        logger.info(f"Circuit breaker '{self.name}' transitioned to HALF_OPEN",
                   previous_state=previous_state.value)
    
    def _transition_to_closed(self):
        """Transition circuit to CLOSED state."""
        previous_state = self.state
        self.state = CircuitState.CLOSED
        self.state_changed_time = time.time()
        self.failure_count = 0
        self.success_count = 0
        self.half_open_calls = 0
        
        logger.info(f"Circuit breaker '{self.name}' transitioned to CLOSED",
                   previous_state=previous_state.value,
                   recovery_time=time.time() - self.last_failure_time)
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state and statistics."""
        with self.lock:
            return {
                "name": self.name,
                "state": self.state.value,
                "failure_count": self.failure_count,
                "success_count": self.success_count,
                "last_failure_time": self.last_failure_time,
                "state_changed_time": self.state_changed_time,
                "half_open_calls": self.half_open_calls,
                "config": self.config.__dict__,
                "stats": self.stats.get_stats(),
                "time_since_last_failure": time.time() - self.last_failure_time if self.last_failure_time > 0 else 0,
                "time_in_current_state": time.time() - self.state_changed_time,
            }
    
    def reset(self):
        """Reset circuit breaker to CLOSED state."""
        with self.lock:
            previous_state = self.state
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.last_failure_time = 0.0
            self.state_changed_time = time.time()
            self.half_open_calls = 0
            self.stats = CircuitBreakerStats(self.config.sliding_window_size)
        
        logger.info(f"Circuit breaker '{self.name}' manually reset",
                   previous_state=previous_state.value)
    
    def force_open(self):
        """Force circuit breaker to OPEN state."""
        with self.lock:
            previous_state = self.state
            self.state = CircuitState.OPEN
            self.last_failure_time = time.time()
            self.state_changed_time = time.time()
        
        logger.warning(f"Circuit breaker '{self.name}' manually forced to OPEN",
                      previous_state=previous_state.value)


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""
    
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self.lock = Lock()
    
    def get_or_create(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """Get existing circuit breaker or create new one."""
        with self.lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(name, config)
            return self._breakers[name]
    
    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        return self._breakers.get(name)
    
    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """Get states of all registered circuit breakers."""
        with self.lock:
            return {name: breaker.get_state() for name, breaker in self._breakers.items()}
    
    def reset_all(self):
        """Reset all circuit breakers."""
        with self.lock:
            for breaker in self._breakers.values():
                breaker.reset()
        logger.info("All circuit breakers reset")
    
    def get_unhealthy_breakers(self) -> List[str]:
        """Get list of circuit breakers in OPEN state."""
        with self.lock:
            return [name for name, breaker in self._breakers.items() 
                   if breaker.state == CircuitState.OPEN]


# Global registry instance
circuit_breaker_registry = CircuitBreakerRegistry()


# Convenience functions
def circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None):
    """Decorator factory for circuit breaker protection."""
    breaker = circuit_breaker_registry.get_or_create(name, config)
    return breaker


def get_circuit_breaker(name: str) -> Optional[CircuitBreaker]:
    """Get circuit breaker by name."""
    return circuit_breaker_registry.get(name)


def get_all_circuit_breaker_states() -> Dict[str, Dict[str, Any]]:
    """Get states of all circuit breakers."""
    return circuit_breaker_registry.get_all_states()


def reset_all_circuit_breakers():
    """Reset all circuit breakers."""
    circuit_breaker_registry.reset_all()


# Pre-configured circuit breakers for common services
def create_service_circuit_breakers():
    """Create circuit breakers for external services."""
    
    # MediaMarkt scraping circuit breaker
    mediamarkt_config = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=300,  # 5 minutes
        success_threshold=2,
        timeout=30.0,
        expected_exception=(Exception,),
        failure_rate_threshold=0.4,
        minimum_calls=5
    )
    circuit_breaker_registry.get_or_create("mediamarkt_scraping", mediamarkt_config)
    
    # Amazon API circuit breaker
    amazon_config = CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=180,  # 3 minutes
        success_threshold=3,
        timeout=15.0,
        expected_exception=(Exception,),
        failure_rate_threshold=0.5,
        minimum_calls=10
    )
    circuit_breaker_registry.get_or_create("amazon_api", amazon_config)
    
    # Keepa API circuit breaker
    keepa_config = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=120,  # 2 minutes
        success_threshold=2,
        timeout=20.0,
        expected_exception=(Exception,),
        failure_rate_threshold=0.3,
        minimum_calls=5
    )
    circuit_breaker_registry.get_or_create("keepa_api", keepa_config)
    
    # Database circuit breaker
    database_config = CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=60,   # 1 minute
        success_threshold=3,
        timeout=30.0,
        expected_exception=(Exception,),
        failure_rate_threshold=0.6,
        minimum_calls=20
    )
    circuit_breaker_registry.get_or_create("database", database_config)
    
    # Redis circuit breaker
    redis_config = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=30,   # 30 seconds
        success_threshold=2,
        timeout=5.0,
        expected_exception=(Exception,),
        failure_rate_threshold=0.4,
        minimum_calls=10
    )
    circuit_breaker_registry.get_or_create("redis", redis_config)
    
    logger.info("Service circuit breakers created")


# Initialize service circuit breakers
create_service_circuit_breakers() 