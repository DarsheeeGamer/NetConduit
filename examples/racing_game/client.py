#!/usr/bin/env python3
"""
Multiplayer Racing Game Client (Pygame)

A graphical racing game client using Pygame.
Connect to a netconduit server and race with other players!
"""

import asyncio
import sys
import os
import math
import threading

# Add parent to path for conduit import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    import pygame
except ImportError:
    print("Pygame not installed! Install with: pip install pygame")
    sys.exit(1)

from conduit import Client, ClientDescriptor


# Game constants
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 600
FPS = 60

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (100, 100, 100)
DARK_GRAY = (50, 50, 50)
GREEN = (0, 200, 0)
GRASS_GREEN = (34, 139, 34)

COLOR_MAP = {
    "red": (255, 60, 60),
    "blue": (60, 60, 255),
    "green": (60, 255, 60),
    "yellow": (255, 255, 60),
    "purple": (180, 60, 255),
    "orange": (255, 165, 0),
    "cyan": (0, 255, 255),
    "magenta": (255, 0, 255),
}


class Car:
    """Represents a racing car."""
    
    def __init__(self, x, y, color="red", name="Player"):
        self.x = x
        self.y = y
        self.angle = 0  # Degrees
        self.speed = 0
        self.color = color
        self.name = name
        self.max_speed = 8
        self.acceleration = 0.3
        self.deceleration = 0.15
        self.turn_speed = 4
        self.width = 40
        self.height = 20
    
    def update(self, keys_pressed):
        """Update car based on input."""
        # Acceleration
        if keys_pressed[pygame.K_UP] or keys_pressed[pygame.K_w]:
            self.speed = min(self.speed + self.acceleration, self.max_speed)
        elif keys_pressed[pygame.K_DOWN] or keys_pressed[pygame.K_s]:
            self.speed = max(self.speed - self.acceleration, -self.max_speed / 2)
        else:
            # Natural deceleration
            if self.speed > 0:
                self.speed = max(0, self.speed - self.deceleration)
            elif self.speed < 0:
                self.speed = min(0, self.speed + self.deceleration)
        
        # Turning (only when moving)
        if abs(self.speed) > 0.1:
            turn_factor = self.speed / self.max_speed
            if keys_pressed[pygame.K_LEFT] or keys_pressed[pygame.K_a]:
                self.angle += self.turn_speed * turn_factor
            if keys_pressed[pygame.K_RIGHT] or keys_pressed[pygame.K_d]:
                self.angle -= self.turn_speed * turn_factor
        
        # Move
        rad = math.radians(self.angle)
        self.x += math.cos(rad) * self.speed
        self.y -= math.sin(rad) * self.speed
        
        # Keep in bounds
        self.x = max(20, min(SCREEN_WIDTH - 20, self.x))
        self.y = max(20, min(SCREEN_HEIGHT - 20, self.y))
    
    def draw(self, screen, is_local=False):
        """Draw the car."""
        color = COLOR_MAP.get(self.color, (255, 0, 0))
        
        # Create car surface
        car_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        
        # Draw car body
        pygame.draw.rect(car_surface, color, (0, 2, self.width - 5, self.height - 4))
        pygame.draw.rect(car_surface, (color[0]//2, color[1]//2, color[2]//2), 
                         (0, 2, self.width - 5, self.height - 4), 2)
        
        # Front (pointed)
        pygame.draw.polygon(car_surface, color, [
            (self.width - 5, 2),
            (self.width, self.height // 2),
            (self.width - 5, self.height - 2)
        ])
        
        # Rotate
        rotated = pygame.transform.rotate(car_surface, self.angle)
        rect = rotated.get_rect(center=(self.x, self.y))
        screen.blit(rotated, rect)
        
        # Draw name above car
        font = pygame.font.Font(None, 20)
        name_surface = font.render(self.name, True, WHITE)
        name_rect = name_surface.get_rect(center=(self.x, self.y - 25))
        screen.blit(name_surface, name_rect)
        
        # Local player indicator
        if is_local:
            pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y - 35)), 3)
    
    def to_dict(self):
        """Export state to dict."""
        return {
            "x": self.x,
            "y": self.y,
            "angle": self.angle,
            "speed": self.speed,
        }


