"""
Authentication Handler

Password-based authentication for Conduit connections.
"""

import hashlib
import secrets
import time
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass, field


# Constants
SALT_LENGTH = 32
HASH_ITERATIONS = 100000
SESSION_TOKEN_LENGTH = 64


def hash_password(password: str, salt: Optional[bytes] = None) -> Tuple[str, bytes]:
    """
    Hash a password using PBKDF2-SHA256.
    
    Args:
        password: Plain text password
        salt: Optional salt (generated if not provided)
        
    Returns:
        Tuple of (hex hash string, salt bytes)
    """
    if salt is None:
        salt = secrets.token_bytes(SALT_LENGTH)
    
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        HASH_ITERATIONS
    )
    
    return key.hex(), salt


def verify_password(password: str, expected_hash: str, salt: bytes) -> bool:
    """
    Verify a password against a hash.
    
    Args:
        password: Plain text password to verify
        expected_hash: Expected hash (hex string)
        salt: Salt used for hashing
        
    Returns:
        True if password matches
    """
    computed_hash, _ = hash_password(password, salt)
    
    # Use constant-time comparison to prevent timing attacks
    return secrets.compare_digest(computed_hash, expected_hash)


def generate_session_token() -> str:
    """
    Generate a secure session token.
    
    Returns:
        Random session token string
    """
    return secrets.token_hex(SESSION_TOKEN_LENGTH)


def generate_auth_challenge() -> bytes:
    """
    Generate a random authentication challenge.
    
    Returns:
        Random challenge bytes
    """
    return secrets.token_bytes(32)


def compute_auth_response(password: str, challenge: bytes) -> str:
    """
    Compute authentication response from password and challenge.
    
    Args:
        password: Password
        challenge: Server challenge
        
    Returns:
        Auth response as hex string
    """
    # Hash = SHA256(password + challenge)
    hasher = hashlib.sha256()
    hasher.update(password.encode('utf-8'))
    hasher.update(challenge)
    return hasher.hexdigest()


def verify_auth_response(password: str, challenge: bytes, response: str) -> bool:
    """
    Verify an authentication response.
    
    Args:
        password: Expected password
        challenge: Challenge that was sent
        response: Client's response
        
    Returns:
        True if response is valid
    """
    expected = compute_auth_response(password, challenge)
    return secrets.compare_digest(expected, response)


@dataclass
class Session:
    """Represents an authenticated session."""
    
    token: str
    client_id: str
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    client_info: Dict[str, Any] = field(default_factory=dict)
    
    def update_activity(self) -> None:
        """Update last activity time."""
        self.last_activity = time.time()
    
    def is_expired(self, timeout_seconds: float) -> bool:
        """Check if session is expired."""
        return (time.time() - self.last_activity) > timeout_seconds
    
    @property
    def age_seconds(self) -> float:
        """Get session age in seconds."""
        return time.time() - self.created_at


class AuthHandler:
    """
    Handles authentication for connections.
    
    Manages password verification and session tokens.
    """
    
    def __init__(
        self,
        password: str,
        session_timeout: float = 3600.0  # 1 hour
    ):
        """
        Initialize auth handler.
        
        Args:
            password: Server password
            session_timeout: Session timeout in seconds
        """
        self._password = password
        self._password_hash, self._password_salt = hash_password(password)
        self._session_timeout = session_timeout
        self._sessions: Dict[str, Session] = {}
        self._pending_challenges: Dict[str, bytes] = {}  # client_id -> challenge
    
    def create_challenge(self, client_id: str) -> bytes:
        """
        Create an authentication challenge for a client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Challenge bytes
        """
        challenge = generate_auth_challenge()
        self._pending_challenges[client_id] = challenge
        return challenge
    
    def verify_response(
        self,
        client_id: str,
        response: str,
        client_info: Optional[Dict[str, Any]] = None
    ) -> Optional[Session]:
        """
        Verify authentication response and create session.
        
        Args:
            client_id: Client identifier
            response: Client's auth response
            client_info: Optional client information
            
        Returns:
            Session if authenticated, None otherwise
        """
        challenge = self._pending_challenges.pop(client_id, None)
        
        if challenge is None:
            return None
        
        if not verify_auth_response(self._password, challenge, response):
            return None
        
        # Create session
        session = Session(
            token=generate_session_token(),
            client_id=client_id,
            client_info=client_info or {},
        )
        
        self._sessions[session.token] = session
        
        return session
    
    def verify_simple(self, password_hash: str) -> bool:
        """
        Simple password verification (hash-based).
        
        For simpler auth without challenge-response.
        
        Args:
            password_hash: SHA256 hash of password
            
        Returns:
            True if password matches
        """
        expected_hash = hashlib.sha256(self._password.encode('utf-8')).hexdigest()
        return secrets.compare_digest(password_hash, expected_hash)
    
    def create_session(
        self,
        client_id: str,
        client_info: Optional[Dict[str, Any]] = None
    ) -> Session:
        """
        Create a new session for an authenticated client.
        
        Args:
            client_id: Client identifier
            client_info: Client information
            
        Returns:
            New session
        """
        session = Session(
            token=generate_session_token(),
            client_id=client_id,
            client_info=client_info or {},
        )
        
        self._sessions[session.token] = session
        return session
    
    def get_session(self, token: str) -> Optional[Session]:
        """
        Get a session by token.
        
        Args:
            token: Session token
            
        Returns:
            Session if found and valid, None otherwise
        """
        session = self._sessions.get(token)
        
        if session is None:
            return None
        
        if session.is_expired(self._session_timeout):
            del self._sessions[token]
            return None
        
        session.update_activity()
        return session
    
    def invalidate_session(self, token: str) -> bool:
        """
        Invalidate a session.
        
        Args:
            token: Session token
            
        Returns:
            True if session was found and removed
        """
        if token in self._sessions:
            del self._sessions[token]
            return True
        return False
    
    def cleanup_expired_sessions(self) -> int:
        """
        Remove all expired sessions.
        
        Returns:
            Number of sessions removed
        """
        expired = [
            token for token, session in self._sessions.items()
            if session.is_expired(self._session_timeout)
        ]
        
        for token in expired:
            del self._sessions[token]
        
        return len(expired)
    
    @property
    def active_session_count(self) -> int:
        """Get number of active sessions."""
        return len(self._sessions)
