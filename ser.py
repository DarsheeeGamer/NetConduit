# server.py
import asyncio
from conduit import Server, ServerDescriptor

server = Server(ServerDescriptor(
    host="0.0.0.0",
    port=9000,
    password="echo_secret",
    name="EchoServer",
))

@server.rpc
async def echo(message: str) -> str:
    """Echo back the received message."""
    return message

@server.on_startup
async def on_startup(srv):
    print(f"Echo RPC server running on {srv.address}")

async def main():
    await server.run()  # blocks until shutdown

if __name__ == "__main__":
    asyncio.run(main())
