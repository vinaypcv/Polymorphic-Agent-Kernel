import tempfile
import shutil
import gc
import pytest
from pak.ebpf_tracer import EBPFSystemTracer
from pak.cuda_bridge import CudaMemoryBridgeWrapper
from pak.distributed import DistributedVTableConsensus
from pak.kernel import PolymorphicAgentKernel

# Test Extension 1: eBPF Kernel Tracing
def test_extension_1_ebpf_tracer():
    tracer = EBPFSystemTracer()
    assert tracer.attach_sys_entry_probe(102) is True
    
    tracer.record_syscall_telemetry(syscall_id=102, latency_ns=140, status_code=0)
    events = tracer.get_telemetry_events()
    
    assert len(events) == 1
    assert events[0]["syscall_id"] == 102
    assert events[0]["latency_ns"] == 140

# Test Extension 2: Zero-Copy CUDA Memory Bridge
def test_extension_2_cuda_memory_bridge():
    cuda_bridge = CudaMemoryBridgeWrapper(size_bytes=1024 * 1024 * 16)
    allocation = cuda_bridge.allocate_unified_frame()
    
    assert allocation["size_bytes"] == 1024 * 1024 * 16
    assert "status" in allocation
    assert cuda_bridge.release_frame() is True

# Test Extension 3: Distributed CRDT Consensus Mesh
def test_extension_3_distributed_consensus_mesh():
    node_a = DistributedVTableConsensus(node_id="node_server_a")
    node_b = DistributedVTableConsensus(node_id="node_server_b")

    # Node A mutates VTable with fitness score 0.85
    mutation_a = node_a.broadcast_vtable_mutation("execute_tool", "code_a", fitness_score=0.85)
    
    # Node B receives mutation from Node A
    applied_b = node_b.receive_remote_mutation(mutation_a)
    assert applied_b is True
    assert "execute_tool" in node_b.crdt_vtable_registry

    # Node B mutates same VTable with higher fitness score 0.98
    mutation_b = node_b.broadcast_vtable_mutation("execute_tool", "code_b", fitness_score=0.98)
    
    # Node A receives mutation from Node B and updates due to higher fitness
    applied_a = node_a.receive_remote_mutation(mutation_b)
    assert applied_a is True
    assert node_a.crdt_vtable_registry["execute_tool"]["fitness_score"] == 0.98

# Test E2E Integration inside Kernel Runtime
def test_next_frontier_kernel_integration():
    db_path = tempfile.mkdtemp(prefix="test_frontier_db_")
    kernel = PolymorphicAgentKernel(session_id="frontier_node_01", db_path=db_path)

    # Check that all next-frontier handles are active
    assert kernel.ebpf_tracer is not None
    assert kernel.cuda_bridge is not None
    assert kernel.consensus_mesh is not None

    cuda_info = kernel.cuda_bridge.allocate_unified_frame()
    assert cuda_info["size_bytes"] > 0

    kernel.close()
    del kernel
    gc.collect()
    shutil.rmtree(db_path, ignore_errors=True)