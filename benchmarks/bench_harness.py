import time
import json
import statistics
import tempfile
import shutil
import pak_core
from pak.kernel import PolymorphicAgentKernel

def run_performance_benchmarks():
    db_path = tempfile.mkdtemp(prefix="pak_bench_vault_")
    session_id = "bench_session_001"
    kernel = PolymorphicAgentKernel(session_id=session_id, db_path=db_path)
    
    results = {}
    print("=" * 80)
    print("  PAK-CORE AAOS EMPIRICAL BENCHMARK SUITE")
    print("=" * 80)

    # 1. VTable Method Hot-Swap Latency
    iterations = 1000
    hot_swap_code = """def execute_tool(self, name, kwargs):
    return {"status": "optimized", "val": kwargs.get("x", 0) * 2}
"""
    latencies_us = []
    for _ in range(iterations):
        t0 = time.perf_counter_ns()
        kernel.secure_hot_swap("execute_tool", hot_swap_code)
        t1 = time.perf_counter_ns()
        latencies_us.append((t1 - t0) / 1000.0)

    results["vtable_hot_swap_latency_us"] = {
        "mean": round(statistics.mean(latencies_us), 2),
        "p95": round(statistics.quantiles(latencies_us, n=20)[18], 2),
        "p99": round(statistics.quantiles(latencies_us, n=100)[98], 2),
        "min": round(min(latencies_us), 2),
        "max": round(max(latencies_us), 2),
    }
    print(f"\n[1/5] VTable Hot-Swap Latency ({iterations} ops):")
    print(f"      Mean: {results['vtable_hot_swap_latency_us']['mean']} µs | P95: {results['vtable_hot_swap_latency_us']['p95']} µs")

    # 2. Zero-Copy Shared Memory IPC Transfer (1MB Payload)
    payload = b"X" * (1024 * 1024)
    shm_latencies_us = []
    for _ in range(iterations):
        t0 = time.perf_counter_ns()
        kernel.ipc_spine.write_frame_zero_copy(payload, offset=0)
        _ = kernel.ipc_spine.read_frame_zero_copy(offset=0)
        t1 = time.perf_counter_ns()
        shm_latencies_us.append((t1 - t0) / 1000.0)

    results["zero_copy_ipc_1mb_latency_us"] = {
        "mean": round(statistics.mean(shm_latencies_us), 2),
        "p95": round(statistics.quantiles(shm_latencies_us, n=20)[18], 2),
        "p99": round(statistics.quantiles(shm_latencies_us, n=100)[98], 2),
        "throughput_mbps": round((1024.0 / (statistics.mean(shm_latencies_us) / 1e6)), 2)
    }
    print(f"\n[2/5] Zero-Copy IPC Mesh (1MB Frame Transfer):")
    print(f"      Mean: {results['zero_copy_ipc_1mb_latency_us']['mean']} µs | Throughput: {results['zero_copy_ipc_1mb_latency_us']['throughput_mbps']} MB/s")

    # 3. Formal Z3 SMT Safety Verification Latency
    smt_latencies_ms = []
    for _ in range(100):
        t0 = time.perf_counter_ns()
        kernel.smt_verifier.prove_safety_invariants(hot_swap_code, "execute_tool")
        t1 = time.perf_counter_ns()
        smt_latencies_ms.append((t1 - t0) / 1e6)

    results["smt_z3_verification_latency_ms"] = {
        "mean": round(statistics.mean(smt_latencies_ms), 3),
        "p95": round(statistics.quantiles(smt_latencies_ms, n=20)[18], 3),
    }
    print(f"\n[3/5] Formal Z3 SMT Safety Verification:")
    print(f"      Mean Latency: {results['smt_z3_verification_latency_ms']['mean']} ms")

    # 4. Multi-Tier Context Memory Swap (L1 RAM <-> L3 Storage Vault)
    page_fault_latencies_us = []
    for i in range(100):
        frame_id = f"f_bench_{i}"
        frame = pak_core.ContextFrame(frame_id, f"Payload_Data_{i}" * 100, pak_core.CacheTier.L1Active)
        kernel.system_kernel.push_context_frame(session_id, frame)
        
        t0 = time.perf_counter_ns()
        kernel.system_kernel.page_fault_swap(session_id, frame_id, pak_core.CacheTier.L3Storage)
        _ = kernel.system_kernel.recall_l3_frame(session_id, frame_id)
        t1 = time.perf_counter_ns()
        page_fault_latencies_us.append((t1 - t0) / 1000.0)

    results["memory_paging_swap_latency_us"] = {
        "mean": round(statistics.mean(page_fault_latencies_us), 2),
        "p95": round(statistics.quantiles(page_fault_latencies_us, n=20)[18], 2),
    }
    print(f"\n[4/5] Context Page Fault Swap (L1 RAM <-> L3 Storage):")
    print(f"      Mean Latency: {results['memory_paging_swap_latency_us']['mean']} µs")

    # 5. Distributed CRDT Vector-Clock Convergence
    crdt_latencies_us = []
    for i in range(iterations):
        t0 = time.perf_counter_ns()
        mutation = kernel.consensus_mesh.broadcast_vtable_mutation("execute_tool", hot_swap_code, fitness_score=0.9 + (i * 0.0001))
        _ = kernel.consensus_mesh.receive_remote_mutation(mutation)
        t1 = time.perf_counter_ns()
        crdt_latencies_us.append((t1 - t0) / 1000.0)

    results["crdt_consensus_convergence_us"] = {
        "mean": round(statistics.mean(crdt_latencies_us), 2),
        "p95": round(statistics.quantiles(crdt_latencies_us, n=20)[18], 2),
    }
    print(f"\n[5/5] Distributed CRDT Vector-Clock Convergence:")
    print(f"      Mean Latency: {results['crdt_consensus_convergence_us']['mean']} µs")

    with open("benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)

    kernel.close()
    shutil.rmtree(db_path, ignore_errors=True)
    
    print("\n" + "=" * 80)
    print("  BENCHMARK SUITE COMPLETE — RESULTS SAVED TO benchmark_results.json")
    print("=" * 80)

if __name__ == "__main__":
    run_performance_benchmarks()
