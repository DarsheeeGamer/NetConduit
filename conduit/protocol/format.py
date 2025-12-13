"""
Conduit Protocol Format

Defines the binary protocol used for communication between client and server.
All messages follow a fixed header format followed by a variable-length payload.

Header Format (32 bytes):
| Field          | Offset | Size | Type   | Description                    |
|----------------|--------|------|--------|--------------------------------|
| Magic          | 0      | 4    | bytes  | b'CNDT' (protocol identifier)  |
| Version        | 4      | 2    | uint16 | Protocol version (1.0 = 0x0100)|
| Message Type   | 6      | 2    | uint16 | Message type enum              |
| Flags          | 8      | 2    | uint16 | Control flags                  |
| Reserved       | 10     | 2    | uint16 | Reserved for future use        |
| Content Length | 12     | 4    | uint32 | Payload length in bytes        |
| Correlation ID | 16     | 8    | uint64 | Match requests/responses       |
| Timestamp      | 24     | 8    | uint64 | Unix timestamp (milliseconds)  |
"""

import struct
from enum import IntEnum, IntFlag
from dataclasses import dataclass
from typing import Optional
import time


# Protocol constants
MAGIC = b'CNDT'
MAGIC_INT = 0x434E4454  # 'CNDT' as big-endian int
HEADER_SIZE = 32
MAX_PAYLOAD_SIZE = 100 * 1024 * 1024  # 100MB max payload
PROTOCOL_VERSION = 0x0100  # Version 1.0


class MessageType(IntEnum):
    """Message type identifiers."""
    
    # Regular messages
    MESSAGE = 0x0001           # Regular message with type and data
    
    # RPC messages
    RPC_REQUEST = 0x0002       # RPC method call
    RPC_RESPONSE = 0x0003      # RPC result (success)
    RPC_ERROR = 0x0004         # RPC error response
    
    # Control messages
    HEARTBEAT_PING = 0x0005    # Heartbeat ping
    HEARTBEAT_PONG = 0x0006    # Heartbeat pong
    
    # Authentication
    AUTH_REQUEST = 0x0007      # Authentication request
    AUTH_SUCCESS = 0x0008      # Authentication success
    AUTH_FAILURE = 0x0009      # Authentication failed
    
    # Flow control
    PAUSE = 0x000A             # Backpressure pause
    RESUME = 0x000B            # Backpressure resume
    
    # Acknowledgment
    ACK = 0x000C               # Message acknowledgment
    NACK = 0x000D              # Negative acknowledgment
    
    # Connection lifecycle
    CLOSE = 0x000E             # Connection close request
    CLOSE_ACK = 0x000F         # Connection close acknowledgment
    
    # Discovery
    RPC_LIST = 0x0010          # List available RPC methods


class MessageFlags(IntFlag):
    """Message flags for additional control."""
    
    NONE = 0x0000
    COMPRESSED = 0x0001        # Payload is compressed
    ENCRYPTED = 0x0002         # Payload is encrypted (beyond TLS)
    REQUIRE_ACK = 0x0004       # Sender expects acknowledgment
    PRIORITY = 0x0008          # High priority message
    FRAGMENT = 0x0010          # Message is fragmented
    LAST_FRAGMENT = 0x0020     # Last fragment of fragmented message
    BINARY = 0x0040            # Payload is binary (not text/JSON)


@dataclass
class MessageHeader:
    """Represents a protocol message header."""
    
    magic: bytes
    version: int
    message_type: MessageType
    flags: MessageFlags
    reserved: int
    content_length: int
    correlation_id: int
    timestamp: int
    
    # Header format: 4s = 4 bytes, H = uint16, I = uint32, Q = uint64
    # Big-endian (network byte order)
    STRUCT_FORMAT = '>4sHHHHIQQ'
    
    @classmethod
    def create(
        cls,
        message_type: MessageType,
        content_length: int,
        correlation_id: int = 0,
        flags: MessageFlags = MessageFlags.NONE,
        timestamp: Optional[int] = None
    ) -> 'MessageHeader':
        """Create a new message header."""
        if timestamp is None:
            timestamp = int(time.time() * 1000)  # Milliseconds
        
        return cls(
            magic=MAGIC,
            version=PROTOCOL_VERSION,
            message_type=message_type,
            flags=flags,
            reserved=0,
            content_length=content_length,
            correlation_id=correlation_id,
            timestamp=timestamp
        )
    
    def to_bytes(self) -> bytes:
        """Serialize header to bytes."""
        return struct.pack(
            self.STRUCT_FORMAT,
            self.magic,
            self.version,
            self.message_type,
            self.flags,
            self.reserved,
            self.content_length,
            self.correlation_id,
            self.timestamp
        )
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'MessageHeader':
        """Deserialize header from bytes."""
        if len(data) < HEADER_SIZE:
            raise ValueError(f"Header too short: expected {HEADER_SIZE}, got {len(data)}")
        
        unpacked = struct.unpack(cls.STRUCT_FORMAT, data[:HEADER_SIZE])
        
        magic = unpacked[0]
        if magic != MAGIC:
            raise ValueError(f"Invalid magic bytes: expected {MAGIC!r}, got {magic!r}")
        
        return cls(
            magic=magic,
            version=unpacked[1],
            message_type=MessageType(unpacked[2]),
            flags=MessageFlags(unpacked[3]),
            reserved=unpacked[4],
            content_length=unpacked[5],
            correlation_id=unpacked[6],
            timestamp=unpacked[7]
        )
    
    def validate(self) -> None:
        """Validate header fields."""
        if self.magic != MAGIC:
            raise ValueError(f"Invalid magic: {self.magic!r}")
        
        if self.version != PROTOCOL_VERSION:
            raise ValueError(f"Unsupported protocol version: {self.version:#06x}")
        
        if self.content_length > MAX_PAYLOAD_SIZE:
            raise ValueError(f"Content length exceeds maximum: {self.content_length} > {MAX_PAYLOAD_SIZE}")
    
    def is_control_message(self) -> bool:
        """Check if this is a control message (no payload expected)."""
        return self.message_type in (
            MessageType.HEARTBEAT_PING,
            MessageType.HEARTBEAT_PONG,
            MessageType.PAUSE,
            MessageType.RESUME,
            MessageType.ACK,
            MessageType.NACK,
            MessageType.CLOSE,
            MessageType.CLOSE_ACK,
        )
    
    def is_rpc(self) -> bool:
        """Check if this is an RPC message."""
        return self.message_type in (
            MessageType.RPC_REQUEST,
            MessageType.RPC_RESPONSE,
            MessageType.RPC_ERROR,
            MessageType.RPC_LIST,
        )
    
    def is_auth(self) -> bool:
        """Check if this is an authentication message."""
        return self.message_type in (
            MessageType.AUTH_REQUEST,
            MessageType.AUTH_SUCCESS,
            MessageType.AUTH_FAILURE,
        )


# Verify header size is correct
assert struct.calcsize(MessageHeader.STRUCT_FORMAT) == HEADER_SIZE, \
    f"Header struct size mismatch: {struct.calcsize(MessageHeader.STRUCT_FORMAT)} != {HEADER_SIZE}"
