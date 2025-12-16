Benchmarks
==========

Performance comparison between netconduit and WebSocket.

Summary
-------

Tests performed on localhost with Python 3.11:

.. list-table::
   :header-rows: 1
   :widths: 30 20 20 30

   * - Test
     - netconduit
     - WebSocket
     - Winner
   * - Connection Time
     - 1.58ms
     - 50.00ms
     - **netconduit**
   * - Message Throughput
     - ~10k msg/s
     - ~11k msg/s
     - WebSocket
   * - Round-trip Latency
     - 0.15ms
     - 0.25ms
     - **netconduit**
   * - File Transfer
     - 95 MB/s
     - 75 MB/s
     - **netconduit**
   * - Memory per Connection
     - 5 KB
     - 8 KB
     - **netconduit**
   * - Code Lines (same features)
     - 25 lines
     - 60 lines
     - **netconduit**

Analysis
--------

netconduit Advantages
^^^^^^^^^^^^^^^^^^^^^

- **Faster connections**: Direct TCP without HTTP upgrade
- **Better file transfer**: Binary chunks without base64 encoding
- **Lower memory**: Minimal protocol overhead
- **Less code**: Built-in RPC, auth, file transfer

WebSocket Advantages
^^^^^^^^^^^^^^^^^^^^

- **Browser support**: Works in web browsers
- **Proxy-friendly**: HTTP upgrade works through proxies
- **Ubiquitous**: Supported everywhere

When to Use netconduit
----------------------

- Server-to-server communication
- Native desktop/mobile applications
- IoT and embedded systems
- Game servers
- Microservices with RPC needs
- When you need built-in file transfer/streaming

When to Use WebSocket
---------------------

- Web browser clients
- Must work through HTTP proxies
- Existing WebSocket infrastructure
- Simple message passing only

Running Benchmarks
------------------

.. code-block:: bash

    python benchmarks/websocket_comparison.py

This generates a detailed report in `benchmarks/benchmark_results.md`.
