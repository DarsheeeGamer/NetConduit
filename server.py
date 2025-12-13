"""
Conduit Server Example
Properly designed with ServerDescriptor configuration
"""

import asyncio
from conduit import Server, ServerDescriptor
from conduit.response import Response, Error

r = Response()
e = Error()

async def main():
    # Create server descriptor with proper configuration
    config = ServerDescriptor(
        name="example_server",
        version="1.0.0",
        description="Example Conduit server for device communication",
        
        # Network configuration
        host="0.0.0.0",  # Listen on all interfaces (IPv4)
        port=8080,
        ipv6=True,  # Also listen on IPv6
        
        # Authentication
        password="kaede123",
        
        # Server limits and tuning
        max_connections=100,  # Maximum concurrent clients
        max_message_size=10 * 1024 * 1024,  # 10MB max message size
        buffer_size=64 * 1024,  # 64KB socket buffer
        
        # Timeouts and heartbeat
        connection_timeout=120,  # Disconnect idle clients after 120s
        heartbeat_interval=30,  # Send heartbeat every 30s
        heartbeat_timeout=90,  # Expect heartbeat response within 90s
        
        # Backpressure configuration
        send_queue_size=1000,  # Max messages in send queue
        receive_queue_size=1000,  # Max messages in receive queue
        enable_backpressure=True,  # Enable flow control
        
        # Advanced options
        enable_compression=False,  # Compress large messages (optional)
        protocol_version="1.0",
    )
    
    # Create server instance
    server = Server(config)
    
    
    # ========================================================================
    # Message Handlers
    # ========================================================================
    
    @server.on("hello")
    async def handle_hello(client, data):
        """Handle 'hello' message type"""
        print(f"[{client.id}] Received hello: {data}")
        await client.send("hello", f"Hi back! You said: {data}")
    
    
    @server.on("chat")
    async def handle_chat(client, data):
        """Handle chat messages"""
        message = data.get("message")
        username = data.get("username", "Anonymous")
        
        print(f"[{client.id}] {username}: {message}")
        
        # Echo back to sender
        await client.send("chat", {
            "from": "server",
            "message": f"Echo: {message}"
        })
    
    
    @server.on("file")
    async def handle_file(client, data):
        """Handle file transfers"""
        filename = data["filename"]
        content = data["content"]
        file_size = len(content)
        
        # Save file
        import os
        os.makedirs("./uploads", exist_ok=True)
        
        filepath = f"./uploads/{filename}"
        with open(filepath, "wb") as f:
            f.write(content)
        
        print(f"[{client.id}] Saved file: {filename} ({file_size} bytes)")
        
        await client.send("file_ack", {
            "filename": filename,
            "status": "saved",
            "size": file_size
        })
    
    
    @server.on("broadcast")
    async def handle_broadcast(client, data):
        """Broadcast message to all connected clients"""
        message = data.get("message")
        
        print(f"[{client.id}] Broadcasting: {message}")
        
        # Send to all clients except sender
        await server.broadcast("broadcast", {
            "from": client.id,
            "message": message
        }, exclude=[client.id])
    
    
    # ========================================================================
    # RPC Handlers
    # ========================================================================
# for RPC use r(the rpc output or blah blah blah)    
# TO see or check for errors use e()
# also use proper data structures for RPC preferably Pydantic or smth pass this data model to a data trucutre constructor or smth ...
    @server.rpc
    async def get_server_info():
        """Get server information and statistics"""
        return {
            "name": config.name,
            "version": config.version,
            "description": config.description,
            "uptime": server.uptime(),
            "active_connections": server.connection_count(),
            "max_connections": config.max_connections,
            "total_bytes_sent": server.total_bytes_sent(),
            "total_bytes_received": server.total_bytes_received(),
        }
    
    
    @server.rpc
    async def echo(message):
        """Simple echo RPC"""
        return {"echo": message}
    
    
    @server.rpc
    async def calculate(operation, a, b):
        """Perform calculation"""
        if operation == "add":
            return {"result": a + b}
        elif operation == "subtract":
            return {"result": a - b}
        elif operation == "multiply":
            return {"result": a * b}
        elif operation == "divide":
            if b == 0:
                raise ValueError("Division by zero")
            return {"result": a / b}
        else:
            raise ValueError(f"Unknown operation: {operation}")
    
    
    @server.rpc
    async def list_clients():
        """Get list of connected clients"""
        clients = []
        for client in server.get_clients():
            clients.append({
                "id": client.id,
                "address": client.address,
                "port": client.port,
                "connected_at": client.connected_at,
                "bytes_sent": client.bytes_sent,
                "bytes_received": client.bytes_received,
            })
        return {"clients": clients}
    
    
    # ========================================================================
    # Lifecycle Hooks
    # ========================================================================
    
    @server.on_connect
    async def on_client_connect(client):
        """Called when a client connects and authenticates"""
        print(f"✓ Client connected: {client.id} from {client.address}:{client.port}")
        
        # Send welcome message
        await client.send("welcome", {
            "message": "Welcome to Conduit Server!",
            "server": config.name,
            "your_id": client.id
        })
    
    
    @server.on_disconnect
    async def on_client_disconnect(client, reason):
        """Called when a client disconnects"""
        print(f"✗ Client disconnected: {client.id} (Reason: {reason})")
    
    
    @server.on_heartbeat_timeout
    async def on_heartbeat_timeout(client):
        """Called when client fails to respond to heartbeat"""
        print(f"⚠ Heartbeat timeout for client: {client.id}")
        # Server will auto-disconnect the client
    
    
    @server.on_error
    async def on_error(client, error):
        """Called when an error occurs with a client"""
        print(f"✗ Error with client {client.id}: {error}")
    
    
    # ========================================================================
    # Start Server
    # ========================================================================
    
    print("=" * 60)
    print(f"Starting {config.name} v{config.version}")
    print(f"Listening on {config.host}:{config.port}")
    print(f"Max connections: {config.max_connections}")
    print(f"Heartbeat interval: {config.heartbeat_interval}s")
    print("=" * 60)
    
    # Start the server
    await server.start()
    
    print("✓ Server started successfully")
    print("Press Ctrl+C to stop")
    
    # Keep server running
    try:
        await server.wait_until_stopped()
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
        await server.stop()
        print("✓ Server stopped")


if __name__ == "__main__":
    asyncio.run(main())
