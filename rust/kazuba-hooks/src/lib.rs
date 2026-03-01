//! # kazuba-hooks
//!
//! High-performance Rust implementations for Claude Code hooks.
//! Provides 10-50x speedup over Python for critical operations.
//!
//! ## Modules
//! - **secrets**: Secret detection engine (API keys, passwords, tokens)
//! - **skill_match**: Skill matching with Aho-Corasick + semantic similarity
//! - **code_quality**: Code quality validation and anti-pattern detection
//! - **patterns**: Unified pattern matching utilities (Aho-Corasick builders)
//! - **bash_safety**: Command safety validation (dangerous command detection)
//! - **recovery**: Failure recovery pattern matching
//! - **subagent**: Skill injection engine for SubagentStart events

#[cfg(feature = "pyo3-bindings")]
use pyo3::prelude::*;

// Core modules
pub mod code_quality;
pub mod patterns;
pub mod secrets;
pub mod skill_match;

// New modules (Pln2 migration)
pub mod bash_safety;
pub mod recovery;
pub mod subagent;

// New modules (Pln3 - Knowledge/Learning/QA)
pub mod knowledge;
pub mod learning;
pub mod qa;

// RLM Integration (Pln3 - Unified Reasoning)
pub mod rlm_reasoning;

// Re-exports for convenience
pub use code_quality::{CodeQualityValidator, Issue, Severity, ValidationResult};
pub use secrets::{SecretMatch, SecretsDetector};
pub use skill_match::{Complexity, SkillMatcher, SkillPattern};

// New exports (Pln2)
pub use bash_safety::{BashSafetyValidator, BashValidationResult, DangerousSeverity};
pub use patterns::{build_ac, build_ac_case_insensitive, extract_directory, extract_module_name};
pub use recovery::{RecoveryMatcher, RecoveryResult, RecoveryStrategy};
pub use subagent::{InjectionResult, Skill, SkillCategory, SkillInjector};

// New exports (Pln3 - Knowledge/Learning/QA)
pub use knowledge::{
    CacheEntry, KnowledgeEngine, KnowledgePattern, KnowledgeQuery, PatternMatch, SignalScores,
};
pub use learning::{
    Action, Cluster, ClusterEngine, MemoryEntry, SimilarityResult, State, TDLearner,
    TDUpdateResult, WorkingMemory,
};
pub use qa::{
    CategorizedIssue, FixPattern, FixPatternMatch, FixPatternMatcher, IssueCategorizer,
    IssueCategory, QualityMetrics, QualityTracker, ROICalculator, ROIMetrics,
};

// RLM Reasoning exports (Pln3 - Unified Reasoning)
pub use rlm_reasoning::{
    ActionType as RlmActionType, ChainOfThought, Decision as RlmDecision,
    DecisionPriority as RlmDecisionPriority, GraphOfThought, ReasoningStep, ReasoningValidator,
    TreeOfThought, ValidationIssue, ValidationIssueType, ValidationResult as RlmValidationResult,
};

// ============================================================================
// PyO3 Bindings
// ============================================================================

// ── Secrets Detection ─────────────────────────────────────────────────────────

#[cfg(feature = "pyo3-bindings")]
#[pyfunction]
#[pyo3(name = "detect_secrets")]
pub fn py_detect_secrets(
    py: Python<'_>,
    content: String,
    file_path: String,
) -> PyResult<Vec<std::collections::HashMap<String, String>>> {
    let detector = SecretsDetector::new();

    if detector.is_safe_file(&file_path) {
        return Ok(vec![]);
    }

    let matches = py.allow_threads(move || detector.detect(&content));

    let result: Vec<std::collections::HashMap<String, String>> = matches
        .into_iter()
        .map(|m| {
            let mut map = std::collections::HashMap::new();
            map.insert("type".to_string(), m.description.clone());
            map.insert("pattern_index".to_string(), m.pattern_index.to_string());
            map
        })
        .collect();

    Ok(result)
}

// ── Code Quality Validation ───────────────────────────────────────────────────

