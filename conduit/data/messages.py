"""
Message Data Models

Pydantic models for all message types in the protocol.
These models are used for serialization/deserialization and validation.
"""

from typing import Any, Optional, Dict, List
from pydantic import BaseModel, Field
from datetime import datetime


class MessageData(BaseModel):
    """
    Base model for regular messages.
    
    Used for MESSAGE type packets with a string type and arbitrary data.
    """
    type: str = Field(..., description="Message type identifier")
    data: Any = Field(default=None, description="Message payload data")
    
    model_config = {
        "extra": "allow",  # Allow extra fields in data
    }


class RPCRequest(BaseModel):
    """
    RPC request data model.
    
    Sent from client to server to invoke a remote procedure.
    """
    method: str = Field(..., description="RPC method name to call")
    params: Dict[str, Any] = Field(default_factory=dict, description="Method parameters")
    
    model_config = {
        "extra": "forbid",
    }


class RPCResponse(BaseModel):
    """
    RPC response data model.
    
    Sent from server to client with the result of an RPC call.
    """
    success: bool = Field(default=True, description="Whether the call succeeded")
    result: Any = Field(default=None, description="Return value from the RPC method")
    
    model_config = {
        "extra": "allow",
    }


class RPCError(BaseModel):
    """
    RPC error data model.
    
    Sent from server to client when an RPC call fails.
    """
    success: bool = Field(default=False, description="Always False for errors")
    error: str = Field(..., description="Error message")
    code: Optional[int] = Field(default=None, description="Optional error code")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    
    model_config = {
        "extra": "forbid",
    }


class AuthRequest(BaseModel):
    """
    Authentication request data model.
    
    Sent from client to server to authenticate.
    """
    password_hash: str = Field(..., description="SHA256 hash of password + salt")
    client_info: Dict[str, Any] = Field(
        default_factory=dict,
        description="Client information (name, version, etc.)"
    )
    protocol_version: str = Field(default="1.0", description="Protocol version client supports")
    
    model_config = {
        "extra": "forbid",
    }


class AuthSuccess(BaseModel):
    """
    Authentication success response.
    
    Sent from server to client on successful authentication.
    """
    session_token: str = Field(..., description="Session token for this connection")
    server_info: Dict[str, Any] = Field(
        default_factory=dict,
        description="Server information (name, version, etc.)"
    )
    heartbeat_interval: int = Field(default=30, description="Expected heartbeat interval")
    
    model_config = {
        "extra": "forbid",
    }


class AuthFailure(BaseModel):
    """
    Authentication failure response.
    
    Sent from server to client when authentication fails.
    """
    reason: str = Field(..., description="Reason for authentication failure")
    retry_allowed: bool = Field(default=False, description="Whether client can retry")
    
    model_config = {
        "extra": "forbid",
    }


class HeartbeatData(BaseModel):
    """
    Heartbeat message data.
    
    Usually empty, but can contain timing info.
    """
    timestamp: Optional[int] = Field(default=None, description="Sender timestamp in ms")
    
    model_config = {
        "extra": "allow",
    }


class CloseReason(BaseModel):
    """
    Connection close data.
    
    Sent when gracefully closing a connection.
    """
    reason: str = Field(default="", description="Reason for closing")
    code: int = Field(default=0, description="Close code")
    
    model_config = {
        "extra": "forbid",
    }


class AckData(BaseModel):
    """
    Acknowledgment data.
    
    Used for message acknowledgments.
    """
    correlation_id: int = Field(..., description="ID of message being acknowledged")
    
    model_config = {
        "extra": "forbid",
    }


class NackData(BaseModel):
    """
    Negative acknowledgment data.
    
    Used when a message cannot be processed.
    """
    correlation_id: int = Field(..., description="ID of message being rejected")
    reason: str = Field(default="", description="Reason for rejection")
    
    model_config = {
        "extra": "forbid",
    }
