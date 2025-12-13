# Message Flow Diagram

This diagram shows the complete message flow between client and server for various operations.

```mermaid
graph TB
    subgraph Phase1["Phase 1: Connection Establishment"]
        P1_1[Client: connect]
        P1_2[Client Transport:<br/>TCP SYN]
        P1_3[Server Transport:<br/>TCP SYN-ACK]
        P1_4[Client Transport:<br/>TCP ACK]
        P1_5[TCP Connection<br/>Established ✓]
        
        P1_1 --> P1_2 --> P1_3 --> P1_4 --> P1_5
    end
    
    subgraph Phase2["Phase 2: Authentication"]
        P2_1[Client Transport:<br/>AUTH_REQUEST<br/>password hash]
        P2_2[Server:<br/>Validate password]
        P2_3{Password<br/>Valid?}
        P2_4[Server Transport:<br/>AUTH_SUCCESS<br/>session token]
        P2_5[Connection<br/>Authenticated ✓]
        
        P2_1 --> P2_2 --> P2_3 -->|Yes| P2_4 --> P2_5
    end
    
    subgraph Phase3["Phase 3: Heartbeat Loop (Continuous)"]
        P3_1[Every 30 seconds]
        P3_2[Client Transport:<br/>HEARTBEAT_PING]
        P3_3[Server Transport:<br/>HEARTBEAT_PONG]
        
        P3_1 --> P3_2 --> P3_3 --> P3_1
    end
    
    subgraph Phase4["Phase 4: Simple Message"]
        P4_1[Client:<br/>send'hello', 'Hi!']
        P4_2[Client Transport:<br/>MESSAGE<br/>type=hello]
        P4_3[Server Transport:<br/>Receive MESSAGE]
        P4_4[Server:<br/>Route to handler]
        P4_5[Server:<br/>Execute handler]
        P4_6[Server Transport:<br/>MESSAGE response]
        P4_7[Client:<br/>Deliver to handler]
        
        P4_1 --> P4_2 --> P4_3 --> P4_4 --> P4_5 --> P4_6 --> P4_7
    end
    
    subgraph Phase5["Phase 5: RPC Call"]
        P5_1[Client:<br/>rpc.call'calculate']
        P5_2[Client Transport:<br/>RPC_REQUEST<br/>corr_id=123]
        P5_3[Server:<br/>Dispatch to<br/>RPC handler]
        P5_4[Server:<br/>Validate with<br/>Pydantic]
        P5_5[Server:<br/>Execute function]
        P5_6[Server:<br/>Wrap with<br/>Response]
        P5_7[Server Transport:<br/>RPC_RESPONSE<br/>corr_id=123]
        P5_8[Client:<br/>Parse with<br/>Pydantic]
        P5_9[Client:<br/>Return typed<br/>object]
        
        P5_1 --> P5_2 --> P5_3 --> P5_4 --> P5_5 --> P5_6 --> P5_7 --> P5_8 --> P5_9
    end
    
    subgraph Phase6["Phase 6: Backpressure"]
        P6_1[Client:<br/>send large_data]
        P6_2{Server buffer<br/>full?}
        P6_3[Server Transport:<br/>PAUSE signal]
        P6_4[Client stops<br/>sending]
        P6_5[Server buffer<br/>has space]
        P6_6[Server Transport:<br/>RESUME signal]
        P6_7[Client resumes<br/>sending]
        
        P6_1 --> P6_2 -->|Yes| P6_3 --> P6_4 --> P6_5 --> P6_6 --> P6_7
    end
    
    subgraph Phase7["Phase 7: Graceful Disconnect"]
        P7_1[Client:<br/>disconnect]
        P7_2[Client Transport:<br/>CLOSE]
        P7_3[Server Transport:<br/>CLOSE_ACK]
        P7_4[Connection<br/>Closed ✓]
        
        P7_1 --> P7_2 --> P7_3 --> P7_4
    end
    
    P1_5 --> P2_1
    P2_5 --> P3_1
    P2_5 --> P4_1
    P2_5 --> P5_1
    P2_5 --> P6_1
    P4_7 --> P7_1
    
    style P1_5 fill:#90EE90
    style P2_5 fill:#90EE90
    style P4_7 fill:#FFE4B5
    style P5_9 fill:#E6E6FA
    style P7_4 fill:#D3D3D3
```

## Message Types

| Type | Direction | Purpose |
|------|-----------|---------|
| **AUTH_REQUEST** | Client → Server | Send password hash |
| **AUTH_SUCCESS** | Server → Client | Authentication OK |
| **MESSAGE** | Bidirectional | Regular message |
| **RPC_REQUEST** | Client → Server | Call RPC method |
| **RPC_RESPONSE** | Server → Client | RPC result |
| **RPC_ERROR** | Server → Client | RPC error |
| **HEARTBEAT_PING** | Bidirectional | Check connection alive |
| **HEARTBEAT_PONG** | Bidirectional | Respond to ping |
| **PAUSE** | Bidirectional | Stop sending (backpressure) |
| **RESUME** | Bidirectional | Resume sending |
| **CLOSE** | Bidirectional | Request connection close |
| **CLOSE_ACK** | Bidirectional | Acknowledge close |

