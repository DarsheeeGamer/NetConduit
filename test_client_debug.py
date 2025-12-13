#!/usr/bin/env python3
"""
Test Client with Verbose Raw Data Logging

Run this in one terminal after starting test_server_debug.py in another.

Usage:
    source .venv/bin/activate
    python test_client_debug.py [--ipv6]
"""

import asyncio
import logging
import sys
import hashlib
import time
import argparse

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("CLIENT")

# Add path for local import
sys.path.insert(0, '.')

from conduit.protocol import ProtocolEncoder, ProtocolDecoder, MessageType, MAGIC, HEADER_SIZE
from conduit.transport import TCPSocket


def log_raw_bytes(label: str, data: bytes, max_display: int = 100):
    """Log raw bytes in readable format."""
    hex_str = data[:max_display].hex()
    display = ' '.join(hex_str[i:i+2] for i in range(0, len(hex_str), 2))
    if len(data) > max_display:
        display += f" ... ({len(data)} total bytes)"
    logger.info(f"[RAW {label}] {display}")


async def run_tests(host: str, port: int, password: str, ipv6: bool = False):
    """Run all client tests."""
    
    encoder = ProtocolEncoder()
    decoder = ProtocolDecoder()
    
    logger.info("=" * 60)
    logger.info(f"  TEST CLIENT STARTING")
    logger.info(f"  Connecting to: {host}:{port}")
    logger.info(f"  Protocol: {'IPv6' if ipv6 else 'IPv4'}")
    logger.info("=" * 60)
    
    socket = None
    
    try:
        # Step 1: Connect
        logger.info("Connecting to server...")
        socket = await TCPSocket.connect(
            host=host,
            port=port,
            timeout=5.0,
            use_ipv6=ipv6,
        )
        logger.info(f"✓ Connected! Local: {socket.local_address}, Remote: {socket.remote_address}")
        logger.info("-" * 60)
        
        # Step 2: Send AUTH_REQUEST
        logger.info("Step 1: Sending AUTH_REQUEST...")
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        logger.info(f"[AUTH] Password hash: {password_hash[:16]}...")
        
        auth_msg = encoder.encode_auth_request(
            password_hash=password_hash,
            client_info={"name": "TestClient", "version": "1.0.0"}
        )
        log_raw_bytes("SENDING AUTH_REQUEST", auth_msg)
        await socket.write(auth_msg)
        
        # Step 3: Wait for AUTH response
        logger.info("Waiting for auth response...")
        raw_response = await asyncio.wait_for(socket.read(4096), timeout=5.0)
        log_raw_bytes("RECEIVED", raw_response)
        
        decoder.feed(raw_response)
        auth_response = decoder.decode_one()
        
        if auth_response is None:
            logger.error("Failed to decode auth response")
            return False
        
        logger.info(f"[DECODED] Type: {auth_response.message_type.name}")
        logger.info(f"[DECODED] Payload: {auth_response.payload}")
        
        if auth_response.message_type != MessageType.AUTH_SUCCESS:
            logger.error(f"❌ Authentication failed! Got: {auth_response.message_type.name}")
            return False
        
        session_token = auth_response.payload.get("session_token")
        server_info = auth_response.payload.get("server_info", {})
        logger.info(f"[AUTH] ✓ Authenticated! Token: {session_token}")
        logger.info(f"[AUTH] Server info: {server_info}")
        logger.info("-" * 60)
        
        # Step 4: Test RPC - listall
        logger.info("Step 2: Testing RPC 'listall'...")
        rpc_msg, corr_id = encoder.encode_rpc_request(method="listall", params={})
        logger.info(f"[RPC] Correlation ID: {corr_id}")
        log_raw_bytes("SENDING RPC_REQUEST", rpc_msg)
        await socket.write(rpc_msg)
        
        raw_response = await asyncio.wait_for(socket.read(4096), timeout=5.0)
        log_raw_bytes("RECEIVED", raw_response)
        
        decoder.feed(raw_response)
        rpc_response = decoder.decode_one()
        
        if rpc_response:
            logger.info(f"[DECODED] Type: {rpc_response.message_type.name}")
            logger.info(f"[DECODED] Correlation ID: {rpc_response.correlation_id}")
            logger.info(f"[DECODED] Payload: {rpc_response.payload}")
        logger.info("-" * 60)
        
        # Step 5: Test RPC - add
        logger.info("Step 3: Testing RPC 'add(a=10, b=20)'...")
        rpc_msg, corr_id = encoder.encode_rpc_request(method="add", params={"a": 10, "b": 20})
        logger.info(f"[RPC] Correlation ID: {corr_id}")
        log_raw_bytes("SENDING RPC_REQUEST", rpc_msg)
        await socket.write(rpc_msg)
        
        raw_response = await asyncio.wait_for(socket.read(4096), timeout=5.0)
        log_raw_bytes("RECEIVED", raw_response)
        
        decoder.feed(raw_response)
        rpc_response = decoder.decode_one()
        
        if rpc_response:
            logger.info(f"[DECODED] Type: {rpc_response.message_type.name}")
            logger.info(f"[DECODED] Payload: {rpc_response.payload}")
            
            result = rpc_response.payload.get("result")
            expected = 30
            if result == expected:
                logger.info(f"[RESULT] ✓ add(10, 20) = {result} (CORRECT)")
            else:
                logger.error(f"[RESULT] ❌ add(10, 20) = {result} (expected {expected})")
        logger.info("-" * 60)
        
        # Step 6: Test RPC - multiply
        logger.info("Step 4: Testing RPC 'multiply(x=3.5, y=2.0)'...")
        rpc_msg, corr_id = encoder.encode_rpc_request(method="multiply", params={"x": 3.5, "y": 2.0})
        log_raw_bytes("SENDING RPC_REQUEST", rpc_msg)
        await socket.write(rpc_msg)
        
        raw_response = await asyncio.wait_for(socket.read(4096), timeout=5.0)
        log_raw_bytes("RECEIVED", raw_response)
        
        decoder.feed(raw_response)
        rpc_response = decoder.decode_one()
        
        if rpc_response:
            result = rpc_response.payload.get("result")
            logger.info(f"[RESULT] multiply(3.5, 2.0) = {result}")
        logger.info("-" * 60)
        
        # Step 7: Test regular message
        logger.info("Step 5: Testing MESSAGE 'hello'...")
        msg = encoder.encode_message("hello", {"name": "World", "timestamp": int(time.time())})
        log_raw_bytes("SENDING MESSAGE", msg)
        await socket.write(msg)
        
        raw_response = await asyncio.wait_for(socket.read(4096), timeout=5.0)
        log_raw_bytes("RECEIVED", raw_response)
        
        decoder.feed(raw_response)
        msg_response = decoder.decode_one()
        
        if msg_response:
            logger.info(f"[DECODED] Type: {msg_response.message_type.name}")
            logger.info(f"[DECODED] Payload: {msg_response.payload}")
        logger.info("-" * 60)
        
        # Step 8: Test heartbeat
        logger.info("Step 6: Testing HEARTBEAT...")
        ping = encoder.encode_heartbeat_ping()
        log_raw_bytes("SENDING PING", ping)
        await socket.write(ping)
        
        raw_response = await asyncio.wait_for(socket.read(4096), timeout=5.0)
        log_raw_bytes("RECEIVED PONG", raw_response)
        
        decoder.feed(raw_response)
        pong = decoder.decode_one()
        
        if pong:
            logger.info(f"[DECODED] Type: {pong.message_type.name}")
            if pong.message_type == MessageType.HEARTBEAT_PONG:
                logger.info("[HEARTBEAT] ✓ Received PONG")
        logger.info("-" * 60)
        
        logger.info("=" * 60)
        logger.info("  ✓ ALL TESTS COMPLETED SUCCESSFULLY!")
        logger.info("=" * 60)
        
        return True
        
    except asyncio.TimeoutError:
        logger.error("❌ Timeout waiting for response!")
        return False
    except ConnectionRefusedError:
        logger.error("❌ Connection refused! Is the server running?")
        return False
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        return False
    finally:
        if socket:
            await socket.close()
            logger.info("Connection closed.")


async def main():
    parser = argparse.ArgumentParser(description="Test Client with Raw Data Logging")
    parser.add_argument("--ipv6", action="store_true", help="Use IPv6 (::1)")
    parser.add_argument("--port", type=int, default=9999, help="Port number")
    parser.add_argument("--password", default="test_secret_123", help="Password")
    args = parser.parse_args()
    
    if args.ipv6:
        host = "::1"
    else:
        host = "127.0.0.1"
    
    success = await run_tests(host, args.port, args.password, args.ipv6)
    
    if success:
        print("\n✓ All tests passed!")
    else:
        print("\n✗ Tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nClient interrupted...")
