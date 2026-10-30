import os
import shutil
import tempfile
import gc
import pytest
from pak.kernel import PolymorphicAgentKernel
from pak.abi import POSIXAISyscallNumber
from pak.smt_verifier import SMTFormalVerifier

# Pillar 1 Verification: Formal SMT Proof Gate
def test_pillar_1_smt_z3_verification():
    verifier = SMTFormalVerifier()
    safe_code = "def execute_tool(self, name, kwargs):\n    return {'status': 'success'}"
    unsafe_code = "def execute_tool(self, name, kwargs):\n    import os\n    os.system('rm -rf /')"
    
    assert verifier.prove_safety_invariants(safe_code, "execute_tool") is True
    assert verifier.prove_safety_invariants(unsafe_code, "execute_tool") is False

# Pillar 2 Verification: Zero-Copy Shared Memory IPC
def test_pillar_2_zero_copy_ipc_mesh():
    db_path = tempfile.mkdtemp(prefix="test_shm_db_")
    session_id = "test_shm_session"
    kernel = PolymorphicAgentKernel(session_id=session_id, db_path=db_path)
    
    payload = b"Zero-Copy IPC Frame Transmission Payload Metrics"
    assert kernel.ipc_spine.write_frame_zero_copy(payload, offset=0) is True
    
    read_data = kernel.ipc_spine.read_frame_zero_copy(offset=0)
    assert read_data == payload

    kernel.close()
    del kernel
    gc.collect()
    shutil.rmtree(db_path, ignore_errors=True)

# Pillar 3 Verification: Speculative Execution Engine
def test_pillar_3_speculative_vtable_execution():
    db_path = tempfile.mkdtemp(prefix="test_spec_db_")
    session_id = "test_spec_session"
    kernel = PolymorphicAgentKernel(session_id=session_id, db_path=db_path)
    
    spec_id, result = kernel.speculator.speculative_pre_execute(
        "execute_tool", {"tx_token": "speculative_token_0x01"}, session_id
    )
    assert spec_id == f"spec_{session_id}"
    assert result["status"] == "success"
    assert result["id"] == "speculative_token_0x01"

    kernel.close()
    del kernel
    gc.collect()
    shutil.rmtree(db_path, ignore_errors=True)

# Pillar 4 Verification: Genetic VTable Autotuner
def test_pillar_4_genetic_autotuner():
    db_path = tempfile.mkdtemp(prefix="test_auto_db_")
    kernel = PolymorphicAgentKernel(session_id="test_auto_session", db_path=db_path)
    
    def superior_candidate(self, name, kwargs):
        return {"status": "success", "id": kwargs.get("tx_token", "promoted")}

    benchmark_data = [{"tx_token": "token_1"}, {"tx_token": "token_2"}]
    promoted = kernel.autotuner.evaluate_and_promote("execute_tool", superior_candidate, benchmark_data)
    
    assert promoted is True
    assert "execute_tool" in kernel.autotuner.fitness_registry

    kernel.close()
    del kernel
    gc.collect()
    shutil.rmtree(db_path, ignore_errors=True)

# Pillar 5 Verification: POSIX-AI ABI System Calls
def test_pillar_5_posix_ai_abi_syscalls():
    db_path = tempfile.mkdtemp(prefix="test_abi_db_")
    kernel = PolymorphicAgentKernel(session_id="test_abi_session", db_path=db_path)
    
    safe_code = "def execute_tool(self, name, kwargs):\n    return {'status': 'healed'}"
    
    # Test SYS_SMT_VERIFY syscall
    res_verify = kernel.abi.syscall(
        POSIXAISyscallNumber.SYS_SMT_VERIFY,
        {"raw_code": safe_code, "method_name": "execute_tool"}
    )
    assert res_verify["return_code"] == 0
    assert res_verify["proven"] is True

    # Test SYS_VTABLE_SWAP syscall
    res_swap = kernel.abi.syscall(
        POSIXAISyscallNumber.SYS_VTABLE_SWAP,
        {"method_name": "execute_tool", "raw_code": safe_code}
    )
    assert res_swap["return_code"] == 0

    kernel.close()
    del kernel
    gc.collect()
    shutil.rmtree(db_path, ignore_errors=True)