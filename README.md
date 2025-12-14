# netconduit

[![PyPI version](https://badge.fury.io/py/netconduit.svg)](https://badge.fury.io/py/netconduit)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![AsyncIO](https://img.shields.io/badge/async-asyncio-green.svg)](https://docs.python.org/3/library/asyncio.html)

**Production-ready async bidirectional TCP communication library with custom binary protocol, type-safe RPC, and Pydantic integration.**

Developed by **Kaede Dev - Kento Hinode**

## Features

- 🚀 **Async/Await** - Built entirely on asyncio for non-blocking I/O
- 🔌 **Raw TCP** - Direct TCP communication (IPv4 & IPv6)
- 📦 **Binary Protocol** - Efficient 32-byte header + MessagePack payload
- 🔐 **Password Authentication** - Secure PBKDF2-SHA256 based auth
- 📡 **Type-Safe RPC** - Remote procedure calls with Pydantic validation
- 💓 **Heartbeat Monitoring** - Automatic connection health checks
- 🚦 **Backpressure** - Flow control to prevent buffer overflow
- 🎨 **Flask-like API** - Decorator-based handler registration

## Installation

```bash
pip install netconduit
```

## Quick Start

### Server

```python
import asyncio
from conduit import Server, ServerDescriptor, Response, data

server = Server(ServerDescriptor(
    host="0.0.0.0",
    port=8080,
    password="your_secret_password",
    name="MyServer",
))

# Handle messages with decorators
@server.on("greeting")
async def handle_greeting(client, message):
    name = message.get("name", "stranger")
    return {"reply": f"Hello, {name}!"}

# Register RPC methods
@server.rpc
async def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

@server.rpc
async def multiply(x: float, y: float) -> float:
    """Multiply two numbers."""
    return x * y

# Lifecycle hooks
@server.on_startup
async def startup(srv):
    print(f"Server starting on {srv.address}")

@server.on_client_connect
async def client_connected(connection):
    print(f"Client connected: {connection.id}")

async def main():
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())
```

### Client

```python
import asyncio
from conduit import Client, ClientDescriptor, data

client = Client(ClientDescriptor(
    server_host="localhost",
    server_port=8080,
    password="your_secret_password",
    name="MyClient",
    reconnect_enabled=True,
))

# Handle server messages
@client.on("broadcast")
async def handle_broadcast(message):
    print(f"Broadcast received: {message}")

@client.on_connect
async def connected(cli):
    print("Connected to server!")

async def main():
    await client.connect()
    
    # Send a message
    await client.send("greeting", {"name": "World"})
    
    # RPC calls
    result = await client.rpc.call("add", args=data(a=10, b=20))
    print(f"10 + 20 = {result}")
    
    result = await client.rpc.call("multiply", args=data(x=3.5, y=2.0))
    print(f"3.5 * 2.0 = {result}")
    
    # Discover available RPC methods
    methods = await client.rpc.discover()
    print(f"Available methods: {[m['name'] for m in methods]}")
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

## Configuration

### ServerDescriptor

```python
ServerDescriptor(
    # Required
    password="secret",
    
    # Optional
    name="my_server",
    version="1.0.0",
    host="0.0.0.0",
    port=8080,
    ipv6=False,
    max_connections=100,
    heartbeat_interval=30.0,
    heartbeat_timeout=90.0,
    enable_compression=False,
    enable_backpressure=True,
)
```

### ClientDescriptor

```python
ClientDescriptor(
    # Required
    server_host="localhost",
    server_port=8080,
    password="secret",
    
    # Optional
    name="my_client",
    version="1.0.0",
    use_ipv6=False,
    reconnect_enabled=True,
    reconnect_attempts=5,
    reconnect_delay=1.0,
    rpc_timeout=30.0,
)
```

## Protocol

netconduit uses a custom binary protocol:

- **Magic**: `CNDT` (4 bytes)
- **Version**: Protocol version (1 byte)
- **Type**: Message type (1 byte)
- **Flags**: Compression, priority, etc. (2 bytes)
- **Length**: Payload length (4 bytes)
- **Correlation ID**: For RPC matching (8 bytes)
- **Timestamp**: Unix timestamp (8 bytes)
- **Reserved**: Future use (4 bytes)
- **Payload**: MessagePack encoded data

### Message Types

| Type | Description |
|------|-------------|
| MESSAGE | Regular message |
| RPC_REQUEST | RPC call |
| RPC_RESPONSE | RPC result |
| RPC_ERROR | RPC error |
| HEARTBEAT_PING | Keep-alive ping |
| HEARTBEAT_PONG | Keep-alive pong |
| AUTH_REQUEST | Authentication |
| AUTH_SUCCESS | Auth success |
| AUTH_FAILURE | Auth failure |

## Testing

```bash
# Install dev dependencies
pip install netconduit[dev]

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=conduit --cov-report=html
```

### Debug Scripts

For manual testing with raw data logging:

```bash
# Terminal 1 - Start server
python test_server_debug.py          # IPv4
python test_server_debug.py --ipv6   # IPv6

# Terminal 2 - Run client
python test_client_debug.py          # IPv4
python test_client_debug.py --ipv6   # IPv6
```

## Requirements

- Python 3.10+
- pydantic >= 2.0
- msgpack >= 1.0

## License

MIT License - see [LICENSE](LICENSE) for details.

## Author

**Kaede Dev - Kento Hinode**  
Email: cleaverdeath@gmail.com  
GitHub: [DarsheeeGamer](https://github.com/DarsheeeGamer)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
