"""
RPC Data Models

Pydantic models for RPC-related data structures.
"""

from typing import Any, Optional, Dict, List
from pydantic import BaseModel, Field


class RPCMethodInfo(BaseModel):
    """
    Information about an RPC method.
    
    Used in RPC discovery responses.
    """
    name: str = Field(..., description="Method name")
    description: str = Field(default="", description="Method description/docstring")
    parameters: Dict[str, str] = Field(
        default_factory=dict,
        description="Parameter name -> type mapping"
    )
    return_type: str = Field(default="Any", description="Return type")
    requires_auth: bool = Field(default=True, description="Whether method requires authentication")
    
    model_config = {
        "extra": "forbid",
    }


class RPCListResponse(BaseModel):
    """
    Response for RPC list/discovery request.
    
    Contains all available RPC methods on the server.
    """
    methods: List[RPCMethodInfo] = Field(
        default_factory=list,
        description="List of available RPC methods"
    )
    server_name: str = Field(default="", description="Server name")
    server_version: str = Field(default="", description="Server version")
    
    model_config = {
        "extra": "forbid",
    }


class RPCCallResult(BaseModel):
    """
    Result of an RPC call on the client side.
    
    Wraps the response with metadata.
    """
    success: bool = Field(..., description="Whether call succeeded")
    result: Any = Field(default=None, description="Return value")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    error_code: Optional[int] = Field(default=None, description="Error code if failed")
    correlation_id: int = Field(..., description="Request correlation ID")
    elapsed_ms: float = Field(default=0, description="Time taken in milliseconds")
    
    model_config = {
        "extra": "allow",
    }
