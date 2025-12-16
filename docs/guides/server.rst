Server Guide
============

Complete guide to creating, configuring, and operating netconduit servers.

.. contents:: Table of Contents
   :local:
   :depth: 2

Creating a Server
-----------------

Basic Server
^^^^^^^^^^^^

.. code-block:: python

    import asyncio
    from conduit import Server, ServerDescriptor

    server = Server(ServerDescriptor(
        host="0.0.0.0",
        port=8080,
        password="secret",
    ))

    asyncio.run(server.run())

Full Configuration Example
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    from conduit import Server, ServerDescriptor

    server = Server(ServerDescriptor(
        # === Network Configuration ===
        host="0.0.0.0",        # Bind to all interfaces
        port=8080,             # Listen port
        
        # === Security ===
        password="my_secure_password_here",
        auth_timeout=30.0,     # Max seconds for client to authenticate
        
        # === Performance Tuning ===
        max_connections=1000,  # Max concurrent clients
        buffer_size=65536,     # Socket buffer (64KB)
        
        # === Heartbeat / Health ===
        heartbeat_interval=30.0,  # Ping every 30 seconds
        heartbeat_timeout=90.0,   # Dead if no response in 90s
        
        # === Metadata ===
        name="ProductionServer",
    ))

ServerDescriptor Reference
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Parameter
     - Default
     - Description
   * - ``host``
     - ``"0.0.0.0"``
     - IP address to bind to
   * - ``port``
     - ``8080``
     - Port number to listen on
   * - ``password``
     - Required
     - Authentication password
   * - ``auth_timeout``
     - ``30.0``
     - Seconds before auth timeout
   * - ``max_connections``
     - ``1000``
     - Maximum concurrent connections
   * - ``buffer_size``
     - ``65536``
     - Socket buffer size in bytes
   * - ``heartbeat_interval``
     - ``30.0``
     - Ping interval in seconds
   * - ``heartbeat_timeout``
     - ``90.0``
     - Consider dead after seconds
   * - ``name``
     - ``"Server"``
     - Server identifier name

Defining RPC Methods
--------------------

Basic RPC
^^^^^^^^^

.. code-block:: python

    @server.rpc
    async def echo(message: str) -> str:
        """Echo back the message."""
        return message

    @server.rpc
    async def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    @server.rpc
    async def get_status() -> dict:
        """Get server status."""
        return {
            "status": "online",
            "clients": server.connection_count,
            "uptime": time.time() - server_start_time,
        }

With Type Validation
^^^^^^^^^^^^^^^^^^^^

Arguments are automatically validated using type hints:

.. code-block:: python

    @server.rpc
    async def create_user(
        username: str,
        email: str,
        age: int,
        active: bool = True
    ) -> dict:
        """
        Create a new user.
        
        Arguments are validated automatically:
        - username must be str
        - email must be str
        - age must be int
        - active defaults to True
        """
        return {
            "id": generate_id(),
            "username": username,
            "email": email,
            "age": age,
            "active": active,
        }

With Pydantic Models
^^^^^^^^^^^^^^^^^^^^

For complex validation:

.. code-block:: python

    from pydantic import BaseModel, Field, EmailStr
    from typing import Optional, List

    class CreateUserRequest(BaseModel):
        username: str = Field(min_length=3, max_length=30)
        email: EmailStr
        age: int = Field(ge=0, le=150)
        roles: List[str] = []

    class UserResponse(BaseModel):
        id: int
        username: str
        email: str
        created_at: str

    @server.rpc
    async def create_user(request: CreateUserRequest) -> UserResponse:
        """
        Pydantic validates:
        - username: 3-30 characters
        - email: valid email format
        - age: 0-150
        - roles: list of strings
        """
        user = await db.create_user(
            username=request.username,
            email=request.email,
            age=request.age,
            roles=request.roles,
        )
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            created_at=user.created_at.isoformat(),
        )

Error Handling in RPC
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    from conduit import Error

    @server.rpc
    async def divide(a: float, b: float) -> float:
        if b == 0:
            # Raise exception - will be sent to client
            raise ValueError("Cannot divide by zero")
        return a / b

    @server.rpc
    async def get_user(user_id: int) -> dict:
        user = await db.get_user(user_id)
        if not user:
            raise KeyError(f"User {user_id} not found")
        return user.to_dict()

