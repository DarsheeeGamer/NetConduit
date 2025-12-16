netconduit Documentation
========================

.. image:: https://img.shields.io/badge/python-3.10+-blue.svg
   :target: https://www.python.org/downloads/

.. image:: https://img.shields.io/badge/License-MIT-yellow.svg
   :target: https://opensource.org/licenses/MIT

**Production-ready async bidirectional TCP communication library.**

Built for server-to-server and native application communication with:

- Custom binary protocol (32-byte header + MessagePack)
- Type-safe RPC with Pydantic validation
- Bidirectional file transfer and streaming
- Password-based authentication
- Automatic reconnection

.. toctree::
   :maxdepth: 2
   :caption: 🚀 Getting Started

   guides/installation
   guides/quickstart

.. toctree::
   :maxdepth: 2
   :caption: 📖 User Guide

   guides/server
   guides/client
   guides/rpc
   guides/messages
   guides/file_transfer
   guides/streaming
   guides/authentication

.. toctree::
   :maxdepth: 2
   :caption: 📚 API Reference

   api/index

.. toctree::
   :maxdepth: 1
   :caption: 📋 Additional

   changelog
   benchmarks


Quick Example
-------------

**Server:**

.. code-block:: python

    from conduit import Server, ServerDescriptor

    server = Server(ServerDescriptor(
        host="0.0.0.0", 
        port=8080, 
        password="secret"
    ))

    @server.rpc
    async def add(a: int, b: int) -> int:
        return a + b

    @server.on("message")
    async def handle_message(client, data):
        await server.broadcast("message", data, exclude={client.id})

    asyncio.run(server.run())

**Client:**

.. code-block:: python

    from conduit import Client, ClientDescriptor, data

    client = Client(ClientDescriptor(
        server_host="localhost",
        server_port=8080,
        password="secret"
    ))

    @client.on("message")
    async def on_message(msg):
        print(f"Received: {msg}")

    async def main():
        await client.connect()
        result = await client.rpc.call("add", args=data(a=10, b=20))
        print(result)  # {'success': True, 'data': 30}

    asyncio.run(main())


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
