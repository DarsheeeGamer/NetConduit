Client Guide
============

Complete guide to creating, configuring, and using netconduit clients.

.. contents:: Table of Contents
   :local:
   :depth: 2

Creating a Client
-----------------

Basic Client
^^^^^^^^^^^^

.. code-block:: python

    import asyncio
    from conduit import Client, ClientDescriptor

    client = Client(ClientDescriptor(
        server_host="localhost",
        server_port=8080,
        password="secret",
    ))

    async def main():
        await client.connect()
        # ... use client
        await client.disconnect()

    asyncio.run(main())

Full Configuration Example
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    from conduit import Client, ClientDescriptor

    client = Client(ClientDescriptor(
        # === Connection ===
        server_host="192.168.1.100",  # Server IP or hostname
        server_port=8080,             # Server port
        
        # === Security ===
        password="my_secure_password",
        
        # === Reconnection ===
        reconnect_enabled=True,       # Auto-reconnect on disconnect
        reconnect_delay=1.0,          # Initial delay (seconds)
        reconnect_max_delay=30.0,     # Max backoff delay
        reconnect_max_attempts=0,     # 0 = infinite retry
        
        # === Performance ===
        buffer_size=65536,            # Socket buffer (64KB)
        
        # === Metadata ===
        name="ProductionClient",
    ))

ClientDescriptor Reference
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Parameter
     - Default
     - Description
   * - ``server_host``
     - ``"localhost"``
     - Server IP or hostname
   * - ``server_port``
     - ``8080``
     - Server port
   * - ``password``
     - Required
     - Authentication password
   * - ``reconnect_enabled``
     - ``True``
     - Auto-reconnect on disconnect
   * - ``reconnect_delay``
     - ``1.0``
     - Initial reconnect delay (seconds)
   * - ``reconnect_max_delay``
     - ``30.0``
     - Maximum backoff delay
   * - ``reconnect_max_attempts``
     - ``0``
     - Max attempts (0 = infinite)
   * - ``buffer_size``
     - ``65536``
     - Socket buffer size
   * - ``name``
     - ``"Client"``
     - Client identifier

Connecting and Disconnecting
----------------------------

Basic Connection
^^^^^^^^^^^^^^^^

.. code-block:: python

    async def main():
        # Connect (handles authentication)
        connected = await client.connect()
        
        if not connected:
            print("Failed to connect (wrong password?)")
            return
        
        print("Connected!")
        
        # ... do stuff
        
        # Disconnect
        await client.disconnect()

Check Connection State
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    # Check if connected
    if client.is_connected:
        print("Connected to server")
    else:
        print("Not connected")

    # Check if authenticated
    if client.is_authenticated:
        print("Authenticated")

Connection with Retry
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    async def connect_with_retry(max_retries=5):
        for attempt in range(max_retries):
            try:
                connected = await client.connect()
                if connected:
                    print("Connected!")
                    return True
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        print("All connection attempts failed")
        return False

RPC Calls
---------

Making Calls
^^^^^^^^^^^^

.. code-block:: python

    from conduit import data

    # Simple call
    result = await client.rpc.call("echo", args=data(message="Hello"))
    print(result)
    # {'success': True, 'data': 'Hello'}

    # Multiple arguments
    result = await client.rpc.call("add", args=data(a=10, b=20))
    print(result.get("data"))  # 30

    # Complex arguments
    result = await client.rpc.call("create_user", args=data(
        username="john_doe",
        email="john@example.com",
        age=25,
        roles=["user", "moderator"],
    ))

Handling Responses
^^^^^^^^^^^^^^^^^^

.. code-block:: python

    result = await client.rpc.call("get_user", args=data(user_id=123))

    if result.get("success"):
        user = result.get("data")
        print(f"User: {user['username']}")
    else:
        error = result.get("error")
        code = result.get("code")
        print(f"Error [{code}]: {error}")

Response Format
^^^^^^^^^^^^^^^

All RPC calls return a dict:

**Success:**

.. code-block:: python

    {
        "success": True,
        "data": <return_value>,
        "correlation_id": "uuid..."
    }

**Error:**

.. code-block:: python

    {
        "success": False,
        "error": "Error message",
        "code": "ERROR_CODE",
        "correlation_id": "uuid..."
    }

Timeout
^^^^^^^

.. code-block:: python

    # Set timeout for slow operations
    try:
        result = await client.rpc.call(
            "slow_operation",
            args=data(param=1),
            timeout=5.0  # 5 second timeout
        )
    except asyncio.TimeoutError:
        print("Operation timed out")