Built-in RPC Methods
^^^^^^^^^^^^^^^^^^^^

These are automatically available:

- ``listall`` - List all registered RPC methods with their signatures

.. code-block:: python

    # Client can discover available methods
    result = await client.rpc.call("listall")
    # Returns list of method info dicts

Message Handlers
----------------

Registering Handlers
^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    @server.on("chat")
    async def handle_chat(client, data):
        """
        Handle 'chat' message type.
        
        Args:
            client: Connection object
                - client.id: Unique connection ID
                - client.send_message(type, data): Send to this client
                - client.is_authenticated: Auth status
            data: dict - The message payload
        
        Returns:
            Optional dict - Sent back to the sender as response
        """
        username = data.get("username", "Anonymous")
        message = data.get("message", "")
        
        print(f"[{username}] {message}")
        
        # Broadcast to everyone except sender
        await server.broadcast("chat", {
            "from": username,
            "message": message,
            "timestamp": time.time(),
        }, exclude={client.id})
        
        # Return acknowledgment to sender
        return {"sent": True}

Multiple Handlers
^^^^^^^^^^^^^^^^^

.. code-block:: python

    @server.on("player_move")
    async def handle_move(client, data):
        x, y = data["x"], data["y"]
        players[client.id].position = (x, y)
        
        await server.broadcast("player_moved", {
            "player_id": client.id[:8],
            "x": x,
            "y": y,
        }, exclude={client.id})

    @server.on("player_attack")
    async def handle_attack(client, data):
        target = data["target_id"]
        damage = calculate_damage(client.id, target)
        
        await server.broadcast("attack", {
            "attacker": client.id[:8],
            "target": target,
            "damage": damage,
        })

    @server.on("chat")
    async def handle_chat(client, data):
        await server.broadcast("chat", {
            "from": players[client.id].name,
            "message": data["message"],
        })

Lifecycle Hooks
---------------

Startup and Shutdown
^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    @server.on_startup
    async def on_startup(srv):
        """Called when server starts listening."""
        print(f"Server started on {srv.address}")
        print(f"Listening on port {srv.port}")
        
        # Initialize resources
        await database.connect()
        await cache.connect()

    @server.on_shutdown
    async def on_shutdown(srv):
        """Called when server is stopping."""
        print("Server shutting down...")
        
        # Cleanup resources
        await database.disconnect()
        await cache.disconnect()
        
        # Notify all clients
        await server.broadcast("server_shutdown", {
            "message": "Server is shutting down"
        })

Client Connection Events
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    connected_clients = {}

    @server.on_client_connect
    async def on_client_connect(connection):
        """Called when a client connects and authenticates."""
        client_id = connection.id
        connected_clients[client_id] = {
            "connected_at": time.time(),
            "username": None,
        }
        
        print(f"[+] Client {client_id[:8]} connected")
        print(f"    Total clients: {len(connected_clients)}")
        
        # Send welcome
        await connection.send_message("welcome", {
            "message": "Welcome to the server!",
            "server_time": time.time(),
        })
        
        # Notify others
        await server.broadcast("user_joined", {
            "id": client_id[:8],
        }, exclude={client_id})

    @server.on_client_disconnect
    async def on_client_disconnect(connection):
        """Called when a client disconnects."""
        client_id = connection.id
        client_info = connected_clients.pop(client_id, {})
        
        connect_time = client_info.get("connected_at", time.time())
        duration = time.time() - connect_time
        
        print(f"[-] Client {client_id[:8]} disconnected after {duration:.1f}s")
        print(f"    Total clients: {len(connected_clients)}")
        
        # Notify others
        await server.broadcast("user_left", {
            "id": client_id[:8],
        })

Broadcasting
------------

Basic Broadcast
^^^^^^^^^^^^^^^

.. code-block:: python

    # Send to all connected clients
    count = await server.broadcast("notification", {
        "type": "info",
        "text": "Server maintenance in 10 minutes"
    })
    print(f"Sent to {count} clients")

