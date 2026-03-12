//! GeneratorGraph — DAG implementation for ACO generator orchestration.
//!
//! Rust equivalent of `scripts/aco/generator_graph.py` (285 lines Python).
//! Uses `petgraph` for graph operations instead of manual adjacency lists.
//!
//! # Performance
//!
//! - Topological sort: O(V + E) via petgraph::algo::toposort
//! - Critical path: O(V + E) via DP over topological order
//! - Parallelizable detection: O(V + E) via BFS level assignment
//! - All operations are deterministic (sorted output for same input)

use std::collections::{BTreeMap, BTreeSet, HashMap};

use petgraph::algo::toposort;
use petgraph::graph::{DiGraph, NodeIndex};
#[cfg(feature = "python")]
use pyo3::prelude::*;
use sha2::{Digest, Sha256};

use super::models::{GeneratorGraphModel, GeneratorNode};

/// Mutable builder for GeneratorGraph — validates and freezes to immutable model.
///
/// Supports dynamic node addition for auto-expansion when validation
/// detects missing generators. All graph operations maintain DAG invariant.
pub struct MutableGeneratorGraph {
    /// petgraph directed graph
    graph: DiGraph<String, ()>,
    /// Map from node ID to petgraph NodeIndex
    index_map: HashMap<String, NodeIndex>,
    /// Map from node ID to GeneratorNode data
    nodes: BTreeMap<String, GeneratorNode>,
}

impl MutableGeneratorGraph {
    /// Create an empty graph.
    pub fn new() -> Self {
        Self {
            graph: DiGraph::new(),
            index_map: HashMap::new(),
            nodes: BTreeMap::new(),
        }
    }

    /// Number of nodes in the graph.
    pub fn len(&self) -> usize {
        self.nodes.len()
    }

    /// Whether the graph is empty.
    pub fn is_empty(&self) -> bool {
        self.nodes.is_empty()
    }

    /// Add a generator node to the graph.
    ///
    /// # Errors
    ///
    /// Returns error if node ID already exists.
    pub fn add_node(&mut self, node: GeneratorNode) -> Result<(), GraphError> {
        if self.nodes.contains_key(&node.id) {
            return Err(GraphError::DuplicateNode(node.id.clone()));
        }

        let idx = self.graph.add_node(node.id.clone());
        self.index_map.insert(node.id.clone(), idx);

        // Add edges for declared dependencies
        for dep in &node.depends_on {
            if let Some(&dep_idx) = self.index_map.get(dep) {
                self.graph.add_edge(dep_idx, idx, ());
            }
            // Note: dependencies on not-yet-added nodes are validated in validate_dependencies()
        }

        self.nodes.insert(node.id.clone(), node);
        Ok(())
    }

    /// Remove a generator node from the graph.
    ///
    /// # Errors
    ///
    /// Returns error if node does not exist.
    pub fn remove_node(&mut self, node_id: &str) -> Result<GeneratorNode, GraphError> {
        let idx = self
            .index_map
            .remove(node_id)
            .ok_or_else(|| GraphError::NodeNotFound(node_id.to_string()))?;

        self.graph.remove_node(idx);
        // Note: petgraph invalidates indices on removal, rebuild index_map
        self.rebuild_index_map();

        self.nodes
            .remove(node_id)
            .ok_or_else(|| GraphError::NodeNotFound(node_id.to_string()))
    }

    /// Verify that the graph has no cycles.
    pub fn validate_acyclic(&self) -> Result<(), GraphError> {
        match toposort(&self.graph, None) {
            Ok(_) => Ok(()),
            Err(_) => Err(GraphError::CycleDetected),
        }
    }

