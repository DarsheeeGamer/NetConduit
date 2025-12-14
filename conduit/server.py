"""
Conduit Server

The main server class for accepting and handling client connections.
"""

import asyncio
import hashlib
from typing import Any, Callable, Dict, List, Optional, Awaitable, Union
import logging

from .data.descriptors import ServerDescriptor
from .transport import TCPServer, TCPSocket, AuthHandler
from .protocol import ProtocolEncoder, ProtocolDecoder, MessageType, DecodedMessage
from .connection import Connection, ConnectionPool
from .messages import MessageRouter, Message
from .rpc import RPCRegistry, RPCDispatcher
from .response import Response, Error

logger = logging.getLogger(__name__)


# Callback types
LifecycleHook = Callable[['Server'], Awaitable[None]]
ConnectionHook = Callable[[Connection], Awaitable[None]]
MessageHandler = Callable[[Connection, Any], Awaitable[Any]]


class Server:
    """
    Conduit Server.
    
    Accepts client connections and handles messages/RPC calls.
    
    Usage:
        server = Server(ServerDescriptor(password="secret123"))
        
        @server.on("hello")
        async def handle_hello(client, data):
            return {"message": f"Hello, {data.get('name', 'client')}!"}
        
        @server.rpc
        async def add(request: AddRequest) -> int:
            return request.a + request.b
        
        await server.run()
    """
    
    def __init__(self, config: ServerDescriptor):
        """
        Initialize server.
        
        Args:
            config: Server configuration
        """
        self._config = config
        
        # TCP server
        self._tcp_server = TCPServer(
            host=config.host,
            port=config.port,
            ipv6=config.ipv6,
            max_connections=config.max_connections,
        )
        
        # Authentication
        self._auth_handler = AuthHandler(
            password=config.password,
            session_timeout=config.connection_timeout,
        )
        
        # Connection pool
        self._pool = ConnectionPool(max_connections=config.max_connections)
        
        # Message routing
        self._message_router = MessageRouter()
        
        # RPC
        self._rpc_registry = RPCRegistry()
        self._rpc_dispatcher = RPCDispatcher(self._rpc_registry)
        
        # Protocol
        self._encoder = ProtocolEncoder(enable_compression=config.enable_compression)
        
        # Response helpers
        self._response = Response()
        self._error = Error()
        
        # Lifecycle hooks
        self._on_startup: List[LifecycleHook] = []
        self._on_shutdown: List[LifecycleHook] = []
        self._on_connect: List[ConnectionHook] = []
        self._on_disconnect: List[ConnectionHook] = []
        
        # State
        self._running = False
    
    # === Decorators ===
    
    def on(
        self,
        message_type: str,
        requires_auth: bool = True
    ) -> Callable:
        """
        Decorator to register a message handler.
        
        Args:
            message_type: Type of message to handle
            requires_auth: Whether authentication is required
            
        Returns:
            Decorator function
        """
        def decorator(handler: MessageHandler) -> MessageHandler:
            self._message_router.register(
                message_type=message_type,
                handler=handler,
                requires_auth=requires_auth,
            )
            return handler
        return decorator
    
    def rpc(
        self,
        name: Optional[str] = None,
        requires_auth: bool = True
    ) -> Callable:
        """
        Decorator to register an RPC method.
        
        Args:
            name: Optional method name (defaults to function name)
            requires_auth: Whether authentication is required
            
        Returns:
            Decorator function
        """
        # Handle both @server.rpc and @server.rpc(name="xxx")
        if callable(name):
            # Called as @server.rpc without parentheses
            handler = name
            self._rpc_registry.register(handler)
            return handler
        
        def decorator(handler: Callable) -> Callable:
            self._rpc_registry.register(handler, name=name, requires_auth=requires_auth)
            return handler
        return decorator
    
    def on_startup(self, handler: LifecycleHook) -> LifecycleHook:
        """Register startup hook."""
        self._on_startup.append(handler)
        return handler
    
    def on_shutdown(self, handler: LifecycleHook) -> LifecycleHook:
        """Register shutdown hook."""
        self._on_shutdown.append(handler)
        return handler
    
    def on_client_connect(self, handler: ConnectionHook) -> ConnectionHook:
        """Register client connect hook."""
        self._on_connect.append(handler)
        return handler
    
    def on_client_disconnect(self, handler: ConnectionHook) -> ConnectionHook:
        """Register client disconnect hook."""
        self._on_disconnect.append(handler)
        return handler
    
    # === Server Lifecycle ===
    
    async def run(self) -> None:
        """Start the server and run until stopped."""
        await self.start()
        
        try:
            await self._tcp_server.wait_until_stopped()
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop()
    
    async def start(self) -> None:
        """Start the server (without blocking)."""
        if self._running:
            return
        
        logger.info(f"Starting server {self._config.name} v{self._config.version}")
        
        # Run startup hooks
        for hook in self._on_startup:
            await hook(self)
        
        # Setup connection pool callbacks
        self._pool.set_callbacks(
            on_connect=self._handle_client_connect,
            on_disconnect=self._handle_client_disconnect,
        )
        
        # Set handler and start TCP server
        self._tcp_server.set_handler(self._handle_new_connection)
        await self._tcp_server.start()
        
        self._running = True
        
        logger.info(f"Server listening on {self._config.host}:{self._config.port}")
    
    async def stop(self) -> None:
        """Stop the server."""
        if not self._running:
            return
        
        logger.info("Stopping server...")
        
        self._running = False
        
        # Close all connections
        await self._pool.close_all()
        
        # Stop TCP server
        await self._tcp_server.stop()
        
        # Run shutdown hooks
        for hook in self._on_shutdown:
            await hook(self)
        
        logger.info("Server stopped")
    
    # === Connection Handling ===
    
    async def _handle_new_connection(self, socket: TCPSocket) -> None:
        """Handle a new client connection."""
        remote = socket.remote_address
        logger.debug(f"New connection from {remote}")
        
        decoder = ProtocolDecoder()
        encoder = ProtocolEncoder(enable_compression=self._config.enable_compression)
        
        try:
            # Authenticate within timeout
            authenticated = await asyncio.wait_for(
                self._authenticate_client(socket, decoder, encoder),
                timeout=self._config.auth_timeout
            )
            
            if not authenticated:
                logger.warning(f"Authentication failed from {remote}")
                return
            
            # Create connection object
            connection = Connection(
                socket=socket,
                encoder=encoder,
                decoder=decoder,
                send_queue_size=self._config.send_queue_size,
                receive_queue_size=self._config.receive_queue_size,
                heartbeat_interval=self._config.heartbeat_interval,
                heartbeat_timeout=self._config.heartbeat_timeout,
                enable_backpressure=self._config.enable_backpressure,
            )
            
            # Add to pool
            if not await self._pool.add(connection):
                logger.warning(f"Connection pool full, rejecting {remote}")
                return
            
            # Set message handler
            connection.set_message_handler(self._handle_message)
            
            # Mark as authenticated (server already authenticated above)
            connection.mark_authenticated()
            
            # Start connection processing
            await connection.start()
            
            # Keep alive until stopped
            while connection.is_connected:
                await asyncio.sleep(1)
                
        except asyncio.TimeoutError:
            logger.warning(f"Authentication timeout from {remote}")
        except Exception as e:
            logger.error(f"Error handling connection from {remote}: {e}")
    
    async def _authenticate_client(
        self,
        socket: TCPSocket,
        decoder: ProtocolDecoder,
        encoder: ProtocolEncoder
    ) -> bool:
        """
        Perform authentication handshake.
        
        Returns:
            True if authenticated
        """
        # Read auth request
        data = await socket.read(self._config.buffer_size)
        if not data:
            return False
        
        decoder.feed(data)
        message = decoder.decode_one()
        
        if message is None:
            return False
        
        if message.message_type != MessageType.AUTH_REQUEST:
            return False
        
        # Verify password
        payload = message.payload
        password_hash = payload.get("password_hash", "")
        client_info = payload.get("client_info", {})
        
        if not self._auth_handler.verify_simple(password_hash):
            # Send failure
            fail_msg = encoder.encode_auth_failure("Invalid password")
            await socket.write(fail_msg)
            return False
        
        # Create session
        import uuid
        client_id = str(uuid.uuid4())
        session = self._auth_handler.create_session(client_id, client_info)
        
        # Send success
        success_msg = encoder.encode_auth_success(
            session_token=session.token,
            server_info={
                "name": self._config.name,
                "version": self._config.version,
            }
        )
        await socket.write(success_msg)
        
        return True
    
    async def _handle_client_connect(self, connection: Connection) -> None:
        """Called when client connects and authenticates."""
        for hook in self._on_connect:
            try:
                await hook(connection)
            except Exception as e:
                logger.error(f"Error in connect hook: {e}")
    
    async def _handle_client_disconnect(self, connection: Connection) -> None:
        """Called when client disconnects."""
        for hook in self._on_disconnect:
            try:
                await hook(connection)
            except Exception as e:
                logger.error(f"Error in disconnect hook: {e}")
    
    # === Message Handling ===
    
    async def _handle_message(
        self,
        connection: Connection,
        message: DecodedMessage
    ) -> None:
        """Handle incoming message."""
        msg_type = message.message_type
        
        # Handle RPC requests
        if msg_type == MessageType.RPC_REQUEST:
            await self._handle_rpc_request(connection, message)
            return
        
        # Handle regular messages
        if msg_type == MessageType.MESSAGE:
            await self._handle_regular_message(connection, message)
            return
    
    async def _handle_rpc_request(
        self,
        connection: Connection,
        message: DecodedMessage
    ) -> None:
        """Handle RPC request."""
        method = message.get_rpc_method()
        params = message.get_rpc_params() or {}
        corr_id = message.correlation_id
        
        # Dispatch
        result = await self._rpc_dispatcher.dispatch(
            method=method,
            params=params,
            authenticated=connection.is_authenticated,
        )
        
        # Send response
        await connection.send_rpc_response(result, corr_id)
    
    async def _handle_regular_message(
        self,
        connection: Connection,
        message: DecodedMessage
    ) -> None:
        """Handle regular message."""
        msg_type_str = message.get_message_type_str()
        data = message.get_data()
        
        # Create message object
        msg = Message(type=msg_type_str, data=data)
        
        # Route to handler
        response = await self._message_router.route(
            message=msg,
            context=connection,
            authenticated=connection.is_authenticated,
        )
        
        # If handler returns response, send it back
        if response is not None:
            await connection.send_message(msg_type_str + "_response", response)
    
    # === Broadcasting ===
    
    async def broadcast(
        self,
        message_type: str,
        data: Any,
        exclude: Optional[set] = None
    ) -> int:
        """
        Broadcast message to all connected clients.
        
        Args:
            message_type: Message type
            data: Message data
            exclude: Set of connection IDs to exclude
            
        Returns:
            Number of clients message was sent to
        """
        return await self._pool.broadcast(message_type, data, exclude)
    
    # === Properties ===
    
    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._running
    
    @property
    def connection_count(self) -> int:
        """Get number of connected clients."""
        return self._pool.count
    
    @property
    def connections(self) -> List[Connection]:
        """Get all connections."""
        return self._pool.get_all()
    
    @property
    def config(self) -> ServerDescriptor:
        """Get server configuration."""
        return self._config
    
    @property
    def address(self) -> tuple:
        """Get server address."""
        return (self._config.host, self._config.port)
    
    @property
    def response(self) -> Response:
        """Get response helper."""
        return self._response
    
    @property
    def error(self) -> Error:
        """Get error helper."""
        return self._error
