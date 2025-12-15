# client.py - Interactive Client with Time Logging
import asyncio
import time
import logging
from datetime import datetime
from conduit import Client, ClientDescriptor, data

# Configure time-based logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("CLIENT")

def timestamp():
    """Get current timestamp string."""
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]

def log(msg: str):
    """Log with timestamp."""
    print(f"[{timestamp()}] {msg}")

client = Client(ClientDescriptor(
    server_host="127.0.0.1",
    server_port=9000,
    password="echo_secret",
    name="InteractiveClient",
    reconnect_enabled=True,
))


# === Handle Messages FROM Server ===

@client.on("chat")
async def on_chat(msg):
    sender = msg.get("from", "Unknown")
    message = msg.get("message", "")
    server_time = msg.get("timestamp", "")
    print(f"\r[{timestamp()}] [CHAT] {sender}: {message} (server: {server_time})\n> ", end="", flush=True)

@client.on("chat_response")
async def on_chat_response(msg):
    pass

@client.on("user_joined")
async def on_user_joined(msg):
    print(f"\r[{timestamp()}] [+] User {msg.get('id')} joined\n> ", end="", flush=True)

@client.on("user_left")
async def on_user_left(msg):
    print(f"\r[{timestamp()}] [-] User {msg.get('id')} left\n> ", end="", flush=True)

@client.on("server_status")
async def on_server_status(msg):
    print(f"\r[{timestamp()}] [SERVER] {msg.get('clients')} clients online\n> ", end="", flush=True)


# === Lifecycle ===

@client.on_connect
async def on_connect(cli):
    log("=" * 50)
    log("Connected to server!")
    log("=" * 50)

@client.on_disconnect
async def on_disconnect(cli):
    log("Disconnected from server")

@client.on_reconnect  
async def on_reconnect(cli):
    log("Reconnected!")


# === Command Handler ===

async def handle_command(line: str) -> bool:
    line = line.strip()
    if not line:
        return True
    
    parts = line.split(" ", 1)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""
    
    start_time = time.time()
    
    try:
        if cmd == "echo":
            if not arg:
                log("Usage: echo <text>")
            else:
                result = await client.rpc.call("echo", args=data(message=arg))
                elapsed = (time.time() - start_time) * 1000
                log(f"Echo: {result} ({elapsed:.2f}ms)")
            
        elif cmd == "reverse":
            if not arg:
                log("Usage: reverse <text>")
            else:
                result = await client.rpc.call("reverse", args=data(text=arg))
                elapsed = (time.time() - start_time) * 1000
                log(f"Reversed: {result} ({elapsed:.2f}ms)")
            
        elif cmd == "calc":
            nums = arg.replace("+", " add ").replace("-", " sub ").replace("*", " mul ").replace("/", " div ")
            p = nums.split()
            if len(p) >= 3:
                result = await client.rpc.call("calculate", args=data(a=float(p[0]), b=float(p[2]), op=p[1]))
                elapsed = (time.time() - start_time) * 1000
                log(f"Result: {result} ({elapsed:.2f}ms)")
            else:
                log("Usage: calc 10 + 20")
                
        elif cmd == "time":
            result = await client.rpc.call("get_time")
            elapsed = (time.time() - start_time) * 1000
            if isinstance(result, dict) and "formatted" in result:
                log(f"Server time: {result['formatted']} ({elapsed:.2f}ms)")
            else:
                log(f"Server time: {result} ({elapsed:.2f}ms)")
            
        elif cmd == "ping":
            send_time = time.time()
            await client.send("ping", {"client_time": send_time})
            elapsed = (time.time() - start_time) * 1000
            log(f"Ping sent ({elapsed:.2f}ms)")
            
        elif cmd == "chat":
            if not arg:
                log("Usage: chat <message>")
            else:
                await client.send("chat", {"username": "User", "message": arg})
                elapsed = (time.time() - start_time) * 1000
                log(f"Message sent ({elapsed:.2f}ms)")
            
        elif cmd == "info":
            result = await client.rpc.call("listall")
            elapsed = (time.time() - start_time) * 1000
            if isinstance(result, list):
                log(f"RPC methods: {[m['name'] for m in result]} ({elapsed:.2f}ms)")
            else:
                log(f"RPC methods: {result} ({elapsed:.2f}ms)")
            
        elif cmd == "help":
            log("""
Commands:
  echo <text>      - Echo text back from server
  reverse <text>   - Reverse text on server
  calc <expr>      - Calculate (e.g., calc 10 + 5)
  time             - Get server time
  ping             - Measure latency
  chat <message>   - Send chat message
  info             - List RPC methods
  quit             - Exit
""")
            
        elif cmd in ("quit", "exit", "q"):
            return False
            
        else:
            log(f"Unknown command: {cmd}. Type 'help' for commands.")
            
    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        log(f"Error: {e} ({elapsed:.2f}ms)")
    
    return True


async def input_loop():
    loop = asyncio.get_event_loop()
    
    while client.is_connected:
        try:
            line = await loop.run_in_executor(None, lambda: input("> "))
            if not await handle_command(line):
                break
        except EOFError:
            break
        except Exception as e:
            if client.is_connected:
                log(f"Input error: {e}")
            break


async def main():
    log("Connecting to server...")
    connected = await client.connect()
    if not connected:
        log("Connection failed!")
        return
    
    log("Type 'help' for available commands.")
    
    try:
        await input_loop()
    except KeyboardInterrupt:
        log("Shutting down...")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
