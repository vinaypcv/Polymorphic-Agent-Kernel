import time
from typing import Dict, Any, List, Optional

class DistributedVTableConsensus:
    """Synchronizes mutated VTable functions across distributed node clusters via CRDT state convergence."""
    
    def __init__(self, node_id: str, cluster_peers: Optional[List[str]] = None):
        self.node_id = node_id
        self.peers = cluster_peers or []
        self.vector_clock: Dict[str, int] = {node_id: 0}
        self.crdt_vtable_registry: Dict[str, Dict[str, Any]] = {}

    def broadcast_vtable_mutation(
        self, method_name: str, raw_code: str, fitness_score: float
    ) -> Dict[str, Any]:
        """Increments local logical clock and emits a CRDT mutation payload."""
        self.vector_clock[self.node_id] = self.vector_clock.get(self.node_id, 0) + 1
        
        payload = {
            "method_name": method_name,
            "raw_code": raw_code,
            "fitness_score": fitness_score,
            "origin_node": self.node_id,
            "vector_clock": dict(self.vector_clock),
            "timestamp_ns": time.time_ns()
        }
        
        self._apply_crdt_mutation(payload)
        return payload

    def receive_remote_mutation(self, payload: Dict[str, Any]) -> bool:
        """Merges remote vector clock and evaluates CRDT fitness convergence."""
        remote_clock = payload.get("vector_clock", {})
        for node, count in remote_clock.items():
            self.vector_clock[node] = max(self.vector_clock.get(node, 0), count)

        return self._apply_crdt_mutation(payload)

    def _apply_crdt_mutation(self, payload: Dict[str, Any]) -> bool:
        method_name = payload["method_name"]
        current = self.crdt_vtable_registry.get(method_name)

        # CRDT Convergence Rule: Promote if no state exists OR if remote fitness > local fitness
        if not current or payload["fitness_score"] > current["fitness_score"]:
            self.crdt_vtable_registry[method_name] = payload
            return True
        return False