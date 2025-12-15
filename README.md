# netconduit

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Production-ready async bidirectional TCP communication library with custom binary protocol, type-safe RPC, and Pydantic integration.**

Developed by **Kaede Dev - Kento Hinode**

## Features

- 🚀 **Async/Await** - Built on asyncio
- 🔌 **Raw TCP** - IPv4 & IPv6 support
- 📦 **Binary Protocol** - 32-byte header + MessagePack
- 🔐 **Password Auth** - SHA256-based authentication
- 📡 **Type-Safe RPC** - Pydantic validation
- 💓 **Heartbeat** - Automatic health monitoring
- 🔄 **Auto-Reconnect** - Exponential backoff

## Installation

```bash
pip install netconduit
```

## Quick Start

### Server

```python
import asyncio
from conduit import Server, ServerDescriptor

server = Server(ServerDescriptor(
    host="0.0.0.0", port=8080, password="secret"
))

@server.rpc
async def add(a: int, b: int) -> int:
    return a + b

@server.on("chat")
async def handle_chat(client, data):
    await server.broadcast("chat", data, exclude={client.id})

asyncio.run(server.run())
```

### Client

```python
import asyncio
from conduit import Client, ClientDescriptor, data

client = Client(ClientDescriptor(
    server_host="localhost", server_port=8080, password="secret"
))

@client.on("chat")
async def on_chat(msg):
    print(f"Chat: {msg}")

async def main():
    await client.connect()
    result = await client.rpc.call("add", args=data(a=10, b=20))
    print(f"Result: {result}")  # {'success': True, 'data': 30}

asyncio.run(main())
```

## Documentation

- [Quick Start](documentation/quickstart.md)
- [Server Guide](documentation/server/README.md)
- [Client Guide](documentation/client/README.md)
- [Examples](documentation/examples.md)
- [Protocol Spec](documentation/protocol/README.md)

## Requirements

- Python 3.10+
- pydantic >= 2.0
- msgpack >= 1.0

## License

MIT License - Kaede Dev - Kento Hinode

**GitHub**: [DarsheeeGamer/NetConduit](https://github.com/DarsheeeGamer/NetConduit)