Discover Methods
^^^^^^^^^^^^^^^^

.. code-block:: python

    # List all available RPC methods
    result = await client.rpc.call("listall")
    
    print("Available methods:")
    for method in result.get("data", []):
        print(f"  - {method['name']}")
        if method.get('description'):
            print(f"    {method['description']}")

Sending Messages
----------------

Basic Send
^^^^^^^^^^

.. code-block:: python

    # Simple message
    await client.send("event", {
        "type": "click",
        "x": 100,
        "y": 200,
    })

    # Chat message
    await client.send("chat", {
        "username": "John",
        "message": "Hello everyone!",
    })

    # Game action
    await client.send("move", {
        "direction": "north",
        "speed": 5,
    })

Receiving Messages
------------------

Register Handlers
^^^^^^^^^^^^^^^^^

.. code-block:: python

    @client.on("chat")
    async def on_chat(data):
        """Handle chat messages."""
        sender = data.get("from", "Unknown")
        message = data.get("message", "")
        print(f"{sender}: {message}")

    @client.on("notification")
    async def on_notification(data):
        """Handle notifications."""
        print(f"[!] {data.get('text')}")

    @client.on("game_state")
    async def on_game_state(data):
        """Handle game state updates."""
        update_local_state(data)

    @client.on("error")
    async def on_error(data):
        """Handle error messages."""
        print(f"Error from server: {data.get('message')}")

Multiple Message Types
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    # Define all handlers together
    
    @client.on("user_joined")
    async def on_user_joined(data):
        print(f"[+] {data['username']} joined")

    @client.on("user_left")
    async def on_user_left(data):
        print(f"[-] {data['username']} left")

    @client.on("broadcast")
    async def on_broadcast(data):
        print(f"[SERVER] {data['message']}")

    @client.on("whisper")
    async def on_whisper(data):
        print(f"[WHISPER from {data['from']}] {data['message']}")

Lifecycle Hooks
---------------

Connection Events
^^^^^^^^^^^^^^^^^

.. code-block:: python

    @client.on_connect
    async def on_connect(cli):
        """Called when connected and authenticated."""
        print("Connected to server!")
        
        # Common patterns:
        # 1. Request initial state
        state = await cli.rpc.call("get_state")
        print(f"Loaded state: {state}")
        
        # 2. Announce presence
        await cli.send("join", {"username": my_username})
        
        # 3. Subscribe to streams
        await cli.rpc.call("subscribe", args=data(channel="updates"))

    @client.on_disconnect
    async def on_disconnect(cli):
        """Called when disconnected."""
        print("Disconnected from server")
        
        # Cleanup
        pause_game()
        show_reconnecting_ui()

    @client.on_reconnect
    async def on_reconnect(cli):
        """Called after successful reconnection."""
        print("Reconnected to server!")
        
        # Re-sync state
        await sync_with_server()
        resume_game()

Interactive Client
------------------

