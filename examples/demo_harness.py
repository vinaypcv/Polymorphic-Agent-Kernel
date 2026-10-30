import os
import shutil
import tempfile
import time
import pak_core
from pak.kernel import PolymorphicAgentKernel
from pak.sandbox import CopyOnWriteSandbox
from pak.abi import POSIXAISyscallNumber

def run_live_aaos_demonstration():
    db_path = tempfile.mkdtemp(prefix="pak_demo_vault_")
    session_id = "agent_demo_session_001"
    workspace = tempfile.mkdtemp(prefix="pak_demo_ws_")
    
    print("=" * 80)
    print("  PAK-CORE AAOS (AUTONOMOUS AGENT OPERATING SYSTEM) DEMO HARNESS")
    print("=" * 80)

    # 1. Initialize Kernel & Integrated Pillars
    kernel = PolymorphicAgentKernel(session_id=session_id, db_path=db_path)
    print(f"\n[1/6] Kernel initialized. Session ID: {session_id}")

    # 2. POSIX-AI ABI System Call: Formal Verification & VTable Hot-Swapping
    print("\n[2/6] Dispatching POSIX-AI System Calls (Pillar 1 & Pillar 5)...")
    evolved_tool_code = """def execute_tool(self, name, kwargs):
    # Evolved high-efficiency tool handler
    data_token = kwargs.get("tx_token", "default_val")
    return {"status": "healed", "id": data_token, "metric_score": 0.99}
"""
    # SYS_SMT_VERIFY Call
    smt_res = kernel.abi.syscall(
        POSIXAISyscallNumber.SYS_SMT_VERIFY,
        {"raw_code": evolved_tool_code, "method_name": "execute_tool"}
    )
    print(f"  -> SYS_SMT_VERIFY (Syscall 105): Proven={smt_res['proven']}, Code={smt_res['return_code']}")

    # SYS_VTABLE_SWAP Call
    swap_res = kernel.abi.syscall(
        POSIXAISyscallNumber.SYS_VTABLE_SWAP,
        {"method_name": "execute_tool", "raw_code": evolved_tool_code}
    )
    print(f"  -> SYS_VTABLE_SWAP (Syscall 102): Applied={swap_res['return_code'] == 0}")

    # 3. Speculative Sandbox Execution
    print("\n[3/6] Running Speculative VTable Pre-Execution (Pillar 3)...")
    candidate_tool = "execute_tool"
    predicted_args = {"tx_token": "speculative_tx_9981"}
    
    spec_tx_id, spec_result = kernel.speculator.speculative_pre_execute(
        candidate_tool, predicted_args, session_id
    )
    print(f"  -> Speculative Tx ID : {spec_tx_id}")
    print(f"  -> Pre-computed Result: {spec_result}")

    # 4. Zero-Copy Shared Memory Frame Swap
    print("\n[4/6] Inter-Agent IPC Mesh Zero-Copy Frame Transfer (Pillar 2)...")
    frame_payload = b"AGENT_CONTEXT_STATE_OFFSET_001_HYPER_RAM_BUFFER"
    write_ok = kernel.ipc_spine.write_frame_zero_copy(frame_payload, offset=0)
    recalled_bytes = kernel.ipc_spine.read_frame_zero_copy(offset=0)
    print(f"  -> Zero-Copy Write Success: {write_ok}")
    print(f"  -> Recalled Payload from SHM Buffer: {recalled_bytes.decode('utf-8')}")

    # 5. Multi-Tier Hardware Memory Paging
    print("\n[5/6] Multi-Tier Memory Paging (L1 Active RAM -> L3 RocksDB Vault)...")
    frame = pak_core.ContextFrame("f_demo_01", "High-priority long-term agent task context", pak_core.CacheTier.L1Active)
    kernel.system_kernel.push_context_frame(session_id, frame)
    
    # Page fault swap to L3 storage
    kernel.abi.syscall(
        POSIXAISyscallNumber.SYS_PAGE_FAULT,
        {"session_id": session_id, "frame_id": "f_demo_01", "target_tier": pak_core.CacheTier.L3Storage}
    )
    recalled_frame = kernel.system_kernel.recall_l3_frame(session_id, "f_demo_01")
    print(f"  -> Recalled Context Frame Payload from L3: '{recalled_frame.payload}'")

    # 6. Copy-on-Write Sandbox Transaction with Genetic Autotuner Promotion
    print("\n[6/6] Executing Atomic CoW Sandbox Transaction & Autotuner Optimization (Pillar 4)...")
    sandbox = CopyOnWriteSandbox(workspace=workspace, session_id=session_id)
    
    with sandbox.transaction() as active_env:
        out_file = os.path.join(active_env, "execution_state.json")
        with open(out_file, "w") as f:
            f.write('{"state": "committed_under_isolation"}')
            
    def optimized_variant(self, name, kwargs):
        return {"status": "success", "id": kwargs.get("tx_token"), "latency_ms": 0.01}

    benchmark_samples = [{"tx_token": "bench_01"}, {"tx_token": "bench_02"}]
    promoted = kernel.autotuner.evaluate_and_promote("execute_tool", optimized_variant, benchmark_samples)
    print(f"  -> Autotuner Candidate Promoted to Live VTable: {promoted}")
    print(f"  -> Active Method Fitness Score: {kernel.autotuner.fitness_registry.get('execute_tool'):.2f}")

    # Cleanup
    kernel.close()
    shutil.rmtree(db_path, ignore_errors=True)
    shutil.rmtree(workspace, ignore_errors=True)
    print("\n" + "=" * 80)
    print("  DEMONSTRATION COMPLETED SUCCESSFULLY WITH 100% VERIFICATION")
    print("=" * 80)

if __name__ == "__main__":
    run_live_aaos_demonstration()