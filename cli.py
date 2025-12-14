# client.py
import asyncio
from conduit import Client, ClientDescriptor, data

client = Client(ClientDescriptor(
    server_host="127.0.0.1",
    server_port=9000,
    password="echo_secret",
    name="EchoClient",
    reconnect_enabled=False,
))

@client.on_connect
async def on_connect(cli):
    print("Connected & authenticated")

    result = await cli.rpc.call(
        "echo",
        args=data(message="Hello NetConduit")
    )

    print("RPC response:", result)

    await cli.disconnect()

@client.on_disconnect
async def on_disconnect(cli):
    print("Disconnected from server")

async def main():
    connected = await client.connect()
    if not connected:
        print("Connection failed")
        return

    # ✅ REQUIRED per asyncio + your lifecycle model
    while client.is_connected:
        await asyncio.sleep(0.1)

if __name__ == "__main__":
    asyncio.run(main())
