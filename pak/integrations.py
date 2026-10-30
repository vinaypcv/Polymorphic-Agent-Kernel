from typing import Dict, Any
from pak.kernel import PolymorphicAgentKernel

class PakLangChainWrapper:
    """Wraps LangChain tool execution inside pak-core SMT sandbox and VTable engine."""
    
    def __init__(self, kernel: PolymorphicAgentKernel):
        self.kernel = kernel

    def run_tool_secured(self, tool_name: str, tool_code: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        swap_ok = self.kernel.secure_hot_swap(tool_name, tool_code)
        if not swap_ok:
            return {"error": "SMT_VERIFICATION_FAILED_OR_UNSAFE"}
        
        func = self.kernel.vtable.get(tool_name)
        if func:
            return func(self.kernel, tool_name, kwargs)
        return {"error": "METHOD_NOT_FOUND"}


class PakVLLMCudaAdapter:
    """Provides vLLM and ONNX model runtimes with direct zero-copy GPU memory pointers."""
    
    def __init__(self, kernel: PolymorphicAgentKernel):
        self.kernel = kernel

    def get_zero_copy_vram_pointer(self) -> Dict[str, Any]:
        return self.kernel.cuda_bridge.allocate_unified_frame()
