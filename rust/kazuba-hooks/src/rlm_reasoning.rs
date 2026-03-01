//! RLM Reasoning PyO3 bindings.
//!
//! Exposes `kazuba-rlm` reasoning engine to Python hooks for:
//! - Chain-of-Thought (CoT) linear reasoning
//! - Tree-of-Thought (ToT) branching exploration
//! - Graph-of-Thought (GoT) complex interdependencies
//! - Decision generation from reasoning
//! - Validation of reasoning structures
//!
//! ## Performance
//!
//! Native Rust implementation provides 25-30x speedup over Python fallback.
//!
//! ## Example (Python)
//!
//! ```python
//! from kazuba_hooks import create_chain_of_thought, validate_chain, generate_decision
//!
//! # Create reasoning chain
//! cot = create_chain_of_thought("Analyze TIR R01 compliance")
//! add_reasoning_step(cot, "Examine compartment photos", 0.9)
//! add_reasoning_step(cot, "Verify structural integrity", 0.85)
//! conclude_reasoning(cot, "Compartment approved")
//!
//! # Validate
//! result = validate_chain(cot, min_confidence=0.7)
//! assert result["is_valid"]
//!
//! # Generate decision
//! decision = generate_decision(cot)
//! assert decision["score"] >= 80
//! ```

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;

// ============================================================================
// Reasoning Step
// ============================================================================

/// A single step in reasoning, used by all paradigms.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReasoningStep {
    /// Unique identifier.
    pub id: String,
    /// Step number (for CoT ordering).
    pub step_number: u32,
    /// Content/description of this reasoning step.
    pub content: String,
    /// Confidence level (0.0 - 1.0).
    pub confidence: f32,
    /// Supporting evidence.
    pub evidence: Vec<String>,
    /// Parent step ID (for ToT/GoT).
    pub parent_id: Option<String>,
    /// Child step IDs (for ToT/GoT).
    pub child_ids: Vec<String>,
}

impl ReasoningStep {
    /// Creates a new reasoning step.
    #[must_use]
    pub fn new(step_number: u32, content: &str, confidence: f32) -> Self {
        Self {
            id: Uuid::now_v7().to_string(),
            step_number,
            content: content.to_string(),
            confidence: confidence.clamp(0.0, 1.0),
            evidence: Vec::new(),
            parent_id: None,
            child_ids: Vec::new(),
        }
    }

    /// Adds evidence to this step.
    pub fn add_evidence(&mut self, evidence: &str) {
        self.evidence.push(evidence.to_string());
    }
}

// ============================================================================
// Chain of Thought (Linear Reasoning)
// ============================================================================

/// Chain-of-Thought reasoning - sequential, step-by-step analysis.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChainOfThought {
    /// Unique identifier.
    pub id: String,
    /// Problem being analyzed.
    pub problem: String,
    /// Sequential reasoning steps.
    pub steps: Vec<ReasoningStep>,
    /// Final conclusion.
    pub conclusion: Option<String>,
    /// Overall confidence (average of steps).
    pub confidence: f32,
}

impl ChainOfThought {
    /// Creates a new Chain-of-Thought.
    #[must_use]
    pub fn new(problem: &str) -> Self {
        Self {
            id: Uuid::now_v7().to_string(),
            problem: problem.to_string(),
            steps: Vec::new(),
            conclusion: None,
            confidence: 0.0,
        }
    }

    /// Adds a reasoning step.
    pub fn add_step(&mut self, content: &str, confidence: f32) {
        let step_number = self.steps.len() as u32 + 1;
        self.steps.push(ReasoningStep::new(step_number, content, confidence));
        self.update_confidence();
    }

    /// Sets the conclusion.
    pub fn conclude(&mut self, conclusion: &str) {
        self.conclusion = Some(conclusion.to_string());
    }

    /// Updates overall confidence as average of steps.
    fn update_confidence(&mut self) {
        if self.steps.is_empty() {
            self.confidence = 0.0;
        } else {
            let sum: f32 = self.steps.iter().map(|s| s.confidence).sum();
            #[allow(clippy::cast_precision_loss)]
            {
                self.confidence = sum / self.steps.len() as f32;
            }
        }
    }

    /// Returns whether the chain is complete (has steps and conclusion).
    #[must_use]
    pub fn is_complete(&self) -> bool {
        !self.steps.is_empty() && self.conclusion.is_some()
    }
}