#[cfg(feature = "pyo3-bindings")]
#[pyfunction]
#[pyo3(name = "validate_code")]
pub fn py_validate_code(
    py: Python<'_>,
    content: String,
    file_path: String,
) -> PyResult<std::collections::HashMap<String, pyo3::PyObject>> {
    use pyo3::ToPyObject;

    let validator = CodeQualityValidator::new();
    let result = py.allow_threads(move || validator.validate(&content, &file_path));

    let mut map = std::collections::HashMap::new();
    map.insert("passed".to_string(), result.passed.to_object(py));
    map.insert("score".to_string(), result.score.to_object(py));

    let issues: Vec<std::collections::HashMap<String, pyo3::PyObject>> = result
        .issues
        .into_iter()
        .map(|issue| {
            let mut issue_map = std::collections::HashMap::new();
            issue_map.insert("line".to_string(), issue.line.to_object(py));
            issue_map.insert("column".to_string(), issue.column.to_object(py));
            issue_map.insert(
                "severity".to_string(),
                match issue.severity {
                    Severity::Error => "error",
                    Severity::Warning => "warning",
                    Severity::Info => "info",
                }
                .to_object(py),
            );
            issue_map.insert("message".to_string(), issue.message.to_object(py));
            issue_map.insert("code".to_string(), issue.code.to_object(py));
            issue_map
        })
        .collect();

    map.insert("issues".to_string(), issues.to_object(py));

    Ok(map)
}

// ── Skill Matching ────────────────────────────────────────────────────────────

#[cfg(feature = "pyo3-bindings")]
#[pyfunction]
#[pyo3(name = "match_skills")]
pub fn py_match_skills(
    py: Python<'_>,
    prompt: String,
    skills_json: String,
    top_k: usize,
) -> PyResult<Vec<std::collections::HashMap<String, pyo3::PyObject>>> {
    use pyo3::ToPyObject;

    // Parse skills from JSON
    let skills: Vec<SkillPattern> = serde_json::from_str(&skills_json).map_err(|e| {
        pyo3::exceptions::PyValueError::new_err(format!("Invalid skills JSON: {}", e))
    })?;

    let matcher = SkillMatcher::new(skills.clone());
    let matches = py.allow_threads(move || matcher.match_skills(&prompt, top_k));

    let result: Vec<std::collections::HashMap<String, pyo3::PyObject>> = matches
        .into_iter()
        .map(|(idx, score)| {
            let mut map = std::collections::HashMap::new();
            map.insert("index".to_string(), idx.to_object(py));
            map.insert("score".to_string(), score.to_object(py));
            map.insert("name".to_string(), skills[idx].name.clone().to_object(py));
            map
        })
        .collect();

    Ok(result)
}

// ── Bash Safety Validation (NEW - Pln2) ──────────────────────────────────────

#[cfg(feature = "pyo3-bindings")]
#[pyfunction]
#[pyo3(name = "validate_bash_command")]
pub fn py_validate_bash_command(
    py: Python<'_>,
    command: String,
) -> PyResult<std::collections::HashMap<String, pyo3::PyObject>> {
    use pyo3::ToPyObject;

    let result = py.allow_threads(move || {
        let validator = BashSafetyValidator::new();
        validator.validate(&command)
    });

    let mut map = std::collections::HashMap::new();
    map.insert("allowed".to_string(), result.allowed.to_object(py));
    map.insert("reason".to_string(), result.reason.to_object(py));

    if let Some(severity) = result.severity {
        let severity_str = match severity {
            DangerousSeverity::High => "high",
            DangerousSeverity::Medium => "medium",
            DangerousSeverity::Low => "low",
        };
        map.insert("severity".to_string(), severity_str.to_object(py));
    } else {
        map.insert("severity".to_string(), py.None());
    }

    if let Some(pattern) = result.matched_pattern {
        map.insert("matched_pattern".to_string(), pattern.to_object(py));
    } else {
        map.insert("matched_pattern".to_string(), py.None());
    }

    Ok(map)
}

