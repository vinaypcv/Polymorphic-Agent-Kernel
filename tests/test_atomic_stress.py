import concurrent.futures
import tempfile
import shutil
import pak_core
from pak.kernel import PolymorphicAgentKernel

def test_lock_free_atomic_pointer_stress_concurrency():
    db_path = tempfile.mkdtemp(prefix="test_atomic_stress_")
    kernel = PolymorphicAgentKernel(session_id="stress_session_001", db_path=db_path)
    
    num_threads = 16
    operations_per_thread = 50

    def worker_task(thread_id: int):
        for i in range(operations_per_thread):
            frame_id = f"f_t{thread_id}_{i}"
            frame = pak_core.ContextFrame(frame_id, f"Payload_content_{thread_id}_{i}", pak_core.CacheTier.L1Active)
            
            # 1. Atomic push
            push_ok = kernel.system_kernel.push_context_frame("stress_session_001", frame)
            assert push_ok is True
            
            # 2. Atomic page fault swap
            swap_ok = kernel.system_kernel.page_fault_swap("stress_session_001", frame_id, pak_core.CacheTier.L3Storage)
            assert swap_ok is True
            
            # 3. Lock-free recall
            recalled = kernel.system_kernel.recall_l3_frame("stress_session_001", frame_id)
            assert recalled is not None
            assert recalled.frame_id == frame_id

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker_task, t) for t in range(num_threads)]
        for future in concurrent.futures.as_completed(futures):
            future.result()

    kernel.close()
    shutil.rmtree(db_path, ignore_errors=True)