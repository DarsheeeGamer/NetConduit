# server.py - Interactive Echo Server with Debug Logging
import asyncio
import time
import logging
from conduit import Server, ServerDescriptor

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("SERVER")

server = Server(ServerDescriptor(
    host="0.0.0.0",
    port=9000,
    password="echo_secret",
    name="EchoServer",
))

# Store connected clients
clients = {}


# === RPC Methods ===

@server.rpc
async def echo(message: str) -> str:
    """Echo back the received message."""
    logger.info(f"[RPC] echo called with: {message}")
    return message

@server.rpc
async def reverse(text: str) -> str:
    """Reverse text."""
    logger.info(f"[RPC] reverse called with: {text}")
    return text[::-1]

@server.rpc
async def calculate(a: float, b: float, op: str) -> float:
    """Calculate: add, sub, mul, div."""
    logger.info(f"[RPC] calculate called: {a} {op} {b}")
    ops = {
        "add": a + b,
        "sub": a - b,
        "mul": a * b,
        "div": a / b if b != 0 else 0,
    }
    result = ops.get(op, 0)
    logger.info(f"[RPC] calculate result: {result}")
    return result

@server.rpc
async def get_time() -> dict:
    """Get server time."""
    logger.info("[RPC] get_time called")
    return {"timestamp": time.time(), "formatted": time.strftime("%Y-%m-%d %H:%M:%S")}


# === Message Handlers ===

@server.on("chat")
async def handle_chat(client, data):
    """Handle chat messages and broadcast to all."""
    sender = data.get("username", "Anonymous")
    message = data.get("message", "")
    
    logger.info(f"[MSG] Chat from {sender}: {message}")
    
    # Broadcast to all other clients
    count = await server.broadcast("chat", {
        "from": sender,
        "message": message,
        "time": time.time(),
    }, exclude={client.id})
    
    logger.info(f"[MSG] Broadcast to {count} clients")
    return {"sent": True, "recipients": count}

@server.on("command")
async def handle_command(client, data):
    """Handle custom commands."""
    cmd = data.get("cmd", "")
    logger.info(f"[MSG] Command: {cmd}")
    
    if cmd == "list_clients":
        return {"clients": list(clients.keys()), "count": len(clients)}
    elif cmd == "server_info":
        return {"name": server.config.name, "clients": server.connection_count}
    else:
        return {"error": f"Unknown command: {cmd}"}


# === Lifecycle ===

@server.on_startup
async def on_startup(srv):
    logger.info("=" * 60)
    logger.info(f"Server starting on {srv.address}")
    logger.info("Available RPC: echo, reverse, calculate, get_time, listall")
    logger.info("Available messages: chat, command")
    logger.info("=" * 60)

@server.on_client_connect
async def on_client_connect(conn):
    clients[conn.id] = {"connected_at": time.time()}
    logger.info(f"[+] Client connected: {conn.id[:8]}... (Total: {len(clients)})")
    
    # Notify other clients
    await server.broadcast("user_joined", {"id": conn.id[:8]}, exclude={conn.id})

@server.on_client_disconnect
async def on_client_disconnect(conn):
    if conn.id in clients:
        del clients[conn.id]
    logger.info(f"[-] Client disconnected: {conn.id[:8]}... (Total: {len(clients)})")
    
    # Notify other clients
    await server.broadcast("user_left", {"id": conn.id[:8]})


# === Background task ===

async def send_server_updates():
    """Send periodic server status to all clients."""
    while True:
        await asyncio.sleep(30)
        if server.is_running and server.connection_count > 0:
            logger.debug(f"Broadcasting server status to {server.connection_count} clients")
            await server.broadcast("server_status", {
                "clients": server.connection_count,
                "uptime": time.time(),
            })


async def main():
    asyncio.create_task(send_server_updates())
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
