#!/usr/bin/env python3
"""TLS Test - Server"""
import asyncio
import sys
import os
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
    print("Starting TLS server on port 9998...")
    await server.start()
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await server.stop()

if __name__ == "__main__":
    asyncio.run(main())
