"""
Conduit Client

The main client class for connecting to Conduit servers.
"""

import asyncio
import hashlib
import time
from typing import Any, Callable, Dict, List, Optional, Awaitable, Union
import logging

from .data.descriptors import ClientDescriptor
from .transport import TCPSocket, ConnectionStateMachine, ConnectionState
from .protocol import ProtocolEncoder, ProtocolDecoder, MessageType, DecodedMessage
from .connection import Connection
from .messages import MessageRouter, Message
from .rpc import RPC, data

logger = logging.getLogger(__name__)


# Callback types
LifecycleHook = Callable[['Client'], Awaitable[None]]
MessageHandler = Callable[[Any], Awaitable[Any]]


class Client:
    """
    Conduit Client.
    
    Connects to a Conduit server and handles messages/RPC calls.
    
    Usage:
        client = Client(ClientDescriptor(
            server_host="localhost",
            server_port=8080,
            password="secret123"
        ))
        
        @client.on("notification")
        async def handle_notification(data):
            print(f"Got notification: {data}")
        
        await client.connect()
        
        # Make RPC call
        result = await client.rpc.call("add", args=data(a=10, b=20))
    """
    
    def __init__(self, config: ClientDescriptor):
        """
        Initialize client.
        
        Args:
            config: Client configuration
        """
        self._config = config
        
        # State
        self._state = ConnectionStateMachine()
        self._socket: Optional[TCPSocket] = None
        self._connection: Optional[Connection] = None
        
        # Protocol
        self._encoder = ProtocolEncoder(enable_compression=config.enable_compression)
        self._decoder = ProtocolDecoder()
        
        # Message routing
        self._message_router = MessageRouter()
        
        # RPC interface
        self._rpc = RPC(self, default_timeout=config.rpc_timeout)
        
        # Pending RPC responses
        self._pending_rpcs: Dict[int, asyncio.Future] = {}
        
        # Session info
        self._session_token: Optional[str] = None
        self._server_info: Dict[str, Any] = {}
        
        # Lifecycle hooks
        self._on_connect: List[LifecycleHook] = []
        self._on_disconnect: List[LifecycleHook] = []
        self._on_reconnect: List[LifecycleHook] = []
        
        # Reconnection state
        self._reconnect_attempts = 0
        self._should_reconnect = True
        
        # Tasks
        self._read_task: Optional[asyncio.Task] = None
        self._write_task: Optional[asyncio.Task] = None
        self._reconnect_task: Optional[asyncio.Task] = None
    
    # === Decorators ===
    
    def on(self, message_type: str) -> Callable:
        """
        Decorator to register a message handler.
        
        Args:
            message_type: Type of message to handle
            
        Returns:
            Decorator function
        """
        def decorator(handler: MessageHandler) -> MessageHandler:
            # Wrap to not require connection parameter
            async def wrapper(conn, data):
                return await handler(data)
            
            self._message_router.register(
                message_type=message_type,
                handler=wrapper,
                requires_auth=False,
            )
            return handler
        return decorator
    
    def on_connect(self, handler: LifecycleHook) -> LifecycleHook:
        """Register connect hook."""
        self._on_connect.append(handler)
        return handler
    
    def on_disconnect(self, handler: LifecycleHook) -> LifecycleHook:
        """Register disconnect hook."""
        self._on_disconnect.append(handler)
        return handler
    
    def on_reconnect(self, handler: LifecycleHook) -> LifecycleHook:
        """Register reconnect hook."""
        self._on_reconnect.append(handler)
        return handler
    
    # === Connection Lifecycle ===
    
    async def connect(self) -> bool:
        """
        Connect to the server.
        
        Returns:
            True if connected successfully
        """
        if self._state.is_connected:
            logger.warning("Already connected")
            return True
        
        self._should_reconnect = True
        return await self._do_connect()
    
    async def _do_connect(self) -> bool:
        """Perform the actual connection."""
        try:
            self._state.start_connecting()
            
            logger.info(f"Connecting to {self._config.server_host}:{self._config.server_port}")
            
            # Connect TCP socket
            self._socket = await TCPSocket.connect(
                host=self._config.server_host,
                port=self._config.server_port,
                timeout=self._config.connect_timeout,
                use_ipv6=self._config.use_ipv6,
                buffer_size=self._config.buffer_size,
            )
            
            self._state.start_authenticating()
            
            # Authenticate
            authenticated = await self._authenticate()
            
            if not authenticated:
                self._state.mark_failed("Authentication failed")
                await self._socket.close()
                return False
            
            self._state.mark_connected()
            
            # Create connection wrapper
            self._connection = Connection(
                socket=self._socket,
                encoder=self._encoder,
                decoder=ProtocolDecoder(),
                send_queue_size=self._config.send_queue_size,
                receive_queue_size=self._config.receive_queue_size,
                heartbeat_interval=self._config.heartbeat_interval,
                heartbeat_timeout=self._config.heartbeat_timeout,
            )
            
            # Set handlers
            self._connection.set_message_handler(self._handle_message)
            self._connection.set_disconnect_handler(self._handle_disconnect)
            
            # Mark connection as authenticated (client already authenticated above)
            self._connection.mark_authenticated()
            
            # Start connection processing
            await self._connection.start()
            
            self._state.mark_active()
            self._reconnect_attempts = 0
            
            # Run connect hooks
            for hook in self._on_connect:
                try:
                    await hook(self)
                except Exception as e:
                    logger.error(f"Error in connect hook: {e}")
            
            logger.info("Connected and authenticated")
            return True
            
        except asyncio.TimeoutError:
            logger.error("Connection timeout")
            self._state.mark_failed("Connection timeout")
            return False
        except OSError as e:
            logger.error(f"Connection failed: {e}")
            self._state.mark_failed(str(e))
            return False
        except Exception as e:
            logger.error(f"Connection error: {e}")
            self._state.mark_failed(str(e))
            return False
    
    async def _authenticate(self) -> bool:
        """Perform authentication handshake."""
        # Send auth request
        password_hash = hashlib.sha256(
            self._config.password.encode('utf-8')
        ).hexdigest()
        
        auth_msg = self._encoder.encode_auth_request(
            password_hash=password_hash,
            client_info={
                "name": self._config.name,
                "version": self._config.version,
            }
        )
        
        await self._socket.write(auth_msg)
        
        # Wait for response
        data = await asyncio.wait_for(
            self._socket.read(self._config.buffer_size),
            timeout=self._config.connect_timeout
        )
        
        if not data:
            return False
        
        self._decoder.feed(data)
        message = self._decoder.decode_one()
        
        if message is None:
            return False
        
        if message.message_type == MessageType.AUTH_SUCCESS:
            self._session_token = message.payload.get("session_token")
            self._server_info = message.payload.get("server_info", {})
            return True
        
        if message.message_type == MessageType.AUTH_FAILURE:
            reason = message.payload.get("reason", "Unknown")
            logger.error(f"Authentication failed: {reason}")
            return False
        
        return False
    
    async def disconnect(self) -> None:
        """Disconnect from the server."""
        self._should_reconnect = False
        
        if self._reconnect_task:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass
        
        if self._connection:
            await self._connection.stop()
            self._connection = None
        
        if self._socket:
            await self._socket.close()
            self._socket = None
        
        self._state.mark_disconnected()
        
        # Run disconnect hooks
        for hook in self._on_disconnect:
            try:
                await hook(self)
            except Exception as e:
                logger.error(f"Error in disconnect hook: {e}")
        
        logger.info("Disconnected")
    
    async def _handle_disconnect(self, connection: Connection) -> None:
        """Handle disconnection."""
        self._state.mark_disconnected()
        
        # Run disconnect hooks
        for hook in self._on_disconnect:
            try:
                await hook(self)
            except Exception as e:
                logger.error(f"Error in disconnect hook: {e}")
        
        # Attempt reconnection if enabled
        if self._should_reconnect and self._config.reconnect_enabled:
            self._reconnect_task = asyncio.create_task(self._reconnect_loop())
    
    async def _reconnect_loop(self) -> None:
        """Reconnection loop with exponential backoff."""
        delay = self._config.reconnect_delay
        
        while self._should_reconnect:
            max_attempts = self._config.reconnect_attempts
            if max_attempts > 0 and self._reconnect_attempts >= max_attempts:
                logger.error(f"Max reconnection attempts ({max_attempts}) reached")
                break
            
            self._reconnect_attempts += 1
            logger.info(f"Reconnection attempt {self._reconnect_attempts}...")
            
            # Wait before reconnecting
            await asyncio.sleep(delay)
            
            # Attempt connection
            if await self._do_connect():
                # Run reconnect hooks
                for hook in self._on_reconnect:
                    try:
                        await hook(self)
                    except Exception as e:
                        logger.error(f"Error in reconnect hook: {e}")
                return
            
            # Exponential backoff
            delay = min(
                delay * self._config.reconnect_delay_multiplier,
                self._config.reconnect_delay_max
            )
    
    # === Message Handling ===
    
    async def _handle_message(
        self,
        connection: Connection,
        message: DecodedMessage
    ) -> None:
        """Handle incoming message."""
        msg_type = message.message_type
        
        # Handle RPC responses
        if msg_type in (MessageType.RPC_RESPONSE, MessageType.RPC_ERROR):
            corr_id = message.correlation_id
            future = self._pending_rpcs.get(corr_id)
            
            if future and not future.done():
                future.set_result(message.payload)
            
            return
        
        # Handle regular messages
        if msg_type == MessageType.MESSAGE:
            msg_type_str = message.get_message_type_str()
            data = message.get_data()
            
            msg = Message(type=msg_type_str, data=data)
            await self._message_router.route(
                message=msg,
                context=self,
                authenticated=True,
            )
    
    # === Sending ===
    
    async def send(self, message_type: str, data: Any) -> None:
        """
        Send a message to the server.
        
        Args:
            message_type: Message type
            data: Message data
        """
        if not self._connection or not self._state.is_connected:
            raise ConnectionError("Not connected")
        
        await self._connection.send_message(message_type, data)
    
    async def _send_rpc_request(self, method: str, params: dict) -> int:
        """
        Internal method to send RPC request.
        
        Returns:
            Correlation ID
        """
        if not self._connection:
            raise ConnectionError("Not connected")
        
        # Send request - Connection handles the pending RPC tracking
        corr_id = await self._connection.send_rpc_request(method, params)
        return corr_id
    
    async def _wait_for_rpc_response(self, correlation_id: int) -> Any:
        """
        Internal method to wait for RPC response.
        
        Returns:
            Response payload
        """
        if not self._connection:
            raise ConnectionError("Not connected")
        
        # Use Connection's RPC response waiting
        return await self._connection.wait_for_rpc_response(correlation_id)
    
    # === Properties ===
    
    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._state.is_connected
    
    @property
    def is_authenticated(self) -> bool:
        """Check if authenticated."""
        return self._session_token is not None
    
    @property
    def state(self) -> ConnectionState:
        """Get connection state."""
        return self._state.state
    
    @property
    def rpc(self) -> RPC:
        """Get RPC interface."""
        return self._rpc
    
    @property
    def config(self) -> ClientDescriptor:
        """Get client configuration."""
        return self._config
    
    @property
    def server_info(self) -> Dict[str, Any]:
        """Get server info from authentication."""
        return self._server_info
    
    @property
    def session_token(self) -> Optional[str]:
        """Get session token."""
        return self._session_token
    
    def health(self) -> dict:
        """Get connection health info."""
        return {
            "connected": self._state.is_connected,
            "state": self._state.state.name,
            "authenticated": self.is_authenticated,
            "reconnect_attempts": self._reconnect_attempts,
            "server_info": self._server_info,
        }
