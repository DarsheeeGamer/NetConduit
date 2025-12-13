# System Architecture Diagram

This diagram shows the overall system architecture with all layers and components.

```mermaid
graph TB
    A[User Code]
    
    A --> B[Server Class]
    A --> C[Client Class]
    
    C --> D[RPC Class]
    
    B --> E[Response Helper]
    B --> F[Error Helper]
    C --> G[data Helper]
    
    E --> H[Data Serializer]
    F --> H
    G --> I[Pydantic Models]
    I --> H
    
    B --> J[Message Router]
    C --> J
    
    J --> K[RPC Registry]
    K --> L[RPC Dispatcher]
    L --> M[RPC Discovery]
    
    J --> N[Message Queue]
    N --> O[ACK System]
    
    J --> P[Connection Manager]
    P --> Q[Heartbeat Monitor]
    P --> R[Backpressure Handler]
    
    P --> S[Protocol Encoder]
    O --> S
    S --> T[Protocol Decoder]
    T --> U[Message Framer]
    
    H --> S
    T --> V[Data Deserializer]
    V --> I
    
    U --> W[TCP Socket Manager]
    W --> X[Auth Handler]
    
    style A fill:#e1f5ff
    style B fill:#ffe1e1
    style C fill:#ffe1e1
    style D fill:#fff4e1
    style K fill:#e1ffe1
    style P fill:#f0e1ff
    style S fill:#ffe1f5
    style W fill:#e1e1ff
```

## Layer Breakdown

### User Application Layer
- **User Code** - Your application code using Conduit

### Public API Layer
- **Server Class** - Server-side API
- **Client Class** - Client-side API
- **RPC Class** - RPC call interface
- **Response/Error/data Helpers** - Convenience wrappers

### Data Layer
- **Pydantic Models** - Type-safe data models
- **Serializer/Deserializer** - Pydantic ↔ bytes conversion

### RPC Layer
- **RPC Registry** - Stores registered RPC methods
- **RPC Dispatcher** - Routes and executes RPC calls
- **RPC Discovery** - Lists available methods

### Messaging Layer
- **Message Router** - Routes messages to handlers
- **Message Queue** - Send/receive buffers
- **ACK System** - Message acknowledgments

### Connection Layer
- **Connection Manager** - Manages connections
- **Heartbeat Monitor** - Connection health
- **Backpressure Handler** - Flow control

### Protocol Layer
- **Encoder/Decoder** - Binary protocol conversion
- **Message Framer** - Message framing and buffering

### Transport Layer
- **TCP Socket Manager** - Raw TCP sockets
- **Auth Handler** - Password authentication
