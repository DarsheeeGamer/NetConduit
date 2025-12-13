"""
Conduit Client Example
Properly designed with ClientDescriptor configuration
"""

import asyncio
from conduit import Client, ClientDescriptor


async def main():
    # Create client descriptor with proper configuration
    config = ClientDescriptor(
        name="example_client",
        version="1.0.0",
        description="Example Conduit client",
        
        # Server connection details
        server_host="127.0.0.1",
        server_port=8080,
        use_ipv6=False,  # Use IPv4 for this connection
        
        # Authentication
        password="kaede123",
        
        # Connection behavior
        connect_timeout=10,  # Timeout for initial connection
        reconnect_enabled=True,  # Auto-reconnect on disconnect
        reconnect_attempts=5,  # Max reconnection attempts
        reconnect_delay=2,  # Delay between reconnect attempts (exponential backoff)
        
        # Message configuration
        max_message_size=10 * 1024 * 1024,  # 10MB max message size
        buffer_size=64 * 1024,  # 64KB socket buffer
        
        # Timeouts
        rpc_timeout=30,  # RPC call timeout (seconds)
        send_timeout=10,  # Message send timeout
        
        # Heartbeat
        heartbeat_interval=30,  # Send heartbeat every 30s
        heartbeat_timeout=90,  # Expect response within 90s
        
        # Backpressure
        send_queue_size=1000,
        receive_queue_size=1000,
        
        # Advanced
        enable_compression=False,
        protocol_version="1.0",
    )
    
    # Create client instance
    client = Client(config)
    
    
    # ========================================================================
    # Message Handlers (for incoming messages from server)
    # ========================================================================
    
    @client.on("welcome")
    async def handle_welcome(data):
        """Handle welcome message from server"""
        print(f"✓ {data['message']}")
        print(f"  Server: {data['server']}")
        print(f"  Your ID: {data['your_id']}")
    
    
    @client.on("hello")
    async def handle_hello(data):
        """Handle hello responses"""
        print(f"[Server] {data}")
    
    
    @client.on("chat")
    async def handle_chat(data):
        """Handle chat messages"""
        from_user = data.get("from", "Unknown")
        message = data.get("message")
        print(f"[{from_user}] {message}")
    
    
    @client.on("file_ack")
    async def handle_file_ack(data):
        """Handle file upload acknowledgment"""
        print(f"✓ File uploaded: {data['filename']} ({data['size']} bytes)")
    
    
    @client.on("broadcast")
    async def handle_broadcast(data):
        """Handle broadcast messages"""
        from_id = data.get("from")
        message = data.get("message")
        print(f"[Broadcast from {from_id}] {message}")
    
    
    # ========================================================================
    # Lifecycle Hooks
    # ========================================================================
    
    @client.on_connect
    async def on_connected():
        """Called when successfully connected to server"""
        print("✓ Connected to server!")
    
    
    @client.on_disconnect
    async def on_disconnected(reason):
        """Called when disconnected from server"""
        print(f"✗ Disconnected: {reason}")
    
    
    @client.on_reconnect
    async def on_reconnecting(attempt):
        """Called when attempting to reconnect"""
        print(f"⟳ Reconnecting... (Attempt {attempt}/{config.reconnect_attempts})")
    
    
    @client.on_error
    async def on_error(error):
        """Called when an error occurs"""
        print(f"✗ Error: {error}")
    
    
    # ========================================================================
    # Connect to Server
    # ========================================================================
    
    print("=" * 60)
    print(f"{config.name} v{config.version}")
    print(f"Connecting to {config.server_host}:{config.server_port}")
    print("=" * 60)
    
    try:
        # Connect to server
        await client.connect()
        
        # Wait a bit for welcome message
        await asyncio.sleep(0.5)
        
        
        # ====================================================================
        # Example 1: Simple messaging
        # ====================================================================
        print("\n[Example 1] Simple Messaging")
        print("-" * 60)
        
        await client.send("hello", "Hi server!")
        await asyncio.sleep(0.3)
        
        await client.send("chat", {
            "username": "Alice",
            "message": "Hello from the client!"
        })
        await asyncio.sleep(0.3)
        
        
        # ====================================================================
        # Example 2: RPC Calls
        # ====================================================================
        print("\n[Example 2] RPC Calls")
        print("-" * 60)
        # uhhh for response handling also use data structures like JSON and give the data parsed not that the user has to manually parse
        # Get server info
        server_info = await client.call("get_server_info")
        print(f"Server Info:")
        print(f"  Name: {server_info['name']}")
        print(f"  Version: {server_info['version']}")
        print(f"  Uptime: {server_info['uptime']:.2f}s")
        print(f"  Connections: {server_info['active_connections']}")
        
        # Echo test
        echo_result = await client.call("echo", message="Test message")
        print(f"Echo: {echo_result['echo']}")
        
        # Calculation
        calc_result = await client.call("calculate", operation="add", a=15, b=27)
        print(f"15 + 27 = {calc_result['result']}")
        
        calc_result = await client.call("calculate", operation="multiply", a=6, b=7)
        print(f"6 × 7 = {calc_result['result']}")
        
        
        # ====================================================================
        # Example 3: File Transfer
        # ====================================================================
        print("\n[Example 3] File Transfer")
        print("-" * 60)
        
        # Create test file
        test_data = b"Hello from Conduit!\nThis is a test file.\n" * 100
        test_filename = "test_file.txt"
        
        print(f"Sending file: {test_filename} ({len(test_data)} bytes)")
        
        await client.send("file", {
            "filename": test_filename,
            "content": test_data
        })
        
        await asyncio.sleep(0.5)
        
        
        # ====================================================================
        # Example 4: Streaming Messages
        # ====================================================================
        print("\n[Example 4] Streaming Messages")
        print("-" * 60)
        
        for i in range(5):
            await client.send("hello", f"Stream message {i+1}")
            await asyncio.sleep(0.2)
        
        
        # ====================================================================
        # Example 5: Broadcasting
        # ====================================================================
        print("\n[Example 5] Broadcasting")
        print("-" * 60)
        # for sending commands to the server use rpc = RPC()
        # commands = rpc.call("listall")
        # print(commands) 
        # now lets say it has the echo command then the LOC ( line of code  ) will be# 
        # print(rpc.call("echo", args=data(message="Hello from the client!", other args ...)))
        # THE DATA COMMAND will convert it into a proper data structure and then send it to the server//
        await client.send("broadcast", {
            "message": "Hello to all connected clients!"
        })
        
        await asyncio.sleep(0.5)
        
        
        # ====================================================================
        # Example 6: Connection Health
        # ====================================================================
        print("\n[Example 6] Connection Health")
        print("-" * 60)
        
        health = client.get_health()
        print(f"Connection Health:")
        print(f"  RTT: {health.rtt_ms:.2f}ms")
        print(f"  Bytes sent: {health.bytes_sent}")
        print(f"  Bytes received: {health.bytes_received}")
        print(f"  Messages sent: {health.messages_sent}")
        print(f"  Messages received: {health.messages_received}")
        print(f"  Last heartbeat: {health.last_heartbeat}")
        
        
        # Keep connection alive for a bit
        print("\n[Keeping connection alive for 5 seconds...]")
        await asyncio.sleep(5)
        
        
    except ConnectionError as e:
        print(f"\n✗ Connection error: {e}")
    except TimeoutError:
        print(f"\n✗ Operation timed out")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
    finally:
        # Always disconnect cleanly
        print("\nDisconnecting...")
        await client.disconnect()
        print("✓ Disconnected cleanly")


if __name__ == "__main__":
    asyncio.run(main())
