"""
Circuit Breaker pattern implementation for external services.
Protects against cascading failures and provides fallback mechanisms.
"""

import time
import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Optional, Dict, Union
from enum import Enum
import functools
import logging
from dataclasses import dataclass, field

from ..logging_config import get_logger

logger = get_logger("circuit_breaker")

class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, calls fail fast
    HALF_OPEN = "half_open"  # Testing if service has recovered

@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5          # Number of failures before opening
    recovery_timeout: int = 30          # Seconds to wait before trying again
    expected_exception: type = Exception  # Exception type that counts as failure
    success_threshold: int = 2          # Successes needed to close circuit
    timeout: float = 5.0               # Request timeout in seconds
    
    def __post_init__(self):
        if isinstance(self.expected_exception, str):
            # Convert string to exception type
            exception_map = {
                'ConnectionError': ConnectionError,
                'TimeoutError': TimeoutError,
                'HTTPError': Exception,
                'Exception': Exception
            }
            self.expected_exception = exception_map.get(self.expected_exception, Exception)

@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    circuit_open_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_calls == 0:
            return 0.0
        return (self.successful_calls / self.total_calls) * 100

class CircuitBreakerError(Exception):
    """Custom exception for circuit breaker failures."""
    def __init__(self, message: str, service_name: str, state: CircuitState):
        super().__init__(message)
        self.service_name = service_name
        self.state = state

