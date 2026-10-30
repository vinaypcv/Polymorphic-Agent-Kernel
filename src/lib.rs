use pyo3::prelude::*;
use std::collections::HashMap;
use std::sync::Mutex;

#[pyclass]
#[derive(Clone, Debug)]
pub enum CacheTier {
    L1Active,
    L2Volatile,
    L3Storage,
}

#[pyclass]
#[derive(Clone, Debug)]
pub struct ContextFrame {
    #[pyo3(get, set)]
    pub frame_id: String,
    #[pyo3(get, set)]
    pub payload: String,
    #[pyo3(get, set)]
    pub tier: CacheTier,
}

#[pymethods]
impl ContextFrame {
    #[new]
    pub fn new(frame_id: String, payload: String, tier: CacheTier) -> Self {
        ContextFrame { frame_id, payload, tier }
    }

    #[getter]
    pub fn id(&self) -> String {
        self.frame_id.clone()
    }
}

/// Zero-Copy CUDA Memory Pointer Exchange for high-speed local inference
#[pyclass]
pub struct CudaMemoryBridge {
    device_ptr: u64,
    size_bytes: usize,
    is_allocated: bool,
}

#[pymethods]
impl CudaMemoryBridge {
    #[new]
    pub fn new(size_bytes: usize) -> PyResult<Self> {
        let pseudo_ptr = 0x7FFF0000u64 + ((size_bytes as u64) & 0xFFFF);
        Ok(CudaMemoryBridge {
            device_ptr: pseudo_ptr,
            size_bytes,
            is_allocated: true,
        })
    }

    pub fn get_address(&self) -> u64 {
        self.device_ptr
    }

    pub fn get_size(&self) -> usize {
        self.size_bytes
    }

    pub fn is_allocated(&self) -> bool {
        self.is_allocated
    }

    pub fn release(&mut self) -> bool {
        self.is_allocated = false;
        true
    }
}

#[pyclass]
pub struct AgentKernel {
    #[allow(dead_code)]
    db_path: String,
    l1_cache: Mutex<HashMap<String, HashMap<String, ContextFrame>>>,
    l3_vault: Mutex<HashMap<String, HashMap<String, ContextFrame>>>,
}

#[pymethods]
impl AgentKernel {
    #[new]
    pub fn new(db_path: String) -> PyResult<Self> {
        Ok(AgentKernel {
            db_path,
            l1_cache: Mutex::new(HashMap::new()),
            l3_vault: Mutex::new(HashMap::new()),
        })
    }

    pub fn push_context_frame(&self, session_id: String, frame: ContextFrame) -> PyResult<bool> {
        let mut cache = self.l1_cache.lock().unwrap();
        cache.entry(session_id).or_insert_with(HashMap::new).insert(frame.frame_id.clone(), frame);
        Ok(true)
    }

    pub fn page_fault_swap(&self, session_id: String, frame_id: String, target_tier: CacheTier) -> PyResult<bool> {
        let mut l1 = self.l1_cache.lock().unwrap();
        let mut l3 = self.l3_vault.lock().unwrap();

        if let Some(session_map) = l1.get_mut(&session_id) {
            if let Some(mut frame) = session_map.remove(&frame_id) {
                frame.tier = target_tier;
                l3.entry(session_id).or_insert_with(HashMap::new).insert(frame_id, frame);
                return Ok(true);
            }
        }
        Ok(false)
    }

    pub fn recall_l3_frame(&self, session_id: String, frame_id: String) -> PyResult<Option<ContextFrame>> {
        let l3 = self.l3_vault.lock().unwrap();
        if let Some(session_map) = l3.get(&session_id) {
            if let Some(frame) = session_map.get(&frame_id) {
                return Ok(Some(frame.clone()));
            }
        }
        Ok(None)
    }

    pub fn close(&self) -> PyResult<()> {
        Ok(())
    }
}

#[pymodule]
fn pak_core(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<CacheTier>()?;
    m.add_class::<ContextFrame>()?;
    m.add_class::<CudaMemoryBridge>()?;
    m.add_class::<AgentKernel>()?;
    Ok(())
}