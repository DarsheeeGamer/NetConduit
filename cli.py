# client.py - Interactive Client with Bidirectional Communication
import asyncio
import sys
from conduit import Client, ClientDescriptor, data

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
    """Receive chat messages from other clients."""
    sender = msg.get("from", "Unknown")
    message = msg.get("message", "")
    print(f"\r[CHAT] {sender}: {message}\n> ", end="", flush=True)

@client.on("chat_response")
async def on_chat_response(msg):
    """Acknowledgement that chat was sent (ignore silently)."""
    pass  # Already printed "Message sent!" in handle_command

@client.on("user_joined")
async def on_user_joined(msg):
    """Someone joined."""
    print(f"\r[+] User {msg.get('id')} joined\n> ", end="", flush=True)

@client.on("user_left")
async def on_user_left(msg):
    """Someone left."""
    print(f"\r[-] User {msg.get('id')} left\n> ", end="", flush=True)

@client.on("server_status")
async def on_server_status(msg):
    """Server status update."""
    print(f"\r[SERVER] {msg.get('clients')} clients online\n> ", end="", flush=True)


# === Lifecycle ===

@client.on_connect
async def on_connect(cli):
    print("=" * 50)
    print("Connected to server!")
    print("=" * 50)

@client.on_disconnect
async def on_disconnect(cli):
    print("\nDisconnected from server")

@client.on_reconnect  
async def on_reconnect(cli):
    print("\nReconnected!")


# === Command Handler ===

async def handle_command(line: str) -> bool:
    """Process user input. Returns False to quit."""
    line = line.strip()
    if not line:
        return True
    
    parts = line.split(" ", 1)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""
    
    try:
        if cmd == "echo":
            if not arg:
                print("Usage: echo <text>")
            else:
                result = await client.rpc.call("echo", args=data(message=arg))
                print(f"Echo: {result}")
            
        elif cmd == "reverse":
            if not arg:
                print("Usage: reverse <text>")
            else:
                result = await client.rpc.call("reverse", args=data(text=arg))
                print(f"Reversed: {result}")
            
        elif cmd == "calc":
            # Format: calc 10 + 20
            nums = arg.replace("+", " add ").replace("-", " sub ").replace("*", " mul ").replace("/", " div ")
            p = nums.split()
            if len(p) >= 3:
                result = await client.rpc.call("calculate", args=data(
                    a=float(p[0]), b=float(p[2]), op=p[1]
                ))
                print(f"Result: {result}")
            else:
                print("Usage: calc 10 + 20")
                
        elif cmd == "time":
            result = await client.rpc.call("get_time")
            if isinstance(result, dict) and "formatted" in result:
                print(f"Server time: {result['formatted']}")
            else:
                print(f"Server time: {result}")
            
        elif cmd == "chat":
            if not arg:
                print("Usage: chat <message>")
            else:
                await client.send("chat", {"username": "User", "message": arg})
                print("Message sent!")
            
        elif cmd == "info":
            result = await client.rpc.call("listall")
            if isinstance(result, list):
                print(f"Available RPC methods: {[m['name'] for m in result]}")
            else:
                print(f"RPC methods: {result}")
            
        elif cmd == "help":
            print("""
Available Commands:
  echo <text>      - Echo text back from server
  reverse <text>   - Reverse text on server
  calc <expr>      - Calculate (e.g., calc 10 + 5)
  time             - Get server time
  chat <message>   - Send chat message to other clients
  info             - List available RPC methods
  quit             - Disconnect and exit
""")
            
        elif cmd in ("quit", "exit", "q"):
            return False
            
        else:
            print(f"Unknown command: {cmd}. Type 'help' for commands.")
            
    except Exception as e:
        print(f"Error: {e}")
    
    return True


async def input_loop():
    """Handle user input in async way."""
    loop = asyncio.get_event_loop()
    
    while client.is_connected:
        try:
            # Use thread executor for blocking input
            line = await loop.run_in_executor(None, lambda: input("> "))
            
            if not await handle_command(line):
                break
                
        except EOFError:
            break
        except Exception as e:
            if client.is_connected:
                print(f"Input error: {e}")
            break


async def main():
    connected = await client.connect()
    if not connected:
        print("Connection failed!")
        return
    
    print("\nType 'help' for available commands.\n")
    
    try:
        await input_loop()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
