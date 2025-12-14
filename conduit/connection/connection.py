"""
Connection Class

Represents a single connection with all associated components.
"""

import asyncio
import time
import uuid
from typing import Any, Optional, Dict, Callable, Awaitable
from dataclasses import dataclass, field
import logging

from ..transport import TCPSocket, ConnectionStateMachine, ConnectionState
from ..transport.auth import Session
from ..protocol import ProtocolEncoder, ProtocolDecoder, DecodedMessage, MessageType
from ..messages import MessageQueue
from ..heartbeat import HeartbeatMonitor
from ..backpressure import FlowController

logger = logging.getLogger(__name__)


@dataclass
class ConnectionStats:
    """Connection statistics."""
    
    connected_at: float = field(default_factory=time.time)
    messages_sent: int = 0
    messages_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    errors: int = 0


class Connection:
    """
    Represents a connection (client or server side).
    
    Combines socket, protocol, queues, heartbeat, and flow control.
    """
    
    def __init__(
        self,
        socket: TCPSocket,
        encoder: Optional[ProtocolEncoder] = None,
        decoder: Optional[ProtocolDecoder] = None,
        send_queue_size: int = 1000,
        receive_queue_size: int = 1000,
        heartbeat_interval: float = 30.0,
        heartbeat_timeout: float = 90.0,
        enable_backpressure: bool = True,
    ):
        """
        Initialize connection.
        
        Args:
            socket: TCP socket wrapper
            encoder: Protocol encoder
            decoder: Protocol decoder
            send_queue_size: Send queue max size
            receive_queue_size: Receive queue max size
            heartbeat_interval: Heartbeat interval
            heartbeat_timeout: Heartbeat timeout
            enable_backpressure: Enable flow control
        """
        self._socket = socket
        self._encoder = encoder or ProtocolEncoder()
        self._decoder = decoder or ProtocolDecoder()
        
        self._id = str(uuid.uuid4())
        self._state = ConnectionStateMachine()
        self._session: Optional[Session] = None
        self._authenticated: bool = False  # Simple auth flag for client-side
        
        # Queues
        self._send_queue: MessageQueue = MessageQueue(maxsize=send_queue_size)
        self._receive_queue: MessageQueue = MessageQueue(maxsize=receive_queue_size)
        
        # Heartbeat
        self._heartbeat = HeartbeatMonitor(
            interval=heartbeat_interval,
            timeout=heartbeat_timeout,
        )
        
        # Flow control
        self._flow_controller = FlowController(enabled=enable_backpressure)
        
        # Stats
        self._stats = ConnectionStats()
        
        # Tasks
        self._read_task: Optional[asyncio.Task] = None
        self._write_task: Optional[asyncio.Task] = None
        
        # Pending RPC responses
        self._pending_rpcs: Dict[int, asyncio.Future] = {}
        
        # Callbacks
        self._on_message: Optional[Callable] = None
        self._on_disconnect: Optional[Callable] = None
    
    @property
    def id(self) -> str:
        """Connection ID."""
        return self._id
    
    @property
    def state(self) -> ConnectionState:
        """Current connection state."""
        return self._state.state
    
    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._state.is_connected
    
    @property
    def is_authenticated(self) -> bool:
        """Check if authenticated."""
        return self._session is not None or self._authenticated
    
    @property
    def session(self) -> Optional[Session]:
        """Get session."""
        return self._session
    
    @property
    def remote_address(self):
        """Get remote address."""
        return self._socket.remote_address
    
    @property
    def stats(self) -> ConnectionStats:
        """Get connection stats."""
        return self._stats
    
    def set_session(self, session: Session) -> None:
        """Set session after authentication."""
        self._session = session
    
    def mark_authenticated(self) -> None:
        """Mark connection as authenticated (for client-side use)."""
        self._authenticated = True
    
    def set_message_handler(self, handler: Callable) -> None:
        """Set message handler callback."""
        self._on_message = handler
    
    def set_disconnect_handler(self, handler: Callable) -> None:
        """Set disconnect handler callback."""
        self._on_disconnect = handler
    
    async def start(self) -> None:
        """Start connection processing."""
        # Proper state transitions: DISCONNECTED -> CONNECTING -> AUTHENTICATING -> CONNECTED -> ACTIVE
        # For server-side connections that are already authenticated, we skip to CONNECTED
        if self._state.state == ConnectionState.DISCONNECTED:
            self._state.start_connecting()
        
        # Skip authenticating since server has already handled it
        if self._state.state == ConnectionState.CONNECTING:
            self._state.transition_to(ConnectionState.CONNECTED)
        
        if self._state.state == ConnectionState.CONNECTED:
            self._state.mark_active()
        
        # Setup heartbeat callbacks
        self._heartbeat.set_callbacks(
            on_send_ping=self._send_heartbeat_ping,
            on_timeout=self._handle_heartbeat_timeout,
        )
        
        # Setup flow control callbacks
        self._flow_controller.set_callbacks(
            on_pause=self._send_pause,
            on_resume=self._send_resume,
        )
        
        # Start tasks
        self._read_task = asyncio.create_task(self._read_loop())
        self._write_task = asyncio.create_task(self._write_loop())
        
        # Start heartbeat
        await self._heartbeat.start()
    
    async def stop(self) -> None:
        """Stop connection processing."""
        self._state.start_closing()
        
        # Stop heartbeat
        await self._heartbeat.stop()
        
        # Cancel tasks
        if self._read_task:
            self._read_task.cancel()
        if self._write_task:
            self._write_task.cancel()
        
        # Wait for tasks
        tasks = [t for t in [self._read_task, self._write_task] if t]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Close socket
        await self._socket.close()
        
        self._state.mark_closed()
        self._state.mark_disconnected()
    
    async def send_message(self, message_type: str, data: Any) -> None:
        """
        Send a regular message.
        
        Args:
            message_type: Message type string
            data: Message data
        """
        encoded = self._encoder.encode_message(message_type, data)
        await self._queue_send(encoded)
    
    async def send_rpc_request(self, method: str, params: dict) -> int:
        """
        Send an RPC request.
        
        Args:
            method: RPC method name
            params: Method parameters
            
        Returns:
            Correlation ID
        """
        encoded, corr_id = self._encoder.encode_rpc_request(method, params)
        
        # Create future for response
        future = asyncio.get_event_loop().create_future()
        self._pending_rpcs[corr_id] = future
        
        await self._queue_send(encoded)
        return corr_id
    
    async def wait_for_rpc_response(self, correlation_id: int) -> Any:
        """
        Wait for RPC response.
        
        Args:
            correlation_id: Request correlation ID
            
        Returns:
            Response data
        """
        future = self._pending_rpcs.get(correlation_id)
        if future is None:
            raise ValueError(f"No pending RPC for correlation ID {correlation_id}")
        
        try:
            return await future
        finally:
            self._pending_rpcs.pop(correlation_id, None)
    
    async def send_rpc_response(self, result: Any, correlation_id: int) -> None:
        """Send RPC response."""
        encoded = self._encoder.encode_rpc_response(result, correlation_id)
        await self._queue_send(encoded)
    
    async def send_rpc_error(self, error: str, correlation_id: int, code: int = None) -> None:
        """Send RPC error response."""
        encoded = self._encoder.encode_rpc_error(error, correlation_id, code)
        await self._queue_send(encoded)
    
    async def _queue_send(self, data: bytes) -> None:
        """Queue data for sending."""
        # Wait if paused
        if self._flow_controller.is_paused:
            await self._flow_controller.wait_for_resume(timeout=30.0)
        
        await self._send_queue.put(data)
    
    async def _read_loop(self) -> None:
        """Read loop - reads from socket and processes messages."""
        try:
            while self._state.can_receive:
                # Read data
                data = await self._socket.read()
                
                if not data:
                    logger.debug("Connection closed by remote")
                    break
                
                self._stats.bytes_received += len(data)
                
                # Feed to decoder
                self._decoder.feed(data)
                
                # Process all complete messages
                for message in self._decoder.decode_all():
                    await self._handle_message(message)
                
                # Check backpressure
                await self._flow_controller.check_and_update(
                    self._receive_queue.fill_ratio
                )
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Read loop error: {e}")
            self._stats.errors += 1
        finally:
            if self._on_disconnect:
                try:
                    await self._on_disconnect(self)
                except Exception:
                    pass
    
    async def _write_loop(self) -> None:
        """Write loop - sends queued messages."""
        try:
            while self._state.can_send or not self._send_queue.is_empty:
                # Get message from queue
                data = await self._send_queue.get(timeout=1.0)
                
                if data is None:
                    continue
                
                try:
                    await self._socket.write(data)
                    self._stats.bytes_sent += len(data)
                    self._stats.messages_sent += 1
                except Exception as e:
                    logger.error(f"Write error: {e}")
                    self._stats.errors += 1
                    break
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Write loop error: {e}")
    
    async def _handle_message(self, message: DecodedMessage) -> None:
        """Handle a decoded message."""
        self._stats.messages_received += 1
        
        msg_type = message.message_type
        
        # Handle control messages
        if msg_type == MessageType.HEARTBEAT_PING:
            self._heartbeat.record_ping()
            await self._send_heartbeat_pong()
            return
        
        if msg_type == MessageType.HEARTBEAT_PONG:
            self._heartbeat.record_pong()
            return
        
        if msg_type == MessageType.PAUSE:
            self._flow_controller.handle_remote_pause()
            return
        
        if msg_type == MessageType.RESUME:
            self._flow_controller.handle_remote_resume()
            return
        
        # Handle RPC responses
        if msg_type in (MessageType.RPC_RESPONSE, MessageType.RPC_ERROR):
            corr_id = message.correlation_id
            future = self._pending_rpcs.get(corr_id)
            
            if future and not future.done():
                # This connection created this RPC request, handle it
                future.set_result(message.payload)
                return
            
            # Otherwise, pass to external handler (e.g., Client has its own pending_rpcs)
            if self._on_message:
                await self._on_message(self, message)
            return
        
        # Handle regular messages - pass to handler
        if self._on_message:
            await self._on_message(self, message)
    
    async def _send_heartbeat_ping(self) -> None:
        """Send heartbeat ping."""
        encoded = self._encoder.encode_heartbeat_ping()
        await self._queue_send(encoded)
    
    async def _send_heartbeat_pong(self) -> None:
        """Send heartbeat pong."""
        encoded = self._encoder.encode_heartbeat_pong()
        await self._queue_send(encoded)
        self._heartbeat.record_pong_sent()
    
    async def _handle_heartbeat_timeout(self) -> None:
        """Handle heartbeat timeout."""
        logger.warning(f"Connection {self._id} heartbeat timeout")
        await self.stop()
    
    async def _send_pause(self) -> None:
        """Send pause signal."""
        encoded = self._encoder.encode_pause()
        # Send directly, don't queue
        await self._socket.write(encoded)
    
    async def _send_resume(self) -> None:
        """Send resume signal."""
        encoded = self._encoder.encode_resume()
        await self._socket.write(encoded)
