#!/usr/bin/env python3
"""
Test Server with Verbose Raw Data Logging

Run this in one terminal to start the server.
Then run test_client_debug.py in another terminal.

Usage:
    source .venv/bin/activate
    python test_server_debug.py [--ipv6]
"""

import asyncio
import logging
import sys
import hashlib
import argparse

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("SERVER")

# Add path for local import
sys.path.insert(0, '.')

from conduit.protocol import ProtocolEncoder, ProtocolDecoder, MessageType, MAGIC, HEADER_SIZE
from conduit.transport import TCPServer, TCPSocket


def log_raw_bytes(label: str, data: bytes, max_display: int = 100):
    """Log raw bytes in readable format."""
    hex_str = data[:max_display].hex()
    display = ' '.join(hex_str[i:i+2] for i in range(0, len(hex_str), 2))
    if len(data) > max_display:
        display += f" ... ({len(data)} total bytes)"
    logger.info(f"[RAW {label}] {display}")


def create_server(host: str, port: int, password: str, ipv6: bool = False):
    """Create a test server."""
    
    encoder = ProtocolEncoder()
    
    async def handle_client(socket: TCPSocket):
        """Handle a single client connection."""
        remote = socket.remote_address
        logger.info("=" * 60)
        logger.info(f"NEW CONNECTION from {remote}")
        logger.info("=" * 60)
        
        decoder = ProtocolDecoder()
        authenticated = False
        
        try:
            # Step 1: Wait for auth request
            logger.info("Waiting for AUTH_REQUEST...")
            
            raw_data = await asyncio.wait_for(socket.read(4096), timeout=30.0)
            if not raw_data:
                logger.error("No data received, client disconnected")
                return
            
            log_raw_bytes("RECEIVED", raw_data)
            
            # Decode
            decoder.feed(raw_data)
            message = decoder.decode_one()
            
            if message is None:
                logger.error("Failed to decode message")
                return
            
            logger.info(f"[DECODED] Type: {message.message_type.name}")
            logger.info(f"[DECODED] Payload: {message.payload}")
            
            if message.message_type != MessageType.AUTH_REQUEST:
                logger.error(f"Expected AUTH_REQUEST, got {message.message_type.name}")
                return
            
            # Verify password
            received_hash = message.payload.get("password_hash", "")
            expected_hash = hashlib.sha256(password.encode()).hexdigest()
            
            logger.info(f"[AUTH] Received hash: {received_hash[:16]}...")
            logger.info(f"[AUTH] Expected hash: {expected_hash[:16]}...")
            
            if received_hash != expected_hash:
                logger.error("[AUTH] ❌ Password mismatch!")
                fail_msg = encoder.encode_auth_failure("Invalid password")
                log_raw_bytes("SENDING AUTH_FAILURE", fail_msg)
                await socket.write(fail_msg)
                return
            
            # Send auth success
            logger.info("[AUTH] ✓ Password verified! Sending success...")
            success_msg = encoder.encode_auth_success(
                session_token="session_" + hashlib.md5(str(remote).encode()).hexdigest()[:16],
                server_info={"name": "TestServer", "version": "1.0.0", "protocol": "IPv6" if ipv6 else "IPv4"}
            )
            log_raw_bytes("SENDING AUTH_SUCCESS", success_msg)
            await socket.write(success_msg)
            authenticated = True
            
            logger.info("[AUTH] ✓ Client authenticated successfully!")
            logger.info("-" * 60)
            
            # Step 2: Handle messages
            while True:
                logger.info("Waiting for messages... (30s timeout)")
                
                raw_data = await asyncio.wait_for(socket.read(4096), timeout=30.0)
                if not raw_data:
                    logger.info("Client disconnected (no data)")
                    break
                
                log_raw_bytes("RECEIVED", raw_data)
                
                decoder.feed(raw_data)
                
                for msg in decoder.decode_all():
                    logger.info(f"[DECODED] Type: {msg.message_type.name}")
                    logger.info(f"[DECODED] Correlation ID: {msg.correlation_id}")
                    logger.info(f"[DECODED] Payload: {msg.payload}")
                    
                    # Handle different message types
                    if msg.message_type == MessageType.HEARTBEAT_PING:
                        logger.info("[HEARTBEAT] Received PING, sending PONG")
                        pong = encoder.encode_heartbeat_pong()
                        log_raw_bytes("SENDING PONG", pong)
                        await socket.write(pong)
                    
                    elif msg.message_type == MessageType.RPC_REQUEST:
                        method = msg.payload.get("method", "")
                        params = msg.payload.get("params", {})
                        logger.info(f"[RPC] Method: {method}, Params: {params}")
                        
                        # Handle RPC methods
                        if method == "listall":
                            result = {
                                "methods": [
                                    {"name": "add", "description": "Add two numbers"},
                                    {"name": "echo", "description": "Echo back message"},
                                    {"name": "multiply", "description": "Multiply two numbers"},
                                ],
                                "count": 3
                            }
                        elif method == "add":
                            a = params.get("a", 0)
                            b = params.get("b", 0)
                            result = a + b
                            logger.info(f"[RPC] add({a}, {b}) = {result}")
                        elif method == "multiply":
                            x = params.get("x", 0)
                            y = params.get("y", 0)
                            result = x * y
                            logger.info(f"[RPC] multiply({x}, {y}) = {result}")
                        elif method == "echo":
                            result = params.get("message", "")
                            logger.info(f"[RPC] echo('{result}')")
                        else:
                            logger.warning(f"[RPC] Unknown method: {method}")
                            error_resp = encoder.encode_rpc_error(f"Unknown method: {method}", msg.correlation_id)
                            log_raw_bytes("SENDING RPC_ERROR", error_resp)
                            await socket.write(error_resp)
                            continue
                        
                        logger.info(f"[RPC] Result: {result}")
                        response = encoder.encode_rpc_response(result, msg.correlation_id)
                        log_raw_bytes("SENDING RPC_RESPONSE", response)
                        await socket.write(response)
                    
                    elif msg.message_type == MessageType.MESSAGE:
                        msg_type = msg.payload.get("type", "")
                        data = msg.payload.get("data", {})
                        logger.info(f"[MESSAGE] Type: '{msg_type}', Data: {data}")
                        
                        # Echo back with response
                        response = encoder.encode_message(
                            f"{msg_type}_response",
                            {"received": True, "original": data, "server": "TestServer"}
                        )
                        log_raw_bytes("SENDING MESSAGE RESPONSE", response)
                        await socket.write(response)
                    
                    else:
                        logger.warning(f"[UNHANDLED] Message type: {msg.message_type.name}")
                    
        except asyncio.TimeoutError:
            logger.warning("Timeout waiting for data")
        except Exception as e:
            logger.error(f"Error handling client: {e}", exc_info=True)
        finally:
            logger.info(f"Connection closed: {remote}")
            await socket.close()
    
    return TCPServer(host=host, port=port, handler=handle_client, ipv6=ipv6)


async def main():
    parser = argparse.ArgumentParser(description="Test Server with Raw Data Logging")
    parser.add_argument("--ipv6", action="store_true", help="Use IPv6 (::1)")
    parser.add_argument("--port", type=int, default=9999, help="Port number")
    parser.add_argument("--password", default="test_secret_123", help="Password")
    args = parser.parse_args()
    
    if args.ipv6:
        host = "::1"
    else:
        host = "127.0.0.1"
    
    server = create_server(host, args.port, args.password, args.ipv6)
    
    logger.info("=" * 60)
    logger.info(f"  TEST SERVER STARTING")
    logger.info(f"  Address: {host}:{args.port}")
    logger.info(f"  Protocol: {'IPv6' if args.ipv6 else 'IPv4'}")
    logger.info(f"  Password: {args.password}")
    logger.info("=" * 60)
    
    await server.start()
    
    logger.info("Server is running. Press Ctrl+C to stop.")
    logger.info(f"Run: python test_client_debug.py {'--ipv6' if args.ipv6 else ''}")
    logger.info("")
    
    try:
        await server.wait_until_stopped()
    except asyncio.CancelledError:
        pass
    except KeyboardInterrupt:
        pass
    finally:
        await server.stop()
        logger.info("Server stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown requested...")
