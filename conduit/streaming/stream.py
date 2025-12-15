"""
Streaming API Module

Provides continuous data streaming between server and client.
"""

import asyncio
from typing import Optional, Callable, Any, AsyncIterator, Dict
from dataclasses import dataclass, field
import time
import logging
import uuid

logger = logging.getLogger(__name__)


@dataclass
class StreamInfo:
    """Information about a stream."""
    stream_id: str
    name: str
    created_at: float = field(default_factory=time.time)
    message_count: int = 0
    bytes_sent: int = 0


class Stream:
    """
    A bidirectional data stream.
    
    Server usage:
        stream = Stream("sensor_data")
        
        # Push data
        await stream.push({"temperature": 22.5})
        
        # Subscribe clients
        @stream.on_subscribe
        async def client_subscribed(client_id):
            print(f"Client {client_id} subscribed")
    
    Client usage:
        async for data in client.subscribe("sensor_data"):
            print(f"Received: {data}")
    """
    
    def __init__(self, name: str, buffer_size: int = 100):
        self.name = name
        self.stream_id = str(uuid.uuid4())
        self.buffer_size = buffer_size
        
        self._subscribers: Dict[str, asyncio.Queue] = {}
        self._running = False
        self._info = StreamInfo(stream_id=self.stream_id, name=name)
        
        # Callbacks
        self._on_subscribe: Optional[Callable] = None
        self._on_unsubscribe: Optional[Callable] = None
    
    @property
    def info(self) -> StreamInfo:
        return self._info
    
    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)
    
    def on_subscribe(self, handler: Callable) -> Callable:
        """Decorator to register subscribe callback."""
        self._on_subscribe = handler
        return handler
    
    def on_unsubscribe(self, handler: Callable) -> Callable:
        """Decorator to register unsubscribe callback."""
        self._on_unsubscribe = handler
        return handler
    
    async def subscribe(self, subscriber_id: str) -> asyncio.Queue:
        """Subscribe to this stream."""
        if subscriber_id in self._subscribers:
            return self._subscribers[subscriber_id]
        
        queue = asyncio.Queue(maxsize=self.buffer_size)
        self._subscribers[subscriber_id] = queue
        
        logger.debug(f"Stream {self.name}: subscriber {subscriber_id[:8]} joined")
        
        if self._on_subscribe:
            await self._on_subscribe(subscriber_id)
        
        return queue
    
    async def unsubscribe(self, subscriber_id: str) -> None:
        """Unsubscribe from this stream."""
        if subscriber_id in self._subscribers:
            del self._subscribers[subscriber_id]
            
            logger.debug(f"Stream {self.name}: subscriber {subscriber_id[:8]} left")
            
            if self._on_unsubscribe:
                await self._on_unsubscribe(subscriber_id)
    
    async def push(self, data: Any) -> int:
        """
        Push data to all subscribers.
        
        Returns:
            Number of subscribers who received the data
        """
        if not self._subscribers:
            return 0
        
        message = {
            "stream": self.name,
            "data": data,
            "timestamp": time.time(),
            "sequence": self._info.message_count,
        }
        
        sent = 0
        for subscriber_id, queue in list(self._subscribers.items()):
            try:
                queue.put_nowait(message)
                sent += 1
            except asyncio.QueueFull:
                logger.warning(f"Stream {self.name}: queue full for {subscriber_id[:8]}")
        
        self._info.message_count += 1
        
        return sent
    
    async def close(self) -> None:
        """Close the stream and notify all subscribers."""
        for subscriber_id, queue in list(self._subscribers.items()):
            try:
                queue.put_nowait({"stream": self.name, "closed": True})
            except asyncio.QueueFull:
                pass
        
        self._subscribers.clear()
        logger.info(f"Stream {self.name} closed")


class StreamManager:
    """
    Manages multiple streams on the server.
    
    Usage:
        manager = StreamManager()
        
        # Create a stream
        sensor_stream = manager.create("sensors")
        
        # Push data
        await sensor_stream.push({"temp": 22.5})
        
        # In RPC handler
        @server.rpc
        async def subscribe_stream(stream_name: str) -> dict:
            return manager.subscribe(stream_name, client.id)
    """
    
    def __init__(self):
        self._streams: Dict[str, Stream] = {}
    
    def create(self, name: str, buffer_size: int = 100) -> Stream:
        """Create a new stream."""
        if name in self._streams:
            return self._streams[name]
        
        stream = Stream(name, buffer_size)
        self._streams[name] = stream
        logger.info(f"Created stream: {name}")
        return stream
    
    def get(self, name: str) -> Optional[Stream]:
        """Get a stream by name."""
        return self._streams.get(name)
    
    def list_streams(self) -> list:
        """List all streams."""
        return [{"name": s.name, "subscribers": s.subscriber_count} for s in self._streams.values()]
    
    async def subscribe(self, stream_name: str, subscriber_id: str) -> dict:
        """Subscribe to a stream."""
        stream = self._streams.get(stream_name)
        if not stream:
            return {"error": f"Stream not found: {stream_name}"}
        
        await stream.subscribe(subscriber_id)
        return {"subscribed": True, "stream": stream_name}
    
    async def unsubscribe(self, stream_name: str, subscriber_id: str) -> dict:
        """Unsubscribe from a stream."""
        stream = self._streams.get(stream_name)
        if stream:
            await stream.unsubscribe(subscriber_id)
        return {"unsubscribed": True}
    
    async def push(self, stream_name: str, data: Any) -> int:
        """Push data to a stream."""
        stream = self._streams.get(stream_name)
        if not stream:
            return 0
        return await stream.push(data)
    
    async def close_all(self) -> None:
        """Close all streams."""
        for stream in self._streams.values():
            await stream.close()
        self._streams.clear()


class ClientStreamConsumer:
    """
    Client-side stream consumer.
    
    Usage:
        consumer = ClientStreamConsumer(client)
        
        async for data in consumer.subscribe("sensors"):
            print(f"Sensor data: {data}")
    """
    
    def __init__(self, client):
        self._client = client
        self._active_streams: Dict[str, asyncio.Queue] = {}
        self._handlers: Dict[str, Callable] = {}
    
    async def subscribe(
        self,
        stream_name: str,
        on_data: Optional[Callable] = None,
    ) -> AsyncIterator[Any]:
        """
        Subscribe to a stream and iterate over data.
        
        Args:
            stream_name: Name of stream to subscribe to
            on_data: Optional callback for each data item
            
        Yields:
            Stream data items
        """
        from conduit import data
        
        # Subscribe via RPC
        result = await self._client.rpc.call("stream_subscribe", args=data(
            stream_name=stream_name,
        ))
        
        if not result.get("success"):
            raise Exception(f"Failed to subscribe: {result}")
        
        # Create local queue
        queue = asyncio.Queue()
        self._active_streams[stream_name] = queue
        
        # Register handler for stream messages
        @self._client.on(f"stream:{stream_name}")
        async def stream_handler(msg):
            if msg.get("closed"):
                queue.put_nowait(None)
            else:
                queue.put_nowait(msg.get("data"))
                if on_data:
                    await on_data(msg.get("data"))
        
        try:
            while True:
                data_item = await queue.get()
                if data_item is None:
                    break
                yield data_item
        finally:
            await self.unsubscribe(stream_name)
    
    async def unsubscribe(self, stream_name: str) -> None:
        """Unsubscribe from a stream."""
        if stream_name in self._active_streams:
            del self._active_streams[stream_name]
        
        from conduit import data
        await self._client.rpc.call("stream_unsubscribe", args=data(
            stream_name=stream_name,
        ))