Command-Line Interface Pattern
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    import asyncio
    from conduit import Client, ClientDescriptor, data

    client = Client(ClientDescriptor(
        server_host="localhost",
        server_port=8080,
        password="secret",
    ))

    # Global username
    username = "User"

    # Message handlers
    @client.on("chat")
    async def on_chat(msg):
        print(f"\r[{msg['from']}] {msg['message']}")
        print("> ", end="", flush=True)

    @client.on("notification")
    async def on_notification(msg):
        print(f"\r[!] {msg['text']}")
        print("> ", end="", flush=True)

    # Interactive loop
    async def input_loop():
        loop = asyncio.get_event_loop()
        
        while client.is_connected:
            try:
                line = await loop.run_in_executor(
                    None, 
                    lambda: input("> ")
                )
                await handle_command(line)
            except EOFError:
                break
            except Exception as e:
                print(f"Error: {e}")

    async def handle_command(line):
        parts = line.strip().split(" ", 1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""
        
        if cmd == "chat" or cmd == "say":
            await client.send("chat", {
                "username": username,
                "message": arg,
            })
        
        elif cmd == "echo":
            result = await client.rpc.call("echo", args=data(message=arg))
            print(f"Echo: {result.get('data')}")
        
        elif cmd == "add":
            nums = arg.split()
            if len(nums) >= 2:
                result = await client.rpc.call("add", args=data(
                    a=int(nums[0]),
                    b=int(nums[1])
                ))
                print(f"Result: {result.get('data')}")
        
        elif cmd == "users":
            result = await client.rpc.call("get_users")
            print(f"Online: {result.get('data')}")
        
        elif cmd == "help":
            print("Commands: chat, echo, add, users, help, quit")
        
        elif cmd in ("quit", "exit", "q"):
            await client.disconnect()
            return
        
        else:
            print(f"Unknown: {cmd}")

    async def main():
        global username
        username = input("Enter username: ").strip() or "User"
        
        print("Connecting...")
        connected = await client.connect()
        if not connected:
            print("Connection failed!")
            return
        
        print("Connected! Type 'help' for commands.")
        
        try:
            await input_loop()
        except KeyboardInterrupt:
            pass
        finally:
            await client.disconnect()
            print("Goodbye!")

    if __name__ == "__main__":
        asyncio.run(main())

Connection Pooling
------------------

For multiple connections:

.. code-block:: python

    from conduit import ClientPool

    pool = ClientPool(
        servers=[
            ("server1.example.com", 8080),
            ("server2.example.com", 8080),
        ],
        password="secret",
        pool_size=2,  # Connections per server
        strategy="round_robin",  # or "random", "least_latency"
    )

    async def main():
        await pool.connect_all()
        
        # RPC calls are load-balanced
        result = await pool.rpc("get_status")
        
        # Broadcast to all
        results = await pool.broadcast_rpc("notify", message="hi")
        
        await pool.disconnect_all()

Complete Example
----------------

Full Chat Client
^^^^^^^^^^^^^^^^

.. code-block:: python

    import asyncio
    import time
    from conduit import Client, ClientDescriptor, data

    # Configuration
    client = Client(ClientDescriptor(
        server_host="localhost",
        server_port=8080,
        password="chat_secret",
        reconnect_enabled=True,
    ))

    username = "Anonymous"
    connected_users = []

    # === Message Handlers ===

    @client.on("chat")
    async def on_chat(msg):
        sender = msg.get("from", "Unknown")
        message = msg.get("message", "")
        timestamp = msg.get("time", time.time())
        t = time.strftime("%H:%M", time.localtime(timestamp))
        print(f"\r[{t}] {sender}: {message}")
        print("> ", end="", flush=True)

    @client.on("user_joined")
    async def on_user_joined(msg):
        user = msg.get("username")
        print(f"\r[+] {user} joined the chat")
        print("> ", end="", flush=True)

    @client.on("user_left")
    async def on_user_left(msg):
        user = msg.get("username")
        print(f"\r[-] {user} left the chat")
        print("> ", end="", flush=True)

    @client.on("server_message")
    async def on_server_message(msg):
        print(f"\r[SERVER] {msg.get('text')}")
        print("> ", end="", flush=True)

    # === Lifecycle ===

    @client.on_connect
    async def on_connect(cli):
        print(f"Connected as {username}!")
        await cli.send("set_name", {"username": username})

    @client.on_disconnect
    async def on_disconnect(cli):
        print("\nDisconnected from server")

    @client.on_reconnect
    async def on_reconnect(cli):
        print("\nReconnected!")
        await cli.send("set_name", {"username": username})

    # === Input Handler ===

    async def handle_input(line):
        line = line.strip()
        if not line:
            return True
        
        if line.startswith("/"):
            # Command
            parts = line[1:].split(" ", 1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""
            
            if cmd == "quit":
                return False
            elif cmd == "users":
                result = await client.rpc.call("get_users")
                print(f"Online: {result.get('data')}")
            elif cmd == "me":
                await client.send("chat", {
                    "username": username,
                    "message": f"* {username} {arg}",
                })
            elif cmd == "help":
                print("Commands: /quit, /users, /me, /help")
            else:
                print(f"Unknown command: /{cmd}")
        else:
            # Regular chat message
            await client.send("chat", {
                "username": username,
                "message": line,
            })
        
        return True

    async def input_loop():
        loop = asyncio.get_event_loop()
        
        while client.is_connected:
            try:
                line = await loop.run_in_executor(None, lambda: input("> "))
                if not await handle_input(line):
                    break
            except EOFError:
                break

    # === Main ===

    async def main():
        global username
        
        username = input("Enter your name: ").strip() or "Anonymous"
        print(f"Connecting to chat server...")
        
        connected = await client.connect()
        if not connected:
            print("Could not connect to server!")
            return
        
        print("Type a message and press Enter. /help for commands.")
        
        try:
            await input_loop()
        except KeyboardInterrupt:
            print("\nExiting...")
        finally:
            await client.disconnect()

    if __name__ == "__main__":
        asyncio.run(main())
