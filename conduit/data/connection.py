"""
Connection Data Models

Pydantic models for connection-related data structures.
"""

from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class ConnectionState(str, Enum):
    """Connection state enumeration."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    AUTHENTICATING = "authenticating"
    CONNECTED = "connected"
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSING = "closing"
    CLOSED = "closed"
    FAILED = "failed"


class ConnectionInfo(BaseModel):
    """
    Information about a connection.
    
    Used to identify and describe connections.
    """
    client_id: str = Field(..., description="Unique client identifier")
    address: str = Field(..., description="Remote address")
    port: int = Field(..., description="Remote port")
    connected_at: datetime = Field(
        default_factory=datetime.now,
        description="Connection timestamp"
    )
    authenticated: bool = Field(default=False, description="Whether authenticated")
    session_token: Optional[str] = Field(default=None, description="Session token if authenticated")
    client_name: str = Field(default="", description="Client name from handshake")
    client_version: str = Field(default="", description="Client version from handshake")
    
    model_config = {
        "extra": "allow",
    }


class ConnectionHealth(BaseModel):
    """
    Health statistics for a connection.
    
    Used for monitoring connection status.
    """
    state: ConnectionState = Field(
        default=ConnectionState.DISCONNECTED,
        description="Current connection state"
    )
    connected: bool = Field(default=False, description="Whether connected")
    authenticated: bool = Field(default=False, description="Whether authenticated")
    
    # Timing
    connected_at: Optional[datetime] = Field(default=None, description="Connection time")
    last_heartbeat_sent: Optional[datetime] = Field(default=None, description="Last heartbeat sent")
    last_heartbeat_received: Optional[datetime] = Field(default=None, description="Last heartbeat received")
    last_message_sent: Optional[datetime] = Field(default=None, description="Last message sent")
    last_message_received: Optional[datetime] = Field(default=None, description="Last message received")
    
    # Latency
    latency_ms: float = Field(default=0, description="Current latency in milliseconds")
    avg_latency_ms: float = Field(default=0, description="Average latency in milliseconds")
    
    # Counters
    messages_sent: int = Field(default=0, description="Total messages sent")
    messages_received: int = Field(default=0, description="Total messages received")
    bytes_sent: int = Field(default=0, description="Total bytes sent")
    bytes_received: int = Field(default=0, description="Total bytes received")
    
    # Errors
    errors: int = Field(default=0, description="Total errors")
    reconnect_count: int = Field(default=0, description="Number of reconnections")
    
    # Queue status
    send_queue_size: int = Field(default=0, description="Current send queue size")
    receive_queue_size: int = Field(default=0, description="Current receive queue size")
    is_paused: bool = Field(default=False, description="Whether backpressure pause is active")
    
    model_config = {
        "extra": "allow",
    }
    
    def is_healthy(self) -> bool:
        """Check if connection is in a healthy state."""
        return (
            self.connected and 
            self.authenticated and 
            self.state == ConnectionState.ACTIVE and
            not self.is_paused
        )


class ClientInfo(BaseModel):
    """
    Information sent by client during authentication.
    """
    name: str = Field(default="conduit_client", description="Client name")
    version: str = Field(default="1.0.0", description="Client version")
    description: str = Field(default="", description="Client description")
    protocol_version: str = Field(default="1.0", description="Protocol version")
    capabilities: list[str] = Field(
        default_factory=list,
        description="Client capabilities"
    )
    
    model_config = {
        "extra": "allow",
    }


class ServerInfo(BaseModel):
    """
    Information sent by server on successful authentication.
    """
    name: str = Field(default="conduit_server", description="Server name")
    version: str = Field(default="1.0.0", description="Server version")
    description: str = Field(default="", description="Server description")
    protocol_version: str = Field(default="1.0", description="Protocol version")
    heartbeat_interval: int = Field(default=30, description="Expected heartbeat interval")
    capabilities: list[str] = Field(
        default_factory=list,
        description="Server capabilities"
    )
    
    model_config = {
        "extra": "allow",
    }