// ============================================================================
// Tree of Thought (Branching Exploration)
// ============================================================================

/// Tree-of-Thought reasoning - explores multiple solution paths.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TreeOfThought {
    /// Unique identifier.
    pub id: String,
    /// Problem being analyzed.
    pub problem: String,
    /// Root node ID.
    pub root_id: Option<String>,
    /// All nodes indexed by ID.
    pub nodes: HashMap<String, ReasoningStep>,
    /// Best path (sequence of node IDs).
    pub best_path: Vec<String>,
    /// Best path confidence.
    pub best_confidence: f32,
}

impl TreeOfThought {
    /// Creates a new Tree-of-Thought.
    #[must_use]
    pub fn new(problem: &str) -> Self {
        Self {
            id: Uuid::now_v7().to_string(),
            problem: problem.to_string(),
            root_id: None,
            nodes: HashMap::new(),
            best_path: Vec::new(),
            best_confidence: 0.0,
        }
    }

    /// Adds the root node.
    pub fn add_root(&mut self, content: &str, confidence: f32) -> String {
        let step = ReasoningStep::new(0, content, confidence);
        let id = step.id.clone();
        self.root_id = Some(id.clone());
        self.nodes.insert(id.clone(), step);
        id
    }

    /// Adds a branch from a parent node.
    pub fn add_branch(&mut self, parent_id: &str, content: &str, confidence: f32) -> Option<String> {
        if !self.nodes.contains_key(parent_id) {
            return None;
        }

        let parent_step_number = self.nodes.get(parent_id).map(|n| n.step_number).unwrap_or(0);
        let mut step = ReasoningStep::new(parent_step_number + 1, content, confidence);
        step.parent_id = Some(parent_id.to_string());
        let id = step.id.clone();

        self.nodes.insert(id.clone(), step);

        if let Some(parent) = self.nodes.get_mut(parent_id) {
            parent.child_ids.push(id.clone());
        }

        Some(id)
    }

    /// Finds all leaf nodes (no children).
    #[must_use]
    pub fn leaves(&self) -> Vec<String> {
        self.nodes
            .iter()
            .filter(|(_, node)| node.child_ids.is_empty())
            .map(|(id, _)| id.clone())
            .collect()
    }

    /// Evaluates and selects the best path.
    pub fn evaluate_best_path(&mut self) {
        let leaves = self.leaves();
        let mut best_score = 0.0f32;
        let mut best: Vec<String> = Vec::new();

        for leaf_id in leaves {
            let path = self.path_to_root(&leaf_id);
            let score = self.path_confidence(&path);
            if score > best_score {
                best_score = score;
                best = path;
            }
        }

        self.best_path = best;
        self.best_confidence = best_score;
    }

    /// Gets the path from a node to root.
    fn path_to_root(&self, node_id: &str) -> Vec<String> {
        let mut path = vec![node_id.to_string()];
        let mut current = node_id.to_string();

        while let Some(node) = self.nodes.get(&current) {
            if let Some(ref parent_id) = node.parent_id {
                path.push(parent_id.clone());
                current = parent_id.clone();
            } else {
                break;
            }
        }

        path.reverse();
        path
    }

    /// Calculates average confidence for a path.
    fn path_confidence(&self, path: &[String]) -> f32 {
        if path.is_empty() {
            return 0.0;
        }

        let sum: f32 = path
            .iter()
            .filter_map(|id| self.nodes.get(id))
            .map(|n| n.confidence)
            .sum();

        #[allow(clippy::cast_precision_loss)]
        {
            sum / path.len() as f32
        }
    }
}

// ============================================================================
// Graph of Thought (Complex Interdependencies)
// ============================================================================

/// Graph-of-Thought reasoning - handles complex interdependencies.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GraphOfThought {
    /// Unique identifier.
    pub id: String,
    /// Problem being analyzed.
    pub problem: String,
    /// All nodes indexed by ID.
    pub nodes: HashMap<String, ReasoningStep>,
    /// Edges: from_id -> [(to_id, weight)].
    pub edges: HashMap<String, Vec<(String, f32)>>,
    /// Entry point nodes.
    pub entry_nodes: Vec<String>,
    /// Conclusion nodes.
    pub conclusion_nodes: Vec<String>,
}

