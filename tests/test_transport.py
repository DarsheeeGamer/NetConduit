"""
Tests for Transport Layer

Tests for TCP socket, connection state machine, and authentication.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from conduit.transport import ConnectionState, ConnectionStateMachine, AuthHandler
from conduit.transport.connection_state import InvalidStateTransition
from conduit.transport.auth import (
    hash_password,
    verify_password,
    generate_session_token,
    compute_auth_response,
    verify_auth_response,
)


class TestConnectionStateMachine:
    """Tests for ConnectionStateMachine."""
    
    def test_initial_state(self):
        """Test initial state is DISCONNECTED."""
        sm = ConnectionStateMachine()
        assert sm.state == ConnectionState.DISCONNECTED
    
    def test_valid_transition(self):
        """Test valid state transitions."""
        sm = ConnectionStateMachine()
        
        sm.start_connecting()
        assert sm.state == ConnectionState.CONNECTING
        
        sm.start_authenticating()
        assert sm.state == ConnectionState.AUTHENTICATING
        
        sm.mark_connected()
        assert sm.state == ConnectionState.CONNECTED
        
        sm.mark_active()
        assert sm.state == ConnectionState.ACTIVE
    
    def test_invalid_transition(self):
        """Test that invalid transitions raise error."""
        sm = ConnectionStateMachine()
        
        # Cannot go from DISCONNECTED directly to ACTIVE
        with pytest.raises(InvalidStateTransition):
            sm.mark_active()
    
    def test_pause_resume(self):
        """Test pause and resume transitions."""
        sm = ConnectionStateMachine()
        sm.start_connecting()
        sm.start_authenticating()
        sm.mark_connected()
        sm.mark_active()
        
        sm.pause()
        assert sm.state == ConnectionState.PAUSED
        assert sm.is_paused
        
        sm.resume()
        assert sm.state == ConnectionState.ACTIVE
        assert sm.is_active
    
    def test_failed_state(self):
        """Test failed state with error message."""
        sm = ConnectionStateMachine()
        sm.start_connecting()
        
        sm.mark_failed("Connection refused")
        
        assert sm.state == ConnectionState.FAILED
        assert sm.is_failed
        assert sm.error_message == "Connection refused"
    
    def test_state_callbacks(self):
        """Test state change callbacks are called."""
        sm = ConnectionStateMachine()
        
        transitions = []
        def callback(old, new):
            transitions.append((old, new))
        
        sm.on_state_change(callback)
        
        sm.start_connecting()
        sm.start_authenticating()
        
        assert len(transitions) == 2
        assert transitions[0] == (ConnectionState.DISCONNECTED, ConnectionState.CONNECTING)
        assert transitions[1] == (ConnectionState.CONNECTING, ConnectionState.AUTHENTICATING)
    
    def test_can_send_check(self):
        """Test can_send property."""
        sm = ConnectionStateMachine()
        assert not sm.can_send
        
        sm.start_connecting()
        assert not sm.can_send
        
        sm.start_authenticating()
        sm.mark_connected()
        sm.mark_active()
        assert sm.can_send
    
    def test_reset(self):
        """Test reset to initial state."""
        sm = ConnectionStateMachine()
        sm.start_connecting()
        sm.start_authenticating()
        sm.mark_connected()
        
        sm.reset()
        
        assert sm.state == ConnectionState.DISCONNECTED
        assert sm.previous_state is None


class TestPasswordHashing:
    """Tests for password hashing functions."""
    
    def test_hash_password(self):
        """Test password hashing."""
        hash1, salt = hash_password("mypassword")
        
        assert isinstance(hash1, str)
        assert isinstance(salt, bytes)
        assert len(salt) == 32
    
    def test_same_password_different_salt(self):
        """Test same password with different salts produces different hashes."""
        hash1, salt1 = hash_password("mypassword")
        hash2, salt2 = hash_password("mypassword")
        
        assert hash1 != hash2
        assert salt1 != salt2
    
    def test_verify_correct_password(self):
        """Test verifying correct password."""
        password = "correctpassword"
        hash_val, salt = hash_password(password)
        
        assert verify_password(password, hash_val, salt)
    
    def test_verify_wrong_password(self):
        """Test verifying wrong password."""
        hash_val, salt = hash_password("correctpassword")
        
        assert not verify_password("wrongpassword", hash_val, salt)
    
    def test_session_token_generation(self):
        """Test session token generation."""
        token1 = generate_session_token()
        token2 = generate_session_token()
        
        assert isinstance(token1, str)
        assert len(token1) == 128  # 64 bytes as hex = 128 chars
        assert token1 != token2


class TestAuthResponse:
    """Tests for challenge-response authentication."""
    
    def test_compute_response(self):
        """Test computing auth response."""
        password = "secret"
        challenge = b"random_challenge"
        
        response = compute_auth_response(password, challenge)
        
        assert isinstance(response, str)
        assert len(response) == 64  # SHA256 hex
    
    def test_verify_correct_response(self):
        """Test verifying correct response."""
        password = "secret"
        challenge = b"random_challenge"
        
        response = compute_auth_response(password, challenge)
        
        assert verify_auth_response(password, challenge, response)
    
    def test_verify_wrong_response(self):
        """Test verifying wrong response."""
        password = "secret"
        challenge = b"random_challenge"
        
        assert not verify_auth_response(password, challenge, "wrong_response")


class TestAuthHandler:
    """Tests for AuthHandler class."""
    
    def test_simple_verification(self):
        """Test simple password verification."""
        handler = AuthHandler(password="secret123")
        
        import hashlib
        correct_hash = hashlib.sha256(b"secret123").hexdigest()
        wrong_hash = hashlib.sha256(b"wrongpassword").hexdigest()
        
        assert handler.verify_simple(correct_hash)
        assert not handler.verify_simple(wrong_hash)
    
    def test_challenge_response_flow(self):
        """Test challenge-response authentication."""
        handler = AuthHandler(password="secret123")
        
        # Create challenge
        challenge = handler.create_challenge("client1")
        assert isinstance(challenge, bytes)
        
        # Compute response
        response = compute_auth_response("secret123", challenge)
        
        # Verify and create session
        session = handler.verify_response("client1", response, {"name": "Client1"})
        
        assert session is not None
        assert session.client_id == "client1"
        assert session.client_info == {"name": "Client1"}
    
    def test_wrong_response_fails(self):
        """Test that wrong response fails."""
        handler = AuthHandler(password="secret123")
        
        challenge = handler.create_challenge("client1")
        
        # Compute response with wrong password
        response = compute_auth_response("wrongpassword", challenge)
        
        session = handler.verify_response("client1", response)
        assert session is None
    
    def test_session_management(self):
        """Test session creation and retrieval."""
        handler = AuthHandler(password="secret", session_timeout=3600)
        
        session = handler.create_session("client1", {"name": "Test"})
        
        assert session is not None
        token = session.token
        
        # Retrieve session
        retrieved = handler.get_session(token)
        assert retrieved is not None
        assert retrieved.client_id == "client1"
    
    def test_session_invalidation(self):
        """Test session invalidation."""
        handler = AuthHandler(password="secret")
        
        session = handler.create_session("client1")
        token = session.token
        
        assert handler.get_session(token) is not None
        
        handler.invalidate_session(token)
        
        assert handler.get_session(token) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