    /// Kahn's algorithm via petgraph — returns deterministic execution order.
    ///
    /// Output is sorted for determinism: same input graph = same output order.
    pub fn topological_sort(&self) -> Result<Vec<String>, GraphError> {
        let sorted = toposort(&self.graph, None).map_err(|_| GraphError::CycleDetected)?;

        // Convert NodeIndex back to node IDs
        let result: Vec<String> = sorted
            .iter()
            .filter_map(|idx| self.graph.node_weight(*idx))
            .cloned()
            .collect();

        Ok(result)
    }

    /// Group nodes by BFS level — same level = parallelizable.
    ///
    /// Returns list of groups where each group contains node IDs that
    /// can execute in parallel. Only groups with 2+ nodes returned.
    pub fn detect_parallelizable(&self) -> Result<Vec<Vec<String>>, GraphError> {
        let all_levels = self.get_all_levels()?;
        Ok(all_levels
            .into_iter()
            .filter(|group| group.len() > 1)
            .collect())
    }

    /// Group all nodes by BFS level — for complete execution plan.
    ///
    /// Returns list of groups ordered by level, including single-node groups.
    pub fn get_all_levels(&self) -> Result<Vec<Vec<String>>, GraphError> {
        let order = self.topological_sort()?;
        let mut levels: HashMap<String, usize> = HashMap::new();

        for nid in &order {
            if let Some(node) = self.nodes.get(nid) {
                let max_dep_level = node
                    .depends_on
                    .iter()
                    .filter_map(|d| levels.get(d))
                    .max()
                    .copied()
                    .map(|l| l + 1)
                    .unwrap_or(0);
                levels.insert(nid.clone(), max_dep_level);
            }
        }

        // Group by level
        let mut level_groups: BTreeMap<usize, Vec<String>> = BTreeMap::new();
        for (nid, lvl) in &levels {
            level_groups.entry(*lvl).or_default().push(nid.clone());
        }

        // Sort within each level for determinism
        Ok(level_groups
            .into_values()
            .map(|mut group| {
                group.sort();
                group
            })
            .collect())
    }

    /// Longest path via dynamic programming.
    ///
    /// Returns list of node IDs forming the longest dependency chain.
    pub fn get_critical_path(&self) -> Result<Vec<String>, GraphError> {
        if self.nodes.is_empty() {
            return Ok(vec![]);
        }

        let order = self.topological_sort()?;
        let mut dp: HashMap<String, Vec<String>> = HashMap::new();

        for nid in &order {
            dp.insert(nid.clone(), vec![nid.clone()]);
        }

        for nid in &order {
            if let Some(node) = self.nodes.get(nid) {
                for dep in &node.depends_on {
                    if let Some(dep_path) = dp.get(dep).cloned() {
                        let mut candidate = dep_path;
                        candidate.push(nid.clone());
                        if candidate.len() > dp[nid].len() {
                            dp.insert(nid.clone(), candidate);
                        }
                    }
                }
            }
        }

        Ok(dp
            .into_values()
            .max_by_key(|path| path.len())
            .unwrap_or_default())
    }

    /// Get all direct dependents (successors) of a node.
    pub fn get_dependents(&self, node_id: &str) -> Result<BTreeSet<String>, GraphError> {
        let idx = self
            .index_map
            .get(node_id)
            .ok_or_else(|| GraphError::NodeNotFound(node_id.to_string()))?;

        let successors: BTreeSet<String> = self
            .graph
            .neighbors_directed(*idx, petgraph::Direction::Outgoing)
            .filter_map(|i| self.graph.node_weight(i))
            .cloned()
            .collect();

        Ok(successors)
    }

    /// Get all direct dependencies (predecessors) of a node.
    pub fn get_dependencies(&self, node_id: &str) -> Result<Vec<String>, GraphError> {
        let node = self
            .nodes
            .get(node_id)
            .ok_or_else(|| GraphError::NodeNotFound(node_id.to_string()))?;
        Ok(node.depends_on.clone())
    }

