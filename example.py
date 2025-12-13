"""
Conduit - Secure Async Bidirectional Communication Library
Example Usage Documentation
"""

import asyncio
from conduit import Server, Client, ServerDescriptor, ClientDescriptor, ConnectionType
from conduit import Message, RPCHandler, FileTransfer
from conduit.auth import AuthMethod


# ============================================================================
# SERVER EXAMPLE
# ============================================================================

async def example_server():
    """Example of setting up a Conduit server"""
    
    # Create server descriptor
    server_desc = ServerDescriptor(
        name="example_server",
        version="1.0.0",
        description="Example Conduit server",
        author="Example Author",
        author_email="example@example.com",
        address="0.0.0.0",  # Listen on all interfaces
        port=8080,
        auth_method=AuthMethod.PASSWORD,  # or AuthMethod.KEY
        auth_secret="kaede123",  # Password or path to key file
        max_connections=100,
        enable_tls=True,  # Enable TLS/SSL
        cert_file="./certs/server.crt",  # Optional: custom cert
        key_file="./certs/server.key",
        heartbeat_interval=30,  # Send heartbeat every 30 seconds
        connection_timeout=120,  # Timeout after 120 seconds of inactivity
    )
    
    # Create server instance
    server = Server(server_desc)
    
    # Register message handlers
    @server.on_message("text")
    async def handle_text_message(conn, message):
        """Handle incoming text messages"""
        print(f"Received from {conn.client_id}: {message.data}")
        # Send response
        await conn.send(Message(type="text", data="Message received!"))
    
    @server.on_message("file")
    async def handle_file(conn, message):
        """Handle incoming file transfers"""
        file_transfer = FileTransfer.from_message(message)
        await file_transfer.save_to("./uploads/")
        print(f"File saved: {file_transfer.filename}")
        await conn.send(Message(type="ack", data={"status": "file_received"}))
    
    # Register RPC handlers
    @server.rpc("get_server_info")
    async def get_server_info(params):
        """RPC: Get server information"""
        return {
            "name": server_desc.name,
            "version": server_desc.version,
            "uptime": server.uptime(),
            "connections": server.connection_count()
        }
    
    @server.rpc("echo")
    async def echo(params):
        """RPC: Echo back the data"""
        return params
    
    @server.rpc("calculate")
    async def calculate(params):
        """RPC: Perform calculation"""
        operation = params.get("operation")
        a = params.get("a")
        b = params.get("b")
        
        if operation == "add":
            return {"result": a + b}
        elif operation == "multiply":
            return {"result": a * b}
        else:
            raise ValueError(f"Unknown operation: {operation}")
    
    # Connection lifecycle handlers
    @server.on_connect
    async def on_client_connect(conn):
        """Called when a client connects"""
        print(f"Client connected: {conn.client_id} from {conn.address}")
    
    @server.on_disconnect
    async def on_client_disconnect(conn):
        """Called when a client disconnects"""
        print(f"Client disconnected: {conn.client_id}")
    
    @server.on_heartbeat_timeout
    async def on_heartbeat_timeout(conn):
        """Called when heartbeat times out"""
        print(f"Heartbeat timeout for client: {conn.client_id}")
        await conn.close()
    
    # Start server
    print(f"Starting server on {server_desc.address}:{server_desc.port}")
    await server.start()
    
    # Keep server running
    try:
        await server.wait_until_stopped()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        await server.stop()


# ============================================================================
# CLIENT EXAMPLE
# ============================================================================

