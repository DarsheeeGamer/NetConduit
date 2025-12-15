# netconduit Documentation

Welcome to the netconduit documentation.

## Quick Navigation

| Guide | Description |
|-------|-------------|
| [Quick Start](quickstart.md) | Get running in 5 minutes |
| [Server Guide](server/README.md) | Complete server documentation |
| [Client Guide](client/README.md) | Complete client documentation |
| [Examples](examples.md) | Real-world examples |
| [Protocol Spec](protocol/README.md) | Binary protocol details |

## Installation

```bash
pip install netconduit
```

## Basic Usage

### Server
```python
from conduit import Server, ServerDescriptor

server = Server(ServerDescriptor(password="secret"))

@server.rpc
async def add(a: int, b: int) -> int:
    return a + b

await server.run()
```

### Client
```python
from conduit import Client, ClientDescriptor, data

client = Client(ClientDescriptor(
    server_host="localhost", server_port=8080, password="secret"
))

await client.connect()
result = await client.rpc.call("add", args=data(a=10, b=20))
```

## Features

- **RPC**: Type-safe remote procedure calls
- **Messages**: Bidirectional messaging
- **Broadcasting**: Send to all clients
- **Heartbeat**: Connection health monitoring
- **Auto-Reconnect**: Automatic reconnection
- **Flow Control**: Backpressure handling

## Support

- **GitHub**: [DarsheeeGamer/NetConduit](https://github.com/DarsheeeGamer/NetConduit)
- **Email**: cleaverdeath@gmail.com

## License

MIT License - Kaede Dev - Kento Hinode
