"""
Conduit Metrics

Built-in metrics collection for monitoring and debugging.
"""

import time
import threading
from typing import Dict, Optional
from dataclasses import dataclass, field


@dataclass
class Metrics:
    """
    Thread-safe metrics collection.
    
    Tracks message counts, bytes transferred, latencies, and connection stats.
    """
    
    # Message counts
    messages_sent: int = 0
    messages_received: int = 0
    
    # Byte counts
    bytes_sent: int = 0
    bytes_received: int = 0
    
    # RPC stats
    rpc_calls_made: int = 0
    rpc_calls_received: int = 0
    rpc_errors: int = 0
    
    # Connection stats
    connections_total: int = 0
    connections_active: int = 0
    connections_failed: int = 0
    
    # Timing
    start_time: float = field(default_factory=time.time)
    last_message_time: float = 0.0
    
    # Latency tracking (simple moving average)
    _latency_sum: float = 0.0
    _latency_count: int = 0
    
    # Lock for thread safety
    _lock: threading.Lock = field(default_factory=threading.Lock)
    
    def record_message_sent(self, size: int) -> None:
        """Record an outgoing message."""
        with self._lock:
            self.messages_sent += 1
            self.bytes_sent += size
            self.last_message_time = time.time()
    
    def record_message_received(self, size: int) -> None:
        """Record an incoming message."""
        with self._lock:
            self.messages_received += 1
            self.bytes_received += size
            self.last_message_time = time.time()
    
    def record_rpc_call(self) -> None:
        """Record an outgoing RPC call."""
        with self._lock:
            self.rpc_calls_made += 1
    
    def record_rpc_received(self) -> None:
        """Record an incoming RPC call."""
        with self._lock:
            self.rpc_calls_received += 1
    
    def record_rpc_error(self) -> None:
        """Record an RPC error."""
        with self._lock:
            self.rpc_errors += 1
    
    def record_latency(self, latency_ms: float) -> None:
        """Record a latency measurement."""
        with self._lock:
            self._latency_sum += latency_ms
            self._latency_count += 1
    
    def record_connection(self) -> None:
        """Record a new connection."""
        with self._lock:
            self.connections_total += 1
            self.connections_active += 1
    
    def record_disconnection(self) -> None:
        """Record a disconnection."""
        with self._lock:
            self.connections_active = max(0, self.connections_active - 1)
    
    def record_connection_failure(self) -> None:
        """Record a failed connection attempt."""
        with self._lock:
            self.connections_failed += 1
    
    @property
    def uptime_seconds(self) -> float:
        """Get uptime in seconds."""
        return time.time() - self.start_time
    
    @property
    def avg_latency_ms(self) -> float:
        """Get average latency in milliseconds."""
        with self._lock:
            if self._latency_count == 0:
                return 0.0
            return self._latency_sum / self._latency_count
    
    @property
    def messages_per_second(self) -> float:
        """Get average messages per second."""
        uptime = self.uptime_seconds
        if uptime == 0:
            return 0.0
        with self._lock:
            return (self.messages_sent + self.messages_received) / uptime
    
    def to_dict(self) -> Dict:
        """Export metrics as dictionary."""
        with self._lock:
            return {
                "messages_sent": self.messages_sent,
                "messages_received": self.messages_received,
                "bytes_sent": self.bytes_sent,
                "bytes_received": self.bytes_received,
                "rpc_calls_made": self.rpc_calls_made,
                "rpc_calls_received": self.rpc_calls_received,
                "rpc_errors": self.rpc_errors,
                "connections_total": self.connections_total,
                "connections_active": self.connections_active,
                "connections_failed": self.connections_failed,
                "uptime_seconds": self.uptime_seconds,
                "avg_latency_ms": self.avg_latency_ms,
                "messages_per_second": self.messages_per_second,
            }
    
    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self.messages_sent = 0
            self.messages_received = 0
            self.bytes_sent = 0
            self.bytes_received = 0
            self.rpc_calls_made = 0
            self.rpc_calls_received = 0
            self.rpc_errors = 0
            self.connections_total = 0
            self.connections_active = 0
            self.connections_failed = 0
            self.start_time = time.time()
            self._latency_sum = 0.0
            self._latency_count = 0


# Global metrics instance (can be replaced per-server/client)
_global_metrics: Optional[Metrics] = None


def get_metrics() -> Metrics:
    """Get the global metrics instance."""
    global _global_metrics
    if _global_metrics is None:
        _global_metrics = Metrics()
    return _global_metrics


def set_metrics(metrics: Metrics) -> None:
    """Set the global metrics instance."""
    global _global_metrics
    _global_metrics = metrics
