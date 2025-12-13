"""
Message Class

Represents a message in the Conduit system.
"""

from typing import Any, Optional, Dict
from dataclasses import dataclass, field
import time
import uuid


@dataclass
class Message:
    """
    Represents a message to be sent or received.
    
    Attributes:
        type: Message type identifier (e.g., "hello", "chat", "file")
        data: Message payload data
        correlation_id: Optional ID to correlate request/response
        timestamp: Message creation timestamp in milliseconds
        metadata: Optional additional metadata
    """
    
    type: str
    data: Any = None
    correlation_id: Optional[int] = None
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Internal tracking
    _id: str = field(default_factory=lambda: str(uuid.uuid4()))
    _acknowledged: bool = False
    _sent_at: Optional[int] = None
    _received_at: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "type": self.type,
            "data": self.data,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create from dictionary."""
        return cls(
            type=data.get("type", ""),
            data=data.get("data"),
            correlation_id=data.get("correlation_id"),
            timestamp=data.get("timestamp", int(time.time() * 1000)),
            metadata=data.get("metadata", {}),
        )
    
    def mark_sent(self) -> None:
        """Mark message as sent."""
        self._sent_at = int(time.time() * 1000)
    
    def mark_received(self) -> None:
        """Mark message as received."""
        self._received_at = int(time.time() * 1000)
    
    def mark_acknowledged(self) -> None:
        """Mark message as acknowledged."""
        self._acknowledged = True
    
    @property
    def is_acknowledged(self) -> bool:
        """Check if message has been acknowledged."""
        return self._acknowledged
    
    @property
    def latency_ms(self) -> Optional[float]:
        """Calculate latency if both sent and received times are available."""
        if self._sent_at and self._received_at:
            return self._received_at - self._sent_at
        return None
    
    def __repr__(self) -> str:
        return f"Message(type={self.type!r}, data={self.data!r}, id={self._id[:8]})"


@dataclass
class PendingMessage:
    """
    A message waiting to be sent or acknowledged.
    """
    
    message: Message
    retries: int = 0
    max_retries: int = 3
    queued_at: int = field(default_factory=lambda: int(time.time() * 1000))
    last_attempt: Optional[int] = None
    
    def can_retry(self) -> bool:
        """Check if message can be retried."""
        return self.retries < self.max_retries
    
    def record_attempt(self) -> None:
        """Record a send attempt."""
        self.retries += 1
        self.last_attempt = int(time.time() * 1000)
    
    @property
    def age_ms(self) -> int:
        """Get message age in milliseconds."""
        return int(time.time() * 1000) - self.queued_at