class RacingGame:
    """Main racing game class."""
    
    def __init__(self, server_host, server_port, password):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("NetConduit Racing")
        self.clock = pygame.time.Clock()
        
        self.server_host = server_host
        self.server_port = server_port
        self.password = password
        
        self.client = None
        self.player_id = None
        self.local_car = None
        self.other_cars = {}  # player_id -> Car
        
        self.connected = False
        self.running = True
        
        self.track = None
        
        # Fonts
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
    
    async def connect(self):
        """Connect to game server."""
        self.client = Client(ClientDescriptor(
            server_host=self.server_host,
            server_port=self.server_port,
            password=self.password,
            reconnect_enabled=True,
        ))
        
        # Set up message handlers
        @self.client.on("joined")
        async def on_joined(data):
            self.player_id = data["player_id"]
            self.track = data.get("track")
            
            # Create local car
            player_data = data["players"].get(self.player_id, {})
            self.local_car = Car(
                player_data.get("x", 100),
                player_data.get("y", 300),
                player_data.get("color", "red"),
                player_data.get("name", "Player"),
            )
            
            # Create other cars
            for pid, pdata in data["players"].items():
                if pid != self.player_id:
                    self.other_cars[pid] = Car(
                        pdata.get("x", 0),
                        pdata.get("y", 0),
                        pdata.get("color", "gray"),
                        pdata.get("name", "Other"),
                    )
            
            self.connected = True
            print(f"Joined as {self.player_id}")
        
        @self.client.on("player_joined")
        async def on_player_joined(data):
            pid = data["player_id"]
            pdata = data["data"]
            self.other_cars[pid] = Car(
                pdata.get("x", 0),
                pdata.get("y", 0),
                pdata.get("color", "gray"),
                pdata.get("name", "Other"),
            )
        
        @self.client.on("player_left")
        async def on_player_left(data):
            pid = data["player_id"]
            if pid in self.other_cars:
                del self.other_cars[pid]
        
        @self.client.on("player_update")
        async def on_player_update(data):
            pid = data["player_id"]
            pdata = data["data"]
            if pid in self.other_cars:
                car = self.other_cars[pid]
                car.x = pdata.get("x", car.x)
                car.y = pdata.get("y", car.y)
                car.angle = pdata.get("angle", car.angle)
                car.speed = pdata.get("speed", car.speed)
        
        @self.client.on("game_state")
        async def on_game_state(data):
            players = data.get("players", {})
            for pid, pdata in players.items():
                if pid == self.player_id:
                    continue
                if pid not in self.other_cars:
                    self.other_cars[pid] = Car(
                        pdata.get("x", 0),
                        pdata.get("y", 0),
                        pdata.get("color", "gray"),
                        pdata.get("name", "Other"),
                    )
                else:
                    car = self.other_cars[pid]
                    car.x = pdata.get("x", car.x)
                    car.y = pdata.get("y", car.y)
                    car.angle = pdata.get("angle", car.angle)
        
        await self.client.connect()
    
    def draw_track(self):
        """Draw the race track."""
        # Background (grass)
        self.screen.fill(GRASS_GREEN)
        
        # Track (gray oval)
        pygame.draw.ellipse(self.screen, GRAY, (50, 50, SCREEN_WIDTH - 100, SCREEN_HEIGHT - 100))
        pygame.draw.ellipse(self.screen, GRASS_GREEN, (150, 150, SCREEN_WIDTH - 300, SCREEN_HEIGHT - 300))
        
        # Track border
        pygame.draw.ellipse(self.screen, WHITE, (50, 50, SCREEN_WIDTH - 100, SCREEN_HEIGHT - 100), 3)
        pygame.draw.ellipse(self.screen, WHITE, (150, 150, SCREEN_WIDTH - 300, SCREEN_HEIGHT - 300), 3)
        
        # Start/finish line
        pygame.draw.rect(self.screen, WHITE, (SCREEN_WIDTH - 150, SCREEN_HEIGHT // 2 - 50, 10, 100))
        
        # Checkpoints
        if self.track and "checkpoints" in self.track:
            for i, cp in enumerate(self.track["checkpoints"]):
                pygame.draw.circle(self.screen, (255, 255, 0), (cp["x"], cp["y"]), 10)
                text = self.small_font.render(str(i + 1), True, BLACK)
                self.screen.blit(text, (cp["x"] - 5, cp["y"] - 8))
    
    def draw_ui(self):
        """Draw game UI."""
        # Connection status
        status = "CONNECTED" if self.connected else "CONNECTING..."
        color = GREEN if self.connected else (255, 255, 0)
        text = self.small_font.render(status, True, color)
        self.screen.blit(text, (10, 10))
        
        # Player count
        count = len(self.other_cars) + (1 if self.local_car else 0)
        text = self.small_font.render(f"Players: {count}", True, WHITE)
        self.screen.blit(text, (10, 35))
        
        # Speed indicator
        if self.local_car:
            speed_text = f"Speed: {abs(self.local_car.speed):.1f}"
            text = self.small_font.render(speed_text, True, WHITE)
            self.screen.blit(text, (SCREEN_WIDTH - 100, 10))
        
        # Controls hint
        hint = "WASD/Arrows to drive | ESC to quit"
        text = self.small_font.render(hint, True, (200, 200, 200))
        self.screen.blit(text, (SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT - 25))
    
    async def send_position(self):
        """Send local car position to server."""
        if self.connected and self.local_car:
            try:
                await self.client.send("update_position", self.local_car.to_dict())
            except:
                pass
    
    async def game_loop(self):
        """Main game loop."""
        send_timer = 0
        
        while self.running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
            
            # Get keys
            keys = pygame.key.get_pressed()
            
            # Update local car
            if self.local_car:
                self.local_car.update(keys)
            
            # Send position every frame for smooth updates
            await self.send_position()
            
            # Draw
            self.draw_track()
            
            # Draw other cars
            for pid, car in self.other_cars.items():
                car.draw(self.screen, is_local=False)
            
            # Draw local car (on top)
            if self.local_car:
                self.local_car.draw(self.screen, is_local=True)
            
            # Draw UI
            self.draw_ui()
            
            pygame.display.flip()
            self.clock.tick(FPS)
            
            # Small delay to allow asyncio
            await asyncio.sleep(0.001)
        
        pygame.quit()
    
    async def run(self):
        """Run the game."""
        await self.connect()
        await self.game_loop()
        
        if self.client:
            await self.client.disconnect()


async def main():
    """Main entry point."""
    # Parse command line args
    host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 9999
    password = sys.argv[3] if len(sys.argv) > 3 else "race2024"
    
    print(f"Connecting to {host}:{port}...")
    
    game = RacingGame(host, port, password)
    await game.run()


if __name__ == "__main__":
    asyncio.run(main())
