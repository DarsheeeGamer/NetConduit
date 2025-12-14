# netconduit Documentation

Welcome to the netconduit documentation.

## Quick Links

| Topic | Description |
|-------|-------------|
| [Server Guide](server/README.md) | Complete server documentation |
| [Client Guide](client/README.md) | Complete client documentation |
| [Protocol Specification](protocol/README.md) | Binary protocol details |

## Installation

```bash
pip install netconduit
```

## Quick Start

### Server

```python
import asyncio
from conduit import Server, ServerDescriptor

server = Server(ServerDescriptor(password="secret"))

@server.rpc
async def add(a: int, b: int) -> int:
    return a + b

asyncio.run(server.run())
```

### Client

```python
import asyncio
from conduit import Client, ClientDescriptor, data

client = Client(ClientDescriptor(
    server_host="localhost",
    server_port=8080,
    password="secret"
))

async def main():
    await client.connect()
    result = await client.rpc.call("add", args=data(a=10, b=20))
    print(f"Result: {result}")
    await client.disconnect()

asyncio.run(main())
```

## Features

- 🚀 Async/Await based on asyncio
- 🔌 Raw TCP communication (IPv4 & IPv6)
- 📦 Custom binary protocol with MessagePack
- 🔐 Password authentication
- 📡 Type-safe RPC with Pydantic
- 💓 Heartbeat monitoring
- 🚦 Backpressure flow control
- 🎨 Flask-like decorator API

## Support

- GitHub: [DarsheeeGamer/NetConduit](https://github.com/DarsheeeGamer/NetConduit)
- Email: cleaverdeath@gmail.com

## License

MIT License - Kaede Dev - Kento Hinode
