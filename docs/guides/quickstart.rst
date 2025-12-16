Quick Start
===========

This guide gets you running in 5 minutes.

1. Create a Server
------------------

Create ``server.py``:

.. code-block:: python

    import asyncio
    from conduit import Server, ServerDescriptor

    # Configure the server
    server = Server(ServerDescriptor(
        host="0.0.0.0",
        port=8080,
        password="my_secret_password",
        name="MyServer",
    ))

    # Define an RPC method
    @server.rpc
    async def greet(name: str) -> str:
        return f"Hello, {name}!"

    @server.rpc
    async def add(a: int, b: int) -> int:
        return a + b

    # Handle messages
    @server.on("chat")
    async def handle_chat(client, data):
        print(f"Chat from {client.id}: {data}")
        # Broadcast to all other clients
        await server.broadcast("chat", data, exclude={client.id})

    # Lifecycle hooks
    @server.on_startup
    async def on_start(srv):
        print(f"Server running on {srv.address}")

    @server.on_client_connect
    async def on_connect(conn):
        print(f"Client {conn.id[:8]} connected")

    # Run the server
    if __name__ == "__main__":
        asyncio.run(server.run())

2. Create a Client
------------------

Create ``client.py``:

.. code-block:: python

    import asyncio
    from conduit import Client, ClientDescriptor, data

    # Configure the client
    client = Client(ClientDescriptor(
        server_host="localhost",
        server_port=8080,
        password="my_secret_password",
        reconnect_enabled=True,
    ))

    # Handle messages from server
    @client.on("chat")
    async def on_chat(msg):
        print(f"Chat received: {msg}")

    @client.on_connect
    async def on_connect(cli):
        print("Connected to server!")

    async def main():
        # Connect
        await client.connect()

        # Call RPC methods
        result = await client.rpc.call("greet", args=data(name="World"))
        print(result)  # {'success': True, 'data': 'Hello, World!'}

        result = await client.rpc.call("add", args=data(a=10, b=20))
        print(result)  # {'success': True, 'data': 30}

        # Send a message
        await client.send("chat", {"message": "Hello everyone!"})

        # Stay connected
        await asyncio.sleep(60)
        await client.disconnect()

    if __name__ == "__main__":
        asyncio.run(main())

3. Run It
---------

**Terminal 1 (Server):**

.. code-block:: bash

    python server.py
    # Output: Server running on 0.0.0.0:8080

**Terminal 2 (Client):**

.. code-block:: bash

    python client.py
    # Output:
    # Connected to server!
    # {'success': True, 'data': 'Hello, World!'}
    # {'success': True, 'data': 30}

Next Steps
----------

- :doc:`server` - Complete server guide
- :doc:`client` - Complete client guide
- :doc:`rpc` - RPC method details
- :doc:`messages` - Message handling