async def example_client():
    """Example of using Conduit client"""
    
    # Create client descriptor
    client_desc = ClientDescriptor(
        name="example_client",
        version="1.0.0",
        description="Example Conduit client",
        author="Example Author",
        author_email="example@example.com",
        server_address="127.0.0.1",
        server_port=8080,
        auth_method=AuthMethod.PASSWORD,
        auth_secret="kaede123",
        enable_tls=True,
        verify_ssl=True,  # Verify server certificate
        reconnect_attempts=5,  # Auto-reconnect on disconnect
        reconnect_delay=2,  # Wait 2 seconds between reconnect attempts
    )
    
    # Create client instance
    client = Client(client_desc)
    
    # Register message handlers (client-side)
    @client.on_message("text")
    async def handle_server_message(message):
        """Handle incoming messages from server"""
        print(f"Server says: {message.data}")
    
    try:
        # Connect to server
        print("Connecting to server...")
        conn = await client.connect()
        
        # Verify connection
        if await client.verify_connection(conn):
            print("✓ Connection verified and authenticated")
        else:
            print("✗ Connection verification failed")
            return
        
        # Example 1: Simple message sending
        print("\n=== Example 1: Simple Messaging ===")
        await conn.send(Message(type="text", data="Hello Server!"))
        
        # Example 2: Waiting for response
        print("\n=== Example 2: Send and Wait for Response ===")
        response = await conn.send_and_wait(
            Message(type="text", data="Need a response"),
            timeout=5.0
        )
        print(f"Got response: {response.data}")
        
        # Example 3: RPC calls
        print("\n=== Example 3: RPC Calls ===")
        
        # Get server info via RPC
        server_info = await client.rpc_call("get_server_info", {})
        print(f"Server info: {server_info}")
        
        # Echo test
        echo_result = await client.rpc_call("echo", {"message": "test"})
        print(f"Echo result: {echo_result}")
        
        # Calculate
        calc_result = await client.rpc_call("calculate", {
            "operation": "add",
            "a": 10,
            "b": 20
        })
        print(f"Calculation result: {calc_result}")
        
        # Example 4: File transfer
        print("\n=== Example 4: File Transfer ===")
        file_transfer = FileTransfer(
            filepath="./test_file.txt",
            chunk_size=1024 * 64  # 64KB chunks
        )
        await conn.send_file(file_transfer, progress_callback=lambda p: print(f"Progress: {p}%"))
        print("File sent successfully")
        
        # Example 5: Streaming data
        print("\n=== Example 5: Streaming ===")
        async with conn.stream() as stream:
            # Send multiple messages
            for i in range(10):
                await stream.send(Message(type="text", data=f"Stream message {i}"))
                await asyncio.sleep(0.1)
            
            # Check for incoming data
            if stream.has_incoming_data():
                while stream.has_incoming_data():
                    msg = await stream.receive()
                    print(f"Streamed response: {msg.data}")
        
        # Example 6: Monitoring connection health
        print("\n=== Example 6: Connection Health ===")
        health = conn.get_health()
        print(f"RTT: {health.rtt_ms}ms")
        print(f"Bytes sent: {health.bytes_sent}")
        print(f"Bytes received: {health.bytes_received}")
        print(f"Messages sent: {health.messages_sent}")
        print(f"Messages received: {health.messages_received}")
        print(f"Last heartbeat: {health.last_heartbeat}")
        
        # Keep connection alive for a bit
        print("\n=== Keeping connection alive (heartbeats will be sent automatically) ===")
        await asyncio.sleep(10)
        
    except ConnectionError as e:
        print(f"Connection error: {e}")
    except TimeoutError:
        print("Operation timed out")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Always close connection
        print("\nClosing connection...")
        await client.close()


# ============================================================================
# ADVANCED EXAMPLE: Peer-to-Peer Communication
# ============================================================================

async def example_peer_to_peer():
    """Example of two peers communicating (both are server and client)"""
    
    # Peer 1: Server on port 8080, connects to peer 2 on port 8081
    peer1_server_desc = ServerDescriptor(
        name="peer1_server",
        address="0.0.0.0",
        port=8080,
        auth_method=AuthMethod.PASSWORD,
        auth_secret="peer_secret"
    )
    
    peer1_client_desc = ClientDescriptor(
        name="peer1_client",
        server_address="127.0.0.1",
        server_port=8081,
        auth_method=AuthMethod.PASSWORD,
        auth_secret="peer_secret"
    )
    
    # Each peer can be both server and client
    peer1_server = Server(peer1_server_desc)
    peer1_client = Client(peer1_client_desc)
    
    # ... Similar setup for peer2 ...
    # This enables true bidirectional peer-to-peer communication


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python example.py server    # Run server")
        print("  python example.py client    # Run client")
        print("  python example.py p2p       # Run peer-to-peer example")
        sys.exit(1)
    
    mode = sys.argv[1]
    
    if mode == "server":
        asyncio.run(example_server())
    elif mode == "client":
        asyncio.run(example_client())
    elif mode == "p2p":
        asyncio.run(example_peer_to_peer())
    else:
        print(f"Unknown mode: {mode}")