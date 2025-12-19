#!/usr/bin/env python3
"""TLS Test - Server"""
import asyncio
import sys
import os
import logging

# Enable logging to see server state
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s - %(message)s')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from conduit import Server, ServerDescriptor

server = Server(ServerDescriptor(
    host="0.0.0.0",
    port=9998,
    password="tlstest",
    ssl_enabled=True,
    ssl_cert_file="cert.pem",
    ssl_key_file="key.pem",
))

@server.on("ping")
async def on_ping(connection, data):
    print(f"Got ping: {data}")
    await connection.send_message("pong", {"message": "TLS works!"})

async def main():
    print(f"Server state: {server.state}")
    await server.start()
    print(f"Server state: {server.state}")
    try:
        await asyncio.sleep(10)
    except KeyboardInterrupt:
        pass
    await server.stop()
    print(f"Server state: {server.state}")

if __name__ == "__main__":
    asyncio.run(main())