// ── Recovery Pattern Matching (NEW - Pln2) ───────────────────────────────────

#[cfg(feature = "pyo3-bindings")]
#[pyfunction]
#[pyo3(name = "match_recovery_pattern")]
pub fn py_match_recovery_pattern(
    py: Python<'_>,
    error: String,
    file_path: String,
) -> PyResult<std::collections::HashMap<String, pyo3::PyObject>> {
    use pyo3::ToPyObject;

    let result = py.allow_threads(move || {
        let matcher = RecoveryMatcher::new();
        matcher.match_error_with_path(&error, &file_path)
    });

    let mut map = std::collections::HashMap::new();
    map.insert(
        "recovery_available".to_string(),
        result.recovery_available.to_object(py),
    );

    let strategy_str = match result.strategy {
        recovery::RecoveryStrategy::AutoFix => "auto_fix",
        recovery::RecoveryStrategy::Suggest => "suggest",
        recovery::RecoveryStrategy::Escalate => "escalate",
        recovery::RecoveryStrategy::VerifyPath => "verify_path",
        recovery::RecoveryStrategy::Analyze => "analyze",
        recovery::RecoveryStrategy::TypeCheck => "type_check",
        recovery::RecoveryStrategy::RerunTests => "rerun_tests",
        recovery::RecoveryStrategy::GitRecovery => "git_recovery",
        recovery::RecoveryStrategy::Retry => "retry",
        recovery::RecoveryStrategy::None => "none",
    };
    map.insert("strategy".to_string(), strategy_str.to_object(py));
    map.insert("description".to_string(), result.description.to_object(py));

    if let Some(cmd) = result.command {
        map.insert("command".to_string(), cmd.to_object(py));
    } else {
        map.insert("command".to_string(), py.None());
    }

    if let Some(sug) = result.suggestion {
        map.insert("suggestion".to_string(), sug.to_object(py));
    } else {
        map.insert("suggestion".to_string(), py.None());
    }

    map.insert("auto_apply".to_string(), result.auto_apply.to_object(py));

    Ok(map)
}

// ── Skill Injection (NEW - Pln2) ─────────────────────────────────────────────

#[cfg(feature = "pyo3-bindings")]
#[pyfunction]
#[pyo3(name = "inject_skills")]
pub fn py_inject_skills(
    py: Python<'_>,
    prompt: String,
    skills_json: String,
    max_skills: usize,
) -> PyResult<std::collections::HashMap<String, pyo3::PyObject>> {
    use pyo3::ToPyObject;

    // Parse skills from JSON
    let skills: Vec<Skill> = serde_json::from_str(&skills_json).map_err(|e| {
        pyo3::exceptions::PyValueError::new_err(format!("Invalid skills JSON: {}", e))
    })?;

    let result = py.allow_threads(move || {
        let injector = SkillInjector::new(skills);
        injector.inject(&prompt, max_skills)
    });

    let mut map = std::collections::HashMap::new();
    map.insert("skills".to_string(), result.skills.to_object(py));
    map.insert(
        "dev_skill_ratio".to_string(),
        result.dev_skill_ratio.to_object(py),
    );
    map.insert(
        "quality_reminders".to_string(),
        result.quality_reminders.to_object(py),
    );
    map.insert("total_score".to_string(), result.total_score.to_object(py));

    Ok(map)
}

// ── Knowledge Engine (NEW - Pln3) ─────────────────────────────────────────────

