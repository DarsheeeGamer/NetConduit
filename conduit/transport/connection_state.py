"""
Connection State Machine

Manages connection states and transitions.
"""

from enum import Enum, auto
from typing import Optional, Set, Dict, Callable
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Connection state enumeration."""
    
    DISCONNECTED = auto()
    CONNECTING = auto()
    AUTHENTICATING = auto()
    CONNECTED = auto()
    ACTIVE = auto()
    PAUSED = auto()
    CLOSING = auto()
    CLOSED = auto()
    FAILED = auto()


# Valid state transitions
VALID_TRANSITIONS: Dict[ConnectionState, Set[ConnectionState]] = {
    ConnectionState.DISCONNECTED: {
        ConnectionState.CONNECTING,
    },
    ConnectionState.CONNECTING: {
        ConnectionState.AUTHENTICATING,
        ConnectionState.CONNECTED,  # Allow direct connection for server-side (already authenticated)
        ConnectionState.FAILED,
        ConnectionState.DISCONNECTED,
        ConnectionState.CLOSING,  # Allow cleanup
    },
    ConnectionState.AUTHENTICATING: {
        ConnectionState.CONNECTED,
        ConnectionState.FAILED,
        ConnectionState.DISCONNECTED,
        ConnectionState.CLOSING,  # Allow cleanup
    },
    ConnectionState.CONNECTED: {
        ConnectionState.ACTIVE,
        ConnectionState.FAILED,
        ConnectionState.DISCONNECTED,
        ConnectionState.CLOSING,
    },
    ConnectionState.ACTIVE: {
        ConnectionState.PAUSED,
        ConnectionState.CLOSING,
        ConnectionState.DISCONNECTED,
        ConnectionState.FAILED,
    },
    ConnectionState.PAUSED: {
        ConnectionState.ACTIVE,
        ConnectionState.CLOSING,
        ConnectionState.DISCONNECTED,
        ConnectionState.FAILED,
    },
    ConnectionState.CLOSING: {
        ConnectionState.CLOSED,
        ConnectionState.DISCONNECTED,
    },
    ConnectionState.CLOSED: {
        ConnectionState.DISCONNECTED,
    },
    ConnectionState.FAILED: {
        ConnectionState.DISCONNECTED,
        ConnectionState.CONNECTING,  # Allow reconnection from failed state
    },
}


class InvalidStateTransition(Exception):
    """Raised when an invalid state transition is attempted."""
    
    def __init__(self, from_state: ConnectionState, to_state: ConnectionState):
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(f"Invalid transition: {from_state.name} -> {to_state.name}")


StateChangeCallback = Callable[[ConnectionState, ConnectionState], None]


@dataclass
class ConnectionStateMachine:
    """
    State machine for connection lifecycle.
    
    Manages state transitions and notifies listeners of changes.
    """
    
    _state: ConnectionState = ConnectionState.DISCONNECTED
    _previous_state: Optional[ConnectionState] = None
    _callbacks: list[StateChangeCallback] = field(default_factory=list)
    _transition_count: int = 0
    _error_message: Optional[str] = None
    
    @property
    def state(self) -> ConnectionState:
        """Get current state."""
        return self._state
    
    @property
    def previous_state(self) -> Optional[ConnectionState]:
        """Get previous state."""
        return self._previous_state
    
    @property
    def transition_count(self) -> int:
        """Get number of state transitions."""
        return self._transition_count
    
    @property
    def error_message(self) -> Optional[str]:
        """Get error message if in FAILED state."""
        return self._error_message if self._state == ConnectionState.FAILED else None
    
    def can_transition_to(self, new_state: ConnectionState) -> bool:
        """
        Check if transition to new state is valid.
        
        Args:
            new_state: State to transition to
            
        Returns:
            True if transition is valid
        """
        valid_states = VALID_TRANSITIONS.get(self._state, set())
        return new_state in valid_states
    
    def transition_to(
        self,
        new_state: ConnectionState,
        error_message: Optional[str] = None
    ) -> None:
        """
        Transition to a new state.
        
        Args:
            new_state: State to transition to
            error_message: Error message if transitioning to FAILED
            
        Raises:
            InvalidStateTransition: If transition is not valid
        """
        if new_state == self._state:
            return  # No-op for same state
        
        if not self.can_transition_to(new_state):
            raise InvalidStateTransition(self._state, new_state)
        
        old_state = self._state
        self._previous_state = old_state
        self._state = new_state
        self._transition_count += 1
        
        if new_state == ConnectionState.FAILED:
            self._error_message = error_message
        else:
            self._error_message = None
        
        logger.debug(f"State transition: {old_state.name} -> {new_state.name}")
        
        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(old_state, new_state)
            except Exception as e:
                logger.warning(f"State change callback error: {e}")
    
    def on_state_change(self, callback: StateChangeCallback) -> None:
        """
        Register a state change callback.
        
        Args:
            callback: Function called with (old_state, new_state)
        """
        self._callbacks.append(callback)
    
    def remove_callback(self, callback: StateChangeCallback) -> bool:
        """
        Remove a state change callback.
        
        Args:
            callback: Callback to remove
            
        Returns:
            True if callback was found and removed
        """
        try:
            self._callbacks.remove(callback)
            return True
        except ValueError:
            return False
    
    def reset(self) -> None:
        """Reset state machine to initial state."""
        self._state = ConnectionState.DISCONNECTED
        self._previous_state = None
        self._error_message = None
    
    # Convenience methods for common transitions
    
    def start_connecting(self) -> None:
        """Start connection attempt."""
        self.transition_to(ConnectionState.CONNECTING)
    
    def start_authenticating(self) -> None:
        """Start authentication."""
        self.transition_to(ConnectionState.AUTHENTICATING)
    
    def mark_connected(self) -> None:
        """Mark as connected (authenticated)."""
        self.transition_to(ConnectionState.CONNECTED)
    
    def mark_active(self) -> None:
        """Mark as fully active."""
        self.transition_to(ConnectionState.ACTIVE)
    
    def pause(self) -> None:
        """Pause for backpressure."""
        self.transition_to(ConnectionState.PAUSED)
    
    def resume(self) -> None:
        """Resume from pause."""
        self.transition_to(ConnectionState.ACTIVE)
    
    def start_closing(self) -> None:
        """Start graceful close."""
        self.transition_to(ConnectionState.CLOSING)
    
    def mark_closed(self) -> None:
        """Mark as closed."""
        self.transition_to(ConnectionState.CLOSED)
    
    def mark_failed(self, reason: str = "") -> None:
        """Mark as failed."""
        self.transition_to(ConnectionState.FAILED, error_message=reason)
    
    def mark_disconnected(self) -> None:
        """Mark as disconnected."""
        self.transition_to(ConnectionState.DISCONNECTED)
    
    # State check helpers
    
    @property
    def is_connected(self) -> bool:
        """Check if in any connected state."""
        return self._state in (
            ConnectionState.CONNECTED,
            ConnectionState.ACTIVE,
            ConnectionState.PAUSED,
        )
    
    @property
    def is_active(self) -> bool:
        """Check if actively sending/receiving."""
        return self._state == ConnectionState.ACTIVE
    
    @property
    def is_paused(self) -> bool:
        """Check if paused for backpressure."""
        return self._state == ConnectionState.PAUSED
    
    @property
    def is_disconnected(self) -> bool:
        """Check if disconnected."""
        return self._state == ConnectionState.DISCONNECTED
    
    @property
    def is_failed(self) -> bool:
        """Check if in failed state."""
        return self._state == ConnectionState.FAILED
    
    @property
    def can_send(self) -> bool:
        """Check if can send messages."""
        return self._state == ConnectionState.ACTIVE
    
    @property
    def can_receive(self) -> bool:
        """Check if can receive messages."""
        return self._state in (ConnectionState.ACTIVE, ConnectionState.PAUSED)
