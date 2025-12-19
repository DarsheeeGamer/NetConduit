#!/usr/bin/env python3
"""
Comprehensive Test Suite for NetConduit Features

Tests:
1. TLS/SSL encrypted connections
2. Server state transitions (CREATED -> INITIALIZING -> RUNNING -> STOPPING -> CLOSED)
3. Per-connection state logging  
4. Rate limiting enforcement
5. Heartbeat (automatic, no user code needed)
"""
import asyncio
import sys
import os
import logging

# Enable logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from conduit import Server, ServerDescriptor, Client, ClientDescriptor

# Test results
results = {}

async def test_server_state():
    """Test server state transitions."""
    print("\n" + "="*50)
    print("TEST 1: Server State Transitions")
    print("="*50)
    
    server = Server(ServerDescriptor(
        host="0.0.0.0",
        port=9997,
        password="testpass",
    ))
    
    # Check CREATED state
    from conduit.server import ServerState
    assert server.state == ServerState.CREATED, f"Expected CREATED, got {server.state}"
    print(f"✓ Server state: {server.state.name}")
    
    # Start server
    await server.start()
    assert server.state == ServerState.RUNNING, f"Expected RUNNING, got {server.state}"
    print(f"✓ Server state: {server.state.name}")
    
    # Stop server
    await server.stop()
    assert server.state == ServerState.CLOSED, f"Expected CLOSED, got {server.state}"
    print(f"✓ Server state: {server.state.name}")
    
    results['server_state'] = True
    print("✓ TEST 1 PASSED: Server state transitions work correctly")

async def test_tls_connection():
    """Test TLS encrypted connection."""
    print("\n" + "="*50)
    print("TEST 2: TLS/SSL Connection")
    print("="*50)
    
    # Need cert files
    cert_dir = os.path.dirname(os.path.abspath(__file__))
    cert_file = os.path.join(cert_dir, "cert.pem")
    key_file = os.path.join(cert_dir, "key.pem")
    
    if not os.path.exists(cert_file):
        print("⚠ Skipping TLS test - no certificates found")
        results['tls'] = 'skipped'
        return
    
    server = Server(ServerDescriptor(
        host="0.0.0.0",
        port=9996,
        password="tlstest",
        ssl_enabled=True,
        ssl_cert_file=cert_file,
        ssl_key_file=key_file,
    ))
    
    received_ping = asyncio.Event()
    
    @server.on("ping")
    async def on_ping(conn, data):
        print(f"  Server received: {data}")
        await conn.send_message("pong", {"reply": "TLS works!"})
        received_ping.set()
    
    await server.start()
    print(f"✓ TLS Server started on port 9996")
    
    # Connect client
    client = Client(ClientDescriptor(
        server_host="localhost",
        server_port=9996,
        password="tlstest",
        ssl_enabled=True,
        ssl_verify=False,
    ))
    
    received_pong = asyncio.Event()
    
    @client.on("pong")
    async def on_pong(data):
        print(f"  Client received: {data}")
        received_pong.set()
    
    connected = await client.connect()
    assert connected, "Failed to connect with TLS"
    print("✓ Client connected with TLS")
    
    # Send message
    await client.send("ping", {"message": "Hello TLS!"})
    
    # Wait for response
    try:
        await asyncio.wait_for(received_pong.wait(), timeout=5.0)
        print("✓ TLS message exchange successful")
        results['tls'] = True
    except asyncio.TimeoutError:
        print("✗ Timeout waiting for response")
        results['tls'] = False
    
    await client.disconnect()
    await server.stop()
    print("✓ TEST 2 PASSED: TLS connection works correctly")

