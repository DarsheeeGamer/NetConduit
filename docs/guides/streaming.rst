Streaming Guide
===============

Bidirectional real-time data streaming.

Overview
--------

Both Server and Client can create and consume streams:

- **Server → Clients**: Push sensor data, game state, etc.
- **Client → Server**: Push video frames, audio, metrics
- **Subscriber pattern**: Multiple consumers per stream
- **Buffered**: Configurable buffer size per subscriber

Setup
-----

.. code-block:: python

    from conduit import StreamManager

    # Create stream manager
    streams = StreamManager()

Server Streaming to Clients
---------------------------

.. code-block:: python

    from conduit import Server, ServerDescriptor, StreamManager
    import asyncio

    server = Server(ServerDescriptor(password="secret"))
    streams = StreamManager(owner="server")

    # Register stream handlers
    streams.register_server_handlers(server)

    # Create a stream
    sensor_stream = streams.create("sensors", buffer_size=100)

    async def broadcast_sensor_data():
        """Background task to push sensor data."""
        while True:
            data = {
                "temperature": read_temperature(),
                "humidity": read_humidity(),
                "timestamp": time.time()
            }
            await sensor_stream.push(data)
            await asyncio.sleep(1.0)

    @server.on_startup
    async def on_start(srv):
        asyncio.create_task(broadcast_sensor_data())

Client Consuming Streams
------------------------

.. code-block:: python

    from conduit import Client, ClientDescriptor, StreamManager

    client = Client(ClientDescriptor(
        server_host="localhost",
        server_port=8080,
        password="secret"
    ))

    streams = StreamManager()
    streams.register_client_handlers(client)

    async def consume_sensors():
        await client.connect()
        
        # Subscribe and iterate
        async for data in streams.subscribe("sensors"):
            print(f"Temp: {data['temperature']}°C")
            print(f"Humidity: {data['humidity']}%")

Client Streaming to Server
--------------------------

Clients can also create streams:

.. code-block:: python

    # Client side - push video frames
    async def stream_video():
        await client.connect()
        
        while capturing:
            frame = camera.read()
            await streams.push_to_server("video_frames", {
                "frame": frame.tobytes(),
                "timestamp": time.time()
            })
            await asyncio.sleep(1/30)  # 30 FPS

    # Server side - consume client stream
    @streams.on_client_stream("video_frames")
    async def handle_frame(client_id, data):
        frame = np.frombuffer(data["frame"], dtype=np.uint8)
        process_frame(frame)

Stream Lifecycle
----------------

.. code-block:: python

    # Create stream
    stream = streams.create("my_stream", buffer_size=50)

    # Subscribe callback
    @stream.on_subscribe
    async def on_sub(subscriber_id):
        print(f"New subscriber: {subscriber_id}")

    # Unsubscribe callback
    @stream.on_unsubscribe
    async def on_unsub(subscriber_id):
        print(f"Lost subscriber: {subscriber_id}")

    # Push data
    count = await stream.push({"value": 42})
    print(f"Sent to {count} subscribers")

    # Close stream
    await stream.close()

Stream Info
-----------

.. code-block:: python

    # Get stream info
    print(f"Name: {stream.info.name}")
    print(f"Owner: {stream.info.owner}")
    print(f"Messages sent: {stream.info.message_count}")
    print(f"Subscribers: {stream.subscriber_count}")
    print(f"Active: {stream.is_active}")

    # List all streams
    for s in streams.list_streams():
        print(f"{s['name']}: {s['subscribers']} subscribers")

Complete Example: Live Dashboard
--------------------------------

**Server (dashboard_server.py):**

.. code-block:: python

    import asyncio
    import psutil
    from conduit import Server, ServerDescriptor, StreamManager

    server = Server(ServerDescriptor(port=8080, password="secret"))
    streams = StreamManager()
    streams.register_server_handlers(server)

    # System metrics stream
    metrics_stream = streams.create("system_metrics")

    async def collect_metrics():
        while True:
            await metrics_stream.push({
                "cpu": psutil.cpu_percent(),
                "memory": psutil.virtual_memory().percent,
                "disk": psutil.disk_usage("/").percent,
            })
            await asyncio.sleep(1.0)

    @server.on_startup
    async def start(srv):
        asyncio.create_task(collect_metrics())

    asyncio.run(server.run())

**Client (dashboard_client.py):**

.. code-block:: python

    import asyncio
    from conduit import Client, ClientDescriptor, StreamManager

    client = Client(ClientDescriptor(
        server_host="localhost",
        server_port=8080,
        password="secret"
    ))

    streams = StreamManager()
    streams.register_client_handlers(client)

    async def main():
        await client.connect()
        
        print("Monitoring system metrics...")
        async for data in streams.subscribe("system_metrics"):
            print(f"CPU: {data['cpu']}% | "
                  f"Memory: {data['memory']}% | "
                  f"Disk: {data['disk']}%")

    asyncio.run(main())
