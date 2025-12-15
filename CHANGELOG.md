# Changelog

All notable changes to netconduit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2024-12-15

### Fixed
- **Connection State Machine**: Fixed invalid state transitions (`DISCONNECTED -> ACTIVE`)
  - Added `CONNECTING -> CONNECTED` transition for server-side connections
  - Added `CONNECTING/AUTHENTICATING -> CLOSING` for proper cleanup
  - Added `FAILED -> CONNECTING` for reconnection support

- **RPC Response Routing**: Fixed RPC responses being intercepted by Connection layer
  - Responses now properly pass through to Client when Connection didn't create the request
  - Removed duplicate future creation between Client and Connection

- **Authentication Flag**: Fixed `is_authenticated` returning False after successful auth
  - Added `mark_authenticated()` method to Connection
  - Both server and client now properly mark connections as authenticated

- **Chat Response Handler**: Added handler for `chat_response` messages to suppress warnings

### Added
- Comprehensive documentation
  - Quick start guide
  - Server and client guides
  - Real-world examples (chat, game server, file transfer)
  - Protocol specification

- Debug logging support in server
- Interactive client example with commands

### Changed
- Development status changed from Alpha to Beta
- Improved error messages and logging

---

## [0.1.0] - 2024-12-14

### Added
- **Core Protocol**
  - Custom binary protocol with 32-byte header
  - MessagePack payload serialization
  - Optional zlib compression
  - Protocol version handling (v1.0)

- **Transport Layer**
  - Async TCP socket wrapper (IPv4 & IPv6)
  - Connection state machine
  - TCPServer for accepting connections

- **Authentication**
  - Password-based authentication (SHA256)
  - Challenge-response protocol
  - Session token management

- **RPC System**
  - RPC registry with decorator support
  - Type-safe dispatching with Pydantic validation
  - Built-in `listall` discovery method
  - Client-side RPC class with timeout handling

- **Messaging**
  - Message class with tracking
  - Async message queues with backpressure
  - Message router with priority support

- **Connection Management**
  - Connection class integrating all components
  - Connection pool for server-side management
  - Heartbeat monitoring with latency tracking
  - Flow control with high/low watermarks

- **High-Level API**
  - Server class with Flask-like decorators
  - Client class with reconnection support
  - Response and Error wrapper helpers
  - Pydantic data models for all types