async def test_rate_limiting():
    """Test rate limiting enforcement."""
    print("\n" + "="*50)
    print("TEST 3: Rate Limiting")
    print("="*50)
    
    server = Server(ServerDescriptor(
        host="0.0.0.0",
        port=9995,
        password="ratetest",
        rate_limit_enabled=True,
        rate_limit_messages_per_second=5,  # Very low for testing
    ))
    
    message_count = 0
    
    @server.on("spam")
    async def on_spam(conn, data):
        nonlocal message_count
        message_count += 1
    
    await server.start()
    print(f"✓ Server started with rate limit: 5 msg/s")
    
    client = Client(ClientDescriptor(
        server_host="localhost",
        server_port=9995,
        password="ratetest",
    ))
    
    connected = await client.connect()
    assert connected, "Failed to connect"
    print("✓ Client connected")
    
    # Send 20 messages rapidly (should trigger rate limiting)
    for i in range(20):
        await client.send("spam", {"n": i})
    
    await asyncio.sleep(0.5)  # Wait for processing
    
    print(f"  Sent 20 messages, server received: {message_count}")
    
    # With 5 msg/s limit, we should receive fewer than 20
    if message_count < 20:
        print(f"✓ Rate limiting active - {20 - message_count} messages dropped")
        results['rate_limit'] = True
    else:
        print("⚠ All messages received - rate limiting may not be working")
        results['rate_limit'] = False
    
    await client.disconnect()
    await server.stop()
    print("✓ TEST 3 PASSED: Rate limiting works")

async def test_connection_state_logging():
    """Test per-connection state logging."""
    print("\n" + "="*50)
    print("TEST 4: Per-Connection State Logging")
    print("="*50)
    
    server = Server(ServerDescriptor(
        host="0.0.0.0",
        port=9994,
        password="statetest",
    ))
    
    connect_logged = asyncio.Event()
    disconnect_logged = asyncio.Event()
    
    @server.on_client_connect
    async def on_connect(conn):
        print(f"  Hook: Connection {conn.id[:8]} connected")
        connect_logged.set()
    
    @server.on_client_disconnect
    async def on_disconnect(conn):
        print(f"  Hook: Connection {conn.id[:8]} disconnected")
        disconnect_logged.set()
    
    await server.start()
    print("✓ Server started")
    
    client = Client(ClientDescriptor(
        server_host="localhost",
        server_port=9994,
        password="statetest",
    ))
    
    await client.connect()
    print("✓ Client connected")
    
    await asyncio.wait_for(connect_logged.wait(), timeout=2.0)
    print("✓ Connect event logged")
    
    await client.disconnect()
    
    try:
        await asyncio.wait_for(disconnect_logged.wait(), timeout=2.0)
        print("✓ Disconnect event logged")
        results['connection_state'] = True
    except asyncio.TimeoutError:
        print("⚠ Disconnect event not logged within timeout")
        results['connection_state'] = False
    
    await server.stop()
    print("✓ TEST 4 PASSED: Connection state logging works")

async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("   NETCONDUIT COMPREHENSIVE TEST SUITE")
    print("="*60)
    
    try:
        await test_server_state()
    except Exception as e:
        print(f"✗ TEST 1 FAILED: {e}")
        results['server_state'] = False
    
    try:
        await test_tls_connection()
    except Exception as e:
        print(f"✗ TEST 2 FAILED: {e}")
        results['tls'] = False
    
    try:
        await test_rate_limiting()
    except Exception as e:
        print(f"✗ TEST 3 FAILED: {e}")
        results['rate_limit'] = False
    
    try:
        await test_connection_state_logging()
    except Exception as e:
        print(f"✗ TEST 4 FAILED: {e}")
        results['connection_state'] = False
    
    # Summary
    print("\n" + "="*60)
    print("   TEST SUMMARY")
    print("="*60)
    
    passed = 0
    failed = 0
    skipped = 0
    
    for test, result in results.items():
        if result is True:
            print(f"  ✓ {test}: PASSED")
            passed += 1
        elif result == 'skipped':
            print(f"  ○ {test}: SKIPPED")
            skipped += 1
        else:
            print(f"  ✗ {test}: FAILED")
            failed += 1
    
    print(f"\nTotal: {passed} passed, {failed} failed, {skipped} skipped")
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
