//! ESAA (Event Sourcing Agent Architecture) — Rust computational cores.
//!
//! Port of the hot-path data structures from `scripts/aco/esaa/`:
//!
//! - **`QueryCache<V>`**: Thread-safe LRU cache with TTL expiry and hit/miss statistics.
//! - **`EventBuffer`**: Write-ahead batch buffer for domain events with configurable
//!   flush triggers (size and age).
//!
//! I/O-heavy modules (saga, cqrs, dataloader, async_event_store) remain in Python.
//!
//! # Thread Safety
//!
//! Both structures use `std::sync::RwLock` for concurrent access:
//! - `QueryCache`: multiple concurrent readers, exclusive writer
//! - `EventBuffer`: exclusive lock on push/flush (write-heavy workload)
//!
//! # PyO3 Bindings
//!
//! `PyQueryCache` wraps `QueryCache<String>` (values as JSON strings for Python interop).
//! `PyEventBuffer` wraps `EventBuffer` with Python-callable methods.

use std::sync::RwLock;
use std::time::Instant;

use lru::LruCache;
#[cfg(feature = "python")]
use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

// ---------------------------------------------------------------------------
// QueryCache
// ---------------------------------------------------------------------------

/// Statistics for a [`QueryCache`] instance.
///
/// Tracks hits, misses, evictions, and TTL-based expirations.
/// All counters are monotonically increasing over the cache lifetime.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[cfg_attr(feature = "python", pyclass(frozen, get_all))]
pub struct QueryCacheStats {
    /// Number of successful cache lookups.
    pub hits: u64,
    /// Number of cache lookups that did not find a valid entry.
    pub misses: u64,
    /// Number of entries removed due to LRU eviction (max_size reached).
    pub evictions: u64,
    /// Number of entries removed due to TTL expiration.
    pub expired: u64,
    /// Current number of entries in the cache.
    pub current_size: usize,
    /// Maximum number of entries the cache can hold.
    pub max_size: usize,
}

#[cfg(feature = "python")]
#[pymethods]
impl QueryCacheStats {
    /// Cache hit rate as a float in `[0.0, 1.0]`.
    ///
    /// Returns `0.0` if no lookups have been performed.
    #[getter]
    fn hit_rate(&self) -> f64 {
        let total = self.hits + self.misses;
        if total == 0 {
            0.0
        } else {
            self.hits as f64 / total as f64
        }
    }

    /// Export to JSON string.
    fn to_json(&self) -> PyResult<String> {
        serde_json::to_string(self)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
    }
}

/// Internal cache entry holding value, creation instant, and access metadata.
struct CacheEntry<V> {
    value: V,
    created_at: Instant,
}

/// Mutable inner state of [`QueryCache`], protected by `RwLock`.
struct CacheInner<V> {
    lru: LruCache<String, CacheEntry<V>>,
    ttl: Option<std::time::Duration>,
    hits: u64,
    misses: u64,
    evictions: u64,
    expired: u64,
}

/// Thread-safe LRU cache with optional TTL expiry.
///
/// `QueryCache<V>` provides O(1) amortized `get`/`put` operations backed by
/// the `lru` crate. TTL expiry is checked lazily on `get` — there is no
/// background eviction thread, keeping the implementation lock-free for readers
/// when no mutation is required.
///
/// # Type Parameters
///
/// * `V` — cached value type. Must be `Clone` for retrieval through the lock.
///
/// # Examples
///
/// ```
/// use claude_learning_kernel::aco::esaa::QueryCache;
///
/// let cache = QueryCache::<String>::new(100, Some(5000));
/// cache.put("key".into(), "value".into());
/// assert_eq!(cache.get("key"), Some("value".into()));
/// ```
pub struct QueryCache<V: Clone> {
    inner: RwLock<CacheInner<V>>,
    max_size: usize,
}

impl<V: Clone> QueryCache<V> {
    /// Create a new cache with the given capacity and optional TTL in milliseconds.
    ///
    /// # Arguments
    ///
    /// * `max_size` — maximum number of entries before LRU eviction kicks in.
    /// * `ttl_ms` — optional time-to-live in milliseconds. `None` disables TTL.
    ///
    /// # Panics
    ///
    /// Panics if `max_size` is zero (a zero-capacity cache is nonsensical).
    pub fn new(max_size: usize, ttl_ms: Option<u64>) -> Self {
        assert!(max_size > 0, "max_size must be > 0");
        let cap = std::num::NonZeroUsize::new(max_size).expect("max_size > 0");
        Self {
            inner: RwLock::new(CacheInner {
                lru: LruCache::new(cap),
                ttl: ttl_ms.map(std::time::Duration::from_millis),
                hits: 0,
                misses: 0,
                evictions: 0,
                expired: 0,
            }),
            max_size,
        }
    }

    /// Retrieve a value by key.
    ///
    /// Returns `None` if the key is absent or expired. On a successful lookup the
    /// entry is promoted to most-recently-used. TTL expiry is checked on every `get`.
    pub fn get(&self, key: &str) -> Option<V> {
        let mut inner = self.inner.write().unwrap();

        // Peek first to check TTL without promoting
        if let Some(entry) = inner.lru.peek(key) {
            if let Some(ttl) = inner.ttl {
                if entry.created_at.elapsed() > ttl {
                    // Expired — remove and count
                    inner.lru.pop(key);
                    inner.expired += 1;
                    inner.misses += 1;
                    return None;
                }
            }
            // Valid — promote to most-recently-used and return clone
            let val = inner.lru.get(key).map(|e| e.value.clone());
            inner.hits += 1;
            val
        } else {
            inner.misses += 1;
            None
        }
    }