#[cfg(feature = "pyo3-bindings")]
#[pyfunction]
#[pyo3(name = "match_knowledge_patterns")]
pub fn py_match_knowledge_patterns(
    py: Python<'_>,
    query_json: String,
    patterns_json: String,
    top_k: usize,
) -> PyResult<Vec<std::collections::HashMap<String, pyo3::PyObject>>> {
    use pyo3::ToPyObject;

    let query: KnowledgeQuery = serde_json::from_str(&query_json).map_err(|e| {
        pyo3::exceptions::PyValueError::new_err(format!("Invalid query JSON: {}", e))
    })?;

    let patterns: Vec<KnowledgePattern> = serde_json::from_str(&patterns_json).map_err(|e| {
        pyo3::exceptions::PyValueError::new_err(format!("Invalid patterns JSON: {}", e))
    })?;

    let results = py.allow_threads(move || {
        let engine = KnowledgeEngine::new(patterns);
        engine.match_patterns(&query, top_k)
    });

    let result: Vec<std::collections::HashMap<String, pyo3::PyObject>> = results
        .into_iter()
        .map(|m| {
            let mut map = std::collections::HashMap::new();
            map.insert("pattern_id".to_string(), m.pattern_id.to_object(py));
            map.insert("score".to_string(), m.score.to_object(py));
            map.insert(
                "keyword_matches".to_string(),
                m.keyword_matches.to_object(py),
            );
            map.insert(
                "keyword_score".to_string(),
                m.signals.keyword_score.to_object(py),
            );
            map.insert(
                "error_code_score".to_string(),
                m.signals.error_code_score.to_object(py),
            );
            map.insert("tag_score".to_string(), m.signals.tag_score.to_object(py));
            map.insert("path_score".to_string(), m.signals.path_score.to_object(py));
            map
        })
        .collect();

    Ok(result)
}

// ── Learning Engine (NEW - Pln3) ──────────────────────────────────────────────

#[cfg(feature = "pyo3-bindings")]
#[pyfunction]
#[pyo3(name = "similarity_search")]
pub fn py_similarity_search(
    py: Python<'_>,
    query: Vec<f32>,
    embeddings_json: String,
    top_k: usize,
) -> PyResult<Vec<std::collections::HashMap<String, pyo3::PyObject>>> {
    use pyo3::ToPyObject;

    let entries: Vec<MemoryEntry> = serde_json::from_str(&embeddings_json).map_err(|e| {
        pyo3::exceptions::PyValueError::new_err(format!("Invalid embeddings JSON: {}", e))
    })?;

    let results = py.allow_threads(move || {
        let mut memory = WorkingMemory::new(entries.len() + 1);
        for entry in entries {
            memory.add(entry);
        }
        memory.similarity_search(&query, top_k)
    });

    let result: Vec<std::collections::HashMap<String, pyo3::PyObject>> = results
        .into_iter()
        .map(|r| {
            let mut map = std::collections::HashMap::new();
            map.insert("index".to_string(), r.index.to_object(py));
            map.insert("id".to_string(), r.id.to_object(py));
            map.insert("similarity".to_string(), r.similarity.to_object(py));
            map
        })
        .collect();

    Ok(result)
}

#[cfg(feature = "pyo3-bindings")]
#[pyfunction]
#[pyo3(name = "td_update")]
pub fn py_td_update(
    py: Python<'_>,
    q_table_json: String,
    state_id: String,
    action_id: String,
    reward: f64,
    next_state_id: String,
    alpha: f64,
    gamma: f64,
    lambda: f64,
) -> PyResult<std::collections::HashMap<String, pyo3::PyObject>> {
    use pyo3::ToPyObject;

    let q_table: std::collections::HashMap<String, f64> =
        serde_json::from_str(&q_table_json).unwrap_or_default();

    let result = py.allow_threads(move || {
        let mut learner = TDLearner::new(alpha, gamma, lambda, 0.1);
        learner.import_q_table(q_table);

        let state = State {
            id: state_id,
            features: String::new(),
        };
        let action = Action {
            id: action_id,
            action_type: String::new(),
        };
        let next_state = State {
            id: next_state_id,
            features: String::new(),
        };

        let update_result = learner.update(&state, &action, reward, &next_state, None);
        let exported = learner.export_q_table();

        (update_result, exported)
    });

    let mut map = std::collections::HashMap::new();
    map.insert(
        "new_q_value".to_string(),
        result.0.new_q_value.to_object(py),
    );
    map.insert("td_error".to_string(), result.0.td_error.to_object(py));
    map.insert(
        "states_updated".to_string(),
        result.0.states_updated.to_object(py),
    );
    map.insert(
        "q_table".to_string(),
        serde_json::to_string(&result.1)
            .unwrap_or_default()
            .to_object(py),
    );

    Ok(map)
}

