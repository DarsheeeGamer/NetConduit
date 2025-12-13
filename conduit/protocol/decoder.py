"""
Conduit Protocol Decoder

Decodes binary messages from the wire format.
"""

from typing import Any, Optional, Tuple
import msgpack

from .format import (
    MessageHeader,
    MessageType,
    MessageFlags,
    HEADER_SIZE,
    MAX_PAYLOAD_SIZE,
)


class DecodeError(Exception):
    """Error during message decoding."""
    pass


class IncompleteMessageError(Exception):
    """Message is incomplete, need more data."""
    
    def __init__(self, bytes_needed: int):
        self.bytes_needed = bytes_needed
        super().__init__(f"Need {bytes_needed} more bytes")


class DecodedMessage:
    """Represents a decoded message."""
    
    def __init__(
        self,
        header: MessageHeader,
        payload: Any,
        raw_payload: bytes,
    ):
        self.header = header
        self.payload = payload
        self.raw_payload = raw_payload
    
    @property
    def message_type(self) -> MessageType:
        return self.header.message_type
    
    @property
    def correlation_id(self) -> int:
        return self.header.correlation_id
    
    @property
    def timestamp(self) -> int:
        return self.header.timestamp
    
    @property
    def flags(self) -> MessageFlags:
        return self.header.flags
    
    def is_compressed(self) -> bool:
        return bool(self.flags & MessageFlags.COMPRESSED)
    
    def get_message_type_str(self) -> Optional[str]:
        """Get string message type for MESSAGE types."""
        if self.message_type == MessageType.MESSAGE and isinstance(self.payload, dict):
            return self.payload.get("type")
        return None
    
    def get_data(self) -> Any:
        """Get message data for MESSAGE types."""
        if self.message_type == MessageType.MESSAGE and isinstance(self.payload, dict):
            return self.payload.get("data")
        return self.payload
    
    def get_rpc_method(self) -> Optional[str]:
        """Get RPC method name for RPC_REQUEST."""
        if self.message_type == MessageType.RPC_REQUEST and isinstance(self.payload, dict):
            return self.payload.get("method")
        return None
    
    def get_rpc_params(self) -> dict:
        """Get RPC parameters for RPC_REQUEST."""
        if self.message_type == MessageType.RPC_REQUEST and isinstance(self.payload, dict):
            return self.payload.get("params", {})
        return {}
    
    def get_rpc_result(self) -> Any:
        """Get RPC result for RPC_RESPONSE."""
        if self.message_type in (MessageType.RPC_RESPONSE, MessageType.RPC_ERROR):
            if isinstance(self.payload, dict):
                return self.payload.get("result")
        return None
    
    def get_rpc_error(self) -> Optional[str]:
        """Get RPC error message for RPC_ERROR."""
        if self.message_type == MessageType.RPC_ERROR and isinstance(self.payload, dict):
            return self.payload.get("error")
        return None
    
    def is_success(self) -> bool:
        """Check if RPC response indicates success."""
        if isinstance(self.payload, dict):
            return self.payload.get("success", True)
        return True
    
    def __repr__(self) -> str:
        return f"DecodedMessage(type={self.message_type.name}, corr_id={self.correlation_id})"


class ProtocolDecoder:
    """Decodes messages from binary protocol format."""
    
    def __init__(self):
        """Initialize decoder."""
        self._buffer = bytearray()
    
    def feed(self, data: bytes) -> None:
        """
        Add data to the internal buffer.
        
        Args:
            data: Received bytes to add to buffer
        """
        self._buffer.extend(data)
    
    def decode_one(self) -> Optional[DecodedMessage]:
        """
        Try to decode one complete message from buffer.
        
        Returns:
            DecodedMessage if a complete message is available, None otherwise
        """
        # Need at least a header
        if len(self._buffer) < HEADER_SIZE:
            return None
        
        try:
            # Parse header
            header = MessageHeader.from_bytes(bytes(self._buffer[:HEADER_SIZE]))
            header.validate()
            
            # Calculate total message size
            total_size = HEADER_SIZE + header.content_length
            
            # Check if we have the complete message
            if len(self._buffer) < total_size:
                return None
            
            # Extract payload
            raw_payload = bytes(self._buffer[HEADER_SIZE:total_size])
            
            # Remove message from buffer
            del self._buffer[:total_size]
            
            # Decompress if needed
            if header.flags & MessageFlags.COMPRESSED:
                import zlib
                raw_payload = zlib.decompress(raw_payload)
            
            # Deserialize payload
            if raw_payload:
                payload = msgpack.unpackb(raw_payload, raw=False)
            else:
                payload = None
            
            return DecodedMessage(header, payload, raw_payload)
            
        except Exception as e:
            raise DecodeError(f"Failed to decode message: {e}") from e
    
    def decode_all(self) -> list[DecodedMessage]:
        """
        Decode all complete messages from buffer.
        
        Returns:
            List of decoded messages
        """
        messages = []
        while True:
            msg = self.decode_one()
            if msg is None:
                break
            messages.append(msg)
        return messages
    
    @staticmethod
    def decode_single(data: bytes) -> DecodedMessage:
        """
        Decode a single complete message from bytes.
        
        Args:
            data: Complete message bytes
            
        Returns:
            Decoded message
            
        Raises:
            IncompleteMessageError: If data is incomplete
            DecodeError: If decoding fails
        """
        if len(data) < HEADER_SIZE:
            raise IncompleteMessageError(HEADER_SIZE - len(data))
        
        try:
            header = MessageHeader.from_bytes(data[:HEADER_SIZE])
            header.validate()
            
            total_size = HEADER_SIZE + header.content_length
            
            if len(data) < total_size:
                raise IncompleteMessageError(total_size - len(data))
            
            raw_payload = data[HEADER_SIZE:total_size]
            
            if header.flags & MessageFlags.COMPRESSED:
                import zlib
                raw_payload = zlib.decompress(raw_payload)
            
            if raw_payload:
                payload = msgpack.unpackb(raw_payload, raw=False)
            else:
                payload = None
            
            return DecodedMessage(header, payload, raw_payload)
            
        except (IncompleteMessageError, DecodeError):
            raise
        except Exception as e:
            raise DecodeError(f"Failed to decode message: {e}") from e
    
    def buffer_size(self) -> int:
        """Get current buffer size."""
        return len(self._buffer)
    
    def clear(self) -> None:
        """Clear the internal buffer."""
        self._buffer.clear()
    
    def peek_header(self) -> Optional[MessageHeader]:
        """
        Peek at the header without consuming it.
        
        Returns:
            MessageHeader if enough data, None otherwise
        """
        if len(self._buffer) < HEADER_SIZE:
            return None
        
        try:
            return MessageHeader.from_bytes(bytes(self._buffer[:HEADER_SIZE]))
        except Exception:
            return None
