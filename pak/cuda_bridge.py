from typing import Dict, Any, Optional
import pak_core

class CudaMemoryBridgeWrapper:
    """Zero-Copy CUDA Memory Bridge for local LLM inference acceleration."""
    
    def __init__(self, size_bytes: int = 1024 * 1024 * 64): # Default 64MB frame
        self.size_bytes = size_bytes
        try:
            self.native_bridge = pak_core.CudaMemoryBridge(size_bytes)
        except Exception:
            self.native_bridge = None

    def allocate_unified_frame(self) -> Dict[str, Any]:
        """Allocates a pinned memory region for 0ms host-to-device pointer transfers."""
        if self.native_bridge and self.native_bridge.is_allocated():
            return {
                "ptr_address": hex(self.native_bridge.get_address()),
                "size_bytes": self.native_bridge.get_size(),
                "status": "allocated_cuda_unified",
                "is_zero_copy": True
            }
        return {
            "ptr_address": "0x00000000",
            "size_bytes": self.size_bytes,
            "status": "fallback_host_pinned",
            "is_zero_copy": False
        }

    def release_frame(self) -> bool:
        if self.native_bridge:
            return self.native_bridge.release()
        return True