"""
Message Queue

Async queues for message handling with backpressure support.
"""

import asyncio
from typing import Any, Optional, Generic, TypeVar
from dataclasses import dataclass
import time

T = TypeVar('T')


class MessageQueue(Generic[T]):
    """
    Async message queue with size limits and backpressure.
    
    Wraps asyncio.Queue with additional functionality for
    monitoring and flow control.
    """
    
    def __init__(self, maxsize: int = 1000):
        """
        Initialize queue.
        
        Args:
            maxsize: Maximum queue size (0 for unlimited)
        """
        self._queue: asyncio.Queue[T] = asyncio.Queue(maxsize=maxsize)
        self._maxsize = maxsize
        self._total_enqueued = 0
        self._total_dequeued = 0
        self._paused = False
    
    async def put(self, item: T, timeout: Optional[float] = None) -> bool:
        """
        Put an item in the queue.
        
        Args:
            item: Item to enqueue
            timeout: Optional timeout in seconds
            
        Returns:
            True if item was enqueued, False if queue is paused
        """
        if self._paused:
            return False
        
        try:
            if timeout is not None:
                await asyncio.wait_for(self._queue.put(item), timeout=timeout)
            else:
                await self._queue.put(item)
            self._total_enqueued += 1
            return True
        except asyncio.TimeoutError:
            return False
    
    def put_nowait(self, item: T) -> bool:
        """
        Put an item without waiting.
        
        Args:
            item: Item to enqueue
            
        Returns:
            True if successful, False if full or paused
        """
        if self._paused:
            return False
        
        try:
            self._queue.put_nowait(item)
            self._total_enqueued += 1
            return True
        except asyncio.QueueFull:
            return False
    
    async def get(self, timeout: Optional[float] = None) -> Optional[T]:
        """
        Get an item from the queue.
        
        Args:
            timeout: Optional timeout in seconds
            
        Returns:
            Item from queue, or None if timeout
        """
        try:
            if timeout is not None:
                item = await asyncio.wait_for(self._queue.get(), timeout=timeout)
            else:
                item = await self._queue.get()
            self._total_dequeued += 1
            return item
        except asyncio.TimeoutError:
            return None
    
    def get_nowait(self) -> Optional[T]:
        """
        Get an item without waiting.
        
        Returns:
            Item from queue, or None if empty
        """
        try:
            item = self._queue.get_nowait()
            self._total_dequeued += 1
            return item
        except asyncio.QueueEmpty:
            return None
    
    def task_done(self) -> None:
        """Mark a task as done."""
        self._queue.task_done()
    
    async def join(self) -> None:
        """Wait for all items to be processed."""
        await self._queue.join()
    
    def pause(self) -> None:
        """Pause the queue (stop accepting items)."""
        self._paused = True
    
    def resume(self) -> None:
        """Resume the queue."""
        self._paused = False
    
    @property
    def is_paused(self) -> bool:
        """Check if queue is paused."""
        return self._paused
    
    @property
    def size(self) -> int:
        """Current queue size."""
        return self._queue.qsize()
    
    @property
    def maxsize(self) -> int:
        """Maximum queue size."""
        return self._maxsize
    
    @property
    def is_full(self) -> bool:
        """Check if queue is full."""
        return self._queue.full()
    
    @property
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return self._queue.empty()
    
    @property
    def fill_ratio(self) -> float:
        """Get queue fill ratio (0.0 to 1.0)."""
        if self._maxsize == 0:
            return 0.0
        return self._queue.qsize() / self._maxsize
    
    @property
    def total_enqueued(self) -> int:
        """Total items ever enqueued."""
        return self._total_enqueued
    
    @property
    def total_dequeued(self) -> int:
        """Total items ever dequeued."""
        return self._total_dequeued
    
    def clear(self) -> int:
        """
        Clear all items from queue.
        
        Returns:
            Number of items cleared
        """
        count = 0
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                count += 1
            except asyncio.QueueEmpty:
                break
        return count
    
    def stats(self) -> dict:
        """Get queue statistics."""
        return {
            "size": self.size,
            "maxsize": self._maxsize,
            "is_full": self.is_full,
            "is_empty": self.is_empty,
            "is_paused": self._paused,
            "fill_ratio": self.fill_ratio,
            "total_enqueued": self._total_enqueued,
            "total_dequeued": self._total_dequeued,
        }


class PriorityMessageQueue(Generic[T]):
    """
    Priority queue for messages.
    
    Higher priority items are dequeued first.
    """
    
    def __init__(self, maxsize: int = 1000):
        """
        Initialize priority queue.
        
        Args:
            maxsize: Maximum queue size
        """
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize=maxsize)
        self._maxsize = maxsize
        self._counter = 0
    
    async def put(self, item: T, priority: int = 0) -> None:
        """
        Put an item with priority.
        
        Args:
            item: Item to enqueue
            priority: Priority (lower = higher priority)
        """
        # Use counter to maintain FIFO order for same priority
        self._counter += 1
        await self._queue.put((priority, self._counter, item))
    
    async def get(self) -> T:
        """Get highest priority item."""
        _, _, item = await self._queue.get()
        return item
    
    @property
    def size(self) -> int:
        """Current queue size."""
        return self._queue.qsize()
    
    @property
    def is_empty(self) -> bool:
        """Check if empty."""
        return self._queue.empty()
