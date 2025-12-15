"""
File Transfer Module

Provides chunked file upload/download with progress tracking and resume support.
"""

import asyncio
import hashlib
import os
import time
import base64
from typing import Optional, Callable, Any, Dict, BinaryIO
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

# Default chunk size (64KB)
DEFAULT_CHUNK_SIZE = 64 * 1024


@dataclass
class TransferProgress:
    """Progress tracking for file transfers."""
    filename: str
    total_size: int
    transferred: int = 0
    chunks_sent: int = 0
    start_time: float = field(default_factory=time.time)
    
    @property
    def percent(self) -> float:
        if self.total_size == 0:
            return 100.0
        return (self.transferred / self.total_size) * 100
    
    @property
    def elapsed(self) -> float:
        return time.time() - self.start_time
    
    @property
    def speed(self) -> float:
        """Bytes per second."""
        if self.elapsed == 0:
            return 0
        return self.transferred / self.elapsed
    
    @property
    def eta(self) -> float:
        """Estimated time remaining in seconds."""
        if self.speed == 0:
            return float('inf')
        remaining = self.total_size - self.transferred
        return remaining / self.speed
    
    def to_dict(self) -> dict:
        return {
            "filename": self.filename,
            "total_size": self.total_size,
            "transferred": self.transferred,
            "percent": round(self.percent, 2),
            "speed_mbps": round(self.speed / 1024 / 1024, 2),
            "eta_seconds": round(self.eta, 1) if self.eta != float('inf') else None,
        }


@dataclass
class TransferMetadata:
    """Metadata for a file transfer."""
    filename: str
    size: int
    checksum: str
    chunk_size: int
    total_chunks: int
    transfer_id: str