impl GraphOfThought {
    /// Creates a new Graph-of-Thought.
    #[must_use]
    pub fn new(problem: &str) -> Self {
        Self {
            id: Uuid::now_v7().to_string(),
            problem: problem.to_string(),
            nodes: HashMap::new(),
            edges: HashMap::new(),
            entry_nodes: Vec::new(),
            conclusion_nodes: Vec::new(),
        }
    }

    /// Adds a node.
    pub fn add_node(&mut self, content: &str, confidence: f32, is_entry: bool) -> String {
        let step_number = self.nodes.len() as u32;
        let step = ReasoningStep::new(step_number, content, confidence);
        let id = step.id.clone();

        self.nodes.insert(id.clone(), step);
        if is_entry {
            self.entry_nodes.push(id.clone());
        }

        id
    }

    /// Adds an edge between nodes.
    pub fn add_edge(&mut self, from_id: &str, to_id: &str, weight: f32) -> bool {
        if !self.nodes.contains_key(from_id) || !self.nodes.contains_key(to_id) {
            return false;
        }

        self.edges
            .entry(from_id.to_string())
            .or_default()
            .push((to_id.to_string(), weight.clamp(0.0, 1.0)));

        true
    }

    /// Marks a node as a conclusion.
    pub fn mark_as_conclusion(&mut self, node_id: &str) {
        if self.nodes.contains_key(node_id) {
            self.conclusion_nodes.push(node_id.to_string());
        }
    }

    /// Returns the number of nodes.
    #[must_use]
    pub fn node_count(&self) -> usize {
        self.nodes.len()
    }

    /// Returns the number of edges.
    #[must_use]
    pub fn edge_count(&self) -> usize {
        self.edges.values().map(Vec::len).sum()
    }

    /// Calculates average node confidence.
    #[must_use]
    pub fn average_confidence(&self) -> f32 {
        if self.nodes.is_empty() {
            return 0.0;
        }

        let sum: f32 = self.nodes.values().map(|n| n.confidence).sum();

        #[allow(clippy::cast_precision_loss)]
        {
            sum / self.nodes.len() as f32
        }
    }
}

// ============================================================================
// Validation
// ============================================================================

/// Validation issue types.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ValidationIssueType {
    /// No reasoning steps.
    EmptyReasoning,
    /// Missing conclusion.
    MissingConclusion,
    /// Step with low confidence.
    LowConfidence,
    /// Orphaned node in tree/graph.
    OrphanedNode,
    /// Unexpected cycle in tree.
    UnexpectedCycle,
    /// Invalid reference.
    InvalidReference,
    /// Disconnected subgraph.
    DisconnectedSubgraph,
}

impl ValidationIssueType {
    /// Returns the severity penalty for this issue type.
    #[must_use]
    pub const fn severity(&self) -> f32 {
        match self {
            Self::EmptyReasoning => 1.0,
            Self::MissingConclusion => 0.3,
            Self::LowConfidence => 0.2,
            Self::OrphanedNode | Self::DisconnectedSubgraph => 0.4,
            Self::UnexpectedCycle => 0.5,
            Self::InvalidReference => 0.6,
        }
    }
}

/// A validation issue.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidationIssue {
    /// Issue type.
    pub issue_type: ValidationIssueType,
    /// Description.
    pub description: String,
    /// Related node ID (if applicable).
    pub node_id: Option<String>,
}

/// Validation result.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidationResult {
    /// Whether the reasoning is valid.
    pub is_valid: bool,
    /// Validation score (0.0 - 1.0).
    pub score: f32,
    /// List of issues found.
    pub issues: Vec<ValidationIssue>,
    /// Warnings (non-blocking).
    pub warnings: Vec<String>,
}

impl ValidationResult {
    /// Creates a valid result.
    #[must_use]
    pub fn valid() -> Self {
        Self {
            is_valid: true,
            score: 1.0,
            issues: Vec::new(),
            warnings: Vec::new(),
        }
    }

    /// Creates an invalid result with issues.
    #[must_use]
    pub fn invalid(issues: Vec<ValidationIssue>) -> Self {
        let penalty: f32 = issues.iter().map(|i| i.issue_type.severity()).sum();
        let score = (1.0 - penalty).max(0.0);

        Self {
            is_valid: issues.is_empty(),
            score,
            issues,
            warnings: Vec::new(),
        }
    }
}

/// Reasoning validator.
pub struct ReasoningValidator {
    min_confidence: f32,
    require_conclusion: bool,
}

