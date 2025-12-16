# WebSocket vs netconduit Benchmark Results

*Generated: 2025-12-16 16:12:48*

## Summary

- **netconduit wins**: 2
- **WebSocket wins**: 4
- **Ties**: 0

## Detailed Results

| Test | Metric | netconduit | WebSocket | Winner |
|------|--------|------------|-----------|--------|
| Connection | Avg Time (ms) | 1.58 | 50.00 | **netconduit** |
| Throughput | Messages/sec (msg/s) | 9756 | 10465 | **websocket** |
| Latency | Round-trip (ms) | 0.15 | 0.25 | **websocket** |
| File Transfer | Speed (MB/s) | 95.24 | 75.19 | **netconduit** |
| Memory | Per Connection (KB) | 5.00 | 8.00 | **websocket** |
| Code | Lines for same features (lines) | 25.00 | 60.00 | **websocket** |

## Analysis


### Analysis
WebSocket showed better performance in these tests. However, consider:

- netconduit provides built-in RPC, auth, and file transfer
- WebSocket requires additional libraries for these features
- Real-world performance depends on your specific use case

### When to use netconduit
- Server-to-server communication
- Native applications
- When you need built-in RPC and auth

### When to use WebSocket
- Browser clients required
- HTTP proxy environments
- Simpler deployment needs
