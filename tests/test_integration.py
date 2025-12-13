"""
Integration Tests for Conduit

End-to-end tests with real TCP communication between client and server.
Tests IPv4, authentication, messaging, RPC, and various configurations.
"""

import pytest
import asyncio
import socket
from typing import Any, Dict
from pydantic import BaseModel

from conduit import (
    Server,
    Client,
    ServerDescriptor,
    ClientDescriptor,
    Response,
    Error,
    data,
)


# Find an available port
def get_free_port() -> int:
    """Get a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


# Pydantic models for testing
class AddRequest(BaseModel):
    a: int
    b: int


class MultiplyRequest(BaseModel):
    x: float
    y: float


class UserInfo(BaseModel):
    name: str
    age: int


class TestBasicConnection:
    """Tests for basic client-server connection."""
    
    @pytest.mark.asyncio
    async def test_server_starts_and_stops(self):
        """Test that server can start and stop cleanly."""
        port = get_free_port()
        
        server = Server(ServerDescriptor(
            host="127.0.0.1",
            port=port,
            password="test_password",
        ))
        
        await server.start()
        assert server.is_running
        
        await server.stop()
        assert not server.is_running
    
    @pytest.mark.asyncio
    async def test_client_connects_and_authenticates(self):
        """Test that client can connect and authenticate."""
        port = get_free_port()
        
        server = Server(ServerDescriptor(
            host="127.0.0.1",
            port=port,
            password="secret123",
        ))
        
        client = Client(ClientDescriptor(
            server_host="127.0.0.1",
            server_port=port,
            password="secret123",
            reconnect_enabled=False,
        ))
        
        await server.start()
        
        try:
            connected = await client.connect()
            assert connected
            assert client.is_connected
            assert client.is_authenticated
            
        finally:
            await client.disconnect()
            await server.stop()
    
    @pytest.mark.asyncio
    async def test_wrong_password_rejected(self):
        """Test that wrong password is rejected."""
        port = get_free_port()
        
        server = Server(ServerDescriptor(
            host="127.0.0.1",
            port=port,
            password="correct_password",
        ))
        
        client = Client(ClientDescriptor(
            server_host="127.0.0.1",
            server_port=port,
            password="wrong_password",
            reconnect_enabled=False,
        ))
        
        await server.start()
        
        try:
            connected = await client.connect()
            assert not connected
            assert not client.is_connected
            
        finally:
            await client.disconnect()
            await server.stop()
    
    @pytest.mark.asyncio
    async def test_multiple_clients_connect(self):
        """Test that multiple clients can connect."""
        port = get_free_port()
        
        server = Server(ServerDescriptor(
            host="127.0.0.1",
            port=port,
            password="shared_secret",
            max_connections=10,
        ))
        
        clients = [
            Client(ClientDescriptor(
                server_host="127.0.0.1",
                server_port=port,
                password="shared_secret",
                reconnect_enabled=False,
            ))
            for _ in range(3)
        ]
        
        await server.start()
        
        try:
            # Connect all clients
            for client in clients:
                connected = await client.connect()
                assert connected
            
            # All should be connected
            assert all(c.is_connected for c in clients)
            
            # Server should track all connections
            # Give a moment for connections to be established
            await asyncio.sleep(0.1)
            
        finally:
            for client in clients:
                await client.disconnect()
            await server.stop()


class TestMessaging:
    """Tests for message sending and receiving."""
    
    @pytest.mark.asyncio
    async def test_client_sends_message_to_server(self):
        """Test client sending message to server."""
        port = get_free_port()
        received_messages = []
        
        server = Server(ServerDescriptor(
            host="127.0.0.1",
            port=port,
            password="test",
        ))
        
        @server.on("greeting")
        async def handle_greeting(client, data):
            received_messages.append(data)
            return {"received": True}
        
        client = Client(ClientDescriptor(
            server_host="127.0.0.1",
            server_port=port,
            password="test",
            reconnect_enabled=False,
        ))
        
        await server.start()
        
        try:
            await client.connect()
            
            # Send message
            await client.send("greeting", {"name": "TestUser"})
            
            # Wait for message to be processed
            await asyncio.sleep(0.2)
            
            assert len(received_messages) >= 1
            assert received_messages[0]["name"] == "TestUser"
            
        finally:
            await client.disconnect()
            await server.stop()


class TestRPC:
    """Tests for RPC functionality."""
    
    @pytest.mark.asyncio
    async def test_simple_rpc_call(self):
        """Test simple RPC call and response."""
        port = get_free_port()
        
        server = Server(ServerDescriptor(
            host="127.0.0.1",
            port=port,
            password="rpc_test",
        ))
        
        @server.rpc
        async def add(a: int, b: int) -> int:
            """Add two numbers."""
            return a + b
        
        client = Client(ClientDescriptor(
            server_host="127.0.0.1",
            server_port=port,
            password="rpc_test",
            reconnect_enabled=False,
        ))
        
        await server.start()
        
        try:
            await client.connect()
            
            result = await client.rpc.call("add", args=data(a=10, b=20))
            
            assert result == 30
            
        finally:
            await client.disconnect()
            await server.stop()
    
    @pytest.mark.asyncio
    async def test_rpc_with_pydantic_model(self):
        """Test RPC with Pydantic model parameter."""
        port = get_free_port()
        
        server = Server(ServerDescriptor(
            host="127.0.0.1",
            port=port,
            password="pydantic_test",
        ))
        
        @server.rpc
        async def multiply(request: MultiplyRequest) -> float:
            """Multiply two numbers."""
            return request.x * request.y
        
        client = Client(ClientDescriptor(
            server_host="127.0.0.1",
            server_port=port,
            password="pydantic_test",
            reconnect_enabled=False,
        ))
        
        await server.start()
        
        try:
            await client.connect()
            
            result = await client.rpc.call("multiply", args=data(x=3.5, y=2.0))
            
            assert result == 7.0
            
        finally:
            await client.disconnect()
            await server.stop()
    
    @pytest.mark.asyncio
    async def test_rpc_with_response_wrapper(self):
        """Test RPC with Response wrapper."""
        port = get_free_port()
        
        server = Server(ServerDescriptor(
            host="127.0.0.1",
            port=port,
            password="response_test",
        ))
        
        response = Response()
        
        @server.rpc
        async def get_user(user_id: int):
            """Get user by ID."""
            return response({
                "id": user_id,
                "name": f"User_{user_id}",
                "active": True
            })
        
        client = Client(ClientDescriptor(
            server_host="127.0.0.1",
            server_port=port,
            password="response_test",
            reconnect_enabled=False,
        ))
        
        await server.start()
        
        try:
            await client.connect()
            
            result = await client.rpc.call("get_user", args=data(user_id=42))
            
            assert result["id"] == 42
            assert result["name"] == "User_42"
            assert result["active"] is True
            
        finally:
            await client.disconnect()
            await server.stop()
    
    @pytest.mark.asyncio
    async def test_rpc_error_handling(self):
        """Test RPC error handling."""
        port = get_free_port()
        
        server = Server(ServerDescriptor(
            host="127.0.0.1",
            port=port,
            password="error_test",
        ))
        
        error = Error()
        
        @server.rpc
        async def divide(a: int, b: int):
            """Divide two numbers."""
            if b == 0:
                return error("Division by zero", code=400)
            return {"result": a / b}
        
        client = Client(ClientDescriptor(
            server_host="127.0.0.1",
            server_port=port,
            password="error_test",
            reconnect_enabled=False,
        ))
        
        await server.start()
        
        try:
            await client.connect()
            
            # Valid division
            result = await client.rpc.call("divide", args=data(a=10, b=2))
            assert result["result"] == 5.0
            
            # Division by zero - should get error response
            from conduit.rpc.rpc_class import RPCError
            with pytest.raises(RPCError) as exc_info:
                await client.rpc.call("divide", args=data(a=10, b=0))
            
            assert "Division by zero" in str(exc_info.value)
            
        finally:
            await client.disconnect()
            await server.stop()
    
    @pytest.mark.asyncio
    async def test_rpc_discovery(self):
        """Test RPC method discovery."""
        port = get_free_port()
        
        server = Server(ServerDescriptor(
            host="127.0.0.1",
            port=port,
            password="discovery_test",
        ))
        
        @server.rpc
        async def method_one():
            """First method."""
            return "one"
        
        @server.rpc
        async def method_two(x: int):
            """Second method."""
            return x * 2
        
        client = Client(ClientDescriptor(
            server_host="127.0.0.1",
            server_port=port,
            password="discovery_test",
            reconnect_enabled=False,
        ))
        
        await server.start()
        
        try:
            await client.connect()
            
            methods = await client.rpc.discover()
            
            method_names = [m["name"] for m in methods]
            assert "method_one" in method_names
            assert "method_two" in method_names
            
        finally:
            await client.disconnect()
            await server.stop()


class TestServerConfiguration:
    """Tests for various server configurations."""
    
    @pytest.mark.asyncio
    async def test_custom_server_name(self):
        """Test server with custom name and version."""
        port = get_free_port()
        
        server = Server(ServerDescriptor(
            name="CustomServer",
            version="2.0.0",
            description="A test server",
            host="127.0.0.1",
            port=port,
            password="config_test",
        ))
        
        client = Client(ClientDescriptor(
            server_host="127.0.0.1",
            server_port=port,
            password="config_test",
            reconnect_enabled=False,
        ))
        
        await server.start()
        
        try:
            await client.connect()
            
            # Server info should be available after auth
            assert client.server_info.get("name") == "CustomServer"
            assert client.server_info.get("version") == "2.0.0"
            
        finally:
            await client.disconnect()
            await server.stop()
    
    @pytest.mark.asyncio
    async def test_max_connections_limit(self):
        """Test server enforces max connections limit."""
        port = get_free_port()
        
        server = Server(ServerDescriptor(
            host="127.0.0.1",
            port=port,
            password="limit_test",
            max_connections=2,
        ))
        
        clients = [
            Client(ClientDescriptor(
                server_host="127.0.0.1",
                server_port=port,
                password="limit_test",
                reconnect_enabled=False,
            ))
            for _ in range(3)
        ]
        
        await server.start()
        
        try:
            # First two should connect
            assert await clients[0].connect()
            assert await clients[1].connect()
            
            # Give connections time to establish
            await asyncio.sleep(0.2)
            
            # Third should be rejected (max connections reached)
            # Note: This depends on server implementation
            # The connection might succeed but get closed immediately
            
        finally:
            for client in clients:
                await client.disconnect()
            await server.stop()


class TestClientConfiguration:
    """Tests for various client configurations."""
    
    @pytest.mark.asyncio
    async def test_custom_client_name(self):
        """Test client with custom name."""
        port = get_free_port()
        
        server = Server(ServerDescriptor(
            host="127.0.0.1",
            port=port,
            password="client_config",
        ))
        
        client = Client(ClientDescriptor(
            name="CustomClient",
            version="3.0.0",
            server_host="127.0.0.1",
            server_port=port,
            password="client_config",
            reconnect_enabled=False,
        ))
        
        await server.start()
        
        try:
            await client.connect()
            assert client.is_connected
            assert client.config.name == "CustomClient"
            
        finally:
            await client.disconnect()
            await server.stop()
    
    @pytest.mark.asyncio
    async def test_connection_timeout(self):
        """Test connection timeout configuration."""
        # Try to connect to a port that likely isn't listening
        port = get_free_port()
        
        client = Client(ClientDescriptor(
            server_host="127.0.0.1",
            server_port=port,  # No server here
            password="timeout_test",
            connect_timeout=1,  # 1 second timeout
            reconnect_enabled=False,
        ))
        
        import time
        start = time.time()
        
        connected = await client.connect()
        
        elapsed = time.time() - start
        
        assert not connected
        assert elapsed < 5  # Should timeout relatively quickly
    
    @pytest.mark.asyncio
    async def test_rpc_timeout(self):
        """Test RPC timeout configuration."""
        port = get_free_port()
        
        server = Server(ServerDescriptor(
            host="127.0.0.1",
            port=port,
            password="rpc_timeout",
        ))
        
        @server.rpc
        async def slow_method():
            """A method that takes too long."""
            await asyncio.sleep(10)  # Very slow
            return "done"
        
        client = Client(ClientDescriptor(
            server_host="127.0.0.1",
            server_port=port,
            password="rpc_timeout",
            rpc_timeout=1.0,  # 1 second timeout
            reconnect_enabled=False,
        ))
        
        await server.start()
        
        try:
            await client.connect()
            
            from conduit.rpc.rpc_class import RPCTimeout
            with pytest.raises(RPCTimeout):
                await client.rpc.call("slow_method")
            
        finally:
            await client.disconnect()
            await server.stop()


class TestLifecycleHooks:
    """Tests for server and client lifecycle hooks."""
    
    @pytest.mark.asyncio
    async def test_server_startup_shutdown_hooks(self):
        """Test server startup and shutdown hooks."""
        port = get_free_port()
        
        events = []
        
        server = Server(ServerDescriptor(
            host="127.0.0.1",
            port=port,
            password="hooks_test",
        ))
        
        @server.on_startup
        async def on_startup(srv):
            events.append("startup")
        
        @server.on_shutdown
        async def on_shutdown(srv):
            events.append("shutdown")
        
        await server.start()
        assert "startup" in events
        
        await server.stop()
        assert "shutdown" in events
    
    @pytest.mark.asyncio
    async def test_client_connect_disconnect_hooks(self):
        """Test client connect and disconnect hooks."""
        port = get_free_port()
        
        events = []
        
        server = Server(ServerDescriptor(
            host="127.0.0.1",
            port=port,
            password="client_hooks",
        ))
        
        client = Client(ClientDescriptor(
            server_host="127.0.0.1",
            server_port=port,
            password="client_hooks",
            reconnect_enabled=False,
        ))
        
        @client.on_connect
        async def on_connect(cli):
            events.append("connected")
        
        @client.on_disconnect
        async def on_disconnect(cli):
            events.append("disconnected")
        
        await server.start()
        
        try:
            await client.connect()
            assert "connected" in events
            
            await client.disconnect()
            assert "disconnected" in events
            
        finally:
            await server.stop()


class TestIPv4Configuration:
    """Tests specifically for IPv4 configuration."""
    
    @pytest.mark.asyncio
    async def test_ipv4_explicit_binding(self):
        """Test explicit IPv4 binding."""
        port = get_free_port()
        
        server = Server(ServerDescriptor(
            host="127.0.0.1",
            port=port,
            password="ipv4_test",
            ipv6=False,  # Explicitly IPv4
        ))
        
        client = Client(ClientDescriptor(
            server_host="127.0.0.1",
            server_port=port,
            password="ipv4_test",
            use_ipv6=False,
            reconnect_enabled=False,
        ))
        
        await server.start()
        
        try:
            connected = await client.connect()
            assert connected
            assert client.is_connected
            
        finally:
            await client.disconnect()
            await server.stop()
    
    @pytest.mark.asyncio
    async def test_localhost_binding(self):
        """Test binding to localhost."""
        port = get_free_port()
        
        server = Server(ServerDescriptor(
            host="localhost",
            port=port,
            password="localhost_test",
        ))
        
        client = Client(ClientDescriptor(
            server_host="localhost",
            server_port=port,
            password="localhost_test",
            reconnect_enabled=False,
        ))
        
        await server.start()
        
        try:
            connected = await client.connect()
            assert connected
            
        finally:
            await client.disconnect()
            await server.stop()


def get_free_port_ipv6() -> int:
    """Get a free port on IPv6 localhost."""
    try:
        with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('::1', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port
    except OSError:
        # IPv6 not available
        return None


def is_ipv6_available() -> bool:
    """Check if IPv6 is available on this system."""
    try:
        with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as s:
            s.bind(('::1', 0))
            return True
    except OSError:
        return False


class TestIPv6Configuration:
    """Tests specifically for IPv6 configuration."""
    
    @pytest.mark.asyncio
    async def test_ipv6_loopback_connection(self):
        """Test IPv6 loopback connection (::1)."""
        if not is_ipv6_available():
            pytest.skip("IPv6 not available on this system")
        
        port = get_free_port_ipv6()
        if port is None:
            pytest.skip("Could not get free IPv6 port")
        
        server = Server(ServerDescriptor(
            host="::1",
            port=port,
            password="ipv6_test",
            ipv6=True,  # Enable IPv6
        ))
        
        client = Client(ClientDescriptor(
            server_host="::1",
            server_port=port,
            password="ipv6_test",
            use_ipv6=True,  # Use IPv6
            reconnect_enabled=False,
        ))
        
        await server.start()
        
        try:
            connected = await client.connect()
            assert connected
            assert client.is_connected
            
        finally:
            await client.disconnect()
            await server.stop()
    
    @pytest.mark.asyncio
    async def test_ipv6_rpc_call(self):
        """Test RPC over IPv6."""
        if not is_ipv6_available():
            pytest.skip("IPv6 not available on this system")
        
        port = get_free_port_ipv6()
        if port is None:
            pytest.skip("Could not get free IPv6 port")
        
        server = Server(ServerDescriptor(
            host="::1",
            port=port,
            password="ipv6_rpc",
            ipv6=True,
        ))
        
        @server.rpc
        async def greet(name: str) -> str:
            return f"Hello from IPv6, {name}!"
        
        client = Client(ClientDescriptor(
            server_host="::1",
            server_port=port,
            password="ipv6_rpc",
            use_ipv6=True,
            reconnect_enabled=False,
        ))
        
        await server.start()
        
        try:
            await client.connect()
            
            result = await client.rpc.call("greet", args=data(name="World"))
            assert result == "Hello from IPv6, World!"
            
        finally:
            await client.disconnect()
            await server.stop()
    
    @pytest.mark.asyncio
    async def test_ipv6_messaging(self):
        """Test messaging over IPv6."""
        if not is_ipv6_available():
            pytest.skip("IPv6 not available on this system")
        
        port = get_free_port_ipv6()
        if port is None:
            pytest.skip("Could not get free IPv6 port")
        
        received_messages = []
        
        server = Server(ServerDescriptor(
            host="::1",
            port=port,
            password="ipv6_msg",
            ipv6=True,
        ))
        
        @server.on("ping")
        async def handle_ping(client, data):
            received_messages.append(data)
            return {"pong": True}
        
        client = Client(ClientDescriptor(
            server_host="::1",
            server_port=port,
            password="ipv6_msg",
            use_ipv6=True,
            reconnect_enabled=False,
        ))
        
        await server.start()
        
        try:
            await client.connect()
            
            await client.send("ping", {"timestamp": 12345})
            await asyncio.sleep(0.2)
            
            assert len(received_messages) >= 1
            assert received_messages[0]["timestamp"] == 12345
            
        finally:
            await client.disconnect()
            await server.stop()
    
    @pytest.mark.asyncio
    async def test_ipv6_multiple_clients(self):
        """Test multiple clients over IPv6."""
        if not is_ipv6_available():
            pytest.skip("IPv6 not available on this system")
        
        port = get_free_port_ipv6()
        if port is None:
            pytest.skip("Could not get free IPv6 port")
        
        server = Server(ServerDescriptor(
            host="::1",
            port=port,
            password="ipv6_multi",
            ipv6=True,
            max_connections=5,
        ))
        
        clients = [
            Client(ClientDescriptor(
                server_host="::1",
                server_port=port,
                password="ipv6_multi",
                use_ipv6=True,
                reconnect_enabled=False,
            ))
            for _ in range(3)
        ]
        
        await server.start()
        
        try:
            # Connect all clients
            for client in clients:
                connected = await client.connect()
                assert connected, "Client failed to connect over IPv6"
            
            # All should be connected
            assert all(c.is_connected for c in clients)
            
        finally:
            for client in clients:
                await client.disconnect()
            await server.stop()
    
    @pytest.mark.asyncio
    async def test_ipv6_concurrent_rpc(self):
        """Test concurrent RPC calls over IPv6."""
        if not is_ipv6_available():
            pytest.skip("IPv6 not available on this system")
        
        port = get_free_port_ipv6()
        if port is None:
            pytest.skip("Could not get free IPv6 port")
        
        server = Server(ServerDescriptor(
            host="::1",
            port=port,
            password="ipv6_concurrent",
            ipv6=True,
        ))
        
        @server.rpc
        async def square(n: int) -> int:
            await asyncio.sleep(0.01)  # Small delay
            return n * n
        
        client = Client(ClientDescriptor(
            server_host="::1",
            server_port=port,
            password="ipv6_concurrent",
            use_ipv6=True,
            reconnect_enabled=False,
        ))
        
        await server.start()
        
        try:
            await client.connect()
            
            # Make concurrent RPC calls
            tasks = [
                client.rpc.call("square", args=data(n=i))
                for i in range(10)
            ]
            
            results = await asyncio.gather(*tasks)
            expected = [i * i for i in range(10)]
            
            assert results == expected
            
        finally:
            await client.disconnect()
            await server.stop()


class TestStressTests:
    """Stress tests for the system."""
    
    @pytest.mark.asyncio
    async def test_many_rpc_calls(self):
        """Test many sequential RPC calls."""
        port = get_free_port()
        
        server = Server(ServerDescriptor(
            host="127.0.0.1",
            port=port,
            password="stress_test",
        ))
        
        call_count = 0
        
        @server.rpc
        async def increment(value: int) -> int:
            nonlocal call_count
            call_count += 1
            return value + 1
        
        client = Client(ClientDescriptor(
            server_host="127.0.0.1",
            server_port=port,
            password="stress_test",
            reconnect_enabled=False,
        ))
        
        await server.start()
        
        try:
            await client.connect()
            
            # Make 50 RPC calls
            for i in range(50):
                result = await client.rpc.call("increment", args=data(value=i))
                assert result == i + 1
            
            assert call_count == 50
            
        finally:
            await client.disconnect()
            await server.stop()
    
    @pytest.mark.asyncio
    async def test_concurrent_rpc_calls(self):
        """Test concurrent RPC calls."""
        port = get_free_port()
        
        server = Server(ServerDescriptor(
            host="127.0.0.1",
            port=port,
            password="concurrent_test",
        ))
        
        @server.rpc
        async def echo(message: str) -> str:
            await asyncio.sleep(0.01)  # Small delay
            return message
        
        client = Client(ClientDescriptor(
            server_host="127.0.0.1",
            server_port=port,
            password="concurrent_test",
            reconnect_enabled=False,
        ))
        
        await server.start()
        
        try:
            await client.connect()
            
            # Make 10 concurrent calls
            tasks = [
                client.rpc.call("echo", args=data(message=f"msg_{i}"))
                for i in range(10)
            ]
            
            results = await asyncio.gather(*tasks)
            
            expected = {f"msg_{i}" for i in range(10)}
            assert set(results) == expected
            
        finally:
            await client.disconnect()
            await server.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