class FileTransfer:
    """
    File transfer handler for chunked uploads/downloads.
    
    Usage (Server):
        transfer = FileTransfer(storage_dir="./uploads")
        
        @server.rpc
        async def upload_start(filename: str, size: int, checksum: str) -> dict:
            return await transfer.start_receive(filename, size, checksum)
        
        @server.rpc
        async def upload_chunk(transfer_id: str, chunk_index: int, data_b64: str) -> dict:
            return await transfer.receive_chunk(transfer_id, chunk_index, data_b64)
    
    Usage (Client):
        transfer = FileTransfer()
        await transfer.send_file(client, "myfile.zip", on_progress=print_progress)
    """
    
    def __init__(
        self,
        storage_dir: str = "./transfers",
        chunk_size: int = DEFAULT_CHUNK_SIZE,
    ):
        self.storage_dir = storage_dir
        self.chunk_size = chunk_size
        self._active_transfers: Dict[str, dict] = {}
        
        os.makedirs(storage_dir, exist_ok=True)
    
    # === Sending (Client-side) ===
    
    async def send_file(
        self,
        client,
        filepath: str,
        on_progress: Optional[Callable[[TransferProgress], None]] = None,
    ) -> dict:
        """
        Send a file to the server.
        
        Args:
            client: Connected Client instance
            filepath: Path to file to send
            on_progress: Progress callback
            
        Returns:
            Transfer result
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        
        filename = os.path.basename(filepath)
        size = os.path.getsize(filepath)
        checksum = self._compute_checksum(filepath)
        total_chunks = (size + self.chunk_size - 1) // self.chunk_size
        
        logger.info(f"Starting upload: {filename} ({size} bytes, {total_chunks} chunks)")
        
        # Start transfer
        from conduit import data
        result = await client.rpc.call("upload_start", args=data(
            filename=filename,
            size=size,
            checksum=checksum,
        ))
        
        if not result.get("success"):
            return result
        
        transfer_id = result.get("data", {}).get("transfer_id")
        
        # Send chunks
        progress = TransferProgress(filename=filename, total_size=size)
        
        with open(filepath, "rb") as f:
            chunk_index = 0
            while True:
                chunk = f.read(self.chunk_size)
                if not chunk:
                    break
                
                chunk_b64 = base64.b64encode(chunk).decode()
                
                result = await client.rpc.call("upload_chunk", args=data(
                    transfer_id=transfer_id,
                    chunk_index=chunk_index,
                    data_b64=chunk_b64,
                ))
                
                if not result.get("success"):
                    logger.error(f"Chunk {chunk_index} failed: {result}")
                    return result
                
                progress.transferred += len(chunk)
                progress.chunks_sent = chunk_index + 1
                
                if on_progress:
                    on_progress(progress)
                
                chunk_index += 1
        
        # Complete transfer
        result = await client.rpc.call("upload_complete", args=data(
            transfer_id=transfer_id,
        ))
        
        logger.info(f"Upload complete: {filename} in {progress.elapsed:.2f}s")
        return result
    
    async def download_file(
        self,
        client,
        remote_filename: str,
        local_path: str,
        on_progress: Optional[Callable[[TransferProgress], None]] = None,
    ) -> dict:
        """
        Download a file from the server.
        
        Args:
            client: Connected Client instance
            remote_filename: Filename on server
            local_path: Local path to save to
            on_progress: Progress callback
            
        Returns:
            Download result
        """
        from conduit import data
        
        # Get file info
        result = await client.rpc.call("download_start", args=data(
            filename=remote_filename,
        ))
        
        if not result.get("success"):
            return result
        
        info = result.get("data", {})
        transfer_id = info.get("transfer_id")
        size = info.get("size", 0)
        total_chunks = info.get("total_chunks", 0)
        
        progress = TransferProgress(filename=remote_filename, total_size=size)
        
        with open(local_path, "wb") as f:
            for chunk_index in range(total_chunks):
                result = await client.rpc.call("download_chunk", args=data(
                    transfer_id=transfer_id,
                    chunk_index=chunk_index,
                ))
                
                if not result.get("success"):
                    return result
                
                chunk_b64 = result.get("data", {}).get("data_b64", "")
                chunk = base64.b64decode(chunk_b64)
                f.write(chunk)
                
                progress.transferred += len(chunk)
                progress.chunks_sent = chunk_index + 1
                
                if on_progress:
                    on_progress(progress)
        
        logger.info(f"Download complete: {remote_filename} in {progress.elapsed:.2f}s")
        return {"success": True, "path": local_path, "size": size}
    
    # === Receiving (Server-side) ===
    
    async def start_receive(
        self,
        filename: str,
        size: int,
        checksum: str,
    ) -> dict:
        """Start receiving a file upload."""
        import uuid
        
        transfer_id = str(uuid.uuid4())
        total_chunks = (size + self.chunk_size - 1) // self.chunk_size
        
        # Create temp file
        temp_path = os.path.join(self.storage_dir, f".{transfer_id}.tmp")
        
        self._active_transfers[transfer_id] = {
            "filename": filename,
            "size": size,
            "checksum": checksum,
            "total_chunks": total_chunks,
            "received_chunks": 0,
            "temp_path": temp_path,
            "final_path": os.path.join(self.storage_dir, filename),
            "file": open(temp_path, "wb"),
            "start_time": time.time(),
        }
        
        logger.info(f"Started receive: {filename} ({size} bytes, id={transfer_id[:8]})")
        
        return {
            "transfer_id": transfer_id,
            "chunk_size": self.chunk_size,
            "total_chunks": total_chunks,
        }
    
    async def receive_chunk(
        self,
        transfer_id: str,
        chunk_index: int,
        data_b64: str,
    ) -> dict:
        """Receive a file chunk."""
        transfer = self._active_transfers.get(transfer_id)
        if not transfer:
            return {"error": "Transfer not found"}
        
        chunk = base64.b64decode(data_b64)
        transfer["file"].write(chunk)
        transfer["received_chunks"] += 1
        
        return {
            "received": True,
            "chunk_index": chunk_index,
            "chunks_received": transfer["received_chunks"],
            "total_chunks": transfer["total_chunks"],
        }
    
    async def complete_receive(self, transfer_id: str) -> dict:
        """Complete a file upload."""
        transfer = self._active_transfers.get(transfer_id)
        if not transfer:
            return {"error": "Transfer not found"}
        
        transfer["file"].close()
        
        # Verify checksum
        computed = self._compute_checksum(transfer["temp_path"])
        if computed != transfer["checksum"]:
            os.remove(transfer["temp_path"])
            del self._active_transfers[transfer_id]
            return {"error": "Checksum mismatch", "expected": transfer["checksum"], "got": computed}
        
        # Move to final location
        os.rename(transfer["temp_path"], transfer["final_path"])
        
        elapsed = time.time() - transfer["start_time"]
        del self._active_transfers[transfer_id]
        
        logger.info(f"Completed receive: {transfer['filename']} in {elapsed:.2f}s")
        
        return {
            "success": True,
            "filename": transfer["filename"],
            "size": transfer["size"],
            "path": transfer["final_path"],
            "elapsed": elapsed,
        }
    
    async def start_download(self, filename: str) -> dict:
        """Start a file download."""
        import uuid
        
        filepath = os.path.join(self.storage_dir, filename)
        if not os.path.exists(filepath):
            return {"error": "File not found"}
        
        size = os.path.getsize(filepath)
        total_chunks = (size + self.chunk_size - 1) // self.chunk_size
        transfer_id = str(uuid.uuid4())
        
        self._active_transfers[transfer_id] = {
            "filepath": filepath,
            "size": size,
            "total_chunks": total_chunks,
            "file": open(filepath, "rb"),
        }
        
        return {
            "transfer_id": transfer_id,
            "size": size,
            "total_chunks": total_chunks,
            "chunk_size": self.chunk_size,
        }
    
    async def get_download_chunk(self, transfer_id: str, chunk_index: int) -> dict:
        """Get a chunk for download."""
        transfer = self._active_transfers.get(transfer_id)
        if not transfer:
            return {"error": "Transfer not found"}
        
        transfer["file"].seek(chunk_index * self.chunk_size)
        chunk = transfer["file"].read(self.chunk_size)
        
        return {
            "chunk_index": chunk_index,
            "data_b64": base64.b64encode(chunk).decode(),
            "size": len(chunk),
        }
    
    def _compute_checksum(self, filepath: str) -> str:
        """Compute SHA256 checksum of a file."""
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
