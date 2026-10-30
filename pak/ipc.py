import struct
from multiprocessing import shared_memory
from typing import Optional

class SharedMemoryIPCSpine:
    """
    Lock-free Zero-Copy Shared Memory IPC Mesh for ultra-low latency inter-agent communication.
    
    Layout: [4-byte Payload Length Header] + [Payload Data Bytes]
    """
    
    def __init__(self, name: str = "pak_ipc_mesh", size: int = 1024 * 1024, create: bool = True):
        self.name = name
        self.size = size
        if create:
            try:
                self.shm = shared_memory.SharedMemory(name=name, create=True, size=size)
            except FileExistsError:
                self.shm = shared_memory.SharedMemory(name=name, create=False)
        else:
            self.shm = shared_memory.SharedMemory(name=name, create=False)

    def write_frame_zero_copy(self, frame_data: bytes, offset: int = 0) -> bool:
        """Writes data into shared memory with a binary length prefix."""
        length = len(frame_data)
        if offset + 4 + length > self.size:
            return False
        
        # Write 4-byte unsigned int header + raw frame bytes
        header = struct.pack("I", length)
        self.shm.buf[offset:offset+4] = header
        self.shm.buf[offset+4:offset+4+length] = frame_data
        return True

    def read_frame_zero_copy(self, offset: int = 0) -> Optional[bytes]:
        """Reads data directly from shared memory using header length offsets."""
        header_bytes = bytes(self.shm.buf[offset:offset+4])
        if not header_bytes or len(header_bytes) < 4:
            return None
        length = struct.unpack("I", header_bytes)[0]
        if length == 0 or offset + 4 + length > self.size:
            return None
        return bytes(self.shm.buf[offset+4:offset+4+length])

    def close_and_unlink(self):
        """Releases shared memory blocks back to OS kernel allocation pools."""
        try:
            self.shm.close()
            self.shm.unlink()
        except FileNotFoundError:
            pass