import time
from typing import Dict, Any, Callable, List

class GeneticVTableAutotuner:
    """Continuously evaluates and promotes optimal VTable method variants."""
    
    def __init__(self, kernel):
        self.kernel = kernel
        self.fitness_registry: Dict[str, float] = {}

    def evaluate_and_promote(
        self, method_name: str, candidate_func: Callable, benchmark_inputs: List[Dict[str, Any]]
    ) -> bool:
        start = time.perf_counter()
        successes = 0
        
        for sample in benchmark_inputs:
            try:
                if hasattr(candidate_func, "__self__"):
                    out = candidate_func(method_name, sample)
                else:
                    out = candidate_func(self.kernel, method_name, sample)
                    
                if out.get("status") in ["success", "hot_patched_healed_state"]:
                    successes += 1
            except Exception:
                pass
                
        elapsed = time.perf_counter() - start
        success_rate = successes / max(len(benchmark_inputs), 1)
        
        fitness_score = success_rate / (elapsed + 1e-6)
        current_best = self.fitness_registry.get(method_name, 0.0)
        
        if fitness_score > current_best:
            self.fitness_registry[method_name] = fitness_score
            self.kernel.vtable[method_name] = candidate_func.__get__(self.kernel, self.kernel.__class__)
            return True
        return False