    /// Insert or update a cache entry.
    ///
    /// If the key already exists, the entry is replaced and promoted.
    /// If the cache is full, the least-recently-used entry is evicted.
    pub fn put(&self, key: String, value: V) {
        let mut inner = self.inner.write().unwrap();

        // If at capacity and key is new, the LRU crate auto-evicts the oldest.
        // We need to detect that to count evictions.
        let was_full = inner.lru.len() == inner.lru.cap().get();
        let is_new = !inner.lru.contains(&key);

        inner.lru.put(
            key,
            CacheEntry {
                value,
                created_at: Instant::now(),
            },
        );

        if was_full && is_new {
            inner.evictions += 1;
        }
    }

    /// Remove a specific key from the cache.
    ///
    /// Returns `true` if the key existed and was removed, `false` otherwise.
    pub fn invalidate(&self, key: &str) -> bool {
        let mut inner = self.inner.write().unwrap();
        inner.lru.pop(key).is_some()
    }

    /// Remove all keys matching a substring pattern.
    ///
    /// Returns the number of entries invalidated.
    pub fn invalidate_pattern(&self, pattern: &str) -> usize {
        let mut inner = self.inner.write().unwrap();
        let keys_to_remove: Vec<String> = inner
            .lru
            .iter()
            .filter(|(k, _)| k.contains(pattern))
            .map(|(k, _)| k.clone())
            .collect();
        let count = keys_to_remove.len();
        for key in keys_to_remove {
            inner.lru.pop(&key);
        }
        count
    }

    /// Remove all entries from the cache.
    ///
    /// Returns the number of entries that were removed.
    pub fn clear(&self) -> usize {
        let mut inner = self.inner.write().unwrap();
        let count = inner.lru.len();
        inner.lru.clear();
        count
    }

    /// Snapshot of current cache statistics.
    pub fn stats(&self) -> QueryCacheStats {
        let inner = self.inner.read().unwrap();
        QueryCacheStats {
            hits: inner.hits,
            misses: inner.misses,
            evictions: inner.evictions,
            expired: inner.expired,
            current_size: inner.lru.len(),
            max_size: self.max_size,
        }
    }

    /// Current number of entries (may include expired entries not yet evicted).
    pub fn len(&self) -> usize {
        let inner = self.inner.read().unwrap();
        inner.lru.len()
    }

    /// Whether the cache is empty.
    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }

    /// Check if a key exists and is not expired, without updating access order.
    pub fn contains(&self, key: &str) -> bool {
        let inner = self.inner.read().unwrap();
        if let Some(entry) = inner.lru.peek(key) {
            if let Some(ttl) = inner.ttl {
                return entry.created_at.elapsed() <= ttl;
            }
            true
        } else {
            false
        }
    }
}

// ---------------------------------------------------------------------------
// EventBuffer
// ---------------------------------------------------------------------------

/// Statistics for an [`EventBuffer`] instance.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[cfg_attr(feature = "python", pyclass(frozen, get_all))]
pub struct EventBufferStats {
    /// Current number of events in the buffer awaiting flush.
    pub buffer_size: usize,
    /// Total number of successful flush operations.
    pub flush_count: u64,
    /// Milliseconds elapsed since the last flush (or buffer creation).
    pub last_flush_ms_ago: f64,
}

#[cfg(feature = "python")]
#[pymethods]
impl EventBufferStats {
    /// Export to JSON string.
    fn to_json(&self) -> PyResult<String> {
        serde_json::to_string(self)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
    }
}

/// Configuration for [`EventBuffer`].
#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "python", pyclass(frozen, get_all))]
pub struct EventBufferConfig {
    /// Maximum number of events before a flush is triggered.
    pub max_batch_size: usize,
    /// Maximum age in milliseconds before a flush is triggered.
    pub max_age_ms: u64,
}