#[cfg(feature = "pyo3-bindings")]
#[pyfunction]
#[pyo3(name = "detect_clusters")]
pub fn py_detect_clusters(
    py: Python<'_>,
    embeddings: Vec<Vec<f32>>,
    min_points: usize,
    epsilon: f32,
) -> PyResult<Vec<std::collections::HashMap<String, pyo3::PyObject>>> {
    use pyo3::ToPyObject;

    let clusters = py.allow_threads(move || {
        let engine = ClusterEngine::new(min_points, epsilon);
        engine.detect_clusters(&embeddings)
    });

    let result: Vec<std::collections::HashMap<String, pyo3::PyObject>> = clusters
        .into_iter()
        .map(|c| {
            let mut map = std::collections::HashMap::new();
            map.insert("id".to_string(), c.id.to_object(py));
            map.insert("size".to_string(), c.size.to_object(py));
            map.insert("point_indices".to_string(), c.point_indices.to_object(py));
            map.insert("centroid".to_string(), c.centroid.to_object(py));
            map
        })
        .collect();

    Ok(result)
}

// ── QA Engine (NEW - Pln3) ────────────────────────────────────────────────────

#[cfg(feature = "pyo3-bindings")]
#[pyfunction]
#[pyo3(name = "categorize_issues")]
pub fn py_categorize_issues(
    py: Python<'_>,
    messages: Vec<String>,
) -> PyResult<Vec<std::collections::HashMap<String, pyo3::PyObject>>> {
    use pyo3::ToPyObject;

    let results = py.allow_threads(move || {
        let categorizer = IssueCategorizer::new();
        let refs: Vec<&str> = messages.iter().map(|s| s.as_str()).collect();
        categorizer.categorize_batch(&refs)
    });

    let result: Vec<std::collections::HashMap<String, pyo3::PyObject>> = results
        .into_iter()
        .map(|c| {
            let mut map = std::collections::HashMap::new();
            map.insert("message".to_string(), c.message.to_object(py));
            map.insert(
                "category".to_string(),
                format!("{:?}", c.category).to_object(py),
            );
            map.insert("confidence".to_string(), c.confidence.to_object(py));
            map.insert(
                "matched_keywords".to_string(),
                c.matched_keywords.to_object(py),
            );
            map
        })
        .collect();

    Ok(result)
}

#[cfg(feature = "pyo3-bindings")]
#[pyfunction]
#[pyo3(name = "calculate_roi")]
pub fn py_calculate_roi(
    py: Python<'_>,
    fixes_applied: u32,
    fixes_succeeded: u32,
    time_invested_ms: i64,
    baseline_manual_time_ms: i64,
) -> PyResult<std::collections::HashMap<String, pyo3::PyObject>> {
    use pyo3::ToPyObject;

    let roi = py.allow_threads(move || {
        let calculator = ROICalculator::new(baseline_manual_time_ms, 5000);
        calculator.calculate(fixes_applied, fixes_succeeded, time_invested_ms, None)
    });

    let mut map = std::collections::HashMap::new();
    map.insert("time_saved_ms".to_string(), roi.time_saved_ms.to_object(py));
    map.insert(
        "time_invested_ms".to_string(),
        roi.time_invested_ms.to_object(py),
    );
    map.insert("fixes_applied".to_string(), roi.fixes_applied.to_object(py));
    map.insert(
        "fixes_succeeded".to_string(),
        roi.fixes_succeeded.to_object(py),
    );
    map.insert("roi_ratio".to_string(), roi.roi_ratio.to_object(py));
    map.insert("weighted_roi".to_string(), roi.weighted_roi.to_object(py));
    map.insert("success_rate".to_string(), roi.success_rate.to_object(py));
    map.insert(
        "efficiency_score".to_string(),
        roi.efficiency_score.to_object(py),
    );

    Ok(map)
}

