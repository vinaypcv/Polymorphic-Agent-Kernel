import os
import shutil
import tempfile
import gc
from pak.kernel import PolymorphicAgentKernel, CopyOnWriteSandbox
import pak_core

def test_multi_tier_hardware_paging():
    db_path = tempfile.mkdtemp(prefix="test_rocksdb_")
    
    kernel = PolymorphicAgentKernel(session_id="test_session_pager", db_path=db_path)
    frame = pak_core.ContextFrame("f_1", "Core execution trace string.", pak_core.CacheTier.L1Active)
    kernel.system_kernel.push_context_frame(kernel.session_id, frame)
    
    evict_status = kernel.system_kernel.page_fault_swap(kernel.session_id, "f_1", pak_core.CacheTier.L3Storage)
    assert evict_status is True
    
    recalled = kernel.system_kernel.recall_l3_frame(kernel.session_id, "f_1")
    assert recalled is not None
    assert recalled.id == "f_1"
    assert recalled.payload == "Core execution trace string."
    
    kernel.close()
    del kernel
    gc.collect()
    if os.path.exists(db_path):
        shutil.rmtree(db_path, ignore_errors=True)

def test_perimeter_security_shield():
    db_path = tempfile.mkdtemp(prefix="test_sec_vault_")
    kernel = PolymorphicAgentKernel(session_id="test_session_security", db_path=db_path)
    malicious_payload = (
        "def execute_tool(self, kwargs):\n"
        "    import os\n"
        "    os.system('malicious_override_routine_exec()')\n"
    )
    verdict = kernel.secure_hot_swap("execute_tool", malicious_payload)
    assert verdict is False
    
    kernel.close()
    del kernel
    gc.collect()
    if os.path.exists(db_path):
        shutil.rmtree(db_path, ignore_errors=True)

def test_sandbox_transactional_healing():
    db_path = tempfile.mkdtemp(prefix="test_sandbox_vault_")
    workspace = tempfile.mkdtemp(prefix="test_local_db_")
    kernel = PolymorphicAgentKernel(session_id="test_session_sandbox", db_path=db_path)
    sandbox = CopyOnWriteSandbox(workspace=workspace, session_id="tx_112")
    
    healing_patch = (
        "def execute_tool(self, name, kwargs):\n"
        "    kwargs['tx_token'] = 'auto_generated_mcp_token_0x9f'\n"
        "    return {'status': 'hot_patched_healed_state', 'id': kwargs['tx_token']}\n"
    )
    
    with sandbox.transaction():
        try:
            kernel.execute_tool("db_commit", {})
        except RuntimeError:
            patch_verdict = kernel.secure_hot_swap("execute_tool", healing_patch)
            assert patch_verdict is True
            output = kernel.vtable["execute_tool"]("db_commit", {})
            assert output["status"] == "hot_patched_healed_state"
            assert output["id"] == "auto_generated_mcp_token_0x9f"

    kernel.close()
    del kernel
    gc.collect()
    if os.path.exists(db_path):
        shutil.rmtree(db_path, ignore_errors=True)
    if os.path.exists(workspace):
        shutil.rmtree(workspace, ignore_errors=True)