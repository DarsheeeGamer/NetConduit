Messages Guide
==============

Free-form message passing between server and clients.

Sending Messages
----------------

**From Server to Client:**

.. code-block:: python

    # Send to specific client
    await connection.send_message("notification", {
        "type": "alert",
        "text": "Your session expires in 5 minutes"
    })

    # Broadcast to all clients
    await server.broadcast("announcement", {
        "text": "Server maintenance at midnight"
    })

    # Broadcast to some clients
    await server.broadcast("team_update", {
        "team": "red",
        "score": 42
    }, include={player1_id, player2_id})

    # Broadcast to all except some
    await server.broadcast("chat", {
        "from": sender_name,
        "message": text
    }, exclude={sender_id})

**From Client to Server:**

.. code-block:: python

    await client.send("chat", {
        "username": "John",
        "message": "Hello everyone!"
    })

    await client.send("game_action", {
        "action": "move",
        "x": 100,
        "y": 200
    })

Handling Messages
-----------------

**Server-side:**

.. code-block:: python

    @server.on("chat")
    async def handle_chat(client, data):
        """
        Args:
            client: Connection object
            data: Message payload (dict)
        
        Returns:
            Optional dict to send back to sender
        """
        username = data.get("username", "Anonymous")
        message = data.get("message", "")
        
        # Log the message
        print(f"[{username}]: {message}")
        
        # Broadcast to others
        await server.broadcast("chat", {
            "from": username,
            "message": message,
            "timestamp": time.time()
        }, exclude={client.id})
        
        # Return acknowledgment to sender
        return {"sent": True, "timestamp": time.time()}

**Client-side:**

.. code-block:: python

    @client.on("chat")
    async def on_chat(data):
        """
        Args:
            data: Message payload (dict)
        """
        sender = data.get("from", "Unknown")
        message = data.get("message", "")
        print(f"{sender}: {message}")

    @client.on("notification")
    async def on_notification(data):
        print(f"[!] {data.get('text')}")

Message Types
-------------

You can define any message type you want:

.. code-block:: python

    # Chat application
    @server.on("chat")
    @server.on("whisper")
    @server.on("join_room")
    @server.on("leave_room")

    # Game application
    @server.on("player_move")
    @server.on("attack")
    @server.on("use_item")
    @server.on("game_state")

    # Monitoring
    @server.on("metric")
    @server.on("log")
    @server.on("alert")

Handler Priority
----------------

Register handlers with priority:

.. code-block:: python

    @server.on("event", priority=10)  # Higher = runs first
    async def high_priority_handler(client, data):
        # Runs before low priority
        pass

    @server.on("event", priority=1)
    async def low_priority_handler(client, data):
        # Runs after high priority
        pass

Pattern: Request/Response
-------------------------

Implement request/response on top of messages:

.. code-block:: python

    # Server
    @server.on("request")
    async def handle_request(client, data):
        request_id = data.get("request_id")
        
        # Process request...
        result = await process(data.get("payload"))
        
        # Send response with same ID
        await client.send_message("response", {
            "request_id": request_id,
            "result": result
        })

    # Client
    pending_requests = {}

    @client.on("response")
    async def on_response(data):
        request_id = data.get("request_id")
        if request_id in pending_requests:
            pending_requests[request_id].set_result(data.get("result"))

    async def make_request(payload):
        request_id = str(uuid.uuid4())
        future = asyncio.Future()
        pending_requests[request_id] = future
        
        await client.send("request", {
            "request_id": request_id,
            "payload": payload
        })
        
        return await asyncio.wait_for(future, timeout=10.0)