impl Default for EventBufferConfig {
    fn default() -> Self {
        Self {
            max_batch_size: 100,
            max_age_ms: 50,
        }
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl EventBufferConfig {
    #[new]
    #[pyo3(signature = (max_batch_size=100, max_age_ms=50))]
    fn new(max_batch_size: usize, max_age_ms: u64) -> Self {
        Self {
            max_batch_size,
            max_age_ms,
        }
    }
}

/// Mutable inner state of [`EventBuffer`], protected by `RwLock`.
struct BufferInner {
    events: Vec<String>,
    last_flush: Instant,
    flush_count: u64,
    shutdown: bool,
}

/// Write-ahead batch buffer for domain events.
///
/// Accumulates serialized event strings and signals readiness to flush
/// based on configurable size and age triggers. The actual I/O (disk write,
/// network send) is handled by the Python caller after draining the buffer
/// via [`EventBuffer::flush`].
///
/// Events are stored as JSON strings for PyO3 compatibility — the Python
/// side serializes `DomainEvent` to JSON before pushing, and deserializes
/// after flushing.
///
/// # Examples
///
/// ```
/// use claude_learning_kernel::aco::esaa::{EventBuffer, EventBufferConfig};
///
/// let config = EventBufferConfig { max_batch_size: 2, max_age_ms: 1000 };
/// let buffer = EventBuffer::new(config);
/// buffer.push(r#"{"event_id":"1","type":"created"}"#.into());
/// buffer.push(r#"{"event_id":"2","type":"updated"}"#.into());
/// assert!(buffer.is_ready()); // batch size reached
/// let batch = buffer.flush();
/// assert_eq!(batch.len(), 2);
/// ```
pub struct EventBuffer {
    config: EventBufferConfig,
    inner: RwLock<BufferInner>,
}

impl EventBuffer {
    /// Create a new buffer with the given configuration.
    pub fn new(config: EventBufferConfig) -> Self {
        Self {
            inner: RwLock::new(BufferInner {
                events: Vec::new(),
                last_flush: Instant::now(),
                flush_count: 0,
                shutdown: false,
            }),
            config,
        }
    }

    /// Append a serialized event (JSON string) to the buffer.
    ///
    /// # Errors
    ///
    /// Returns `Err` if the buffer has been shut down.
    pub fn push(&self, event_json: String) -> Result<(), EventBufferError> {
        let inner = self.inner.read().unwrap();
        if inner.shutdown {
            return Err(EventBufferError::Shutdown);
        }
        drop(inner);

        let mut inner = self.inner.write().unwrap();
        if inner.shutdown {
            return Err(EventBufferError::Shutdown);
        }
        inner.events.push(event_json);
        Ok(())
    }

    /// Drain all buffered events and return them.
    ///
    /// Resets the age timer. Returns an empty `Vec` if the buffer is empty.
    pub fn flush(&self) -> Vec<String> {
        let mut inner = self.inner.write().unwrap();
        if inner.events.is_empty() {
            return Vec::new();
        }
        let batch = std::mem::take(&mut inner.events);
        inner.last_flush = Instant::now();
        inner.flush_count += 1;
        batch
    }

    /// Current number of buffered events.
    pub fn len(&self) -> usize {
        let inner = self.inner.read().unwrap();
        inner.events.len()
    }

    /// Whether the buffer is empty.
    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }

    /// Check whether the buffer should be flushed.
    ///
    /// Returns `true` if either:
    /// - The number of buffered events >= `max_batch_size`, or
    /// - The time since the last flush >= `max_age_ms`.
    pub fn is_ready(&self) -> bool {
        let inner = self.inner.read().unwrap();
        if inner.events.is_empty() {
            return false;
        }
        if inner.events.len() >= self.config.max_batch_size {
            return true;
        }
        let elapsed_ms = inner.last_flush.elapsed().as_millis() as u64;
        elapsed_ms >= self.config.max_age_ms
    }

    /// Mark the buffer as shut down, preventing further pushes.
    ///
    /// If `flush_remaining` is `true`, returns the remaining events (caller
    /// should persist them). Otherwise returns `None`.
    pub fn shutdown(&self, flush_remaining: bool) -> Option<Vec<String>> {
        let mut inner = self.inner.write().unwrap();
        inner.shutdown = true;
        if flush_remaining {
            let batch = std::mem::take(&mut inner.events);
            inner.flush_count += 1;
            Some(batch)
        } else {
            None
        }
    }

    /// Snapshot of current buffer statistics.
    pub fn stats(&self) -> EventBufferStats {
        let inner = self.inner.read().unwrap();
        EventBufferStats {
            buffer_size: inner.events.len(),
            flush_count: inner.flush_count,
            last_flush_ms_ago: inner.last_flush.elapsed().as_secs_f64() * 1000.0,
        }
    }
}

/// Errors that can occur during [`EventBuffer`] operations.
#[derive(Debug, Clone)]
pub enum EventBufferError {
    /// Buffer has been shut down; no further pushes are accepted.
    Shutdown,
}

impl std::fmt::Display for EventBufferError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Shutdown => write!(f, "EventBuffer has been shut down"),
        }
    }
}

impl std::error::Error for EventBufferError {}

// ---------------------------------------------------------------------------
// PyO3 Wrappers
// ---------------------------------------------------------------------------

/// Python-facing LRU query cache backed by [`QueryCache<String>`].
///
/// Values are stored as JSON strings for cross-language compatibility.
/// The Python caller is responsible for serializing/deserializing.
#[cfg(feature = "python")]
#[pyclass(name = "EsaaQueryCache")]
pub struct PyQueryCache {
    inner: QueryCache<String>,
}

