# Client Documentation

Complete guide to using the netconduit Client.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Client Configuration](#client-configuration)
3. [Connection Management](#connection-management)
4. [Sending Messages](#sending-messages)
5. [Message Handlers](#message-handlers)
6. [RPC Calls](#rpc-calls)
7. [Lifecycle Hooks](#lifecycle-hooks)
8. [Reconnection](#reconnection)
9. [Error Handling](#error-handling)
10. [Advanced Usage](#advanced-usage)

---

## Getting Started

### Basic Client Setup

```python
import asyncio
from conduit import Client, ClientDescriptor

# Create client with configuration
client = Client(ClientDescriptor(
    server_host="localhost",     # Required: Server address
    server_port=8080,            # Required: Server port
    password="your_password",    # Required: Auth password
))

async def main():
    # Connect to server
    connected = await client.connect()
    
    if connected:
        print("Connected successfully!")
        
        # Do operations...
        
        await client.disconnect()
    else:
        print("Connection failed!")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Client Configuration

### ClientDescriptor Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `server_host` | str | **Required** | Server hostname/IP |
| `server_port` | int | **Required** | Server port |
| `password` | str | **Required** | Authentication password |
| `name` | str | `"conduit_client"` | Client name |
| `version` | str | `"1.0.0"` | Client version |
| `use_ipv6` | bool | `False` | Use IPv6 |
| `connect_timeout` | float | `10.0` | Connection timeout |
| `buffer_size` | int | `65536` | Socket buffer size |
| `heartbeat_interval` | float | `30.0` | Heartbeat interval |
| `heartbeat_timeout` | float | `90.0` | Heartbeat timeout |
| `send_queue_size` | int | `1000` | Send queue size |
| `receive_queue_size` | int | `1000` | Receive queue size |
| `enable_compression` | bool | `False` | Enable compression |
| `rpc_timeout` | float | `30.0` | Default RPC timeout |
| `reconnect_enabled` | bool | `True` | Enable auto-reconnect |
| `reconnect_attempts` | int | `5` | Max reconnect attempts (0 = unlimited) |
| `reconnect_delay` | float | `1.0` | Initial reconnect delay |
| `reconnect_delay_multiplier` | float | `2.0` | Backoff multiplier |
| `reconnect_delay_max` | float | `60.0` | Max reconnect delay |

### Example: Full Configuration

```python
from conduit import Client, ClientDescriptor

client = Client(ClientDescriptor(
    # Connection
    server_host="game.example.com",
    server_port=9000,
    password="game_secret_key",
    
    # Identity
    name="GameClient",
    version="2.0.0",
    
    # Timeouts
    connect_timeout=5.0,
    rpc_timeout=10.0,
    
    # Heartbeat
    heartbeat_interval=15.0,
    heartbeat_timeout=45.0,
    
    # Reconnection
    reconnect_enabled=True,
    reconnect_attempts=10,
    reconnect_delay=2.0,
    reconnect_delay_max=30.0,
    
    # Performance
    buffer_size=131072,
    enable_compression=True,
))
```

---

## Connection Management

### Connect and Check Status

```python
# Connect to server
connected = await client.connect()

# Check connection status
if client.is_connected:
    print("Connected!")
    
if client.is_authenticated:
    print("Authenticated!")

# Get connection state
from conduit import ConnectionState
state = client.state
print(f"State: {state.name}")
```

### Connection States

| State | Description |
|-------|-------------|
| `DISCONNECTED` | Not connected |
| `CONNECTING` | Connection in progress |
| `AUTHENTICATING` | Auth handshake in progress |
| `CONNECTED` | Connected but not active |
| `ACTIVE` | Ready for communication |
| `PAUSED` | Paused (backpressure) |
| `CLOSING` | Closing connection |
| `CLOSED` | Connection closed |
| `FAILED` | Connection failed |

### Disconnect

```python
# Gracefully disconnect
await client.disconnect()

# Check status
print(f"Connected: {client.is_connected}")  # False
```

### Server Information

```python
# After connecting, access server info
server_info = client.server_info
print(f"Server name: {server_info.get('name')}")
print(f"Server version: {server_info.get('version')}")

# Session token
token = client.session_token
print(f"Session: {token}")
```

### Connection Health

```python
# Get health status
health = client.health()
print(f"Connected: {health['connected']}")
print(f"State: {health['state']}")
print(f"Authenticated: {health['authenticated']}")
print(f"Reconnect attempts: {health['reconnect_attempts']}")
```

---

## Sending Messages

### Send a Message

```python
# Send message to server
await client.send("chat_message", {
    "message": "Hello, server!",
    "timestamp": time.time(),
})
```

### Send with Different Types

```python
# Send player position
await client.send("player_move", {
    "x": 100.5,
    "y": 200.0,
    "z": 0.0,
})

# Send game action
await client.send("player_action", {
    "action": "attack",
    "target_id": "enemy_001",
    "weapon": "sword",
})

# Send settings update
await client.send("update_settings", {
    "music_volume": 0.8,
    "sfx_volume": 1.0,
    "notifications": True,
})
```

---

## Message Handlers

### Register Message Handler

```python
@client.on("server_announcement")
async def handle_announcement(data):
    """
    Handle incoming announcement from server.
    
    Args:
        data: Message payload from server
    """
    print(f"Announcement: {data['message']}")

@client.on("chat_message")
async def handle_chat(data):
    sender = data.get("from", "Unknown")
    message = data.get("message", "")
    print(f"[{sender}]: {message}")

@client.on("player_joined")
async def handle_player_joined(data):
    player_id = data["player_id"]
    print(f"Player {player_id} joined the game!")
```

### Handle Game Events

```python
@client.on("game_state")
async def handle_game_state(data):
    """Handle game state updates."""
    players = data.get("players", [])
    scores = data.get("scores", {})
    
    for player in players:
        score = scores.get(player["id"], 0)
        print(f"{player['name']}: {score} points")

@client.on("damage_received")
async def handle_damage(data):
    """Handle damage notification."""
    amount = data["amount"]
    source = data["source"]
    current_health = data["current_health"]
    
    print(f"Took {amount} damage from {source}! HP: {current_health}")

@client.on("item_collected")
async def handle_item(data):
    """Handle item collection."""
    item_name = data["item"]["name"]
    quantity = data.get("quantity", 1)
    print(f"Collected {quantity}x {item_name}")
```

---

## RPC Calls

### Basic RPC Call

```python
from conduit import data

# Call RPC method
result = await client.rpc.call("add", args=data(a=10, b=20))
print(f"Result: {result}")  # 30

# Call with float arguments
result = await client.rpc.call("multiply", args=data(x=3.5, y=2.0))
print(f"Result: {result}")  # 7.0

# Call with string arguments
result = await client.rpc.call("greet", args=data(name="World"))
print(f"Result: {result}")  # "Hello, World!"
```

### RPC with Complex Data

```python
# Send complex objects
result = await client.rpc.call("create_user", args=data(
    username="player1",
    email="player1@example.com",
    age=25,
    metadata={
        "country": "US",
        "language": "en",
    }
))

print(f"Created user: {result}")
```

### RPC with Timeout

```python
# Custom timeout for this call
result = await client.rpc.call(
    "slow_operation",
    args=data(param="value"),
    timeout=60.0  # 60 second timeout
)
```

### Discover Available Methods

```python
# Get list of available RPC methods
methods = await client.rpc.discover()

print("Available RPC methods:")
for method in methods:
    print(f"  - {method['name']}: {method.get('description', 'No description')}")
```

### Handle RPC Errors

```python
from conduit.rpc.rpc_class import RPCError, RPCTimeout

try:
    result = await client.rpc.call("some_method", args=data(x=1))
    print(f"Success: {result}")
    
except RPCTimeout:
    print("RPC call timed out!")
    
except RPCError as e:
    print(f"RPC error: {e.message}")
    print(f"Error code: {e.code}")
    if e.details:
        print(f"Details: {e.details}")
```

### RPC Response Handling

```python
# Handle response with success/error format
result = await client.rpc.call("get_user", args=data(user_id=123))

if isinstance(result, dict):
    if result.get("success"):
        user = result.get("data")
        print(f"User found: {user}")
    else:
        error = result.get("error")
        print(f"Error: {error}")
```

---

## Lifecycle Hooks

### Connect Hook

```python
@client.on_connect
async def on_connect(cli):
    """Called when client connects to server."""
    print("Connected to server!")
    print(f"Server info: {cli.server_info}")
    
    # Initialize resources
    await load_user_data()
    
    # Notify server we're ready
    await cli.send("client_ready", {
        "version": cli.config.version,
    })
```

### Disconnect Hook

```python
@client.on_disconnect
async def on_disconnect(cli):
    """Called when client disconnects."""
    print("Disconnected from server")
    
    # Cleanup
    await save_user_data()
    
    # Update UI
    show_disconnected_message()
```

### Reconnect Hook

```python
@client.on_reconnect
async def on_reconnect(cli):
    """Called when client reconnects after disconnect."""
    print("Reconnected to server!")
    
    # Re-sync state
    await cli.send("request_sync", {})
    
    # Update UI
    hide_reconnecting_overlay()
```

---

## Reconnection

### Automatic Reconnection

```python
# Enable auto-reconnect (default is True)
client = Client(ClientDescriptor(
    server_host="localhost",
    server_port=8080,
    password="secret",
    
    # Reconnection settings
    reconnect_enabled=True,
    reconnect_attempts=5,       # Max attempts (0 = unlimited)
    reconnect_delay=1.0,        # Initial delay (seconds)
    reconnect_delay_multiplier=2.0,  # Exponential backoff
    reconnect_delay_max=60.0,   # Max delay between attempts
))
```

### Disable Reconnection

```python
# Disable for single-shot connections
client = Client(ClientDescriptor(
    server_host="localhost",
    server_port=8080,
    password="secret",
    reconnect_enabled=False,
))
```

### Track Reconnection

```python
@client.on_disconnect
async def on_disconnect(cli):
    print("Disconnected! Waiting for reconnect...")

@client.on_reconnect
async def on_reconnect(cli):
    health = cli.health()
    attempts = health['reconnect_attempts']
    print(f"Reconnected after {attempts} attempts!")
```

---

## Error Handling

### Connection Errors

```python
try:
    connected = await client.connect()
    if not connected:
        print("Failed to connect - check credentials")
        
except ConnectionRefusedError:
    print("Server is not running!")
    
except asyncio.TimeoutError:
    print("Connection timed out!")
    
except Exception as e:
    print(f"Connection error: {e}")
```

### RPC Errors

```python
from conduit.rpc.rpc_class import RPCError, RPCTimeout

async def safe_rpc_call():
    try:
        result = await client.rpc.call("risky_operation", args=data(x=1))
        return result
        
    except RPCTimeout:
        print("Operation timed out")
        return None
        
    except RPCError as e:
        print(f"RPC failed: {e.message}")
        return None
```

### Send Errors

```python
from conduit.exceptions import NotConnectedError

try:
    await client.send("message", {"data": "value"})
except NotConnectedError:
    print("Not connected to server!")
```

---

## Advanced Usage

### IPv6 Connection

```python
client = Client(ClientDescriptor(
    server_host="::1",          # IPv6 localhost
    server_port=8080,
    password="secret",
    use_ipv6=True,              # Enable IPv6
))
```

### Access Configuration

```python
# Get client configuration
config = client.config

print(f"Client name: {config.name}")
print(f"Server: {config.server_host}:{config.server_port}")
print(f"RPC timeout: {config.rpc_timeout}")
```

### Connection Timeout

```python
# Short timeout for quick connection check
client = Client(ClientDescriptor(
    server_host="localhost",
    server_port=8080,
    password="secret",
    connect_timeout=3.0,  # 3 second timeout
    reconnect_enabled=False,
))

connected = await client.connect()
if not connected:
    print("Server not responding quickly")
```

---

## Complete Example

```python
#!/usr/bin/env python3
"""Complete client example with all features."""

import asyncio
import time
from conduit import Client, ClientDescriptor, data

# Configuration
client = Client(ClientDescriptor(
    server_host="localhost",
    server_port=8080,
    password="secret123",
    name="ExampleClient",
    version="1.0.0",
    reconnect_enabled=True,
    reconnect_attempts=3,
))


# === Lifecycle Hooks ===

@client.on_connect
async def on_connect(cli):
    print(f"Connected to {cli.server_info.get('name', 'server')}!")
    
    # Request initial data
    stats = await cli.rpc.call("get_stats")
    print(f"Server has {stats.get('data', {}).get('clients', 0)} clients")

@client.on_disconnect
async def on_disconnect(cli):
    print("Disconnected from server")

@client.on_reconnect
async def on_reconnect(cli):
    print("Reconnected!")


# === Message Handlers ===

@client.on("announcement")
async def handle_announcement(msg):
    print(f"[ANNOUNCEMENT] {msg.get('message')}")

@client.on("chat")
async def handle_chat(msg):
    sender = msg.get("from", "Unknown")
    text = msg.get("message", "")
    print(f"[CHAT] {sender}: {text}")

@client.on("pong")
async def handle_pong(msg):
    print(f"Received pong at {msg.get('time')}")


# === Main ===

async def main():
    # Connect
    connected = await client.connect()
    if not connected:
        print("Failed to connect!")
        return
    
    print("Running client. Press Ctrl+C to exit.\n")
    
    try:
        # Send ping
        response = await client.send("ping", {})
        print(f"Ping sent")
        
        # RPC call: calculate
        result = await client.rpc.call("calculate", args=data(
            a=100,
            b=25,
            operation="add"
        ))
        print(f"100 + 25 = {result.get('data', {}).get('result')}")
        
        # RPC call: multiply
        result = await client.rpc.call("calculate", args=data(
            a=7.5,
            b=4.0,
            operation="multiply"
        ))
        print(f"7.5 * 4.0 = {result.get('data', {}).get('result')}")
        
        # Send chat message
        await client.send("chat", {"message": "Hello from client!"})
        
        # Discover available methods
        methods = await client.rpc.discover()
        print(f"\nAvailable RPC methods: {[m['name'] for m in methods]}")
        
        # Keep running to receive messages
        while client.is_connected:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await client.disconnect()
        print("Disconnected. Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Quick Reference

### Connection
```python
await client.connect()       # Connect to server
await client.disconnect()    # Disconnect
client.is_connected         # Check if connected
client.is_authenticated     # Check if authenticated
client.health()             # Get connection health
```

### Messaging
```python
await client.send(type, data)           # Send message
@client.on("type")                      # Handle message
```

### RPC
```python
result = await client.rpc.call(method, args=data(...))  # Call RPC
methods = await client.rpc.discover()                    # List methods
```

### Lifecycle
```python
@client.on_connect           # Connection hook
@client.on_disconnect        # Disconnection hook
@client.on_reconnect         # Reconnection hook
```
