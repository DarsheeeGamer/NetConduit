#!/usr/bin/env python3
"""
Multiplayer Racing Game Server

A simple racing game server using netconduit.
Tracks player positions and broadcasts updates to all clients.
"""

import asyncio
import sys
import os

# Add parent to path for conduit import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from conduit import Server, ServerDescriptor, data


# Game state
players = {}  # player_id -> {x, y, angle, speed, color, name}
player_counter = 0


def get_new_player_id():
    """Generate unique player ID."""
    global player_counter
    player_counter += 1
    return f"player_{player_counter}"


# Create server
server = Server(ServerDescriptor(
    host="0.0.0.0",
    port=9999,
    password="race2024",
    max_connections=10,
    heartbeat_interval=5,
))


@server.on_client_connect
async def on_connect(connection):
    """Handle new player connection."""
    player_id = get_new_player_id()
    connection.player_id = player_id
    
    # Assign random starting position and color
    import random
    colors = ["red", "blue", "green", "yellow", "purple", "orange", "cyan", "magenta"]
    
    players[player_id] = {
        "x": 100 + random.randint(0, 200),
        "y": 300 + random.randint(-50, 50),
        "angle": 0,
        "speed": 0,
        "color": colors[len(players) % len(colors)],
        "name": f"Racer {len(players) + 1}",
    }
    
    print(f"[+] {player_id} joined ({len(players)} players)")
    
    # Send join confirmation with player ID and all current players
    await connection.send_message("joined", {
        "player_id": player_id,
        "players": players,
        "track": {
            "width": 1200,
            "height": 600,
            "checkpoints": [
                {"x": 200, "y": 100},
                {"x": 1000, "y": 100},
                {"x": 1000, "y": 500},
                {"x": 200, "y": 500},
            ],
        }
    })
    
    # Broadcast new player to others
    for conn in server.connections:
        if hasattr(conn, 'player_id') and conn.player_id != player_id:
            await conn.send_message("player_joined", {
                "player_id": player_id,
                "data": players[player_id],
            })


@server.on_client_disconnect
async def on_disconnect(connection):
    """Handle player disconnect."""
    if hasattr(connection, 'player_id'):
        player_id = connection.player_id
        if player_id in players:
            del players[player_id]
            print(f"[-] {player_id} left ({len(players)} players)")
            
            # Broadcast player left
            for conn in server.connections:
                if hasattr(conn, 'player_id') and conn.player_id != player_id:
                    try:
                        await conn.send_message("player_left", {"player_id": player_id})
                    except:
                        pass


@server.on("update_position")
async def on_position_update(connection, data):
    """Handle player position update."""
    if not hasattr(connection, 'player_id'):
        return
    
    player_id = connection.player_id
    if player_id not in players:
        return
    
    # Update player state
    players[player_id].update({
        "x": data.get("x", players[player_id]["x"]),
        "y": data.get("y", players[player_id]["y"]),
        "angle": data.get("angle", players[player_id]["angle"]),
        "speed": data.get("speed", players[player_id]["speed"]),
    })
    
    # Broadcast to all other players
    for conn in server.connections:
        if hasattr(conn, 'player_id') and conn.player_id != player_id:
            try:
                await conn.send_message("player_update", {
                    "player_id": player_id,
                    "data": players[player_id],
                })
            except:
                pass


@server.rpc(name="get_players")
async def get_players():
    """Get all current players."""
    return players


@server.rpc(name="set_name")
async def set_name(request):
    """Set player name."""
    player_id = request.player_id
    name = request.name
    
    if player_id in players:
        players[player_id]["name"] = name
        return {"success": True}
    return {"success": False}


async def game_loop():
    """Heartbeat - sync state for late joiners only (every 1s)."""
    while True:
        await asyncio.sleep(1.0)  # Just for late joiner sync
        
        if not players:
            continue
        
        # Sync full state occasionally (for late joiners)
        for conn in server.connections:
            if hasattr(conn, 'player_id'):
                try:
                    await conn.send_message("game_state", {"players": players})
                except:
                    pass


async def main():
    """Start the racing game server."""
    print("=" * 50)
    print("  MULTIPLAYER RACING GAME SERVER")
    print("=" * 50)
    print(f"Listening on 0.0.0.0:9999")
    print(f"Password: race2024")
    print("=" * 50)
    
    # Start game loop in background
    asyncio.create_task(game_loop())
    
    # Start server
    await server.start()
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