#[cfg(feature = "pyo3-bindings")]
#[pyfunction]
#[pyo3(name = "find_fix_patterns")]
pub fn py_find_fix_patterns(
    py: Python<'_>,
    issue: String,
    patterns_json: String,
    threshold: f32,
) -> PyResult<Vec<std::collections::HashMap<String, pyo3::PyObject>>> {
    use pyo3::ToPyObject;

    let patterns: Vec<FixPattern> = serde_json::from_str(&patterns_json).map_err(|e| {
        pyo3::exceptions::PyValueError::new_err(format!("Invalid patterns JSON: {}", e))
    })?;

    let results = py.allow_threads(move || {
        let matcher = FixPatternMatcher::new(patterns);
        matcher.find_matches(&issue, threshold)
    });

    let result: Vec<std::collections::HashMap<String, pyo3::PyObject>> = results
        .into_iter()
        .map(|m| {
            let mut map = std::collections::HashMap::new();
            map.insert("pattern_id".to_string(), m.pattern_id.to_object(py));
            map.insert("score".to_string(), m.score.to_object(py));
            map.insert(
                "matched_keywords".to_string(),
                m.matched_keywords.to_object(py),
            );
            map.insert("fix_template".to_string(), m.fix_template.to_object(py));
            map.insert(
                "expected_success_rate".to_string(),
                m.expected_success_rate.to_object(py),
            );
            map
        })
        .collect();

    Ok(result)
}

// ── RLM Reasoning (NEW - Pln3 Unified) ─────────────────────────────────────────

#[cfg(feature = "pyo3-bindings")]
#[pyfunction]
#[pyo3(name = "create_chain_of_thought")]
pub fn py_create_chain_of_thought(problem: String) -> PyResult<String> {
    let cot = rlm_reasoning::ChainOfThought::new(&problem);
    serde_json::to_string(&cot)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Serialization error: {e}")))
}

#[cfg(feature = "pyo3-bindings")]
#[pyfunction]
#[pyo3(name = "add_reasoning_step")]
pub fn py_add_reasoning_step(
    cot_json: String,
    content: String,
    confidence: f32,
) -> PyResult<String> {
    let mut cot: rlm_reasoning::ChainOfThought = serde_json::from_str(&cot_json)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid CoT JSON: {e}")))?;

    cot.add_step(&content, confidence);

    serde_json::to_string(&cot)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Serialization error: {e}")))
}

#[cfg(feature = "pyo3-bindings")]
#[pyfunction]
#[pyo3(name = "conclude_reasoning")]
pub fn py_conclude_reasoning(cot_json: String, conclusion: String) -> PyResult<String> {
    let mut cot: rlm_reasoning::ChainOfThought = serde_json::from_str(&cot_json)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid CoT JSON: {e}")))?;

    cot.conclude(&conclusion);

    serde_json::to_string(&cot)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Serialization error: {e}")))
}

#[cfg(feature = "pyo3-bindings")]
#[pyfunction]
#[pyo3(name = "validate_chain")]
pub fn py_validate_chain(
    py: Python<'_>,
    cot_json: String,
    min_confidence: f32,
    require_conclusion: bool,
) -> PyResult<std::collections::HashMap<String, pyo3::PyObject>> {
    use pyo3::ToPyObject;

    let cot: rlm_reasoning::ChainOfThought = serde_json::from_str(&cot_json)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid CoT JSON: {e}")))?;

    let result = py.allow_threads(move || {
        let validator = rlm_reasoning::ReasoningValidator::new()
            .with_min_confidence(min_confidence)
            .with_require_conclusion(require_conclusion);
        validator.validate_chain(&cot)
    });

    let mut map = std::collections::HashMap::new();
    map.insert("is_valid".to_string(), result.is_valid.to_object(py));
    map.insert("score".to_string(), result.score.to_object(py));

    let issues: Vec<std::collections::HashMap<String, pyo3::PyObject>> = result
        .issues
        .into_iter()
        .map(|issue| {
            let mut issue_map = std::collections::HashMap::new();
            issue_map.insert(
                "type".to_string(),
                format!("{:?}", issue.issue_type).to_object(py),
            );
            issue_map.insert("description".to_string(), issue.description.to_object(py));
            if let Some(node_id) = issue.node_id {
                issue_map.insert("node_id".to_string(), node_id.to_object(py));
            }
            issue_map
        })
        .collect();

    map.insert("issues".to_string(), issues.to_object(py));
    map.insert("warnings".to_string(), result.warnings.to_object(py));

    Ok(map)
}

