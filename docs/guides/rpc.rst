RPC Guide
=========

Remote Procedure Calls with type safety.

Defining RPC Methods
--------------------

.. code-block:: python

    from conduit import Server, ServerDescriptor

    server = Server(ServerDescriptor(password="secret"))

    # Simple method
    @server.rpc
    async def echo(message: str) -> str:
        return message

    # Multiple arguments
    @server.rpc
    async def add(a: int, b: int) -> int:
        return a + b

    # Optional arguments
    @server.rpc
    async def greet(name: str, greeting: str = "Hello") -> str:
        return f"{greeting}, {name}!"

    # Complex return type
    @server.rpc
    async def get_user(user_id: int) -> dict:
        return {
            "id": user_id,
            "name": "John",
            "active": True
        }

Pydantic Models
---------------

Use Pydantic for complex validation:

.. code-block:: python

    from pydantic import BaseModel, Field
    from typing import Optional, List

    class CreateUserRequest(BaseModel):
        username: str = Field(min_length=3, max_length=20)
        email: str
        age: Optional[int] = None

    class UserResponse(BaseModel):
        id: int
        username: str
        created_at: str

    @server.rpc
    async def create_user(request: CreateUserRequest) -> UserResponse:
        # Pydantic validates the request automatically
        user = await database.create_user(
            username=request.username,
            email=request.email,
            age=request.age
        )
        return UserResponse(
            id=user.id,
            username=user.username,
            created_at=user.created_at.isoformat()
        )

Calling RPC Methods
-------------------

.. code-block:: python

    from conduit import Client, ClientDescriptor, data

    client = Client(ClientDescriptor(
        server_host="localhost",
        server_port=8080,
        password="secret"
    ))

    # Call with named arguments
    result = await client.rpc.call("add", args=data(a=10, b=20))
    # {'success': True, 'data': 30}

    # Call with Pydantic model
    result = await client.rpc.call("create_user", args=data(
        username="john_doe",
        email="john@example.com",
        age=25
    ))
    # {'success': True, 'data': {'id': 1, 'username': 'john_doe', ...}}

Error Handling
--------------

.. code-block:: python

    # Server-side error
    @server.rpc
    async def divide(a: float, b: float) -> float:
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b

    # Client-side handling
    result = await client.rpc.call("divide", args=data(a=10, b=0))
    if not result.get("success"):
        print(f"Error: {result.get('error')}")  # "Cannot divide by zero"

Timeout
-------

.. code-block:: python

    # Set timeout for slow methods
    try:
        result = await client.rpc.call("slow_operation", 
                                       args=data(param=1),
                                       timeout=5.0)
    except TimeoutError:
        print("Method timed out")

Method Discovery
----------------

List all available RPC methods:

.. code-block:: python

    # Built-in listall method
    result = await client.rpc.call("listall")
    
    for method in result.get("data", []):
        print(f"{method['name']}")
        print(f"  Description: {method.get('description', 'N/A')}")
        print(f"  Parameters: {method.get('parameters', [])}")

Response Format
---------------

All RPC calls return a standardized response:

**Success:**

.. code-block:: json

    {
        "success": true,
        "data": <return_value>,
        "correlation_id": "..."
    }

**Error:**

.. code-block:: json

    {
        "success": false,
        "error": "Error message",
        "code": "ERROR_CODE",
        "correlation_id": "..."
    }
