import os
import shutil
import tempfile
import gc
import concurrent.futures
import pytest
from pak.kernel import PolymorphicAgentKernel, CopyOnWriteSandbox
from pak.guard import IntentShieldValidator
import pak_core

# ==============================================================================
# 1. MEMORY & ROCKSDB BOUNDARY TEST CASES
# ==============================================================================

def test_rocksdb_non_existent_frame_recall():
    """Verify recalling a frame ID that was never written returns None instead of throwing an error."""
    db_path = tempfile.mkdtemp(prefix="test_missing_key_")
    kernel = PolymorphicAgentKernel(session_id="session_missing_key", db_path=db_path)
    
    recalled = kernel.system_kernel.recall_l3_frame("session_missing_key", "non_existent_frame_999")
    assert recalled is None

    kernel.close()
    del kernel
    gc.collect()
    shutil.rmtree(db_path, ignore_errors=True)

def test_rocksdb_large_payload_paging():
    """Verify that multi-megabyte context frames are properly serialized and decompressed by RocksDB."""
    db_path = tempfile.mkdtemp(prefix="test_large_payload_")
    kernel = PolymorphicAgentKernel(session_id="session_large_payload", db_path=db_path)
    
    # 5MB synthetic trace context frame
    large_payload = "X" * (5 * 1024 * 1024)
    frame = pak_core.ContextFrame("f_large", large_payload, pak_core.CacheTier.L1Active)
    
    kernel.system_kernel.push_context_frame(kernel.session_id, frame)
    assert kernel.system_kernel.page_fault_swap(kernel.session_id, "f_large", pak_core.CacheTier.L3Storage) is True
    
    recalled = kernel.system_kernel.recall_l3_frame(kernel.session_id, "f_large")
    assert recalled is not None
    assert len(recalled.payload) == len(large_payload)

    kernel.close()
    del kernel
    gc.collect()
    shutil.rmtree(db_path, ignore_errors=True)

# ==============================================================================
# 2. SECURITY SHIELD EVASION TEST CASES
# ==============================================================================

@pytest.mark.parametrize("malicious_code", [
    "def execute_tool(self, kwargs):\n    import os\n    os.system('whoami')",
    "def execute_tool(self, kwargs):\n    import subprocess\n    subprocess.Popen(['calc'])",
    "def execute_tool(self, kwargs):\n    return eval('2 + 2')",
    "def execute_tool(self, kwargs):\n    return globals()['__builtins__']",
    "def execute_tool(self, kwargs):\n    return getattr(self, 'secret')"
])
def test_security_shield_blocks_prohibited_tokens(malicious_code):
    """Verify that all blocked token patterns fail verification."""
    validator = IntentShieldValidator()
    assert validator.inspect_and_tokenize_intent(malicious_code) is False

def test_security_shield_handles_syntax_errors():
    """Verify that unparseable Python code is rejected by AST inspection without crashing the kernel."""
    db_path = tempfile.mkdtemp(prefix="test_syntax_err_")
    kernel = PolymorphicAgentKernel(session_id="session_syntax_err", db_path=db_path)
    
    invalid_syntax_code = "def execute_tool(self, kwargs):\n    return {'status': "  # Unmatched parenthesis
    assert kernel.secure_hot_swap("execute_tool", invalid_syntax_code) is False

    kernel.close()
    del kernel
    gc.collect()
    shutil.rmtree(db_path, ignore_errors=True)

# ==============================================================================
# 3. TRANSACTIONAL SANDBOX EDGE CASES
# ==============================================================================