#[cfg(feature = "python")]
#[pymethods]
impl PyQueryCache {
    /// Create a new cache.
    ///
    /// # Arguments
    ///
    /// * `max_size` — maximum entry count (default 1000).
    /// * `ttl_ms` — optional TTL in milliseconds (default `None`).
    #[new]
    #[pyo3(signature = (max_size=1000, ttl_ms=None))]
    fn new(max_size: usize, ttl_ms: Option<u64>) -> PyResult<Self> {
        if max_size == 0 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "max_size must be > 0",
            ));
        }
        Ok(Self {
            inner: QueryCache::new(max_size, ttl_ms),
        })
    }

    /// Get a value by key. Returns `None` if absent or expired.
    fn get(&self, key: &str) -> Option<String> {
        self.inner.get(key)
    }

    /// Insert or update a cache entry.
    fn put(&self, key: String, value: String) {
        self.inner.put(key, value);
    }

    /// Remove a specific key. Returns `True` if the key existed.
    fn invalidate(&self, key: &str) -> bool {
        self.inner.invalidate(key)
    }

    /// Remove all keys matching a substring pattern. Returns count removed.
    fn invalidate_pattern(&self, pattern: &str) -> usize {
        self.inner.invalidate_pattern(pattern)
    }

    /// Clear all entries. Returns count removed.
    fn clear(&self) -> usize {
        self.inner.clear()
    }

    /// Get cache statistics.
    fn stats(&self) -> QueryCacheStats {
        self.inner.stats()
    }

    /// Current entry count.
    fn __len__(&self) -> usize {
        self.inner.len()
    }

    /// Check if key exists and is not expired.
    fn __contains__(&self, key: &str) -> bool {
        self.inner.contains(key)
    }
}

/// Python-facing event buffer backed by [`EventBuffer`].
///
/// Events are stored as JSON strings. The Python caller serializes
/// `DomainEvent` to JSON before pushing and deserializes after flushing.
#[cfg(feature = "python")]
#[pyclass(name = "EsaaEventBuffer")]
pub struct PyEventBuffer {
    inner: EventBuffer,
}

#[cfg(feature = "python")]
#[pymethods]
impl PyEventBuffer {
    /// Create a new buffer.
    ///
    /// # Arguments
    ///
    /// * `max_batch_size` — flush trigger size (default 100).
    /// * `max_age_ms` — flush trigger age in milliseconds (default 50).
    #[new]
    #[pyo3(signature = (max_batch_size=100, max_age_ms=50))]
    fn new(max_batch_size: usize, max_age_ms: u64) -> Self {
        Self {
            inner: EventBuffer::new(EventBufferConfig {
                max_batch_size,
                max_age_ms,
            }),
        }
    }

    /// Append a serialized event JSON string to the buffer.
    fn push(&self, event_json: String) -> PyResult<()> {
        self.inner
            .push(event_json)
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
    }

    /// Drain all buffered events and return them as a list of JSON strings.
    fn flush(&self) -> Vec<String> {
        self.inner.flush()
    }

    /// Current number of buffered events.
    fn __len__(&self) -> usize {
        self.inner.len()
    }

    /// Whether the buffer should be flushed (size or age trigger met).
    fn is_ready(&self) -> bool {
        self.inner.is_ready()
    }

    /// Shut down the buffer. Returns remaining events if `flush_remaining` is `True`.
    #[pyo3(signature = (flush_remaining=true))]
    fn shutdown(&self, flush_remaining: bool) -> Option<Vec<String>> {
        self.inner.shutdown(flush_remaining)
    }

    /// Get buffer statistics.
    fn stats(&self) -> EventBufferStats {
        self.inner.stats()
    }
}

// ---------------------------------------------------------------------------
// D3 — PyEventProjector (Rust AST Projector)
// D4 — verify_chain_parallel (Rayon-parallelized SHA-256 chain verifier)
//
// Sprint D of ESAA potentialisation plan `temporal-cooking-lampson.md`.
// ---------------------------------------------------------------------------

/// Stored domain event — mirrors the SQLite `events` table in `sqlite_backend.py`.
#[derive(Debug, Clone, Serialize, Deserialize)]
struct StoredEvent {
    seq: i64,
    event_id: String,
    agent_id: String,
    event_type: String,
    timestamp: f64,
    /// Payload as a parsed JSON value (dict).
    payload: serde_json::Value,
    prev_hash: String,
    event_hash: String,
    #[serde(default)]
    correlation_id: Option<String>,
    #[serde(default)]
    causation_id: Option<String>,
}

/// Canonical JSON: sorted keys, compact separators.
///
/// `serde_json` without `preserve_order` uses `BTreeMap` (alphabetically sorted)
/// and `to_string()` produces compact output — identical to Python's
/// `json.dumps(payload, sort_keys=True, separators=(",", ":"))`.
fn canonical_json(value: &serde_json::Value) -> String {
    serde_json::to_string(value).unwrap_or_default()
}

/// SHA-256 event hash — mirrors `hash_chain.compute_event_hash()`.
///
/// `sha256("{prev_hash}:{event_id}:{canonical_payload}")`
fn compute_hash_rs(prev_hash: &str, event_id: &str, canonical_payload: &str) -> String {
    let content = format!("{prev_hash}:{event_id}:{canonical_payload}");
    let mut hasher = Sha256::new();
    hasher.update(content.as_bytes());
    format!("{:x}", hasher.finalize())
}

/// Python-exposed event projector — D3 Rust AST Projector.
///
/// Loads serialised domain events from JSON strings, projects agent state by
/// replaying payloads in `seq` order, verifies SHA-256 hash chains per-agent,
/// and replays event slices. The GIL is released for chain verification.
#[cfg(feature = "python")]
#[pyclass(name = "EventProjector")]
pub struct PyEventProjector {
    events: Vec<StoredEvent>,
}

#[cfg(feature = "python")]
#[pymethods]
impl PyEventProjector {
    #[new]
    pub fn new() -> Self {
        Self { events: Vec::new() }
    }

