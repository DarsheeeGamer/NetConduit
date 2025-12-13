"""
Conduit - Production-Ready Async Bidirectional TCP Communication Library

A Python library for secure, asynchronous, bidirectional communication over raw TCP.
Features: Custom binary protocol, password authentication, type-safe RPC with Pydantic,
heartbeat monitoring, backpressure flow control, and Flask/FastAPI-inspired API.

Usage:
    from conduit import Server, Client, ServerDescriptor, ClientDescriptor
    from conduit import RPC, data, Response, Error
    
    # Server
    server = Server(ServerDescriptor(password="secret"))
    
    @server.on("hello")
    async def handle_hello(client, data):
        return {"message": f"Hello, {data['name']}!"}
    
    @server.rpc
    async def add(request: AddRequest) -> int:
        return request.a + request.b
    
    await server.run()
    
    # Client
    client = Client(ClientDescriptor(
        server_host="localhost",
        server_port=8080,
        password="secret"
    ))
    
    await client.connect()
    result = await client.rpc.call("add", args=data(a=10, b=20))
"""

# Version info
from .__version__ import __version__, __protocol_version__

# Main classes
from .server import Server
from .client import Client

# Configuration
from .data.descriptors import ServerDescriptor, ClientDescriptor

# Messages
from .messages import Message

# RPC
from .rpc import RPC, data

# Response helpers
from .response import Response, Error

# Connection
from .connection import Connection, ConnectionPool

# Data models
from .data import (
    MessageData,
    RPCRequest,
    RPCResponse,
    RPCError,
    AuthRequest,
    AuthSuccess,
    AuthFailure,
    RPCMethodInfo,
    RPCListResponse,
    ConnectionInfo,
    ConnectionHealth,
)

# Protocol (for advanced usage)
from .protocol import (
    MessageType,
    MessageFlags,
    MessageHeader,
    ProtocolEncoder,
    ProtocolDecoder,
    MAGIC,
    HEADER_SIZE,
    PROTOCOL_VERSION,
)

# Transport (for advanced usage)
from .transport import ConnectionState

# Exceptions
from .exceptions import (
    ConduitError,
    ConnectionError,
    AuthenticationError,
    ProtocolError,
    TimeoutError,
    RPCError as RPCException,
    ValidationError,
    BackpressureError,
    QueueFullError,
    NotConnectedError,
    AlreadyConnectedError,
    ServerError,
    ClientError,
)

__all__ = [
    # Version
    "__version__",
    "__protocol_version__",
    
    # Main classes
    "Server",
    "Client",
    
    # Configuration
    "ServerDescriptor",
    "ClientDescriptor",
    
    # Messages
    "Message",
    
    # RPC
    "RPC",
    "data",
    
    # Response helpers
    "Response",
    "Error",
    
    # Connection
    "Connection",
    "ConnectionPool",
    
    # Data models
    "MessageData",
    "RPCRequest",
    "RPCResponse",
    "RPCError",
    "AuthRequest",
    "AuthSuccess",
    "AuthFailure",
    "RPCMethodInfo",
    "RPCListResponse",
    "ConnectionInfo",
    "ConnectionHealth",
    
    # Protocol
    "MessageType",
    "MessageFlags",
    "MessageHeader",
    "ProtocolEncoder",
    "ProtocolDecoder",
    "MAGIC",
    "HEADER_SIZE",
    "PROTOCOL_VERSION",
    
    # Transport
    "ConnectionState",
    
    # Exceptions
    "ConduitError",
    "ConnectionError",
    "AuthenticationError",
    "ProtocolError",
    "TimeoutError",
    "RPCException",
    "ValidationError",
    "BackpressureError",
    "QueueFullError",
    "NotConnectedError",
    "AlreadyConnectedError",
    "ServerError",
    "ClientError",
]