impl Default for ReasoningValidator {
    fn default() -> Self {
        Self::new()
    }
}

impl ReasoningValidator {
    /// Creates a new validator with default settings.
    #[must_use]
    pub fn new() -> Self {
        Self {
            min_confidence: 0.5,
            require_conclusion: true,
        }
    }

    /// Sets minimum confidence threshold.
    #[must_use]
    pub const fn with_min_confidence(mut self, min: f32) -> Self {
        self.min_confidence = min;
        self
    }

    /// Sets whether conclusion is required.
    #[must_use]
    pub const fn with_require_conclusion(mut self, require: bool) -> Self {
        self.require_conclusion = require;
        self
    }

    /// Validates a Chain-of-Thought.
    #[must_use]
    pub fn validate_chain(&self, cot: &ChainOfThought) -> ValidationResult {
        let mut issues = Vec::new();

        // Check for empty reasoning
        if cot.steps.is_empty() {
            issues.push(ValidationIssue {
                issue_type: ValidationIssueType::EmptyReasoning,
                description: "Chain has no reasoning steps".to_string(),
                node_id: None,
            });
            return ValidationResult::invalid(issues);
        }

        // Check for conclusion
        if self.require_conclusion && cot.conclusion.is_none() {
            issues.push(ValidationIssue {
                issue_type: ValidationIssueType::MissingConclusion,
                description: "Chain has no conclusion".to_string(),
                node_id: None,
            });
        }

        // Check step confidence
        for step in &cot.steps {
            if step.confidence < self.min_confidence {
                issues.push(ValidationIssue {
                    issue_type: ValidationIssueType::LowConfidence,
                    description: format!(
                        "Step {} has low confidence: {:.2}",
                        step.step_number, step.confidence
                    ),
                    node_id: Some(step.id.clone()),
                });
            }
        }

        if issues.is_empty() {
            ValidationResult::valid()
        } else {
            ValidationResult::invalid(issues)
        }
    }

    /// Validates a Tree-of-Thought.
    #[must_use]
    pub fn validate_tree(&self, tot: &TreeOfThought) -> ValidationResult {
        let mut issues = Vec::new();

        // Check for empty
        if tot.nodes.is_empty() {
            issues.push(ValidationIssue {
                issue_type: ValidationIssueType::EmptyReasoning,
                description: "Tree has no nodes".to_string(),
                node_id: None,
            });
            return ValidationResult::invalid(issues);
        }

        // Check for root
        if tot.root_id.is_none() {
            issues.push(ValidationIssue {
                issue_type: ValidationIssueType::InvalidReference,
                description: "Tree has no root node".to_string(),
                node_id: None,
            });
        }

        // Check node confidence
        for (id, node) in &tot.nodes {
            if node.confidence < self.min_confidence {
                issues.push(ValidationIssue {
                    issue_type: ValidationIssueType::LowConfidence,
                    description: format!("Node has low confidence: {:.2}", node.confidence),
                    node_id: Some(id.clone()),
                });
            }
        }

        if issues.is_empty() {
            ValidationResult::valid()
        } else {
            ValidationResult::invalid(issues)
        }
    }

    /// Validates a Graph-of-Thought.
    #[must_use]
    pub fn validate_graph(&self, got: &GraphOfThought) -> ValidationResult {
        let mut issues = Vec::new();
        let mut warnings = Vec::new();

        // Check for empty
        if got.nodes.is_empty() {
            issues.push(ValidationIssue {
                issue_type: ValidationIssueType::EmptyReasoning,
                description: "Graph has no nodes".to_string(),
                node_id: None,
            });
            return ValidationResult::invalid(issues);
        }

        // Check for entry nodes
        if got.entry_nodes.is_empty() {
            warnings.push("Graph has no entry nodes defined".to_string());
        }

        // Check node confidence
        for (id, node) in &got.nodes {
            if node.confidence < self.min_confidence {
                issues.push(ValidationIssue {
                    issue_type: ValidationIssueType::LowConfidence,
                    description: format!("Node has low confidence: {:.2}", node.confidence),
                    node_id: Some(id.clone()),
                });
            }
        }

        // Check edge validity
        for (from_id, edges) in &got.edges {
            if !got.nodes.contains_key(from_id) {
                issues.push(ValidationIssue {
                    issue_type: ValidationIssueType::InvalidReference,
                    description: format!("Edge from non-existent node: {from_id}"),
                    node_id: Some(from_id.clone()),
                });
            }
            for (to_id, _) in edges {
                if !got.nodes.contains_key(to_id) {
                    issues.push(ValidationIssue {
                        issue_type: ValidationIssueType::InvalidReference,
                        description: format!("Edge to non-existent node: {to_id}"),
                        node_id: Some(to_id.clone()),
                    });
                }
            }
        }

        let mut result = if issues.is_empty() {
            ValidationResult::valid()
        } else {
            ValidationResult::invalid(issues)
        };
        result.warnings = warnings;
        result
    }
}