Selective Broadcast
^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    # Send to specific clients only
    team_red = {player.id for player in players if player.team == "red"}
    await server.broadcast("team_message", {
        "message": "Red team objective updated"
    }, include=team_red)

    # Send to everyone EXCEPT some clients
    await server.broadcast("chat", {
        "from": sender_name,
        "message": text
    }, exclude={sender_id})  # Don't send to sender

    # Combine: send to specific clients except some
    await server.broadcast("update", {
        "state": game_state
    }, include=active_players, exclude=spectators)

Direct Client Communication
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    # Get connection and send directly
    connection = server._pool.get(client_id)
    if connection:
        await connection.send_message("private", {
            "text": "This is only for you"
        })

Connection Management
---------------------

Get Connection Info
^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    # Total connection count
    print(f"Connected clients: {server.connection_count}")

    # Check if server is running
    if server.is_running:
        print("Server is active")

    # Get specific connection
    conn = server._pool.get(client_id)
    if conn:
        print(f"Client {conn.id} is connected")
        print(f"Authenticated: {conn.is_authenticated}")

Disconnect Client
^^^^^^^^^^^^^^^^^

.. code-block:: python

    # Kick a client
    conn = server._pool.get(client_id)
    if conn:
        await conn.send_message("kicked", {"reason": "Violation"})
        await conn.disconnect()

Running the Server
------------------

Simple Run
^^^^^^^^^^

.. code-block:: python

    if __name__ == "__main__":
        asyncio.run(server.run())

With Background Tasks
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    async def periodic_broadcast():
        """Broadcast server status every 30 seconds."""
        while True:
            await asyncio.sleep(30)
            if server.is_running:
                await server.broadcast("server_status", {
                    "clients": server.connection_count,
                    "time": time.time(),
                })

    async def main():
        # Start background task
        asyncio.create_task(periodic_broadcast())
        
        # Run server (blocks)
        await server.run()

    if __name__ == "__main__":
        asyncio.run(main())

Graceful Shutdown
^^^^^^^^^^^^^^^^^

.. code-block:: python

    async def main():
        try:
            await server.run()
        except KeyboardInterrupt:
            print("Shutting down...")
        finally:
            await server.stop()

    # Or with signal handlers
    import signal

    def handle_signal(sig, frame):
        asyncio.create_task(server.stop())

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

Complete Example
----------------

Full Chat Server
^^^^^^^^^^^^^^^^

.. code-block:: python

    import asyncio
    import time
    from conduit import Server, ServerDescriptor

    server = Server(ServerDescriptor(
        host="0.0.0.0",
        port=8080,
        password="chat_secret",
        name="ChatServer",
    ))

    users = {}  # client_id -> username

    # === RPC Methods ===

    @server.rpc
    async def set_username(username: str) -> dict:
        # Will get client context from RPC system
        return {"set": True, "username": username}

    @server.rpc
    async def get_users() -> list:
        return list(users.values())

    @server.rpc
    async def get_user_count() -> int:
        return len(users)

    # === Message Handlers ===

    @server.on("chat")
    async def handle_chat(client, data):
        username = users.get(client.id, "Anonymous")
        message = data.get("message", "")
        
        await server.broadcast("chat", {
            "from": username,
            "message": message,
            "time": time.time(),
        }, exclude={client.id})
        
        return {"sent": True}

    @server.on("set_name")
    async def handle_set_name(client, data):
        username = data.get("username", "Anonymous")
        old_name = users.get(client.id)
        users[client.id] = username
        
        if old_name:
            await server.broadcast("name_change", {
                "old": old_name,
                "new": username,
            })
        
        return {"username": username}

    # === Lifecycle ===

    @server.on_startup
    async def on_startup(srv):
        print(f"Chat server running on {srv.address}")

    @server.on_client_connect
    async def on_connect(conn):
        users[conn.id] = f"User_{conn.id[:4]}"
        print(f"[+] {users[conn.id]} joined ({len(users)} online)")
        
        await server.broadcast("user_joined", {
            "username": users[conn.id],
            "count": len(users),
        }, exclude={conn.id})

    @server.on_client_disconnect
    async def on_disconnect(conn):
        username = users.pop(conn.id, "Unknown")
        print(f"[-] {username} left ({len(users)} online)")
        
        await server.broadcast("user_left", {
            "username": username,
            "count": len(users),
        })

    # === Run ===

    if __name__ == "__main__":
        asyncio.run(server.run())
