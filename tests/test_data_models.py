"""
Tests for Data Models

Tests for Pydantic data models including descriptors, messages, and RPC.
"""

import pytest
from pydantic import ValidationError

from conduit.data import (
    ServerDescriptor,
    ClientDescriptor,
    MessageData,
    RPCRequest,
    RPCResponse,
    RPCError,
    AuthRequest,
    AuthSuccess,
    AuthFailure,
    RPCMethodInfo,
    RPCListResponse,
    ConnectionInfo,
    ConnectionHealth,
)
from conduit.data.connection import ConnectionState


class TestServerDescriptor:
    """Tests for ServerDescriptor."""
    
    def test_minimal_config(self):
        """Test creating descriptor with only password."""
        config = ServerDescriptor(password="secret123")
        
        assert config.password == "secret123"
        assert config.host == "0.0.0.0"
        assert config.port == 8080
        assert config.name == "conduit_server"
    
    def test_full_config(self):
        """Test creating descriptor with all options."""
        config = ServerDescriptor(
            name="my_server",
            version="2.0.0",
            host="127.0.0.1",
            port=9000,
            password="supersecret",
            max_connections=500,
            heartbeat_interval=60,
            heartbeat_timeout=180,
        )
        
        assert config.name == "my_server"
        assert config.version == "2.0.0"
        assert config.host == "127.0.0.1"
        assert config.port == 9000
        assert config.max_connections == 500
        assert config.heartbeat_interval == 60
        assert config.heartbeat_timeout == 180
    
    def test_invalid_port(self):
        """Test that invalid port raises error."""
        with pytest.raises(ValidationError):
            ServerDescriptor(password="secret", port=99999)
        
        with pytest.raises(ValidationError):
            ServerDescriptor(password="secret", port=0)
    
    def test_empty_password(self):
        """Test that empty password raises error."""
        with pytest.raises(ValidationError):
            ServerDescriptor(password="")
    
    def test_heartbeat_timeout_validation(self):
        """Test heartbeat timeout must be > interval."""
        with pytest.raises(ValidationError):
            ServerDescriptor(
                password="secret",
                heartbeat_interval=60,
                heartbeat_timeout=30  # Less than interval
            )
    
    def test_extra_fields_forbidden(self):
        """Test that extra fields raise error."""
        with pytest.raises(ValidationError):
            ServerDescriptor(password="secret", unknown_field="value")


class TestClientDescriptor:
    """Tests for ClientDescriptor."""
    
    def test_minimal_config(self):
        """Test creating with required fields only."""
        config = ClientDescriptor(
            server_host="localhost",
            server_port=8080,
            password="secret123"
        )
        
        assert config.server_host == "localhost"
        assert config.server_port == 8080
        assert config.password == "secret123"
        assert config.reconnect_enabled is True
    
    def test_reconnection_config(self):
        """Test reconnection configuration."""
        config = ClientDescriptor(
            server_host="localhost",
            server_port=8080,
            password="secret",
            reconnect_enabled=True,
            reconnect_attempts=10,
            reconnect_delay=5.0,
            reconnect_delay_max=120.0,
        )
        
        assert config.reconnect_attempts == 10
        assert config.reconnect_delay == 5.0
        assert config.reconnect_delay_max == 120.0
    
    def test_missing_required(self):
        """Test that missing required fields raise error."""
        with pytest.raises(ValidationError):
            ClientDescriptor(server_host="localhost")  # Missing port and password


class TestMessageModels:
    """Tests for message data models."""
    
    def test_message_data(self):
        """Test MessageData model."""
        msg = MessageData(type="hello", data={"name": "world"})
        assert msg.type == "hello"
        assert msg.data == {"name": "world"}
    
    def test_rpc_request(self):
        """Test RPCRequest model."""
        req = RPCRequest(method="add", params={"a": 1, "b": 2})
        assert req.method == "add"
        assert req.params == {"a": 1, "b": 2}
    
    def test_rpc_request_empty_params(self):
        """Test RPCRequest with empty params."""
        req = RPCRequest(method="get_status")
        assert req.params == {}
    
    def test_rpc_response(self):
        """Test RPCResponse model."""
        resp = RPCResponse(success=True, result=42)
        assert resp.success is True
        assert resp.result == 42
    
    def test_rpc_error(self):
        """Test RPCError model."""
        err = RPCError(error="Something failed", code=500)
        assert err.success is False
        assert err.error == "Something failed"
        assert err.code == 500


class TestAuthModels:
    """Tests for auth data models."""
    
    def test_auth_request(self):
        """Test AuthRequest model."""
        req = AuthRequest(
            password_hash="abc123",
            client_info={"name": "test_client"}
        )
        assert req.password_hash == "abc123"
        assert req.client_info == {"name": "test_client"}
    
    def test_auth_success(self):
        """Test AuthSuccess model."""
        resp = AuthSuccess(
            session_token="token123",
            server_info={"name": "test_server"},
            heartbeat_interval=30
        )
        assert resp.session_token == "token123"
        assert resp.heartbeat_interval == 30
    
    def test_auth_failure(self):
        """Test AuthFailure model."""
        resp = AuthFailure(reason="Invalid password")
        assert resp.reason == "Invalid password"
        assert resp.retry_allowed is False


class TestRPCModels:
    """Tests for RPC data models."""
    
    def test_rpc_method_info(self):
        """Test RPCMethodInfo model."""
        info = RPCMethodInfo(
            name="calculate",
            description="Calculate something",
            parameters={"a": "int", "b": "int"},
            return_type="int"
        )
        assert info.name == "calculate"
        assert info.parameters == {"a": "int", "b": "int"}
    
    def test_rpc_list_response(self):
        """Test RPCListResponse model."""
        method1 = RPCMethodInfo(name="method1", description="First method")
        method2 = RPCMethodInfo(name="method2", description="Second method")
        
        resp = RPCListResponse(
            methods=[method1, method2],
            server_name="test_server",
            server_version="1.0.0"
        )
        
        assert len(resp.methods) == 2
        assert resp.methods[0].name == "method1"


class TestConnectionModels:
    """Tests for connection data models."""
    
    def test_connection_info(self):
        """Test ConnectionInfo model."""
        info = ConnectionInfo(
            client_id="abc123",
            address="192.168.1.100",
            port=54321
        )
        assert info.client_id == "abc123"
        assert info.address == "192.168.1.100"
        assert info.authenticated is False
    
    def test_connection_health(self):
        """Test ConnectionHealth model."""
        health = ConnectionHealth(
            state=ConnectionState.ACTIVE,
            connected=True,
            authenticated=True,
            latency_ms=25.5,
            messages_sent=100,
            messages_received=95
        )
        
        assert health.connected is True
        assert health.is_healthy() is True
        assert health.latency_ms == 25.5
    
    def test_health_unhealthy_when_paused(self):
        """Test that connection is unhealthy when paused."""
        health = ConnectionHealth(
            state=ConnectionState.PAUSED,
            connected=True,
            authenticated=True,
            is_paused=True
        )
        
        assert health.is_healthy() is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
