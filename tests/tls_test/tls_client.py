#!/usr/bin/env python3
"""TLS Test - Client"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from conduit import Client, ClientDescriptor

client = Client(ClientDescriptor(
    server_host="localhost",
    server_port=9998,
    password="tlstest",
    ssl_enabled=True,
    ssl_verify=False,  # Self-signed cert
))

@client.on("pong")
async def on_pong(data):
    print(f"Got pong: {data}")

async def main():
    print("Connecting with TLS...")
    connected = await client.connect()
    
    if connected:
        print("Connected! Sending ping...")
        await client.send("ping", {"test": "hello TLS"})
        await asyncio.sleep(2)
        await client.disconnect()
        print("TLS test passed!")
    else:
        print("Connection failed!")

if __name__ == "__main__":
    asyncio.run(main())
