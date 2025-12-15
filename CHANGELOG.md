# Changelog

All notable changes to netconduit will be documented in this file.

## [3.0.0] - 2024-12-15

### Added
- **File Transfer** (`conduit.transfer`)
  - `FileTransfer` - chunked upload/download with SHA256 checksum
  - `TransferProgress` - progress tracking with speed/ETA

- **Streaming API** (`conduit.streaming`)
  - `Stream` - continuous data streams with subscribers
  - `StreamManager` - server-side stream management
  - `ClientStreamConsumer` - client-side stream consumption

- **Client Pool** (`conduit.pool`)
  - `ClientPool` - multiple connections with load balancing
  - Strategies: round_robin, random, least_latency

- **Time Logging** in ser.py and cli.py with latency measurement

---

## [2.0.0] - 2024-12-15

### Fixed
- Connection state machine invalid transitions
- RPC response routing bug
- Authentication flag not being set

---

## [0.1.0] - 2024-12-14

### Added
- Initial release: binary protocol, RPC, heartbeat, backpressure