#[cfg(feature = "pyo3-bindings")]
#[pyfunction]
#[pyo3(name = "generate_decision_from_chain")]
pub fn py_generate_decision_from_chain(
    py: Python<'_>,
    cot_json: String,
) -> PyResult<std::collections::HashMap<String, pyo3::PyObject>> {
    use pyo3::ToPyObject;

    let cot: rlm_reasoning::ChainOfThought = serde_json::from_str(&cot_json)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid CoT JSON: {e}")))?;

    let decision = py.allow_threads(move || rlm_reasoning::Decision::from_chain(&cot));

    let mut map = std::collections::HashMap::new();
    map.insert("id".to_string(), decision.id.to_object(py));
    map.insert("paradigm".to_string(), decision.paradigm.to_object(py));
    map.insert("reasoning_id".to_string(), decision.reasoning_id.to_object(py));
    map.insert("score".to_string(), decision.score.to_object(py));
    map.insert("confidence".to_string(), decision.confidence.to_object(py));
    map.insert(
        "action".to_string(),
        format!("{:?}", decision.action).to_object(py),
    );
    map.insert(
        "priority".to_string(),
        format!("{:?}", decision.priority).to_object(py),
    );
    map.insert("justification".to_string(), decision.justification.to_object(py));
    map.insert("risks".to_string(), decision.risks.to_object(py));

    Ok(map)
}

#[cfg(feature = "pyo3-bindings")]
#[pyfunction]
#[pyo3(name = "create_tree_of_thought")]
pub fn py_create_tree_of_thought(problem: String) -> PyResult<String> {
    let tot = rlm_reasoning::TreeOfThought::new(&problem);
    serde_json::to_string(&tot)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Serialization error: {e}")))
}

#[cfg(feature = "pyo3-bindings")]
#[pyfunction]
#[pyo3(name = "add_tree_root")]
pub fn py_add_tree_root(tot_json: String, content: String, confidence: f32) -> PyResult<String> {
    let mut tot: rlm_reasoning::TreeOfThought = serde_json::from_str(&tot_json)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid ToT JSON: {e}")))?;

    tot.add_root(&content, confidence);

    serde_json::to_string(&tot)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Serialization error: {e}")))
}

#[cfg(feature = "pyo3-bindings")]
#[pyfunction]
#[pyo3(name = "add_tree_branch")]
pub fn py_add_tree_branch(
    tot_json: String,
    parent_id: String,
    content: String,
    confidence: f32,
) -> PyResult<String> {
    let mut tot: rlm_reasoning::TreeOfThought = serde_json::from_str(&tot_json)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid ToT JSON: {e}")))?;

    tot.add_branch(&parent_id, &content, confidence);

    serde_json::to_string(&tot)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Serialization error: {e}")))
}

#[cfg(feature = "pyo3-bindings")]
#[pyfunction]
#[pyo3(name = "evaluate_tree_best_path")]
pub fn py_evaluate_tree_best_path(
    py: Python<'_>,
    tot_json: String,
) -> PyResult<std::collections::HashMap<String, pyo3::PyObject>> {
    use pyo3::ToPyObject;

    let mut tot: rlm_reasoning::TreeOfThought = serde_json::from_str(&tot_json)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid ToT JSON: {e}")))?;

    py.allow_threads(|| tot.evaluate_best_path());

    let mut map = std::collections::HashMap::new();
    map.insert("best_path".to_string(), tot.best_path.to_object(py));
    map.insert("best_confidence".to_string(), tot.best_confidence.to_object(py));
    map.insert(
        "tot_json".to_string(),
        serde_json::to_string(&tot).unwrap_or_default().to_object(py),
    );

    Ok(map)
}

