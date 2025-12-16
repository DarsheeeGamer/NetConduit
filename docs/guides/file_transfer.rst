File Transfer Guide
===================

Bidirectional file transfer with chunked upload/download.

Overview
--------

Both Server and Client can send and receive files:

- **Client → Server**: Upload files to server
- **Server → Client**: Push files to clients
- **Chunked transfer**: Large files sent in 64KB chunks
- **Checksum verification**: SHA256 integrity check
- **Progress tracking**: Speed, ETA, completion %

Setup
-----

.. code-block:: python

    from conduit import FileTransferHandler

    # Create handler with storage directory
    transfer = FileTransferHandler(
        storage_dir="./files",
        chunk_size=64 * 1024  # 64KB chunks
    )

Server Receiving Files
----------------------

.. code-block:: python

    from conduit import Server, ServerDescriptor, FileTransferHandler

    server = Server(ServerDescriptor(password="secret"))
    transfer = FileTransferHandler(storage_dir="./uploads")

    # Register transfer RPC handlers
    transfer.register_server_handlers(server)

    # Handle received files
    @transfer.on_file_received
    async def on_file(client, filepath, metadata):
        print(f"Received: {filepath}")
        print(f"Size: {metadata['size']} bytes")
        print(f"Checksum: {metadata['checksum']}")

Client Sending Files
--------------------

.. code-block:: python

    from conduit import Client, ClientDescriptor, FileTransferHandler

    client = Client(ClientDescriptor(
        server_host="localhost",
        server_port=8080,
        password="secret"
    ))

    transfer = FileTransferHandler()

    async def upload_file():
        await client.connect()
        
        # Progress callback
        def on_progress(progress):
            print(f"{progress.percent:.1f}% - {progress.speed/1024:.1f} KB/s")
        
        result = await transfer.send_to_server(
            client,
            "large_file.zip",
            on_progress=on_progress
        )
        
        if result.get("success"):
            print(f"Uploaded to: {result['path']}")

Server Sending Files
--------------------

Push files from server to clients:

.. code-block:: python

    # Send to specific client
    result = await transfer.send_to_client(
        server,
        client_id,
        "./reports/monthly.pdf",
        on_progress=lambda p: print(f"{p.percent:.1f}%")
    )

Client Receiving Files
----------------------

Download files from server:

.. code-block:: python

    # Register handlers first
    transfer.register_client_handlers(client)

    # Handle incoming files
    @transfer.on_file_received
    async def on_file(filepath, metadata):
        print(f"Downloaded: {filepath}")

    # Or explicitly download
    result = await transfer.receive_from_server(
        client,
        "report.pdf",
        local_dir="./downloads"
    )

Progress Tracking
-----------------

.. code-block:: python

    def on_progress(progress):
        print(f"File: {progress.filename}")
        print(f"Progress: {progress.percent:.1f}%")
        print(f"Transferred: {progress.transferred} / {progress.total_size}")
        print(f"Speed: {progress.speed / 1024 / 1024:.2f} MB/s")
        print(f"ETA: {progress.eta:.1f} seconds")

List Available Files
--------------------

.. code-block:: python

    # Client lists files on server
    result = await client.rpc.call("file_list")
    for file in result.get("data", {}).get("files", []):
        print(f"{file['name']} - {file['size']} bytes")

Complete Example
----------------

**Server (file_server.py):**

.. code-block:: python

    import asyncio
    from conduit import Server, ServerDescriptor, FileTransferHandler

    server = Server(ServerDescriptor(
        port=8080,
        password="secret"
    ))

    transfer = FileTransferHandler(storage_dir="./server_files")
    transfer.register_server_handlers(server)

    @transfer.on_file_received
    async def on_file(client, path, meta):
        print(f"Received {meta['filename']} ({meta['size']} bytes)")
        # Process the file...

    asyncio.run(server.run())

**Client (file_client.py):**

.. code-block:: python

    import asyncio
    from conduit import Client, ClientDescriptor, FileTransferHandler

    client = Client(ClientDescriptor(
        server_host="localhost",
        server_port=8080,
        password="secret"
    ))

    transfer = FileTransferHandler()

    async def main():
        await client.connect()
        
        # Upload a file
        result = await transfer.send_to_server(
            client,
            "my_document.pdf",
            on_progress=lambda p: print(f"\r{p.percent:.1f}%", end="")
        )
        print(f"\nUploaded: {result}")

        await client.disconnect()

    asyncio.run(main())
