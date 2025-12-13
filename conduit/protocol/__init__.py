"""
Conduit Protocol Package

Exports for the protocol layer.
"""

from .format import (
    MAGIC,
    HEADER_SIZE,
    MAX_PAYLOAD_SIZE,
    PROTOCOL_VERSION,
    MessageType,
    MessageFlags,
    MessageHeader,
)

from .encoder import ProtocolEncoder

from .decoder import (
    ProtocolDecoder,
    DecodedMessage,
    DecodeError,
    IncompleteMessageError,
)

__all__ = [
    # Constants
    "MAGIC",
    "HEADER_SIZE",
    "MAX_PAYLOAD_SIZE",
    "PROTOCOL_VERSION",
    
    # Enums
    "MessageType",
    "MessageFlags",
    
    # Header
    "MessageHeader",
    
    # Encoder/Decoder
    "ProtocolEncoder",
    "ProtocolDecoder",
    "DecodedMessage",
    
    # Exceptions
    "DecodeError",
    "IncompleteMessageError",
]
