# Examples

Real-world examples using netconduit.

## Chat Application

### chat_server.py

```python
import asyncio
import time
from conduit import Server, ServerDescriptor

server = Server(ServerDescriptor(
    host="0.0.0.0", port=9000, password="chat_secret"
))

users = {}

@server.on("join")
async def handle_join(client, data):
    username = data.get("username", f"User_{client.id[:4]}")
    users[client.id] = username
    await server.broadcast("system", {"message": f"{username} joined"}, exclude={client.id})
    return {"success": True, "username": username}

@server.on("message")
async def handle_message(client, data):
    username = users.get(client.id, "Anonymous")
    await server.broadcast("message", {
        "from": username, "text": data.get("text"), "time": time.time()
    }, exclude={client.id})
    return {"sent": True}

@server.on_client_disconnect
async def on_disconnect(conn):
    username = users.pop(conn.id, None)
    if username:
        await server.broadcast("system", {"message": f"{username} left"})

@server.rpc
async def list_users() -> list:
    return list(users.values())

asyncio.run(server.run())
```

### chat_client.py

```python
import asyncio
from conduit import Client, ClientDescriptor, data

client = Client(ClientDescriptor(
    server_host="127.0.0.1", server_port=9000, password="chat_secret"
))

@client.on("message")
async def on_message(msg):
    print(f"[{msg['from']}]: {msg['text']}")

@client.on("system")
async def on_system(msg):
    print(f"*** {msg['message']} ***")

async def main():
    await client.connect()
    username = input("Username: ")
    await client.send("join", {"username": username})
    
    loop = asyncio.get_event_loop()
    while client.is_connected:
        text = await loop.run_in_executor(None, input)
        if text:
            await client.send("message", {"text": text})

asyncio.run(main())
```

---

## Game Server

```python
import asyncio
import random
from conduit import Server, ServerDescriptor

server = Server(ServerDescriptor(
    host="0.0.0.0", port=9001, password="game_secret"
))

players = {}

@server.rpc
async def spawn(name: str) -> dict:
    pid = str(random.randint(1000, 9999))
    players[pid] = {"x": random.randint(0, 100), "y": random.randint(0, 100), "health": 100, "name": name}
    return {"id": pid, **players[pid]}

@server.rpc
async def move(player_id: str, dx: int, dy: int) -> dict:
    if player_id not in players:
        return {"error": "Player not found"}
    players[player_id]["x"] += dx
    players[player_id]["y"] += dy
    await server.broadcast("player_moved", {"id": player_id, **players[player_id]})
    return players[player_id]

@server.rpc
async def attack(attacker_id: str, target_id: str) -> dict:
    if target_id not in players:
        return {"error": "Target not found"}
    players[target_id]["health"] -= 10
    await server.broadcast("damage", {"target": target_id, "health": players[target_id]["health"]})
    return {"success": True}

asyncio.run(server.run())
```

---

## File Transfer

```python
import asyncio
import base64
import os
from conduit import Server, ServerDescriptor

server = Server(ServerDescriptor(
    host="0.0.0.0", port=9002, password="file_secret"
))

STORAGE = "./uploads"
os.makedirs(STORAGE, exist_ok=True)

@server.rpc
async def upload(filename: str, content_b64: str) -> dict:
    content = base64.b64decode(content_b64)
    path = os.path.join(STORAGE, filename)
    with open(path, "wb") as f:
        f.write(content)
    return {"success": True, "size": len(content)}

@server.rpc
async def download(filename: str) -> dict:
    path = os.path.join(STORAGE, filename)
    if not os.path.exists(path):
        return {"error": "File not found"}
    with open(path, "rb") as f:
        content = f.read()
    return {"filename": filename, "content_b64": base64.b64encode(content).decode()}

@server.rpc
async def list_files() -> list:
    return os.listdir(STORAGE)

asyncio.run(server.run())
```

---

## Monitoring Dashboard

```python
import asyncio
import psutil
import time
from conduit import Server, ServerDescriptor

server = Server(ServerDescriptor(
    host="0.0.0.0", port=9003, password="monitor_secret"
))

@server.rpc
async def get_system_info() -> dict:
    return {
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "timestamp": time.time(),
    }

async def broadcast_stats():
    while True:
        await asyncio.sleep(5)
        if server.connection_count > 0:
            await server.broadcast("stats", {
                "cpu": psutil.cpu_percent(),
                "memory": psutil.virtual_memory().percent,
            })

async def main():
    asyncio.create_task(broadcast_stats())
    await server.run()

asyncio.run(main())
```