    /// Verify all contracts are fully defined.
    ///
    /// Returns list of violation messages. Empty = all contracts valid.
    pub fn validate_contracts(&self) -> Vec<String> {
        let mut violations = Vec::new();
        for (nid, node) in &self.nodes {
            if node.contract.precondition.is_empty() {
                violations.push(format!("{nid}: missing precondition"));
            }
            if node.contract.postcondition.is_empty() {
                violations.push(format!("{nid}: missing postcondition"));
            }
            if node.contract.invariant.is_empty() {
                violations.push(format!("{nid}: missing invariant"));
            }
            if node.outputs.rollback_script.is_empty() {
                violations.push(format!(
                    "{nid}: missing rollback_script (triad mandatory)"
                ));
            }
        }
        violations
    }

    /// Verify all declared dependencies reference existing nodes.
    pub fn validate_dependencies(&self) -> Vec<String> {
        let known: BTreeSet<&str> = self.nodes.keys().map(String::as_str).collect();
        let mut violations = Vec::new();
        for (nid, node) in &self.nodes {
            for dep in &node.depends_on {
                if !known.contains(dep.as_str()) {
                    violations.push(format!("{nid}: depends on unknown node '{dep}'"));
                }
            }
        }
        violations
    }

    /// Validate and convert to immutable GeneratorGraphModel.
    ///
    /// # Errors
    ///
    /// Returns error if graph has cycles or unresolved dependencies.
    pub fn freeze(&self, objective_hash: Option<&str>) -> Result<GeneratorGraphModel, GraphError> {
        // Validate before freezing
        let dep_violations = self.validate_dependencies();
        if !dep_violations.is_empty() {
            return Err(GraphError::UnresolvedDependencies(dep_violations));
        }

        let sort_order = self.topological_sort()?;
        let critical = self.get_critical_path()?;
        let parallel = self.detect_parallelizable()?;

        let hash = match objective_hash {
            Some(h) => h.to_string(),
            None => {
                let mut hasher = Sha256::new();
                hasher.update(format!("{sort_order:?}"));
                format!("{:.16x}", hasher.finalize())
            }
        };

        let nodes: Vec<GeneratorNode> = sort_order
            .iter()
            .filter_map(|nid| self.nodes.get(nid))
            .cloned()
            .collect();

        Ok(GeneratorGraphModel {
            nodes,
            critical_path: critical,
            parallelizable: parallel,
            objective_hash: hash,
        })
    }

    /// Rebuild the petgraph index map after node removal.
    fn rebuild_index_map(&mut self) {
        self.graph = DiGraph::new();
        self.index_map.clear();

        // Re-add all nodes
        for nid in self.nodes.keys() {
            let idx = self.graph.add_node(nid.clone());
            self.index_map.insert(nid.clone(), idx);
        }

        // Re-add all edges
        for (nid, node) in &self.nodes {
            if let Some(&to_idx) = self.index_map.get(nid) {
                for dep in &node.depends_on {
                    if let Some(&from_idx) = self.index_map.get(dep) {
                        self.graph.add_edge(from_idx, to_idx, ());
                    }
                }
            }
        }
    }
}

impl Default for MutableGeneratorGraph {
    fn default() -> Self {
        Self::new()
    }
}

/// Errors that can occur during graph operations.
#[derive(Debug, Clone)]
pub enum GraphError {
    /// Node ID already exists in the graph.
    DuplicateNode(String),
    /// Node ID not found in the graph.
    NodeNotFound(String),
    /// Cycle detected — DAG invariant violated.
    CycleDetected,
    /// Unresolved dependencies found.
    UnresolvedDependencies(Vec<String>),
}

impl std::fmt::Display for GraphError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::DuplicateNode(id) => write!(f, "Duplicate node ID: {id}"),
            Self::NodeNotFound(id) => write!(f, "Node not found: {id}"),
            Self::CycleDetected => {
                write!(f, "Cycle detected in GeneratorGraph — DAG invariant violated")
            }
            Self::UnresolvedDependencies(deps) => {
                write!(f, "Unresolved dependencies: {}", deps.join("; "))
            }
        }
    }
}

