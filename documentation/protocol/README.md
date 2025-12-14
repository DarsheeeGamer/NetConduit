# Protocol Documentation

Technical specification for the netconduit binary protocol.

## Table of Contents

1. [Overview](#overview)
2. [Header Format](#header-format)
3. [Message Types](#message-types)
4. [Message Flags](#message-flags)
5. [Payload Format](#payload-format)
6. [Authentication Flow](#authentication-flow)
7. [Heartbeat Protocol](#heartbeat-protocol)
8. [Backpressure Flow Control](#backpressure-flow-control)

---

## Overview

netconduit uses a custom binary protocol optimized for low-latency bidirectional communication.

### Key Features

- **Binary Header**: 32-byte fixed header for fast parsing
- **MessagePack Payload**: Efficient binary serialization
- **Correlation IDs**: Match requests with responses
- **Compression**: Optional zlib compression
- **Version Support**: Protocol versioning for compatibility

---

## Header Format

Every message starts with a 32-byte header:

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|     Magic (4 bytes)  = "CNDT"                                 |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|    Version    |     Type      |           Flags               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       Payload Length (4 bytes)                |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                               |
|                    Correlation ID (8 bytes)                   |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                               |
|                      Timestamp (8 bytes)                      |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       Reserved (4 bytes)                      |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

### Field Description

| Field | Offset | Size | Description |
|-------|--------|------|-------------|
| Magic | 0 | 4 | Magic bytes `"CNDT"` (0x434E4454) |
| Version | 4 | 1 | Protocol version (currently 1) |
| Type | 5 | 1 | Message type (see below) |
| Flags | 6 | 2 | Message flags (see below) |
| Length | 8 | 4 | Payload length in bytes |
| Correlation ID | 12 | 8 | Request/response matching ID |
| Timestamp | 20 | 8 | Unix timestamp (milliseconds) |
| Reserved | 28 | 4 | Reserved for future use |

### Header Constants

```python
MAGIC = b"CNDT"           # Magic bytes
PROTOCOL_VERSION = 1       # Current protocol version
HEADER_SIZE = 32          # Header size in bytes
```

---

## Message Types

| Value | Name | Description |
|-------|------|-------------|
| 0x01 | `MESSAGE` | Regular message |
| 0x02 | `RPC_REQUEST` | RPC call request |
| 0x03 | `RPC_RESPONSE` | RPC call response |
| 0x04 | `RPC_ERROR` | RPC error response |
| 0x05 | `HEARTBEAT_PING` | Keep-alive ping |
| 0x06 | `HEARTBEAT_PONG` | Keep-alive pong |
| 0x07 | `PAUSE` | Flow control pause |
| 0x08 | `RESUME` | Flow control resume |
| 0x10 | `AUTH_REQUEST` | Authentication request |
| 0x11 | `AUTH_SUCCESS` | Authentication success |
| 0x12 | `AUTH_FAILURE` | Authentication failure |
| 0x13 | `AUTH_CHALLENGE` | Auth challenge (optional) |
| 0x14 | `AUTH_RESPONSE` | Auth challenge response |
| 0x20 | `DISCONNECT` | Graceful disconnect |
| 0xFF | `ERROR` | Protocol error |

---

## Message Flags

Flags are a 16-bit field with the following bits:

| Bit | Name | Description |
|-----|------|-------------|
| 0 | `COMPRESSED` | Payload is zlib compressed |
| 1 | `ENCRYPTED` | Payload is encrypted (reserved) |
| 2 | `PRIORITY_HIGH` | High priority message |
| 3 | `PRIORITY_LOW` | Low priority message |
| 4 | `REQUIRES_ACK` | Requires acknowledgment |
| 5-15 | Reserved | Reserved for future use |

### Flag Constants

```python
FLAG_COMPRESSED = 0x0001
FLAG_ENCRYPTED = 0x0002
FLAG_PRIORITY_HIGH = 0x0004
FLAG_PRIORITY_LOW = 0x0008
FLAG_REQUIRES_ACK = 0x0010
```

---

## Payload Format

Payloads are serialized using MessagePack.

### Regular Message (MESSAGE)

```python
{
    "type": str,     # Message type string
    "data": dict,    # Message payload
}
```

Example:
```python
{
    "type": "chat_message",
    "data": {
        "from": "user123",
        "message": "Hello!",
        "timestamp": 1702500000
    }
}
```

### RPC Request (RPC_REQUEST)

```python
{
    "method": str,   # Method name
    "params": dict,  # Method parameters
}
```

Example:
```python
{
    "method": "add",
    "params": {"a": 10, "b": 20}
}
```

### RPC Response (RPC_RESPONSE)

```python
{
    "success": True,
    "result": any,   # Return value
}
```

Example:
```python
{
    "success": True,
    "result": 30
}
```

### RPC Error (RPC_ERROR)

```python
{
    "success": False,
    "error": str,    # Error message
    "code": int,     # Error code (optional)
    "details": dict, # Additional details (optional)
}
```

Example:
```python
{
    "success": False,
    "error": "Method not found: unknown_method",
    "code": 4000
}
```

### Auth Request (AUTH_REQUEST)

```python
{
    "password_hash": str,  # SHA-256 hash of password
    "client_info": {
        "name": str,       # Client name
        "version": str,    # Client version
    }
}
```

### Auth Success (AUTH_SUCCESS)

```python
{
    "session_token": str,  # Session token for reconnection
    "server_info": {
        "name": str,       # Server name
        "version": str,    # Server version
    }
}
```

### Auth Failure (AUTH_FAILURE)

```python
{
    "reason": str,         # Failure reason
    "retry_allowed": bool, # Whether retry is allowed
}
```

---

## Authentication Flow

```
Client                                 Server
  |                                      |
  |-------- TCP Connect ---------------->|
  |                                      |
  |-------- AUTH_REQUEST --------------->|
  |         {password_hash, client_info} |
  |                                      |
  |         Verify password              |
  |                                      |
  |<------- AUTH_SUCCESS ----------------|
  |         {session_token, server_info} |
  |                                      |
  |         (Start normal communication) |
  |                                      |
```

### Password Hashing

Passwords are hashed client-side before transmission:

```python
import hashlib

password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
```

---

## Heartbeat Protocol

Heartbeats maintain connection health and detect dead connections.

### Flow

```
Client                                 Server
  |                                      |
  | <------ HEARTBEAT_PING ------------- |
  |                                      |
  | ------- HEARTBEAT_PONG ----------> |
  |                                      |
  |       (repeat at interval)           |
```

### Configuration

- **Interval**: How often pings are sent (default: 30s)
- **Timeout**: Maximum time without pong before disconnect (default: 90s)

---

## Backpressure Flow Control

Flow control prevents buffer overflow when sender is faster than receiver.

### Watermarks

- **High Watermark**: Buffer fill ratio to trigger pause (default: 0.8)
- **Low Watermark**: Buffer fill ratio to trigger resume (default: 0.5)

### Flow

```
Sender                                 Receiver
  |                                      |
  |------- MESSAGE ---------------------->|
  |------- MESSAGE ---------------------->|
  |------- MESSAGE ---------------------->| Buffer filling
  |                                      |
  |<------ PAUSE -------------------------| High watermark reached
  |                                      |
  |       (sender stops sending)         |
  |                                      |
  |<------ RESUME ------------------------| Low watermark reached
  |                                      |
  |------- MESSAGE ---------------------->| Resume sending
  |                                      |
```

---

## Wire Format Example

Example of a complete message in hex:

```
Header (32 bytes):
43 4E 44 54    # Magic: "CNDT"
01             # Version: 1
02             # Type: RPC_REQUEST
00 00          # Flags: none
00 00 00 1A    # Length: 26 bytes
00 00 00 00 00 00 00 01  # Correlation ID: 1
00 00 01 9B 18 DA A2 B4  # Timestamp
00 00 00 00    # Reserved

Payload (26 bytes - MessagePack encoded):
82             # fixmap with 2 entries
A6 6D 65 74 68 6F 64  # "method"
A3 61 64 64    # "add"
A6 70 61 72 61 6D 73  # "params"
82             # fixmap with 2 entries
A1 61          # "a"
0A             # 10
A1 62          # "b"
14             # 20
```

---

## Compression

When compression is enabled (FLAG_COMPRESSED set):

1. Payload is compressed with zlib (level 6)
2. Compressed data replaces original payload
3. Length field reflects compressed size
4. Small payloads (<100 bytes) may not compress

### Compression Check

```python
import zlib

if len(payload) > 100:
    compressed = zlib.compress(payload, level=6)
    if len(compressed) < len(payload):
        # Use compressed
        flags |= FLAG_COMPRESSED
        payload = compressed
```
