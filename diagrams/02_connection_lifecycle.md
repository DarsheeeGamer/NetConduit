# Connection Lifecycle Diagram

This diagram shows the complete lifecycle of a connection from initial state through various states to disconnection.

```mermaid
graph TB
    Start([Start]) --> Disconnected[Disconnected<br/>No connection]
    
    Disconnected -->|"Client calls<br/>connect()"| Connecting[Connecting<br/>TCP handshake]
    
    Connecting -->|"TCP established"| Authenticating[Authenticating<br/>Sending password]
    Connecting -->|"TCP error/timeout"| ConnFailed[Connection Failed]
    
    Authenticating -->|"Password OK"| Connected[Connected<br/>Waiting for heartbeat]
    Authenticating -->|"Wrong password"| AuthFailed[Auth Failed]
    
    Connected -->|"First heartbeat OK"| Active[Active<br/>Fully operational]
    
    Active -->|"Normal operations"| Active
    Note1[Send/Receive messages<br/>RPC calls<br/>File transfers<br/>Heartbeat exchanges]
    Note1 -.-> Active
    
    Active -->|"Buffer full"| Paused[Paused<br/>Backpressure active]
    Paused -->|"Buffer available"| Active
    Note2[Receiver buffer full<br/>Temporarily stop sending]
    Note2 -.-> Paused
    
    Active -->|"close() called"| Closing[Closing<br/>Graceful shutdown]
    Active -->|"Heartbeat timeout"| HBDead[Heartbeat Dead]
    Active -->|"Network failure"| NetErr[Network Error]
    
    HBDead --> Disconnected
    NetErr --> Disconnected
    
    Closing --> Closed[Closed<br/>Resources freed]
    Closed --> Disconnected
    
    ConnFailed --> Disconnected
    AuthFailed --> Disconnected
    
    Disconnected -->|"Auto-reconnect<br/>(if enabled)"| Connecting
    Note3[Exponential backoff<br/>between attempts]
    Note3 -.-> Connecting
    
    Disconnected --> End([End])
    
    style Active fill:#90EE90
    style Disconnected fill:#FFE4B5
    style Paused fill:#FFB6C1
    style HBDead fill:#FFA07A
    style NetErr fill:#FFA07A
    style AuthFailed fill:#FF6B6B
    style ConnFailed fill:#FF6B6B
```

## State Descriptions

| State | Description |
|-------|-------------|
| **Disconnected** | No connection, idle state |
| **Connecting** | TCP connection in progress |
| **Authenticating** | Sending password, waiting for auth response |
| **Connected** | Authenticated, waiting for first heartbeat |
| **Active** | Fully operational, can send/receive |
| **Paused** | Flow control active, temporary pause |
| **Closing** | Graceful shutdown in progress |
| **Closed** | Connection closed, resources cleaned up |
| **HeartbeatDead** | Heartbeat timeout detected |
| **NetworkError** | Network failure detected |
| **ConnectionFailed** | Failed to establish TCP connection |
| **AuthFailed** | Authentication failed |