impl std::error::Error for GraphError {}

// --- PyO3 Wrapper ---

#[cfg(feature = "python")]
#[pyclass(name = "AcoGraph")]
pub struct PyAcoGraph {
    inner: MutableGeneratorGraph,
}

#[cfg(feature = "python")]
#[pymethods]
impl PyAcoGraph {
    #[new]
    fn new() -> Self {
        Self {
            inner: MutableGeneratorGraph::new(),
        }
    }

    /// Number of nodes.
    fn __len__(&self) -> usize {
        self.inner.len()
    }

    /// Add a generator node.
    fn add_node(&mut self, node: GeneratorNode) -> PyResult<()> {
        self.inner
            .add_node(node)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
    }

    /// Remove a generator node.
    fn remove_node(&mut self, node_id: &str) -> PyResult<GeneratorNode> {
        self.inner
            .remove_node(node_id)
            .map_err(|e| pyo3::exceptions::PyKeyError::new_err(e.to_string()))
    }

    /// Topological sort — deterministic execution order.
    fn topological_sort(&self) -> PyResult<Vec<String>> {
        self.inner
            .topological_sort()
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
    }

    /// Groups that can run in parallel (2+ nodes per group).
    fn detect_parallelizable(&self) -> PyResult<Vec<Vec<String>>> {
        self.inner
            .detect_parallelizable()
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
    }

    /// All execution levels (including single-node groups).
    fn get_all_levels(&self) -> PyResult<Vec<Vec<String>>> {
        self.inner
            .get_all_levels()
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
    }

    /// Longest dependency chain.
    fn get_critical_path(&self) -> PyResult<Vec<String>> {
        self.inner
            .get_critical_path()
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
    }

    /// Validate DAG invariant (no cycles).
    fn validate_acyclic(&self) -> PyResult<bool> {
        self.inner
            .validate_acyclic()
            .map(|()| true)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
    }

    /// Validate all contracts are complete.
    fn validate_contracts(&self) -> Vec<String> {
        self.inner.validate_contracts()
    }

    /// Validate all dependencies reference existing nodes.
    fn validate_dependencies(&self) -> Vec<String> {
        self.inner.validate_dependencies()
    }

    /// Freeze to immutable GeneratorGraphModel.
    fn freeze(&self, objective_hash: Option<String>) -> PyResult<GeneratorGraphModel> {
        self.inner
            .freeze(objective_hash.as_deref())
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
    }
}

// --- Unit Tests ---

#[cfg(test)]
mod tests {
    use super::*;
    use crate::aco::models::{GeneratorContract, GeneratorOutputs, GeneratorType};

    fn make_node(id: &str, depends_on: Vec<&str>) -> GeneratorNode {
        GeneratorNode {
            id: id.to_string(),
            description: format!("Node {id}"),
            generator_type: GeneratorType::Template,
            inputs_data: vec![],
            inputs_templates: vec![],
            inputs_constraints: vec![],
            outputs: GeneratorOutputs {
                execution_script: format!("exec_{id}.py"),
                validation_script: format!("val_{id}.py"),
                rollback_script: format!("rb_{id}.py"),
            },
            contract: GeneratorContract {
                precondition: "pre".into(),
                postcondition: "post".into(),
                invariant: "inv".into(),
            },
            acceptance_criteria: "tests pass".into(),
            depends_on: depends_on.into_iter().map(String::from).collect(),
        }
    }

    #[test]
    fn test_empty_graph() {
        let g = MutableGeneratorGraph::new();
        assert!(g.is_empty());
        assert_eq!(g.len(), 0);
    }

    #[test]
    fn test_add_and_count_nodes() {
        let mut g = MutableGeneratorGraph::new();
        g.add_node(make_node("A", vec![])).unwrap();
        g.add_node(make_node("B", vec!["A"])).unwrap();
        g.add_node(make_node("C", vec!["A"])).unwrap();
        assert_eq!(g.len(), 3);
    }

