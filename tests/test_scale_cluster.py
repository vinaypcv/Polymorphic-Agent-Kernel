import time
import pytest
from pak.distributed import DistributedVTableConsensus

def test_scale_1000_sub_agents_crdt_mesh():
    num_agents = 1000
    agents = [DistributedVTableConsensus(node_id=f"agent_node_{i}") for i in range(num_agents)]
    
    leader = agents[0]
    mutation_payload = leader.broadcast_vtable_mutation(
        method_name="execute_tool",
        raw_code="def execute_tool(self, name, kwargs): return {'status': 'hyper_scaled'}",
        fitness_score=99999.9
    )

    t0 = time.perf_counter_ns()
    converged_count = 0
    for follower in agents[1:]:
        if follower.receive_remote_mutation(mutation_payload):
            converged_count += 1
    t1 = time.perf_counter_ns()

    total_time_ms = (t1 - t0) / 1e6
    assert converged_count == 999
    assert total_time_ms < 100.0  # Must converge across 1,000 nodes in under 100ms