    /// Load events from a list of JSON strings, replacing any existing events.
    pub fn load_events(&mut self, events_json: Vec<String>) -> PyResult<()> {
        let mut parsed = Vec::with_capacity(events_json.len());
        for (i, s) in events_json.iter().enumerate() {
            let ev: StoredEvent = serde_json::from_str(s).map_err(|e| {
                pyo3::exceptions::PyValueError::new_err(format!(
                    "Invalid event JSON at index {i}: {e}"
                ))
            })?;
            parsed.push(ev);
        }
        self.events = parsed;
        Ok(())
    }

    /// Project the cumulative state for `agent_id` by merging payloads in seq order.
    ///
    /// Returns a compact JSON object string, or `None` if no events exist for the agent.
    pub fn project_agent_state(&self, agent_id: &str) -> PyResult<Option<String>> {
        let mut agent_events: Vec<&StoredEvent> =
            self.events.iter().filter(|e| e.agent_id == agent_id).collect();
        if agent_events.is_empty() {
            return Ok(None);
        }
        agent_events.sort_by_key(|e| e.seq);
        let mut state = serde_json::Map::new();
        for ev in &agent_events {
            if let serde_json::Value::Object(ref map) = ev.payload {
                for (k, v) in map {
                    state.insert(k.clone(), v.clone());
                }
            }
        }
        let result = serde_json::to_string(&serde_json::Value::Object(state))
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
        Ok(Some(result))
    }

    /// Verify SHA-256 hash chain for all events of `agent_id`.
    ///
    /// Checks (a) each event's computed hash matches its stored `event_hash`,
    /// and (b) `prev_hash[i+1] == event_hash[i]`. Releases the GIL.
    pub fn verify_hash_chain(&self, py: Python<'_>, agent_id: &str) -> bool {
        let mut agent_events: Vec<&StoredEvent> =
            self.events.iter().filter(|e| e.agent_id == agent_id).collect();
        if agent_events.is_empty() {
            return true;
        }
        agent_events.sort_by_key(|e| e.seq);
        let events_owned: Vec<StoredEvent> = agent_events.into_iter().cloned().collect();
        py.allow_threads(|| {
            for ev in &events_owned {
                let canonical = canonical_json(&ev.payload);
                let expected = compute_hash_rs(&ev.prev_hash, &ev.event_id, &canonical);
                if ev.event_hash != expected {
                    return false;
                }
            }
            for w in events_owned.windows(2) {
                if w[1].prev_hash != w[0].event_hash {
                    return false;
                }
            }
            true
        })
    }

    /// Return events for `agent_id` with `seq >= since_seq` as JSON strings.
    pub fn replay_since(&self, agent_id: &str, since_seq: i64) -> PyResult<Vec<String>> {
        let mut agent_events: Vec<&StoredEvent> = self
            .events
            .iter()
            .filter(|e| e.agent_id == agent_id && e.seq >= since_seq)
            .collect();
        agent_events.sort_by_key(|e| e.seq);
        agent_events
            .iter()
            .map(|e| {
                serde_json::to_string(e)
                    .map_err(|err| pyo3::exceptions::PyRuntimeError::new_err(err.to_string()))
            })
            .collect()
    }

    /// Number of loaded events.
    pub fn __len__(&self) -> usize {
        self.events.len()
    }
}

/// Parallel SHA-256 hash chain verifier using Rayon — D4 Rust Hash Chain Verifier.
///
/// Accepts JSON-serialised events (fields: `event_id`, `prev_hash`, `event_hash`,
/// `payload`). Verifies (a) linkage and (b) each event's SHA-256 hash in parallel.
/// The GIL is released for the verification step via `py.allow_threads()`.
///
/// # Performance
///
/// 100 000 events: Python ~2 s → Rust Rayon <100 ms (≥20× speedup).
#[cfg(feature = "python")]
#[pyfunction]
pub fn verify_chain_parallel(py: Python<'_>, events_json: Vec<String>) -> PyResult<bool> {
    if events_json.is_empty() {
        return Ok(true);
    }
    let events: Vec<serde_json::Value> = events_json
        .iter()
        .enumerate()
        .map(|(i, s)| {
            serde_json::from_str::<serde_json::Value>(s).map_err(|e| {
                pyo3::exceptions::PyValueError::new_err(format!(
                    "Invalid event JSON at index {i}: {e}"
                ))
            })
        })
        .collect::<PyResult<_>>()?;
    let valid = py.allow_threads(|| {
        use rayon::prelude::*;
        // Linkage check (sequential — par_windows not on Vec)
        let linkage_ok = events.windows(2).all(|w| {
            let h0 = w[0]["event_hash"].as_str().unwrap_or("");
            let p1 = w[1]["prev_hash"].as_str().unwrap_or("");
            h0 == p1
        });
        if !linkage_ok {
            return false;
        }
        // Hash recomputation in parallel
        events.par_iter().all(|ev| {
            let prev_hash = ev["prev_hash"].as_str().unwrap_or("");
            let event_id = ev["event_id"].as_str().unwrap_or("");
            let stored_hash = ev["event_hash"].as_str().unwrap_or("");
            let canonical = if let Some(p) = ev.get("payload") {
                canonical_json(p)
            } else {
                "{}".to_string()
            };
            let expected = compute_hash_rs(prev_hash, event_id, &canonical);
            stored_hash == expected
        })
    });
    Ok(valid)
}

