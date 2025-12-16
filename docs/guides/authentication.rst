Authentication Guide
====================

Password-based authentication with SHA256.

How It Works
------------

.. code-block:: text

    Client                              Server
      │                                   │
      │──── TCP Connect ────────────────►│
      │                                   │
      │──── Auth Request ───────────────►│
      │     {password_hash: SHA256(...)} │
      │                                   │
      │◄─── Auth Response ───────────────│
      │     {success: true/false}        │
      │                                   │
      │     (If success, proceed)        │
      │                                   │

Server Configuration
--------------------

.. code-block:: python

    from conduit import Server, ServerDescriptor

    server = Server(ServerDescriptor(
        host="0.0.0.0",
        port=8080,
        password="my_secure_password",  # Required
        auth_timeout=30.0,  # Max seconds to authenticate
    ))

Client Configuration
--------------------

.. code-block:: python

    from conduit import Client, ClientDescriptor

    client = Client(ClientDescriptor(
        server_host="localhost",
        server_port=8080,
        password="my_secure_password",  # Must match server
    ))

Authentication Flow
-------------------

1. Client connects via TCP
2. Connection enters ``AUTHENTICATING`` state
3. Client sends password hash (SHA256)
4. Server verifies hash
5. If valid: ``CONNECTED`` → ``ACTIVE``
6. If invalid: Connection closed with error

Handling Auth Failure
---------------------

.. code-block:: python

    async def main():
        try:
            connected = await client.connect()
            if not connected:
                print("Connection failed (possibly wrong password)")
                return
            
            print("Connected and authenticated!")
            
        except AuthenticationError as e:
            print(f"Authentication failed: {e}")

Security Notes
--------------

**Current Security Model:**

- Password is hashed with SHA256 before transmission
- One password per server (all clients share it)
- Suitable for internal/trusted networks

**For Production:**

- Use strong, unique passwords
- Run behind firewall
- Consider additional transport security

**Not Included (by design):**

- TLS/SSL (use stunnel or nginx if needed)
- User accounts (implement in your app layer)
- Certificate authentication

Custom Authentication
---------------------

You can implement custom auth by extending the handlers:

.. code-block:: python

    # Store authenticated users
    authenticated_users = {}

    @server.on("custom_auth")
    async def handle_auth(client, data):
        username = data.get("username")
        password = data.get("password")
        
        # Your custom verification
        if verify_user(username, password):
            authenticated_users[client.id] = username
            return {"success": True, "user": username}
        else:
            return {"success": False, "error": "Invalid credentials"}

    @server.on("protected_action")
    async def protected(client, data):
        if client.id not in authenticated_users:
            return {"error": "Not authenticated"}
        
        # Handle the action...

Timeouts
--------

Authentication must complete within the timeout:

.. code-block:: python

    ServerDescriptor(
        auth_timeout=30.0,  # 30 seconds to authenticate
    )

If a client doesn't authenticate in time, the connection is closed.