class CircuitBreaker:
    """Circuit breaker implementation for external service calls."""
    
    def __init__(
        self, 
        service_name: str, 
        config: Optional[CircuitBreakerConfig] = None,
        fallback_func: Optional[Callable] = None
    ):
        self.service_name = service_name
        self.config = config or CircuitBreakerConfig()
        self.fallback_func = fallback_func
        
        # State
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = None  # Will be created on first use
        
        # Statistics
        self._stats = CircuitBreakerStats()
        
        self.logger = get_logger("circuit_breaker", service=service_name)
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state
    
    @property
    def stats(self) -> CircuitBreakerStats:
        """Get circuit statistics."""
        return self._stats
    
    async def _get_lock(self):
        """Get or create lock lazily."""
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt to reset from OPEN to HALF_OPEN."""
        if self._state != CircuitState.OPEN:
            return False
        
        if self._last_failure_time is None:
            return True
        
        return time.time() - self._last_failure_time >= self.config.recovery_timeout
    
    async def _call_with_timeout(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with timeout."""
        try:
            if asyncio.iscoroutinefunction(func):
                return await asyncio.wait_for(func(*args, **kwargs), timeout=self.config.timeout)
            else:
                return await asyncio.get_event_loop().run_in_executor(
                    None, functools.partial(func, *args, **kwargs)
                )
        except asyncio.TimeoutError:
            raise TimeoutError(f"Call to {self.service_name} timed out after {self.config.timeout}s")
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker.
        
        Args:
            func: Function to call
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result or fallback value
            
        Raises:
            CircuitBreakerError: If circuit is open or call fails
        """
        lock = await self._get_lock()
        async with lock:
            self._stats.total_calls += 1
            
            # Check if circuit is open
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitState.HALF_OPEN
                    self._success_count = 0
                    self.logger.info("circuit_half_open", service=self.service_name)
                else:
                    self.logger.warning("circuit_open_call_rejected", service=self.service_name)
                    raise CircuitBreakerError(
                        f"Circuit breaker OPEN for {self.service_name}",
                        self.service_name,
                        self._state
                    )
            
            # Attempt the call
            try:
                result = await self._call_with_timeout(func, *args, **kwargs)
                
                # Success
                self._on_success()
                return result
                
            except Exception as e:
                # Failure
                self._on_failure(e)
                
                # Try fallback if available
                if self.fallback_func:
                    try:
                        self.logger.info("using_fallback", service=self.service_name, error=str(e))
                        if asyncio.iscoroutinefunction(self.fallback_func):
                            return await self.fallback_func(*args, **kwargs)
                        else:
                            return self.fallback_func(*args, **kwargs)
                    except Exception as fallback_error:
                        self.logger.error(
                            "fallback_failed", 
                            service=self.service_name, 
                            error=str(fallback_error)
                        )
                
                # Re-raise original error
                raise
    
    def _on_success(self):
        """Handle successful call."""
        self._stats.successful_calls += 1
        self._stats.last_success_time = datetime.now(timezone.utc)
        
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.success_threshold:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self.logger.info("circuit_closed", service=self.service_name)
        
        self.logger.debug("call_success", service=self.service_name, state=self._state.value)
    
    def _on_failure(self, error: Exception):
        """Handle failed call."""
        self._stats.failed_calls += 1
        self._stats.last_failure_time = datetime.now(timezone.utc)
        
        # Check if this error counts as failure
        if isinstance(error, self.config.expected_exception):
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._state == CircuitState.CLOSED and self._failure_count >= self.config.failure_threshold:
                self._state = CircuitState.OPEN
                self._stats.circuit_open_count += 1
                self.logger.warning(
                    "circuit_opened", 
                    service=self.service_name,
                    failure_count=self._failure_count,
                    threshold=self.config.failure_threshold
                )
            elif self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._failure_count = 1
                self._last_failure_time = time.time()
                self.logger.warning("circuit_reopened", service=self.service_name)
        
        self.logger.error(
            "call_failure", 
            service=self.service_name,
            error=str(error),
            state=self._state.value,
            failure_count=self._failure_count
        )
    
    async def reset(self):
        """Manually reset circuit breaker to CLOSED state."""
        lock = await self._get_lock()
        async with lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None
            self.logger.info("circuit_manually_reset", service=self.service_name)
    
    def get_health(self) -> Dict[str, Any]:
        """Get circuit breaker health status."""
        return {
            "service": self.service_name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "stats": {
                "total_calls": self._stats.total_calls,
                "success_rate": self._stats.success_rate,
                "circuit_open_count": self._stats.circuit_open_count,
                "last_failure_time": self._stats.last_failure_time.isoformat() if self._stats.last_failure_time else None,
                "last_success_time": self._stats.last_success_time.isoformat() if self._stats.last_success_time else None
            },
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "timeout": self.config.timeout
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

# Global circuit breaker registry
_circuit_breakers: Dict[str, CircuitBreaker] = {}

def get_circuit_breaker(
    service_name: str, 
    config: Optional[CircuitBreakerConfig] = None,
    fallback_func: Optional[Callable] = None
) -> CircuitBreaker:
    """Get or create circuit breaker for a service."""
    if service_name not in _circuit_breakers:
        _circuit_breakers[service_name] = CircuitBreaker(service_name, config, fallback_func)
    return _circuit_breakers[service_name]

def circuit_breaker(
    service_name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 30,
    timeout: float = 5.0,
    expected_exception: Union[str, type] = Exception,
    fallback_func: Optional[Callable] = None
):
    """Decorator for circuit breaker protection."""
    
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            config = CircuitBreakerConfig(
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                timeout=timeout,
                expected_exception=expected_exception
            )
            
            breaker = get_circuit_breaker(service_name, config, fallback_func)
            return await breaker.call(func, *args, **kwargs)
        
        return wrapper
    return decorator

# Fallback functions for common scenarios
async def mtconnect_fallback(*args, **kwargs) -> Dict:
    """Fallback for MTConnect service - returns simulated data."""
    machine_id = kwargs.get('machine_id', args[0] if args else 'UNKNOWN')
    
    logger.warning("mtconnect_fallback_used", machine_id=machine_id)
    
    return {
        "controller": {
            "status": "RUNNING",
            "mode": "AUTOMATIC"
        },
        "power": {
            "status": "ON"
        },
        "path": {
            "command": "IDLE",
            "program": "UNKNOWN"
        },
        "spindle": {
            "speed": 0,
            "load": 0.0
        },
        "source": "circuit_breaker_fallback",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

async def database_fallback(*args, **kwargs) -> Dict:
    """Fallback for database operations - returns empty result."""
    logger.warning("database_fallback_used")
    return {"data": [], "count": 0, "source": "circuit_breaker_fallback"}
