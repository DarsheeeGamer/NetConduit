"""
Heartbeat Monitor

Monitors connection health via periodic heartbeats.
"""

import asyncio
import time
from typing import Optional, Callable, Awaitable
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


# Callback types
HeartbeatSendCallback = Callable[[], Awaitable[None]]
HeartbeatTimeoutCallback = Callable[[], Awaitable[None]]


@dataclass
class HeartbeatStats:
    """Heartbeat statistics."""
    
    pings_sent: int = 0
    pongs_received: int = 0
    pongs_sent: int = 0
    pings_received: int = 0
    last_ping_sent: Optional[float] = None
    last_pong_received: Optional[float] = None
    last_ping_received: Optional[float] = None
    last_pong_sent: Optional[float] = None
    current_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    min_latency_ms: float = float('inf')
    max_latency_ms: float = 0.0
    timeouts: int = 0
    
    def record_latency(self, latency_ms: float) -> None:
        """Record a latency measurement."""
        self.current_latency_ms = latency_ms
        self.min_latency_ms = min(self.min_latency_ms, latency_ms)
        self.max_latency_ms = max(self.max_latency_ms, latency_ms)
        
        # Exponential moving average
        alpha = 0.3
        if self.avg_latency_ms == 0:
            self.avg_latency_ms = latency_ms
        else:
            self.avg_latency_ms = alpha * latency_ms + (1 - alpha) * self.avg_latency_ms


class HeartbeatMonitor:
    """
    Monitors connection health via heartbeats.
    
    Sends periodic pings and expects pongs within timeout.
    Triggers callback if connection appears dead.
    """
    
    def __init__(
        self,
        interval: float = 30.0,
        timeout: float = 90.0,
        on_send_ping: Optional[HeartbeatSendCallback] = None,
        on_timeout: Optional[HeartbeatTimeoutCallback] = None,
    ):
        """
        Initialize heartbeat monitor.
        
        Args:
            interval: Ping interval in seconds
            timeout: Time without pong before timeout
            on_send_ping: Callback to send ping
            on_timeout: Callback on heartbeat timeout
        """
        self._interval = interval
        self._timeout = timeout
        self._on_send_ping = on_send_ping
        self._on_timeout = on_timeout
        
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._stats = HeartbeatStats()
        
        self._last_pong_time: float = 0.0
        self._pending_ping_time: Optional[float] = None
    
    def set_callbacks(
        self,
        on_send_ping: HeartbeatSendCallback,
        on_timeout: HeartbeatTimeoutCallback
    ) -> None:
        """
        Set heartbeat callbacks.
        
        Args:
            on_send_ping: Called to send ping
            on_timeout: Called on timeout
        """
        self._on_send_ping = on_send_ping
        self._on_timeout = on_timeout
    
    async def start(self) -> None:
        """Start heartbeat monitoring."""
        if self._running:
            return
        
        if self._on_send_ping is None:
            raise ValueError("on_send_ping callback not set")
        
        self._running = True
        self._last_pong_time = time.time()
        self._task = asyncio.create_task(self._heartbeat_loop())
        
        logger.debug(f"Heartbeat monitor started (interval={self._interval}s, timeout={self._timeout}s)")
    
    async def stop(self) -> None:
        """Stop heartbeat monitoring."""
        if not self._running:
            return
        
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        
        logger.debug("Heartbeat monitor stopped")
    
    async def _heartbeat_loop(self) -> None:
        """Main heartbeat loop."""
        while self._running:
            try:
                # Wait for interval
                await asyncio.sleep(self._interval)
                
                if not self._running:
                    break
                
                # Check timeout
                time_since_pong = time.time() - self._last_pong_time
                
                if time_since_pong > self._timeout:
                    self._stats.timeouts += 1
                    logger.warning(f"Heartbeat timeout! No pong for {time_since_pong:.1f}s")
                    
                    if self._on_timeout:
                        await self._on_timeout()
                    
                    # Don't break - let the timeout handler decide what to do
                    continue
                
                # Send ping
                self._pending_ping_time = time.time()
                self._stats.pings_sent += 1
                self._stats.last_ping_sent = self._pending_ping_time
                
                if self._on_send_ping:
                    await self._on_send_ping()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(1)
    
    def record_pong(self) -> None:
        """
        Record that a pong was received.
        
        Call this when you receive a pong from the remote.
        """
        now = time.time()
        self._last_pong_time = now
        self._stats.pongs_received += 1
        self._stats.last_pong_received = now
        
        # Calculate latency
        if self._pending_ping_time is not None:
            latency_ms = (now - self._pending_ping_time) * 1000
            self._stats.record_latency(latency_ms)
            self._pending_ping_time = None
    
    def record_ping(self) -> None:
        """
        Record that a ping was received.
        
        Call this when you receive a ping from the remote.
        """
        now = time.time()
        self._stats.pings_received += 1
        self._stats.last_ping_received = now
    
    def record_pong_sent(self) -> None:
        """
        Record that a pong was sent.
        
        Call this when you send a pong.
        """
        self._stats.pongs_sent += 1
        self._stats.last_pong_sent = time.time()
    
    def reset(self) -> None:
        """Reset last pong time (e.g., on reconnect)."""
        self._last_pong_time = time.time()
        self._pending_ping_time = None
    
    @property
    def is_running(self) -> bool:
        """Check if monitor is running."""
        return self._running
    
    @property
    def stats(self) -> HeartbeatStats:
        """Get heartbeat statistics."""
        return self._stats
    
    @property
    def time_since_last_pong(self) -> float:
        """Time since last pong in seconds."""
        if self._last_pong_time == 0:
            return 0.0
        return time.time() - self._last_pong_time
    
    @property
    def is_healthy(self) -> bool:
        """Check if heartbeat is healthy (not timed out)."""
        return self.time_since_last_pong < self._timeout
    
    @property
    def latency_ms(self) -> float:
        """Current latency in milliseconds."""
        return self._stats.current_latency_ms
    
    @property
    def avg_latency_ms(self) -> float:
        """Average latency in milliseconds."""
        return self._stats.avg_latency_ms
