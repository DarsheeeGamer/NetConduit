# server.py - Echo Server with Time Logging
import asyncio
import time
import logging
from datetime import datetime
from conduit import Server, ServerDescriptor

# Configure time-based logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d | %(levelname)-8s | %(name)-20s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("SERVER")

def timestamp():
    """Get current timestamp string."""
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]

server = Server(ServerDescriptor(
    host="0.0.0.0",
    port=9000,
    password="echo_secret",
    name="EchoServer",
))

users = {}


# === RPC Methods ===

@server.rpc
async def echo(message: str) -> str:
    logger.info(f"[{timestamp()}] RPC echo: {message}")
    return message

@server.rpc
async def reverse(text: str) -> str:
    logger.info(f"[{timestamp()}] RPC reverse: {text}")
    return text[::-1]

@server.rpc
async def calculate(a: float, b: float, op: str) -> float:
    logger.info(f"[{timestamp()}] RPC calculate: {a} {op} {b}")
    ops = {"add": a + b, "sub": a - b, "mul": a * b, "div": a / b if b else 0}
    result = ops.get(op, 0)
    logger.info(f"[{timestamp()}] Result: {result}")
    return result

@server.rpc
async def get_time() -> dict:
    now = datetime.now()
    logger.info(f"[{timestamp()}] RPC get_time")
    return {
        "timestamp": time.time(),
        "formatted": now.strftime("%Y-%m-%d %H:%M:%S"),
        "iso": now.isoformat(),
    }


# === Message Handlers ===

@server.on("chat")
async def handle_chat(client, data):
    sender = data.get("username", "Anonymous")
    message = data.get("message", "")
    logger.info(f"[{timestamp()}] CHAT from {sender}: {message}")
    
    count = await server.broadcast("chat", {
        "from": sender,
        "message": message,
        "time": time.time(),
        "timestamp": timestamp(),
    }, exclude={client.id})
    
    logger.info(f"[{timestamp()}] Broadcast to {count} clients")
    return {"sent": True, "recipients": count}

@server.on("ping")
async def handle_ping(client, data):
    send_time = data.get("client_time", 0)
    receive_time = time.time()
    logger.info(f"[{timestamp()}] PING received, latency: {(receive_time - send_time)*1000:.2f}ms")
    return {"pong": True, "server_time": receive_time}


# === Lifecycle ===

@server.on_startup
async def on_startup(srv):
    logger.info("=" * 60)
    logger.info(f"[{timestamp()}] Server starting on {srv.address}")
    logger.info(f"[{timestamp()}] Available RPC: echo, reverse, calculate, get_time")
    logger.info("=" * 60)

@server.on_client_connect
async def on_client_connect(conn):
    users[conn.id] = {"connected_at": time.time()}
    logger.info(f"[{timestamp()}] [+] Client {conn.id[:8]} connected (Total: {len(users)})")
    await server.broadcast("user_joined", {
        "id": conn.id[:8],
        "time": timestamp(),
    }, exclude={conn.id})

@server.on_client_disconnect
async def on_client_disconnect(conn):
    connect_time = users.get(conn.id, {}).get("connected_at", time.time())
    duration = time.time() - connect_time
    users.pop(conn.id, None)
    logger.info(f"[{timestamp()}] [-] Client {conn.id[:8]} disconnected after {duration:.1f}s (Total: {len(users)})")
    await server.broadcast("user_left", {"id": conn.id[:8], "time": timestamp()})


# === Background Tasks ===

async def send_server_updates():
    while True:
        await asyncio.sleep(30)
        if server.is_running and server.connection_count > 0:
            logger.debug(f"[{timestamp()}] Broadcasting status to {server.connection_count} clients")
            await server.broadcast("server_status", {
                "clients": server.connection_count,
                "uptime": time.time(),
                "time": timestamp(),
            })


async def main():
    asyncio.create_task(send_server_updates())
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