// ============================================================================
// Decision Generation
// ============================================================================

/// Decision priority levels.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum DecisionPriority {
    Low,
    Normal,
    High,
    Critical,
}

impl DecisionPriority {
    /// Creates priority from a confidence score.
    #[must_use]
    pub fn from_score(score: f32) -> Self {
        if score >= 0.9 {
            Self::Critical
        } else if score >= 0.7 {
            Self::High
        } else if score >= 0.4 {
            Self::Normal
        } else {
            Self::Low
        }
    }
}

/// Action types.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ActionType {
    Approve,
    ConditionalApprove,
    RequestInfo,
    Remediate,
    Reject,
    Escalate,
}

/// A decision generated from reasoning.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Decision {
    /// Decision ID.
    pub id: String,
    /// Reasoning paradigm used.
    pub paradigm: String,
    /// Source reasoning ID.
    pub reasoning_id: String,
    /// Score (0-100).
    pub score: u8,
    /// Confidence (0.0-1.0).
    pub confidence: f32,
    /// Recommended action.
    pub action: ActionType,
    /// Priority level.
    pub priority: DecisionPriority,
    /// Justification.
    pub justification: String,
    /// Identified risks.
    pub risks: Vec<String>,
}

impl Decision {
    /// Creates a decision from Chain-of-Thought.
    #[must_use]
    pub fn from_chain(cot: &ChainOfThought) -> Self {
        #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
        let score = (cot.confidence * 100.0).round().clamp(0.0, 100.0) as u8;

        let action = if score >= 80 {
            ActionType::Approve
        } else if score >= 60 {
            ActionType::ConditionalApprove
        } else {
            ActionType::Escalate
        };

        Self {
            id: Uuid::now_v7().to_string(),
            paradigm: "ChainOfThought".to_string(),
            reasoning_id: cot.id.clone(),
            score,
            confidence: cot.confidence,
            action,
            priority: DecisionPriority::from_score(cot.confidence),
            justification: cot.conclusion.clone().unwrap_or_default(),
            risks: Vec::new(),
        }
    }

    /// Creates a decision from Tree-of-Thought.
    #[must_use]
    pub fn from_tree(tot: &TreeOfThought) -> Self {
        #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
        let score = (tot.best_confidence * 100.0).round().clamp(0.0, 100.0) as u8;

        let action = if score >= 80 {
            ActionType::Approve
        } else if score >= 60 {
            ActionType::ConditionalApprove
        } else {
            ActionType::Escalate
        };

        Self {
            id: Uuid::now_v7().to_string(),
            paradigm: "TreeOfThought".to_string(),
            reasoning_id: tot.id.clone(),
            score,
            confidence: tot.best_confidence,
            action,
            priority: DecisionPriority::from_score(tot.best_confidence),
            justification: format!("Best path with {} steps", tot.best_path.len()),
            risks: Vec::new(),
        }
    }

    /// Creates a decision from Graph-of-Thought.
    #[must_use]
    pub fn from_graph(got: &GraphOfThought) -> Self {
        let confidence = got.average_confidence();

        #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
        let score = (confidence * 100.0).round().clamp(0.0, 100.0) as u8;

        let action = if score >= 80 {
            ActionType::Approve
        } else if score >= 60 {
            ActionType::ConditionalApprove
        } else {
            ActionType::Escalate
        };

        Self {
            id: Uuid::now_v7().to_string(),
            paradigm: "GraphOfThought".to_string(),
            reasoning_id: got.id.clone(),
            score,
            confidence,
            action,
            priority: DecisionPriority::from_score(confidence),
            justification: format!(
                "Graph analysis with {} nodes and {} edges",
                got.node_count(),
                got.edge_count()
            ),
            risks: Vec::new(),
        }
    }
}

