netconduit Documentation
========================

**Production-ready async bidirectional TCP communication library with custom binary protocol, type-safe RPC, and Pydantic integration.**

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   quickstart
   installation

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   server
   client
   rpc
   streaming
   file_transfer

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/server
   api/client
   api/protocol
   api/transfer
   api/streaming

.. toctree::
   :maxdepth: 1
   :caption: Additional

   changelog
   benchmarks


Features
--------

* **Async/Await** - Built entirely on asyncio
* **Raw TCP** - Direct TCP (IPv4 & IPv6)
* **Binary Protocol** - 32-byte header + MessagePack
* **Password Auth** - SHA256-based authentication
* **Type-Safe RPC** - Pydantic validation
* **Bidirectional Streaming** - Both sides can push/consume
* **File Transfer** - Chunked with checksum verification
* **Auto-Reconnect** - Exponential backoff


Quick Example
-------------

Server:

.. code-block:: python

    from conduit import Server, ServerDescriptor

    server = Server(ServerDescriptor(password="secret"))

    @server.rpc
    async def add(a: int, b: int) -> int:
        return a + b

    async def main():
        await server.run()

Client:

.. code-block:: python

    from conduit import Client, ClientDescriptor, data

    client = Client(ClientDescriptor(
        server_host="localhost",
        server_port=8080,
        password="secret"
    ))

    async def main():
        await client.connect()
        result = await client.rpc.call("add", args=data(a=10, b=20))
        print(result)  # {'success': True, 'data': 30}


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