#[cfg(feature = "pyo3-bindings")]
#[pyfunction]
#[pyo3(name = "generate_decision_from_tree")]
pub fn py_generate_decision_from_tree(
    py: Python<'_>,
    tot_json: String,
) -> PyResult<std::collections::HashMap<String, pyo3::PyObject>> {
    use pyo3::ToPyObject;

    let tot: rlm_reasoning::TreeOfThought = serde_json::from_str(&tot_json)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid ToT JSON: {e}")))?;

    let decision = py.allow_threads(move || rlm_reasoning::Decision::from_tree(&tot));

    let mut map = std::collections::HashMap::new();
    map.insert("id".to_string(), decision.id.to_object(py));
    map.insert("paradigm".to_string(), decision.paradigm.to_object(py));
    map.insert("score".to_string(), decision.score.to_object(py));
    map.insert("confidence".to_string(), decision.confidence.to_object(py));
    map.insert(
        "action".to_string(),
        format!("{:?}", decision.action).to_object(py),
    );
    map.insert(
        "priority".to_string(),
        format!("{:?}", decision.priority).to_object(py),
    );
    map.insert("justification".to_string(), decision.justification.to_object(py));

    Ok(map)
}

// ── Module Registration ───────────────────────────────────────────────────────

#[cfg(feature = "pyo3-bindings")]
#[pymodule]
fn kazuba_hooks(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Existing functions
    m.add_function(wrap_pyfunction!(py_detect_secrets, m)?)?;
    m.add_function(wrap_pyfunction!(py_validate_code, m)?)?;
    m.add_function(wrap_pyfunction!(py_match_skills, m)?)?;

    // New functions (Pln2)
    m.add_function(wrap_pyfunction!(py_validate_bash_command, m)?)?;
    m.add_function(wrap_pyfunction!(py_match_recovery_pattern, m)?)?;
    m.add_function(wrap_pyfunction!(py_inject_skills, m)?)?;

    // New functions (Pln3 - Knowledge/Learning/QA)
    m.add_function(wrap_pyfunction!(py_match_knowledge_patterns, m)?)?;
    m.add_function(wrap_pyfunction!(py_similarity_search, m)?)?;
    m.add_function(wrap_pyfunction!(py_td_update, m)?)?;
    m.add_function(wrap_pyfunction!(py_detect_clusters, m)?)?;
    m.add_function(wrap_pyfunction!(py_categorize_issues, m)?)?;
    m.add_function(wrap_pyfunction!(py_calculate_roi, m)?)?;
    m.add_function(wrap_pyfunction!(py_find_fix_patterns, m)?)?;

    // RLM Reasoning functions (Pln3 - Unified Reasoning Engine)
    m.add_function(wrap_pyfunction!(py_create_chain_of_thought, m)?)?;
    m.add_function(wrap_pyfunction!(py_add_reasoning_step, m)?)?;
    m.add_function(wrap_pyfunction!(py_conclude_reasoning, m)?)?;
    m.add_function(wrap_pyfunction!(py_validate_chain, m)?)?;
    m.add_function(wrap_pyfunction!(py_generate_decision_from_chain, m)?)?;
    m.add_function(wrap_pyfunction!(py_create_tree_of_thought, m)?)?;
    m.add_function(wrap_pyfunction!(py_add_tree_root, m)?)?;
    m.add_function(wrap_pyfunction!(py_add_tree_branch, m)?)?;
    m.add_function(wrap_pyfunction!(py_evaluate_tree_best_path, m)?)?;
    m.add_function(wrap_pyfunction!(py_generate_decision_from_tree, m)?)?;

    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_secrets_detector_api_key() {
        let detector = SecretsDetector::new();
        let content = r#"api_key = "sk-1234567890abcdefghijklmnopqrstuvwxyz123456""#;
        let matches = detector.detect(content);
        assert!(!matches.is_empty(), "Should detect API key");
    }
}
