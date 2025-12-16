Changelog
=========

All notable changes to netconduit will be documented here.

[4.0.0] - 2024-12-16
--------------------

Added
^^^^^

- **Bidirectional File Transfer**
  
  - ``FileTransferHandler`` class for both Server and Client
  - Server can push files to clients
  - Client can upload files to server
  - Chunked transfer with progress tracking
  - SHA256 checksum verification

- **Bidirectional Streaming API**

  - ``StreamManager`` for both Server and Client
  - Server can push real-time data to clients
  - Clients can push streams to server
  - Subscriber pattern with buffering

- **Sphinx Documentation**

  - Complete user guides for all components
  - API reference with autodoc
  - ReadTheDocs integration

- **WebSocket Comparison Benchmarks**

  - Honest performance comparison
  - Connection, throughput, latency tests

[3.0.0] - 2024-12-15
--------------------

Added
^^^^^

- ``FileTransfer`` module (client-to-server only)
- ``StreamManager`` for server-side streaming
- ``ClientPool`` for connection pooling
- Time logging in example scripts

[2.0.0] - 2024-12-15
--------------------

Fixed
^^^^^

- Connection state machine invalid transitions
- RPC response routing bug
- Authentication flag not being set after auth

Added
^^^^^

- Comprehensive error handling
- Debug logging support

[0.1.0] - 2024-12-14
--------------------

Initial release with:

- Custom binary protocol (32-byte header + MessagePack)
- Password-based authentication (SHA256)
- Type-safe RPC with Pydantic validation
- Message passing with handlers
- Heartbeat monitoring
- Backpressure flow control
- Auto-reconnect for clients
