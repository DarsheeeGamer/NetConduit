# Quick Start Guide

Get up and running with netconduit in 5 minutes.

## Installation

```bash
pip install netconduit
```

## Step 1: Create a Server

```python
# server.py
import asyncio
from conduit import Server, ServerDescriptor

server = Server(ServerDescriptor(
    host="0.0.0.0",
    port=9000,
    password="my_secret",
))

@server.rpc
async def echo(message: str) -> str:
    return message

@server.rpc
async def add(a: int, b: int) -> int:
    return a + b

@server.on("greet")
async def handle_greet(client, data):
    return {"greeting": f"Hello, {data.get('name')}!"}

@server.on_startup
async def on_startup(srv):
    print(f"Server running on {srv.address}")

asyncio.run(server.run())
```

## Step 2: Create a Client

```python
# client.py
import asyncio
from conduit import Client, ClientDescriptor, data

client = Client(ClientDescriptor(
    server_host="127.0.0.1",
    server_port=9000,
    password="my_secret",
))

@client.on_connect
async def on_connect(cli):
    print("Connected!")

async def main():
    await client.connect()
    
    # RPC calls
    result = await client.rpc.call("echo", args=data(message="Hello!"))
    print(f"Echo: {result}")
    
    result = await client.rpc.call("add", args=data(a=10, b=20))
    print(f"Add: {result}")
    
    await client.disconnect()

asyncio.run(main())
```

## Step 3: Run

```bash
# Terminal 1
python server.py

# Terminal 2
python client.py
```

## Output

**Server:**
```
Server running on ('0.0.0.0', 9000)
```

**Client:**
```
Connected!
Echo: {'success': True, 'data': 'Hello!'}
Add: {'success': True, 'data': 30}
```

## Next Steps

- [Server Guide](server/README.md) - Full server documentation
- [Client Guide](client/README.md) - Full client documentation
- [Examples](examples.md) - Real-world examples
