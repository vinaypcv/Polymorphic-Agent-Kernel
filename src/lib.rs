use pyo3::prelude::*;
use rocksdb::{Options, DB};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::time::{SystemTime, UNIX_EPOCH};

#[pyclass]
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub enum CacheTier {
    L1Active,
    L2Graph,
    L3Storage,
}

#[pyclass]
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ContextFrame {
    #[pyo3(get, set)]
    pub id: String,
    #[pyo3(get, set)]
    pub payload: String,
    #[pyo3(get, set)]
    pub tier: CacheTier,
}

#[pymethods]
impl ContextFrame {
    #[new]
    fn new(id: String, payload: String, tier: CacheTier) -> Self {
        ContextFrame { id, payload, tier }
    }
}

#[pyclass]
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct SecurityAuditToken {
    #[pyo3(get)]
    pub timestamp: u64,
    #[pyo3(get)]
    pub action_hash: String,
    #[pyo3(get)]
    pub identity_scope: String,
}

#[pymethods]
impl SecurityAuditToken {
    #[new]
    fn new(action_hash: String, identity_scope: String) -> Self {
        let start = SystemTime::now();
        let timestamp = start.duration_since(UNIX_EPOCH).unwrap_or_default().as_secs();
        SecurityAuditToken {
            timestamp,
            action_hash,
            identity_scope,
        }
    }
}

#[pyclass]
pub struct AgentKernel {
    context_manager: Arc<Mutex<HashMap<String, Vec<ContextFrame>>>>,
    db_instance: Arc<Mutex<Option<DB>>>,
}

#[pymethods]
impl AgentKernel {
    #[new]
    fn new(db_path: String) -> PyResult<Self> {
        let mut opts = Options::default();
        opts.create_if_missing(true);
        opts.set_max_background_jobs(4);
        opts.set_write_buffer_size(64 * 1024 * 1024);
        let db = DB::open(&opts, db_path)
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("RocksDB Init Error: {}", e)))?;
        Ok(AgentKernel {
            context_manager: Arc::new(Mutex::new(HashMap::new())),
            db_instance: Arc::new(Mutex::new(Some(db))),
        })
    }

    fn close(&self) -> PyResult<()> {
        let mut db_guard = self.db_instance.lock()
            .map_err(|_| pyo3::exceptions::PyRuntimeError::new_err("Context mutex poisoned"))?;
        *db_guard = None;
        Ok(())
    }

    fn push_context_frame(&self, session_id: String, frame: ContextFrame) -> PyResult<()> {
        let mut binding = self.context_manager.lock()
            .map_err(|_| pyo3::exceptions::PyRuntimeError::new_err("Context mutex poisoned"))?;
        binding.entry(session_id).or_insert_with(Vec::new).push(frame);
        Ok(())
    }

    fn page_fault_swap(&self, session_id: String, frame_id: String, target_tier: CacheTier) -> PyResult<bool> {
        let mut binding = self.context_manager.lock()
            .map_err(|_| pyo3::exceptions::PyRuntimeError::new_err("Context mutex poisoned"))?;
        if let Some(frames) = binding.get_mut(&session_id) {
            if let Some(frame) = frames.iter_mut().find(|f| f.id == frame_id) {
                if target_tier == CacheTier::L3Storage {
                    let serialized = serde_json::to_string(&frame)
                        .map_err(|e| pyo3::exceptions::PyTypeError::new_err(format!("Serialization Error: {}", e)))?;
                    let storage_key = format!("{}:{}", session_id, frame_id);
                    let db_guard = self.db_instance.lock()
                        .map_err(|_| pyo3::exceptions::PyRuntimeError::new_err("DB lock poisoned"))?;
                    if let Some(ref db) = *db_guard {
                        db.put(storage_key.as_bytes(), serialized.as_bytes())
                            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("RocksDB Error: {}", e)))?;
                    } else {
                        return Err(pyo3::exceptions::PyRuntimeError::new_err("RocksDB handle closed"));
                    }
                    frame.payload = String::new();
                }
                frame.tier = target_tier;
                return Ok(true);
            }
        }
        Ok(false)
    }

    fn recall_l3_frame(&self, session_id: String, frame_id: String) -> PyResult<Option<ContextFrame>> {
        let storage_key = format!("{}:{}", session_id, frame_id);
        let db_guard = self.db_instance.lock()
            .map_err(|_| pyo3::exceptions::PyRuntimeError::new_err("DB lock poisoned"))?;
        if let Some(ref db) = *db_guard {
            match db.get(storage_key.as_bytes()) {
                Ok(Some(bytes)) => {
                    let raw = String::from_utf8(bytes)
                        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Encoding Error: {}", e)))?;
                    let mut frame: ContextFrame = serde_json::from_str(&raw)
                        .map_err(|e| pyo3::exceptions::PyTypeError::new_err(format!("Deserialization Error: {}", e)))?;
                    frame.tier = CacheTier::L1Active;
                    Ok(Some(frame))
                },
                Ok(None) => Ok(None),
                Err(e) => Err(pyo3::exceptions::PyRuntimeError::new_err(format!("RocksDB Error: {}", e))),
            }
        } else {
            Err(pyo3::exceptions::PyRuntimeError::new_err("RocksDB handle closed"))
        }
    }
}

#[pymodule]
fn pak_core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<CacheTier>()?;
    m.add_class::<ContextFrame>()?;
    m.add_class::<SecurityAuditToken>()?;
    m.add_class::<AgentKernel>()?;
    Ok(())
}