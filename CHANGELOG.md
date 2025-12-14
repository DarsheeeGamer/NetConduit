# Changelog

All notable changes to netconduit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
  - Password-based authentication (PBKDF2-SHA256)
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

- **Configuration**
  - ServerDescriptor and ClientDescriptor
  - Comprehensive validation
  - Sensible defaults

### Developer Experience

- 85+ unit tests
- Debug scripts for raw data logging
- IPv4 and IPv6 support
- Comprehensive documentation

## [Unreleased]

### Planned

- File transfer support
- Streaming API
- TLS/SSL option
- Connection pooling improvements
- Performance benchmarks
