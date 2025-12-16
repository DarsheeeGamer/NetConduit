"""
Rate Limiting for Conduit

Token bucket rate limiter for per-connection rate limiting.
"""

import time
import threading
from dataclasses import dataclass, field


@dataclass
class RateLimiter:
    """
    Token bucket rate limiter.
    
    Limits messages/bytes per second per connection.
    """
    
    # Limits (0 = unlimited)
    messages_per_second: int = 0
    bytes_per_second: int = 0
    
    # Token buckets
    _message_tokens: float = field(default=0.0, init=False)
    _byte_tokens: float = field(default=0.0, init=False)
    _last_refill: float = field(default_factory=time.time, init=False)
    
    # Lock for thread safety
    _lock: threading.Lock = field(default_factory=threading.Lock)
    
    def __post_init__(self):
        # Start with full buckets
        self._message_tokens = float(self.messages_per_second)
        self._byte_tokens = float(self.bytes_per_second)
    
    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self._last_refill
        self._last_refill = now
        
        if self.messages_per_second > 0:
            self._message_tokens = min(
                self._message_tokens + elapsed * self.messages_per_second,
                float(self.messages_per_second)  # Cap at max
            )
        
        if self.bytes_per_second > 0:
            self._byte_tokens = min(
                self._byte_tokens + elapsed * self.bytes_per_second,
                float(self.bytes_per_second)  # Cap at max
            )
    
    def try_acquire(self, bytes_count: int = 0) -> bool:
        """
        Try to acquire tokens for a message.
        
        Args:
            bytes_count: Number of bytes in the message
            
        Returns:
            True if allowed, False if rate limited
        """
        # If no limits, always allow
        if self.messages_per_second == 0 and self.bytes_per_second == 0:
            return True
        
        with self._lock:
            self._refill()
            
            # Check message limit
            if self.messages_per_second > 0:
                if self._message_tokens < 1.0:
                    return False
            
            # Check byte limit
            if self.bytes_per_second > 0:
                if self._byte_tokens < bytes_count:
                    return False
            
            # Consume tokens
            if self.messages_per_second > 0:
                self._message_tokens -= 1.0
            if self.bytes_per_second > 0:
                self._byte_tokens -= bytes_count
            
            return True
    
    def time_until_allowed(self, bytes_count: int = 0) -> float:
        """
        Get time in seconds until next message is allowed.
        
        Returns:
            Seconds to wait, 0 if immediately allowed
        """
        if self.messages_per_second == 0 and self.bytes_per_second == 0:
            return 0.0
        
        with self._lock:
            self._refill()
            
            wait_time = 0.0
            
            if self.messages_per_second > 0 and self._message_tokens < 1.0:
                needed = 1.0 - self._message_tokens
                wait_time = max(wait_time, needed / self.messages_per_second)
            
            if self.bytes_per_second > 0 and self._byte_tokens < bytes_count:
                needed = bytes_count - self._byte_tokens
                wait_time = max(wait_time, needed / self.bytes_per_second)
            
            return wait_time
    
    @property
    def is_enabled(self) -> bool:
        """Check if rate limiting is enabled."""
        return self.messages_per_second > 0 or self.bytes_per_second > 0


@dataclass 
class RateLimitConfig:
    """Rate limiting configuration."""
    
    enabled: bool = False
    messages_per_second: int = 100
    bytes_per_second: int = 10 * 1024 * 1024  # 10MB/s
    
    def create_limiter(self) -> RateLimiter:
        """Create a rate limiter from this config."""
        if not self.enabled:
            return RateLimiter()  # Unlimited
        return RateLimiter(
            messages_per_second=self.messages_per_second,
            bytes_per_second=self.bytes_per_second,
        )
