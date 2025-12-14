# Server Documentation

Complete guide to using the netconduit Server.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Server Configuration](#server-configuration)
3. [Message Handlers](#message-handlers)
4. [RPC Methods](#rpc-methods)
5. [Lifecycle Hooks](#lifecycle-hooks)
6. [Broadcasting](#broadcasting)
7. [Connection Management](#connection-management)
8. [Error Handling](#error-handling)
9. [Advanced Usage](#advanced-usage)

---

## Getting Started

### Basic Server Setup

```python
import asyncio
from conduit import Server, ServerDescriptor

# Create server with configuration
server = Server(ServerDescriptor(
    password="your_secret_password",  # Required
    host="0.0.0.0",                   # Listen address
    port=8080,                        # Listen port
))

async def main():
    await server.run()  # Blocks until server stops

if __name__ == "__main__":
    asyncio.run(main())
```

### Start Without Blocking

```python
async def main():
    await server.start()  # Non-blocking
    
    # Do other things...
    
    await server.stop()   # Stop when done
```

---

## Server Configuration

### ServerDescriptor Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `password` | str | **Required** | Authentication password |
| `name` | str | `"conduit_server"` | Server name |
| `version` | str | `"1.0.0"` | Server version |
| `description` | str | `""` | Server description |
| `host` | str | `"0.0.0.0"` | Bind address |
| `port` | int | `8080` | Listen port |
| `ipv6` | bool | `False` | Use IPv6 |
| `max_connections` | int | `100` | Max concurrent clients |
| `buffer_size` | int | `65536` | Socket buffer size |
| `connection_timeout` | float | `30.0` | Connection timeout (seconds) |
| `auth_timeout` | float | `10.0` | Authentication timeout |
| `heartbeat_interval` | float | `30.0` | Heartbeat ping interval |
| `heartbeat_timeout` | float | `90.0` | Heartbeat timeout |
| `send_queue_size` | int | `1000` | Send queue size |
| `receive_queue_size` | int | `1000` | Receive queue size |
| `enable_compression` | bool | `False` | Enable zlib compression |
| `enable_backpressure` | bool | `True` | Enable flow control |

### Example: Full Configuration

```python
from conduit import Server, ServerDescriptor

server = Server(ServerDescriptor(
    # Identity
    name="MyGameServer",
    version="2.0.0",
    description="Game server with RPC support",
    
    # Network
    host="0.0.0.0",
    port=9000,
    ipv6=False,
    
    # Security
    password="super_secret_password_123",
    auth_timeout=5.0,
    
    # Performance
    max_connections=500,
    buffer_size=131072,
    send_queue_size=2000,
    receive_queue_size=2000,
    
    # Health
    heartbeat_interval=30.0,
    heartbeat_timeout=90.0,
    
    # Features
    enable_compression=True,
    enable_backpressure=True,
))
```

---

## Message Handlers

### Register Message Handler

Use the `@server.on()` decorator to handle incoming messages:

```python
@server.on("chat_message")
async def handle_chat(client, data):
    """
    Handle incoming chat message.
    
    Args:
        client: Connection object (the sender)
        data: Message payload (dict)
    
    Returns:
        Response data (optional, sent back to client)
    """
    username = data.get("username")
    message = data.get("message")
    
    print(f"[{username}]: {message}")
    
    # Return value is sent back as response
    return {"received": True, "timestamp": time.time()}
```

### Multiple Message Types

```python
@server.on("player_move")
async def handle_move(client, data):
    x, y = data["x"], data["y"]
    # Process movement
    return {"success": True, "position": {"x": x, "y": y}}

@server.on("player_attack")
async def handle_attack(client, data):
    target_id = data["target"]
    damage = calculate_damage(data)
    return {"hit": True, "damage": damage}

@server.on("player_heal")
async def handle_heal(client, data):
    amount = data.get("amount", 10)
    return {"healed": True, "amount": amount}
```

### Access Client Information

```python
@server.on("identify")
async def handle_identify(client, data):
    # Access client properties
    client_id = client.id
    remote_address = client.remote_address
    is_authenticated = client.is_authenticated
    
    return {
        "your_id": client_id,
        "your_address": str(remote_address),
        "authenticated": is_authenticated,
    }
```

---

## RPC Methods

### Basic RPC Registration

```python
@server.rpc
async def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

@server.rpc
async def multiply(x: float, y: float) -> float:
    """Multiply two numbers."""
    return x * y

@server.rpc
async def greet(name: str) -> str:
    """Return a greeting."""
    return f"Hello, {name}!"
```

### RPC with Pydantic Models

```python
from pydantic import BaseModel
from conduit import Response

class UserCreateRequest(BaseModel):
    username: str
    email: str
    age: int

class UserResponse(BaseModel):
    id: int
    username: str
    email: str

@server.rpc
async def create_user(request: UserCreateRequest) -> UserResponse:
    """Create a new user with validation."""
    # Pydantic automatically validates the request
    user_id = await database.create_user(
        username=request.username,
        email=request.email,
        age=request.age
    )
    
    return UserResponse(
        id=user_id,
        username=request.username,
        email=request.email
    )
```

### RPC with Response Wrapper

```python
from conduit import Response, Error

response = Response()
error = Error()

@server.rpc
async def get_user(user_id: int):
    """Get user by ID with proper response wrapping."""
    user = await database.get_user(user_id)
    
    if user is None:
        return error.not_found("User", identifier=user_id)
    
    return response(user)

@server.rpc
async def delete_user(user_id: int):
    """Delete user with error handling."""
    try:
        await database.delete_user(user_id)
        return response.ok(message="User deleted successfully")
    except PermissionError:
        return error.permission_denied("delete_user")
    except Exception as e:
        return error.internal(details={"error": str(e)})
```

### Custom RPC Method Name

```python
@server.rpc(name="users.list")
async def list_users(limit: int = 10, offset: int = 0):
    """List users with custom method name."""
    users = await database.get_users(limit=limit, offset=offset)
    return response.with_pagination(
        data=users,
        total=await database.count_users(),
        page=offset // limit + 1,
        page_size=limit
    )
```

---

## Lifecycle Hooks

### Startup Hook

```python
@server.on_startup
async def on_startup(srv):
    """Called when server starts."""
    print(f"Server starting on {srv.config.host}:{srv.config.port}")
    
    # Initialize resources
    await database.connect()
    await cache.connect()

@server.on_startup
async def load_config(srv):
    """Multiple startup hooks are supported."""
    config = load_configuration()
    srv.config_data = config
```

### Shutdown Hook

```python
@server.on_shutdown
async def on_shutdown(srv):
    """Called when server stops."""
    print("Server shutting down...")
    
    # Cleanup resources
    await database.disconnect()
    await cache.disconnect()
```

### Client Connection Hooks

```python
@server.on_client_connect
async def on_client_connect(connection):
    """Called when a client connects and authenticates."""
    print(f"Client connected: {connection.id} from {connection.remote_address}")
    
    # Track connection
    connected_clients[connection.id] = {
        "connected_at": time.time(),
        "address": connection.remote_address,
    }
    
    # Notify other clients
    await server.broadcast("user_joined", {
        "user_id": connection.id,
    }, exclude={connection.id})

@server.on_client_disconnect
async def on_client_disconnect(connection):
    """Called when a client disconnects."""
    print(f"Client disconnected: {connection.id}")
    
    # Cleanup
    if connection.id in connected_clients:
        del connected_clients[connection.id]
    
    # Notify other clients
    await server.broadcast("user_left", {
        "user_id": connection.id,
    })
```

---

## Broadcasting

### Broadcast to All Clients

```python
# Send to all authenticated clients
await server.broadcast("announcement", {
    "message": "Server will restart in 5 minutes",
    "type": "warning",
})
```

### Broadcast with Exclusions

```python
@server.on("chat_message")
async def handle_chat(client, data):
    # Broadcast to everyone except sender
    await server.broadcast(
        "chat_message",
        {
            "from": client.id,
            "message": data["message"],
            "timestamp": time.time(),
        },
        exclude={client.id}  # Exclude the sender
    )
    
    return {"sent": True}
```

### Targeted Sending

```python
# Send to specific client
for connection in server.connections:
    if connection.id == target_client_id:
        await connection.send_message("private_message", {
            "from": sender_id,
            "message": message,
        })
        break
```

---

## Connection Management

### Get All Connections

```python
# Get all connected clients
connections = server.connections

for conn in connections:
    print(f"Client: {conn.id}, Address: {conn.remote_address}")
```

### Connection Count

```python
count = server.connection_count
print(f"Currently {count} clients connected")
```

### Check Server Status

```python
if server.is_running:
    print("Server is running")
else:
    print("Server is stopped")
```

---

## Error Handling

### Using Error Helper

```python
from conduit import Error

error = Error()

@server.rpc
async def process_payment(amount: float, card_token: str):
    # Validation error
    if amount <= 0:
        return error.validation(
            "Amount must be positive",
            field="amount",
            expected="positive number",
            received=amount
        )
    
    # Not found error
    card = await get_card(card_token)
    if not card:
        return error.not_found("Card", identifier=card_token)
    
    # Permission error
    if not card.is_active:
        return error.permission_denied("process_payment")
    
    try:
        result = await charge_card(card, amount)
        return response(result)
    except TimeoutError:
        return error.timeout("payment_gateway")
    except Exception as e:
        return error.internal(details={"reason": str(e)})
```

### Error Codes

| Code | Constant | Description |
|------|----------|-------------|
| 1000 | `UNKNOWN` | Unknown error |
| 1001 | `INTERNAL` | Internal server error |
| 2000 | `VALIDATION` | Validation failed |
| 2001 | `MISSING_FIELD` | Required field missing |
| 2002 | `INVALID_TYPE` | Invalid data type |
| 3000 | `AUTH_REQUIRED` | Authentication required |
| 3001 | `AUTH_FAILED` | Authentication failed |
| 3002 | `PERMISSION_DENIED` | Permission denied |
| 4000 | `METHOD_NOT_FOUND` | RPC method not found |
| 4001 | `INVALID_PARAMS` | Invalid parameters |
| 5000 | `CONNECTION_ERROR` | Connection error |
| 5001 | `TIMEOUT` | Operation timeout |
| 6000 | `RATE_LIMITED` | Rate limit exceeded |

---

## Advanced Usage

### Custom Server Properties

```python
# Access configuration
config = server.config
print(f"Max connections: {config.max_connections}")

# Server address
host, port = server.address
print(f"Listening on {host}:{port}")
```

### IPv6 Server

```python
server = Server(ServerDescriptor(
    host="::1",           # IPv6 localhost
    # or host="::",       # All IPv6 interfaces
    port=8080,
    password="secret",
    ipv6=True,            # Enable IPv6 mode
))
```

### Graceful Shutdown

```python
import signal

async def main():
    server = Server(config)
    
    # Handle SIGTERM/SIGINT
    loop = asyncio.get_event_loop()
    
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig,
            lambda: asyncio.create_task(server.stop())
        )
    
    await server.run()

asyncio.run(main())
```

---

## Complete Example

```python
#!/usr/bin/env python3
"""Complete server example with all features."""

import asyncio
import time
from pydantic import BaseModel
from conduit import Server, ServerDescriptor, Response, Error, data

# Configuration
server = Server(ServerDescriptor(
    name="ExampleServer",
    version="1.0.0",
    host="0.0.0.0",
    port=8080,
    password="secret123",
    max_connections=100,
))

response = Response()
error = Error()

# Track connected clients
clients = {}


# === Lifecycle ===

@server.on_startup
async def startup(srv):
    print(f"Starting {srv.config.name} v{srv.config.version}")
    print(f"Listening on {srv.config.host}:{srv.config.port}")

@server.on_shutdown
async def shutdown(srv):
    print(f"Shutting down. Goodbye!")

@server.on_client_connect
async def client_connected(conn):
    clients[conn.id] = {"connected_at": time.time()}
    print(f"Client {conn.id} connected")
    await server.broadcast("user_join", {"id": conn.id}, exclude={conn.id})

@server.on_client_disconnect
async def client_disconnected(conn):
    if conn.id in clients:
        del clients[conn.id]
    print(f"Client {conn.id} disconnected")
    await server.broadcast("user_leave", {"id": conn.id})


# === Message Handlers ===

@server.on("ping")
async def handle_ping(client, data):
    return {"pong": True, "time": time.time()}

@server.on("chat")
async def handle_chat(client, data):
    await server.broadcast("chat", {
        "from": client.id,
        "message": data.get("message", ""),
        "timestamp": time.time(),
    }, exclude={client.id})
    return {"sent": True}


# === RPC Methods ===

class CalculateRequest(BaseModel):
    a: float
    b: float
    operation: str

@server.rpc
async def calculate(request: CalculateRequest):
    """Perform calculation."""
    ops = {
        "add": lambda a, b: a + b,
        "subtract": lambda a, b: a - b,
        "multiply": lambda a, b: a * b,
        "divide": lambda a, b: a / b if b != 0 else None,
    }
    
    if request.operation not in ops:
        return error.validation(
            f"Unknown operation: {request.operation}",
            field="operation"
        )
    
    result = ops[request.operation](request.a, request.b)
    
    if result is None:
        return error("Division by zero", code=400)
    
    return response({"result": result})

@server.rpc
async def get_stats():
    """Get server statistics."""
    return response({
        "clients": len(clients),
        "uptime": time.time(),
    })


# === Main ===

async def main():
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())
```