    #[test]
    fn test_duplicate_node_error() {
        let mut g = MutableGeneratorGraph::new();
        g.add_node(make_node("A", vec![])).unwrap();
        let err = g.add_node(make_node("A", vec![]));
        assert!(err.is_err());
        assert!(matches!(err.unwrap_err(), GraphError::DuplicateNode(_)));
    }

    #[test]
    fn test_topological_sort_linear() {
        let mut g = MutableGeneratorGraph::new();
        g.add_node(make_node("A", vec![])).unwrap();
        g.add_node(make_node("B", vec!["A"])).unwrap();
        g.add_node(make_node("C", vec!["B"])).unwrap();

        let order = g.topological_sort().unwrap();
        assert_eq!(order, vec!["A", "B", "C"]);
    }

    #[test]
    fn test_topological_sort_diamond() {
        // A → B, A → C, B → D, C → D
        let mut g = MutableGeneratorGraph::new();
        g.add_node(make_node("A", vec![])).unwrap();
        g.add_node(make_node("B", vec!["A"])).unwrap();
        g.add_node(make_node("C", vec!["A"])).unwrap();
        g.add_node(make_node("D", vec!["B", "C"])).unwrap();

        let order = g.topological_sort().unwrap();
        // A must come first, D must come last
        assert_eq!(order[0], "A");
        assert_eq!(order[3], "D");
        // B and C can be in either order but both before D
        let b_pos = order.iter().position(|x| x == "B").unwrap();
        let c_pos = order.iter().position(|x| x == "C").unwrap();
        assert!(b_pos < 3);
        assert!(c_pos < 3);
    }

    #[test]
    fn test_critical_path_linear() {
        let mut g = MutableGeneratorGraph::new();
        g.add_node(make_node("A", vec![])).unwrap();
        g.add_node(make_node("B", vec!["A"])).unwrap();
        g.add_node(make_node("C", vec!["B"])).unwrap();

        let path = g.get_critical_path().unwrap();
        assert_eq!(path, vec!["A", "B", "C"]);
    }

    #[test]
    fn test_critical_path_diamond() {
        let mut g = MutableGeneratorGraph::new();
        g.add_node(make_node("A", vec![])).unwrap();
        g.add_node(make_node("B", vec!["A"])).unwrap();
        g.add_node(make_node("C", vec!["A"])).unwrap();
        g.add_node(make_node("D", vec!["B", "C"])).unwrap();

        let path = g.get_critical_path().unwrap();
        // Longest path: A → B → D or A → C → D (both length 3)
        assert_eq!(path.len(), 3);
        assert_eq!(path[0], "A");
        assert_eq!(path[2], "D");
    }

    #[test]
    fn test_parallelizable_diamond() {
        let mut g = MutableGeneratorGraph::new();
        g.add_node(make_node("A", vec![])).unwrap();
        g.add_node(make_node("B", vec!["A"])).unwrap();
        g.add_node(make_node("C", vec!["A"])).unwrap();
        g.add_node(make_node("D", vec!["B", "C"])).unwrap();

        let parallel = g.detect_parallelizable().unwrap();
        // B and C are parallelizable
        assert_eq!(parallel.len(), 1);
        assert!(parallel[0].contains(&"B".to_string()));
        assert!(parallel[0].contains(&"C".to_string()));
    }

    #[test]
    fn test_all_levels() {
        let mut g = MutableGeneratorGraph::new();
        g.add_node(make_node("A", vec![])).unwrap();
        g.add_node(make_node("B", vec!["A"])).unwrap();
        g.add_node(make_node("C", vec!["A"])).unwrap();
        g.add_node(make_node("D", vec!["B", "C"])).unwrap();

        let levels = g.get_all_levels().unwrap();
        assert_eq!(levels.len(), 3); // Level 0: [A], Level 1: [B, C], Level 2: [D]
        assert_eq!(levels[0], vec!["A"]);
        assert_eq!(levels[1], vec!["B", "C"]);
        assert_eq!(levels[2], vec!["D"]);
    }