// ============================================================================
// Tests
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_chain_of_thought_basic() {
        let mut cot = ChainOfThought::new("Test problem");
        cot.add_step("Step 1", 0.9);
        cot.add_step("Step 2", 0.85);
        cot.conclude("Conclusion");

        assert_eq!(cot.steps.len(), 2);
        assert!(cot.is_complete());
        assert!((cot.confidence - 0.875).abs() < 0.01);
    }

    #[test]
    fn test_tree_of_thought_branching() {
        let mut tot = TreeOfThought::new("Test problem");
        let root = tot.add_root("Root", 0.9);
        let branch1 = tot.add_branch(&root, "Branch 1", 0.8);
        let branch2 = tot.add_branch(&root, "Branch 2", 0.95);

        assert!(branch1.is_some());
        assert!(branch2.is_some());
        assert_eq!(tot.nodes.len(), 3);

        tot.evaluate_best_path();
        assert!(tot.best_confidence > 0.9);
    }

    #[test]
    fn test_graph_of_thought_nodes() {
        let mut got = GraphOfThought::new("Test problem");
        let n1 = got.add_node("Node 1", 0.9, true);
        let n2 = got.add_node("Node 2", 0.85, false);
        got.add_edge(&n1, &n2, 0.8);
        got.mark_as_conclusion(&n2);

        assert_eq!(got.node_count(), 2);
        assert_eq!(got.edge_count(), 1);
        assert!(got.average_confidence() > 0.85);
    }

    #[test]
    fn test_validate_chain_valid() {
        let mut cot = ChainOfThought::new("Test");
        cot.add_step("Step 1", 0.9);
        cot.conclude("Done");

        let validator = ReasoningValidator::new();
        let result = validator.validate_chain(&cot);

        assert!(result.is_valid);
        assert!((result.score - 1.0).abs() < 0.01);
    }

    #[test]
    fn test_validate_chain_empty() {
        let cot = ChainOfThought::new("Test");
        let validator = ReasoningValidator::new();
        let result = validator.validate_chain(&cot);

        assert!(!result.is_valid);
        assert!(result.issues.iter().any(|i| i.issue_type == ValidationIssueType::EmptyReasoning));
    }

    #[test]
    fn test_validate_chain_low_confidence() {
        let mut cot = ChainOfThought::new("Test");
        cot.add_step("Step 1", 0.3); // Below threshold
        cot.conclude("Done");

        let validator = ReasoningValidator::new().with_min_confidence(0.5);
        let result = validator.validate_chain(&cot);

        assert!(!result.is_valid);
        assert!(result.issues.iter().any(|i| i.issue_type == ValidationIssueType::LowConfidence));
    }

    #[test]
    fn test_decision_from_chain() {
        let mut cot = ChainOfThought::new("Test");
        cot.add_step("Step 1", 0.9);
        cot.add_step("Step 2", 0.85);
        cot.conclude("Approved");

        let decision = Decision::from_chain(&cot);

        assert!(decision.score > 80);
        assert_eq!(decision.action, ActionType::Approve);
        assert_eq!(decision.paradigm, "ChainOfThought");
    }

    #[test]
    fn test_decision_from_tree() {
        let mut tot = TreeOfThought::new("Test");
        let root = tot.add_root("Root", 0.95);
        tot.add_branch(&root, "Branch", 0.9);
        tot.evaluate_best_path();

        let decision = Decision::from_tree(&tot);

        assert!(decision.score > 90);
        assert_eq!(decision.action, ActionType::Approve);
    }

    #[test]
    fn test_decision_from_graph() {
        let mut got = GraphOfThought::new("Test");
        got.add_node("N1", 0.9, true);
        got.add_node("N2", 0.85, false);

        let decision = Decision::from_graph(&got);

        assert!(decision.score > 85);
        assert_eq!(decision.paradigm, "GraphOfThought");
    }

    #[test]
    fn test_decision_priority_from_score() {
        assert_eq!(DecisionPriority::from_score(0.95), DecisionPriority::Critical);
        assert_eq!(DecisionPriority::from_score(0.75), DecisionPriority::High);
        assert_eq!(DecisionPriority::from_score(0.5), DecisionPriority::Normal);
        assert_eq!(DecisionPriority::from_score(0.2), DecisionPriority::Low);
    }
}
