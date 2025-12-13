"""
Conduit Data Models

Pydantic models for type-safe data structures used throughout the library.
All data that flows through the system should be defined here.
"""

from .descriptors import ServerDescriptor, ClientDescriptor
from .messages import (
    MessageData,
    RPCRequest,
    RPCResponse,
    RPCError,
    AuthRequest,
    AuthSuccess,
    AuthFailure,
)
from .rpc import RPCMethodInfo, RPCListResponse
from .connection import ConnectionInfo, ConnectionHealth

__all__ = [
    # Descriptors
    "ServerDescriptor",
    "ClientDescriptor",
    
    # Messages
    "MessageData",
    "RPCRequest",
    "RPCResponse",
    "RPCError",
    "AuthRequest",
    "AuthSuccess",
    "AuthFailure",
    
    # RPC
    "RPCMethodInfo",
    "RPCListResponse",
    
    # Connection
    "ConnectionInfo",
    "ConnectionHealth",
]