    #[test]
    fn test_validate_contracts() {
        let mut g = MutableGeneratorGraph::new();
        let mut node = make_node("A", vec![]);
        node.contract.precondition = String::new(); // Missing precondition
        g.add_node(node).unwrap();

        let violations = g.validate_contracts();
        assert_eq!(violations.len(), 1);
        assert!(violations[0].contains("missing precondition"));
    }

    #[test]
    fn test_validate_dependencies_unknown() {
        let mut g = MutableGeneratorGraph::new();
        g.add_node(make_node("A", vec!["NONEXISTENT"])).unwrap();

        let violations = g.validate_dependencies();
        assert_eq!(violations.len(), 1);
        assert!(violations[0].contains("unknown node 'NONEXISTENT'"));
    }

    #[test]
    fn test_freeze_success() {
        let mut g = MutableGeneratorGraph::new();
        g.add_node(make_node("A", vec![])).unwrap();
        g.add_node(make_node("B", vec!["A"])).unwrap();

        let frozen = g.freeze(Some("test_hash")).unwrap();
        assert_eq!(frozen.nodes.len(), 2);
        assert_eq!(frozen.objective_hash, "test_hash");
        assert_eq!(frozen.nodes[0].id, "A");
        assert_eq!(frozen.nodes[1].id, "B");
    }

    #[test]
    fn test_freeze_rejects_unresolved() {
        let mut g = MutableGeneratorGraph::new();
        g.add_node(make_node("A", vec!["MISSING"])).unwrap();

        let result = g.freeze(None);
        assert!(result.is_err());
    }

    #[test]
    fn test_remove_node() {
        let mut g = MutableGeneratorGraph::new();
        g.add_node(make_node("A", vec![])).unwrap();
        g.add_node(make_node("B", vec![])).unwrap();
        assert_eq!(g.len(), 2);

        g.remove_node("A").unwrap();
        assert_eq!(g.len(), 1);

        let err = g.remove_node("A");
        assert!(err.is_err());
    }

    #[test]
    fn test_get_dependents() {
        let mut g = MutableGeneratorGraph::new();
        g.add_node(make_node("A", vec![])).unwrap();
        g.add_node(make_node("B", vec!["A"])).unwrap();
        g.add_node(make_node("C", vec!["A"])).unwrap();

        let deps = g.get_dependents("A").unwrap();
        assert!(deps.contains("B"));
        assert!(deps.contains("C"));
        assert_eq!(deps.len(), 2);
    }

    #[test]
    fn test_empty_graph_critical_path() {
        let g = MutableGeneratorGraph::new();
        let path = g.get_critical_path().unwrap();
        assert!(path.is_empty());
    }

    #[test]
    fn test_single_node_graph() {
        let mut g = MutableGeneratorGraph::new();
        g.add_node(make_node("SOLO", vec![])).unwrap();

        let order = g.topological_sort().unwrap();
        assert_eq!(order, vec!["SOLO"]);

        let path = g.get_critical_path().unwrap();
        assert_eq!(path, vec!["SOLO"]);

        let parallel = g.detect_parallelizable().unwrap();
        assert!(parallel.is_empty()); // No parallelism with 1 node
    }

    #[test]
    fn test_wide_graph_parallelism() {
        // All nodes independent → all at level 0
        let mut g = MutableGeneratorGraph::new();
        for i in 0..5 {
            g.add_node(make_node(&format!("N{i}"), vec![])).unwrap();
        }

        let parallel = g.detect_parallelizable().unwrap();
        assert_eq!(parallel.len(), 1); // One group with all 5
        assert_eq!(parallel[0].len(), 5);
    }
}
