"""
Conduit Protocol Encoder

Encodes messages into binary format for transmission.
"""

import time
from typing import Any, Optional
import msgpack

from .format import (
    MessageHeader,
    MessageType,
    MessageFlags,
    HEADER_SIZE,
    MAX_PAYLOAD_SIZE,
)


class ProtocolEncoder:
    """Encodes messages into binary protocol format."""
    
    def __init__(self, enable_compression: bool = False):
        """
        Initialize encoder.
        
        Args:
            enable_compression: Whether to compress large payloads
        """
        self.enable_compression = enable_compression
        self._correlation_counter = 0
    
    def _next_correlation_id(self) -> int:
        """Generate next correlation ID."""
        self._correlation_counter += 1
        return self._correlation_counter
    
    def encode(
        self,
        message_type: MessageType,
        payload: Any = None,
        correlation_id: Optional[int] = None,
        flags: MessageFlags = MessageFlags.NONE,
    ) -> bytes:
        """
        Encode a message into binary format.
        
        Args:
            message_type: Type of message
            payload: Message payload (will be serialized with msgpack)
            correlation_id: Optional correlation ID (auto-generated if None for RPC)
            flags: Message flags
            
        Returns:
            Complete binary message (header + payload)
        """
        # Serialize payload
        if payload is not None:
            payload_bytes = msgpack.packb(payload, use_bin_type=True)
        else:
            payload_bytes = b''
        
        # Check payload size
        if len(payload_bytes) > MAX_PAYLOAD_SIZE:
            raise ValueError(f"Payload too large: {len(payload_bytes)} > {MAX_PAYLOAD_SIZE}")
        
        # Compress if enabled and beneficial
        if self.enable_compression and len(payload_bytes) > 1024:
            import zlib
            compressed = zlib.compress(payload_bytes, level=6)
            if len(compressed) < len(payload_bytes):
                payload_bytes = compressed
                flags |= MessageFlags.COMPRESSED
        
        # Auto-generate correlation ID for RPC requests
        if correlation_id is None and message_type == MessageType.RPC_REQUEST:
            correlation_id = self._next_correlation_id()
        
        # Create header
        header = MessageHeader.create(
            message_type=message_type,
            content_length=len(payload_bytes),
            correlation_id=correlation_id or 0,
            flags=flags,
        )
        
        # Combine header and payload
        return header.to_bytes() + payload_bytes
    
    def encode_message(
        self,
        message_type_str: str,
        data: Any,
        correlation_id: Optional[int] = None,
    ) -> bytes:
        """
        Encode a regular message.
        
        Args:
            message_type_str: String message type (e.g., "hello", "chat")
            data: Message data
            correlation_id: Optional correlation ID
            
        Returns:
            Encoded message bytes
        """
        payload = {
            "type": message_type_str,
            "data": data,
        }
        return self.encode(
            MessageType.MESSAGE,
            payload,
            correlation_id=correlation_id,
        )
    
    def encode_rpc_request(
        self,
        method: str,
        params: Optional[dict] = None,
        correlation_id: Optional[int] = None,
    ) -> tuple[bytes, int]:
        """
        Encode an RPC request.
        
        Args:
            method: RPC method name
            params: Method parameters
            correlation_id: Optional correlation ID (auto-generated if None)
            
        Returns:
            Tuple of (encoded bytes, correlation_id)
        """
        if correlation_id is None:
            correlation_id = self._next_correlation_id()
        
        payload = {
            "method": method,
            "params": params or {},
        }
        
        encoded = self.encode(
            MessageType.RPC_REQUEST,
            payload,
            correlation_id=correlation_id,
        )
        
        return encoded, correlation_id
    
    def encode_rpc_response(
        self,
        result: Any,
        correlation_id: int,
        success: bool = True,
    ) -> bytes:
        """
        Encode an RPC response.
        
        Args:
            result: Response data
            correlation_id: Correlation ID from request
            success: Whether the call was successful
            
        Returns:
            Encoded response bytes
        """
        payload = {
            "success": success,
            "result": result,
        }
        
        message_type = MessageType.RPC_RESPONSE if success else MessageType.RPC_ERROR
        
        return self.encode(
            message_type,
            payload,
            correlation_id=correlation_id,
        )
    
    def encode_rpc_error(
        self,
        error_message: str,
        correlation_id: int,
        error_code: Optional[int] = None,
    ) -> bytes:
        """
        Encode an RPC error response.
        
        Args:
            error_message: Error message
            correlation_id: Correlation ID from request
            error_code: Optional error code
            
        Returns:
            Encoded error response bytes
        """
        payload = {
            "success": False,
            "error": error_message,
            "code": error_code,
        }
        
        return self.encode(
            MessageType.RPC_ERROR,
            payload,
            correlation_id=correlation_id,
        )
    
    def encode_auth_request(self, password_hash: str, client_info: dict) -> bytes:
        """
        Encode an authentication request.
        
        Args:
            password_hash: Hashed password
            client_info: Client information dict
            
        Returns:
            Encoded auth request bytes
        """
        payload = {
            "password_hash": password_hash,
            "client_info": client_info,
        }
        return self.encode(MessageType.AUTH_REQUEST, payload)
    
    def encode_auth_success(self, session_token: str, server_info: dict) -> bytes:
        """
        Encode an authentication success response.
        
        Args:
            session_token: Session token for client
            server_info: Server information dict
            
        Returns:
            Encoded auth success bytes
        """
        payload = {
            "session_token": session_token,
            "server_info": server_info,
        }
        return self.encode(MessageType.AUTH_SUCCESS, payload)
    
    def encode_auth_failure(self, reason: str) -> bytes:
        """
        Encode an authentication failure response.
        
        Args:
            reason: Failure reason
            
        Returns:
            Encoded auth failure bytes
        """
        payload = {"reason": reason}
        return self.encode(MessageType.AUTH_FAILURE, payload)
    
    def encode_heartbeat_ping(self) -> bytes:
        """Encode a heartbeat ping."""
        return self.encode(MessageType.HEARTBEAT_PING)
    
    def encode_heartbeat_pong(self) -> bytes:
        """Encode a heartbeat pong."""
        return self.encode(MessageType.HEARTBEAT_PONG)
    
    def encode_pause(self) -> bytes:
        """Encode a backpressure pause signal."""
        return self.encode(MessageType.PAUSE)
    
    def encode_resume(self) -> bytes:
        """Encode a backpressure resume signal."""
        return self.encode(MessageType.RESUME)
    
    def encode_ack(self, correlation_id: int) -> bytes:
        """Encode a message acknowledgment."""
        return self.encode(MessageType.ACK, correlation_id=correlation_id)
    
    def encode_nack(self, correlation_id: int, reason: str = "") -> bytes:
        """Encode a negative acknowledgment."""
        payload = {"reason": reason} if reason else None
        return self.encode(MessageType.NACK, payload, correlation_id=correlation_id)
    
    def encode_close(self, reason: str = "") -> bytes:
        """Encode a connection close request."""
        payload = {"reason": reason} if reason else None
        return self.encode(MessageType.CLOSE, payload)
    
    def encode_close_ack(self) -> bytes:
        """Encode a connection close acknowledgment."""
        return self.encode(MessageType.CLOSE_ACK)
    
    def encode_rpc_list(self, methods: list[dict]) -> bytes:
        """
        Encode RPC method list response.
        
        Args:
            methods: List of method info dicts
            
        Returns:
            Encoded response bytes
        """
        payload = {"methods": methods}
        return self.encode(MessageType.RPC_LIST, payload)