def test_sandbox_nested_directory_rollback():
    """Verify that complex nested directory trees created during a failed transaction are fully wiped."""
    workspace = tempfile.mkdtemp(prefix="test_nested_ws_")
    sandbox = CopyOnWriteSandbox(workspace=workspace, session_id="tx_nested_fail")
    
    with pytest.raises(RuntimeError):
        with sandbox.transaction() as active_env:
            # Create a nested directory structure in the virtual overlay
            nested_dir = os.path.join(active_env, "subdir1", "subdir2")
            os.makedirs(nested_dir, exist_ok=True)
            with open(os.path.join(nested_dir, "temp_data.txt"), "w") as f:
                f.write("uncommitted changes")
            
            # Intentionally fail execution
            raise RuntimeError("Forced Transaction Failure")

    # Confirm host workspace remained completely untouched
    assert not os.path.exists(os.path.join(workspace, "subdir1"))
    shutil.rmtree(workspace, ignore_errors=True)

def test_sandbox_successful_atomic_commit():
    """Verify that files created inside a passing transaction cleanly persist to the primary workspace."""
    workspace = tempfile.mkdtemp(prefix="test_commit_ws_")
    sandbox = CopyOnWriteSandbox(workspace=workspace, session_id="tx_commit_pass")
    
    with sandbox.transaction() as active_env:
        file_path = os.path.join(active_env, "output.json")
        with open(file_path, "w") as f:
            f.write('{"status": "committed"}')

    # Confirm changes persisted to workspace
    committed_file = os.path.join(workspace, "output.json")
    assert os.path.exists(committed_file)
    with open(committed_file, "r") as f:
        assert f.read() == '{"status": "committed"}'

    shutil.rmtree(workspace, ignore_errors=True)

# ==============================================================================
# 4. POLYMORPHIC VTABLE LIFECYCLE TEST CASES
# ==============================================================================

def test_vtable_sequential_hot_swapping():
    """Verify that hot-swapping the same function multiple times cleanly overwrites the previous implementation."""
    db_path = tempfile.mkdtemp(prefix="test_vtable_overwrite_")
    kernel = PolymorphicAgentKernel(session_id="session_overwrite", db_path=db_path)
    
    version1_code = "def execute_tool(self, name, kwargs):\n    return {'v': 1}"
    version2_code = "def execute_tool(self, name, kwargs):\n    return {'v': 2}"

    assert kernel.secure_hot_swap("execute_tool", version1_code) is True
    assert kernel.vtable["execute_tool"]("tool_a", {})["v"] == 1

    assert kernel.secure_hot_swap("execute_tool", version2_code) is True
    assert kernel.vtable["execute_tool"]("tool_a", {})["v"] == 2

    kernel.close()
    del kernel
    gc.collect()
    shutil.rmtree(db_path, ignore_errors=True)

# ==============================================================================
# 5. CONCURRENT THREAD STRESS TEST
# ==============================================================================

def test_concurrent_vtable_and_paging_access():
    """Stress test thread safety by simulating 20 parallel threads making concurrent VTable calls."""
    db_path = tempfile.mkdtemp(prefix="test_concurrent_")
    kernel = PolymorphicAgentKernel(session_id="session_concurrent", db_path=db_path)

    def worker_thread(thread_idx: int):
        frame_id = f"frame_thread_{thread_idx}"
        frame = pak_core.ContextFrame(frame_id, f"payload_{thread_idx}", pak_core.CacheTier.L1Active)
        kernel.system_kernel.push_context_frame(kernel.session_id, frame)
        kernel.system_kernel.page_fault_swap(kernel.session_id, frame_id, pak_core.CacheTier.L3Storage)
        recalled = kernel.system_kernel.recall_l3_frame(kernel.session_id, frame_id)
        assert recalled is not None
        res = kernel.vtable["execute_tool"]("db_commit", {"tx_token": f"token_{thread_idx}"})
        assert res["id"] == f"token_{thread_idx}"

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(worker_thread, i) for i in range(20)]
        for future in concurrent.futures.as_completed(futures):
            future.result()  # Will re-raise exceptions if any occurred inside threads

    kernel.close()
    del kernel
    gc.collect()
    shutil.rmtree(db_path, ignore_errors=True)