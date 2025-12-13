"""
Flow Controller

Manages backpressure for preventing buffer overflow.
"""

import asyncio
from typing import Optional, Callable, Awaitable
from enum import Enum, auto
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class BackpressureState(Enum):
    """Backpressure state."""
    
    FLOWING = auto()     # Normal operation
    PAUSED = auto()      # Sender should pause
    RESUMING = auto()    # Transitioning back to flowing


SendPauseCallback = Callable[[], Awaitable[None]]
SendResumeCallback = Callable[[], Awaitable[None]]


@dataclass
class FlowStats:
    """Flow control statistics."""
    
    pause_count: int = 0
    resume_count: int = 0
    total_pause_duration_ms: float = 0.0
    current_pause_start: Optional[float] = None


class FlowController:
    """
    Controls message flow to prevent buffer overflow.
    
    Monitors queue fill levels and sends pause/resume signals.
    """
    
    def __init__(
        self,
        high_watermark: float = 0.8,
        low_watermark: float = 0.5,
        enabled: bool = True,
        on_pause: Optional[SendPauseCallback] = None,
        on_resume: Optional[SendResumeCallback] = None,
    ):
        """
        Initialize flow controller.
        
        Args:
            high_watermark: Fill ratio to trigger pause (0.0-1.0)
            low_watermark: Fill ratio to trigger resume (0.0-1.0)
            enabled: Whether backpressure is enabled
            on_pause: Callback to send pause signal
            on_resume: Callback to send resume signal
        """
        self._high_watermark = high_watermark
        self._low_watermark = low_watermark
        self._enabled = enabled
        self._on_pause = on_pause
        self._on_resume = on_resume
        
        self._state = BackpressureState.FLOWING
        self._stats = FlowStats()
        self._paused_event = asyncio.Event()
        self._paused_event.set()  # Start unpaused
    
    def set_callbacks(
        self,
        on_pause: SendPauseCallback,
        on_resume: SendResumeCallback
    ) -> None:
        """Set flow control callbacks."""
        self._on_pause = on_pause
        self._on_resume = on_resume
    
    async def check_and_update(self, fill_ratio: float) -> BackpressureState:
        """
        Check fill ratio and update state.
        
        Args:
            fill_ratio: Current buffer fill ratio (0.0-1.0)
            
        Returns:
            Current backpressure state
        """
        if not self._enabled:
            return BackpressureState.FLOWING
        
        if self._state == BackpressureState.FLOWING:
            if fill_ratio >= self._high_watermark:
                await self._trigger_pause()
                
        elif self._state == BackpressureState.PAUSED:
            if fill_ratio <= self._low_watermark:
                await self._trigger_resume()
        
        return self._state
    
    async def _trigger_pause(self) -> None:
        """Trigger pause state."""
        if self._state == BackpressureState.PAUSED:
            return
        
        logger.debug("Triggering backpressure PAUSE")
        
        import time
        self._state = BackpressureState.PAUSED
        self._stats.pause_count += 1
        self._stats.current_pause_start = time.time()
        self._paused_event.clear()
        
        if self._on_pause:
            try:
                await self._on_pause()
            except Exception as e:
                logger.error(f"Error in pause callback: {e}")
    
    async def _trigger_resume(self) -> None:
        """Trigger resume state."""
        if self._state == BackpressureState.FLOWING:
            return
        
        logger.debug("Triggering backpressure RESUME")
        
        import time
        self._state = BackpressureState.FLOWING
        self._stats.resume_count += 1
        
        if self._stats.current_pause_start:
            duration = (time.time() - self._stats.current_pause_start) * 1000
            self._stats.total_pause_duration_ms += duration
            self._stats.current_pause_start = None
        
        self._paused_event.set()
        
        if self._on_resume:
            try:
                await self._on_resume()
            except Exception as e:
                logger.error(f"Error in resume callback: {e}")
    
    async def wait_for_resume(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for resume signal.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if resumed, False if timeout
        """
        try:
            if timeout:
                await asyncio.wait_for(self._paused_event.wait(), timeout=timeout)
            else:
                await self._paused_event.wait()
            return True
        except asyncio.TimeoutError:
            return False
    
    def handle_remote_pause(self) -> None:
        """Handle pause signal from remote."""
        self._state = BackpressureState.PAUSED
        self._paused_event.clear()
        self._stats.pause_count += 1
    
    def handle_remote_resume(self) -> None:
        """Handle resume signal from remote."""
        self._state = BackpressureState.FLOWING
        self._paused_event.set()
        self._stats.resume_count += 1
    
    @property
    def state(self) -> BackpressureState:
        """Get current state."""
        return self._state
    
    @property
    def is_paused(self) -> bool:
        """Check if paused."""
        return self._state == BackpressureState.PAUSED
    
    @property
    def is_flowing(self) -> bool:
        """Check if flowing normally."""
        return self._state == BackpressureState.FLOWING
    
    @property
    def enabled(self) -> bool:
        """Check if backpressure is enabled."""
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Enable/disable backpressure."""
        self._enabled = value
        if not value:
            self._state = BackpressureState.FLOWING
            self._paused_event.set()
    
    @property
    def stats(self) -> FlowStats:
        """Get flow statistics."""
        return self._stats
    
    def reset(self) -> None:
        """Reset to flowing state."""
        self._state = BackpressureState.FLOWING
        self._paused_event.set()
        self._stats.current_pause_start = None
