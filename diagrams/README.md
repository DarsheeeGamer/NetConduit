# Conduit Architecture Diagrams

**Complete visual documentation of the Conduit architecture**

---

## Diagrams in Order

### 1. [System Architecture](file:///home/kento/projects/unknown/diagrams/01_system_architecture.md)
Overview of all layers and components from user code down to TCP sockets.

**Shows:**
- Layer organization (API → Data → RPC → Messaging → Connection → Protocol → Transport)
- Component relationships
- Data flow through the system

---

### 2. [Connection Lifecycle](file:///home/kento/projects/unknown/diagrams/02_connection_lifecycle.md)
State machine showing all connection states and transitions.

**Shows:**
- Connection states (Disconnected → Connecting → Authenticating → Active → etc.)
- State transitions
- Error handling paths
- Auto-reconnection flow

---

### 3. [Message Flow](file:///home/kento/projects/unknown/diagrams/03_message_flow.md)
Sequence diagram of client-server communication.

**Shows:**
- Connection establishment
- Authentication handshake
- Heartbeat loop
- Simple message exchange
- RPC call flow
- Backpressure handling
- Graceful disconnect

---

### 4. [RPC Flow with Discovery](file:///home/kento/projects/unknown/diagrams/04_rpc_flow.md)
Detailed RPC system operation.

**Shows:**
- RPC discovery (`rpc.call("listall")`)
- Type-safe RPC calls with Pydantic
- Parameter validation
- Response/Error wrapping
- Correlation ID matching
- Error scenarios

---

## Quick Reference

| Diagram | Purpose | Key Concepts |
|---------|---------|--------------|
| **System Architecture** | Overall structure | Layers, components, dependencies |
| **Connection Lifecycle** | Connection states | State machine, transitions, errors |
| **Message Flow** | Communication protocol | Messages, heartbeat, backpressure |
| **RPC Flow** | RPC system details | Discovery, type safety, errors |

---

## Reading Order

**For understanding the system:**
1. Start with **System Architecture** - see the big picture
2. Then **Connection Lifecycle** - understand connection states
3. Then **Message Flow** - see how data moves
4. Finally **RPC Flow** - understand RPC specifics

**For implementation:**
1. Start with **System Architecture** - know what to build
2. Use **Connection Lifecycle** - implement state machine
3. Use **Message Flow** - implement protocol
4. Use **RPC Flow** - implement RPC system