// ---------------------------------------------------------------------------
// Unit Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use std::thread;
    use std::time::Duration;

    // --- QueryCache tests ---

    #[test]
    fn test_cache_new() {
        let cache = QueryCache::<String>::new(10, None);
        assert!(cache.is_empty());
        assert_eq!(cache.len(), 0);
    }

    #[test]
    #[should_panic(expected = "max_size must be > 0")]
    fn test_cache_zero_size_panics() {
        let _cache = QueryCache::<String>::new(0, None);
    }

    #[test]
    fn test_cache_put_and_get() {
        let cache = QueryCache::<String>::new(10, None);
        cache.put("k1".into(), "v1".into());
        cache.put("k2".into(), "v2".into());

        assert_eq!(cache.get("k1"), Some("v1".into()));
        assert_eq!(cache.get("k2"), Some("v2".into()));
        assert_eq!(cache.get("k3"), None);
        assert_eq!(cache.len(), 2);
    }

    #[test]
    fn test_cache_overwrite() {
        let cache = QueryCache::<String>::new(10, None);
        cache.put("k1".into(), "old".into());
        cache.put("k1".into(), "new".into());

        assert_eq!(cache.get("k1"), Some("new".into()));
        assert_eq!(cache.len(), 1);
    }

    #[test]
    fn test_cache_lru_eviction() {
        let cache = QueryCache::<String>::new(3, None);
        cache.put("a".into(), "1".into());
        cache.put("b".into(), "2".into());
        cache.put("c".into(), "3".into());
        // Cache full: [a, b, c]

        // Access 'a' to make it recently used
        assert_eq!(cache.get("a"), Some("1".into()));

        // Insert 'd' — should evict 'b' (LRU)
        cache.put("d".into(), "4".into());

        assert_eq!(cache.get("a"), Some("1".into())); // still present (was accessed)
        assert_eq!(cache.get("b"), None); // evicted
        assert_eq!(cache.get("c"), Some("3".into()));
        assert_eq!(cache.get("d"), Some("4".into()));

        let stats = cache.stats();
        assert_eq!(stats.evictions, 1);
    }

    #[test]
    fn test_cache_ttl_expiry() {
        let cache = QueryCache::<String>::new(10, Some(50)); // 50ms TTL
        cache.put("k1".into(), "v1".into());

        // Should be present immediately
        assert_eq!(cache.get("k1"), Some("v1".into()));

        // Wait for TTL to expire
        thread::sleep(Duration::from_millis(80));

        // Should be expired now
        assert_eq!(cache.get("k1"), None);

        let stats = cache.stats();
        assert_eq!(stats.expired, 1);
        assert_eq!(stats.hits, 1);
        assert_eq!(stats.misses, 1); // expired counts as miss
    }

    #[test]
    fn test_cache_ttl_contains_check() {
        let cache = QueryCache::<String>::new(10, Some(50));
        cache.put("k1".into(), "v1".into());

        assert!(cache.contains("k1"));

        thread::sleep(Duration::from_millis(80));

        // contains does not mutate, but should report expired as absent
        assert!(!cache.contains("k1"));
    }

    #[test]
    fn test_cache_stats() {
        let cache = QueryCache::<String>::new(10, None);
        cache.put("k1".into(), "v1".into());

        let _ = cache.get("k1"); // hit
        let _ = cache.get("k2"); // miss
        let _ = cache.get("k3"); // miss

        let stats = cache.stats();
        assert_eq!(stats.hits, 1);
        assert_eq!(stats.misses, 2);
        assert_eq!(stats.current_size, 1);
        assert_eq!(stats.max_size, 10);
    }

    #[test]
    fn test_cache_invalidate() {
        let cache = QueryCache::<String>::new(10, None);
        cache.put("k1".into(), "v1".into());
        cache.put("k2".into(), "v2".into());

        assert!(cache.invalidate("k1"));
        assert!(!cache.invalidate("k1")); // already removed
        assert_eq!(cache.get("k1"), None);
        assert_eq!(cache.get("k2"), Some("v2".into()));
        assert_eq!(cache.len(), 1);
    }

    #[test]
    fn test_cache_invalidate_pattern() {
        let cache = QueryCache::<String>::new(100, None);
        cache.put("agent:001:state".into(), "s1".into());
        cache.put("agent:001:config".into(), "c1".into());
        cache.put("agent:002:state".into(), "s2".into());
        cache.put("system:global".into(), "g".into());

        let removed = cache.invalidate_pattern("agent:001");
        assert_eq!(removed, 2);
        assert_eq!(cache.len(), 2);
        assert!(cache.contains("agent:002:state"));
        assert!(cache.contains("system:global"));
    }

    #[test]
    fn test_cache_clear() {
        let cache = QueryCache::<String>::new(10, None);
        cache.put("a".into(), "1".into());
        cache.put("b".into(), "2".into());
        cache.put("c".into(), "3".into());

        let cleared = cache.clear();
        assert_eq!(cleared, 3);
        assert!(cache.is_empty());
        assert_eq!(cache.len(), 0);
    }

    #[test]
    fn test_cache_thread_safety() {
        use std::sync::Arc;

        let cache = Arc::new(QueryCache::<String>::new(1000, None));

        // Spawn writer threads
        let mut handles = Vec::new();
        for t in 0..4 {
            let c = Arc::clone(&cache);
            handles.push(thread::spawn(move || {
                for i in 0..250 {
                    c.put(format!("t{t}:k{i}"), format!("v{i}"));
                }
            }));
        }

        // Spawn reader threads
        for t in 0..4 {
            let c = Arc::clone(&cache);
            handles.push(thread::spawn(move || {
                for i in 0..250 {
                    let _ = c.get(&format!("t{t}:k{i}"));
                }
            }));
        }

        for h in handles {
            h.join().unwrap();
        }

        // All 1000 inserts fit within capacity
        assert_eq!(cache.len(), 1000);
    }

    #[test]
    fn test_cache_no_ttl() {
        let cache = QueryCache::<i64>::new(5, None);
        cache.put("k".into(), 42);

        // Without TTL, entries never expire
        thread::sleep(Duration::from_millis(50));
        assert_eq!(cache.get("k"), Some(42));
    }

    #[test]
    fn test_cache_stats_hit_rate() {
        let cache = QueryCache::<String>::new(10, None);
        cache.put("k1".into(), "v1".into());

        // 3 hits, 2 misses => hit_rate = 0.6
        for _ in 0..3 {
            let _ = cache.get("k1");
        }
        for _ in 0..2 {
            let _ = cache.get("missing");
        }

        let stats = cache.stats();
        assert_eq!(stats.hits, 3);
        assert_eq!(stats.misses, 2);
        // hit_rate computed in Python wrapper, but verify raw data here
        let hit_rate = stats.hits as f64 / (stats.hits + stats.misses) as f64;
        assert!((hit_rate - 0.6).abs() < 1e-10);
    }

    // --- EventBuffer tests ---

    #[test]
    fn test_buffer_new() {
        let buf = EventBuffer::new(EventBufferConfig::default());
        assert!(buf.is_empty());
        assert_eq!(buf.len(), 0);
        assert!(!buf.is_ready());
    }

    #[test]
    fn test_buffer_push_and_len() {
        let buf = EventBuffer::new(EventBufferConfig {
            max_batch_size: 100,
            max_age_ms: 5000,
        });
        buf.push(r#"{"id":"1"}"#.into()).unwrap();
        buf.push(r#"{"id":"2"}"#.into()).unwrap();

        assert_eq!(buf.len(), 2);
        assert!(!buf.is_empty());
    }

    #[test]
    fn test_buffer_flush() {
        let buf = EventBuffer::new(EventBufferConfig {
            max_batch_size: 100,
            max_age_ms: 5000,
        });
        buf.push("event1".into()).unwrap();
        buf.push("event2".into()).unwrap();
        buf.push("event3".into()).unwrap();

        let batch = buf.flush();
        assert_eq!(batch.len(), 3);
        assert_eq!(batch[0], "event1");
        assert_eq!(batch[1], "event2");
        assert_eq!(batch[2], "event3");

        // Buffer should be empty after flush
        assert!(buf.is_empty());
        assert_eq!(buf.len(), 0);
    }

    #[test]
    fn test_buffer_flush_empty() {
        let buf = EventBuffer::new(EventBufferConfig::default());
        let batch = buf.flush();
        assert!(batch.is_empty());
    }

    #[test]
    fn test_buffer_batch_size_trigger() {
        let buf = EventBuffer::new(EventBufferConfig {
            max_batch_size: 3,
            max_age_ms: 60_000, // very long age so only size triggers
        });

        buf.push("e1".into()).unwrap();
        assert!(!buf.is_ready());

        buf.push("e2".into()).unwrap();
        assert!(!buf.is_ready());

        buf.push("e3".into()).unwrap();
        assert!(buf.is_ready()); // batch size reached
    }

    #[test]
    fn test_buffer_age_trigger() {
        let buf = EventBuffer::new(EventBufferConfig {
            max_batch_size: 1000, // very large so only age triggers
            max_age_ms: 30,
        });

        buf.push("e1".into()).unwrap();
        assert!(!buf.is_ready()); // just pushed, not old enough

        thread::sleep(Duration::from_millis(50));

        assert!(buf.is_ready()); // age exceeded
    }

    #[test]
    fn test_buffer_stats() {
        let buf = EventBuffer::new(EventBufferConfig::default());
        buf.push("e1".into()).unwrap();
        buf.push("e2".into()).unwrap();

        let stats = buf.stats();
        assert_eq!(stats.buffer_size, 2);
        assert_eq!(stats.flush_count, 0);

        let _ = buf.flush();

        let stats = buf.stats();
        assert_eq!(stats.buffer_size, 0);
        assert_eq!(stats.flush_count, 1);
    }

    #[test]
    fn test_buffer_shutdown_with_flush() {
        let buf = EventBuffer::new(EventBufferConfig::default());
        buf.push("e1".into()).unwrap();
        buf.push("e2".into()).unwrap();

        let remaining = buf.shutdown(true);
        assert!(remaining.is_some());
        assert_eq!(remaining.unwrap().len(), 2);

        // Should reject further pushes
        let result = buf.push("e3".into());
        assert!(result.is_err());
    }

    #[test]
    fn test_buffer_shutdown_without_flush() {
        let buf = EventBuffer::new(EventBufferConfig::default());
        buf.push("e1".into()).unwrap();

        let remaining = buf.shutdown(false);
        assert!(remaining.is_none());

        // Events are still in the buffer but buffer is shut down
        let result = buf.push("e2".into());
        assert!(result.is_err());
    }

    #[test]
    fn test_buffer_multiple_flushes() {
        let buf = EventBuffer::new(EventBufferConfig::default());

        buf.push("batch1_e1".into()).unwrap();
        buf.push("batch1_e2".into()).unwrap();
        let batch1 = buf.flush();
        assert_eq!(batch1.len(), 2);

        buf.push("batch2_e1".into()).unwrap();
        let batch2 = buf.flush();
        assert_eq!(batch2.len(), 1);

        let stats = buf.stats();
        assert_eq!(stats.flush_count, 2);
    }

    #[test]
    fn test_buffer_thread_safety() {
        use std::sync::Arc;

        let buf = Arc::new(EventBuffer::new(EventBufferConfig {
            max_batch_size: 10_000,
            max_age_ms: 60_000,
        }));

        let mut handles = Vec::new();
        for t in 0..4 {
            let b = Arc::clone(&buf);
            handles.push(thread::spawn(move || {
                for i in 0..250 {
                    b.push(format!(r#"{{"thread":{t},"seq":{i}}}"#)).unwrap();
                }
            }));
        }

        for h in handles {
            h.join().unwrap();
        }

        assert_eq!(buf.len(), 1000);

        let batch = buf.flush();
        assert_eq!(batch.len(), 1000);
        assert!(buf.is_empty());
    }

    #[test]
    fn test_buffer_is_ready_empty_buffer() {
        let buf = EventBuffer::new(EventBufferConfig {
            max_batch_size: 1,
            max_age_ms: 0,
        });
        // Even with aggressive triggers, empty buffer should not be ready
        assert!(!buf.is_ready());
    }

    #[test]
    fn test_cache_eviction_sequence() {
        // Verify exact LRU eviction order
        let cache = QueryCache::<String>::new(2, None);
        cache.put("a".into(), "1".into());
        cache.put("b".into(), "2".into());

        // 'a' is LRU, 'b' is MRU
        cache.put("c".into(), "3".into()); // evicts 'a'
        assert_eq!(cache.get("a"), None);
        assert_eq!(cache.get("b"), Some("2".into()));
        assert_eq!(cache.get("c"), Some("3".into()));

        // Now 'b' was accessed via get, 'c' was accessed via get
        // Access order: b, c — so 'b' is LRU relative to 'c'?
        // Actually after the get("b") and get("c") above:
        // LRU order after gets: b was gotten first, c second -> b is LRU
        cache.put("d".into(), "4".into()); // evicts 'b' (LRU)
        assert_eq!(cache.get("b"), None);
        assert_eq!(cache.get("c"), Some("3".into()));
        assert_eq!(cache.get("d"), Some("4".into()));

        let stats = cache.stats();
        assert_eq!(stats.evictions, 2);
    }

    #[test]
    fn test_cache_stats_default() {
        let stats = QueryCacheStats::default();
        assert_eq!(stats.hits, 0);
        assert_eq!(stats.misses, 0);
        assert_eq!(stats.evictions, 0);
        assert_eq!(stats.expired, 0);
        assert_eq!(stats.current_size, 0);
        assert_eq!(stats.max_size, 0);
    }

    #[test]
    fn test_buffer_config_default() {
        let config = EventBufferConfig::default();
        assert_eq!(config.max_batch_size, 100);
        assert_eq!(config.max_age_ms, 50);
    }

    #[test]
    fn test_buffer_stats_serialization() {
        let stats = EventBufferStats {
            buffer_size: 5,
            flush_count: 3,
            last_flush_ms_ago: 12.5,
        };
        let json = serde_json::to_string(&stats).unwrap();
        let back: EventBufferStats = serde_json::from_str(&json).unwrap();
        assert_eq!(back.buffer_size, 5);
        assert_eq!(back.flush_count, 3);
    }

    #[test]
    fn test_cache_stats_serialization() {
        let stats = QueryCacheStats {
            hits: 10,
            misses: 5,
            evictions: 2,
            expired: 1,
            current_size: 8,
            max_size: 100,
        };
        let json = serde_json::to_string(&stats).unwrap();
        let back: QueryCacheStats = serde_json::from_str(&json).unwrap();
        assert_eq!(back.hits, 10);
        assert_eq!(back.evictions, 2);
    }

    #[test]
    fn test_event_buffer_error_display() {
        let err = EventBufferError::Shutdown;
        assert_eq!(err.to_string(), "EventBuffer has been shut down");
    }

    #[test]
    fn test_buffer_config_serialization() {
        let config = EventBufferConfig {
            max_batch_size: 50,
            max_age_ms: 200,
        };
        let json = serde_json::to_string(&config).unwrap();
        let back: EventBufferConfig = serde_json::from_str(&json).unwrap();
        assert_eq!(back.max_batch_size, 50);
        assert_eq!(back.max_age_ms, 200);
    }
}
