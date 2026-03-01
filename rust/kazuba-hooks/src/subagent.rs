//! # Skill Injection Engine for SubagentStart Events
//!
//! High-performance skill matching for injecting relevant skills into subagent prompts.
//! Uses Aho-Corasick for O(n) keyword matching with priority-based skill selection.
//!
//! ## Features
//! - Fast keyword matching using Aho-Corasick
//! - Priority-based skill ranking
//! - Development skill ratio tracking (target: 80%)
//! - Quality reminders injection

use crate::patterns::build_ac_case_insensitive;
use aho_corasick::AhoCorasick;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Skill category for priority ordering.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum SkillCategory {
    Development,
    Generic,
    Domain,
    Research,
    Quality,
}

impl SkillCategory {
    /// Check if this is a development-related category.
    pub fn is_development(&self) -> bool {
        matches!(self, SkillCategory::Development | SkillCategory::Quality)
    }
}

/// Skill definition with keywords for matching.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Skill {
    /// Unique skill name/identifier.
    pub name: String,
    /// Skill category for grouping.
    pub category: SkillCategory,
    /// Keywords that trigger this skill (case-insensitive).
    pub keywords: Vec<String>,
    /// Base priority score (0.0 - 1.0).
    pub priority: f32,
    /// Optional description for the skill.
    #[serde(default)]
    pub description: String,
}

/// Result of skill injection.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InjectionResult {
    /// List of matched skill names (ordered by relevance).
    pub skills: Vec<String>,
    /// Ratio of development skills to total skills (target: 0.8).
    pub dev_skill_ratio: f32,
    /// Quality reminders to include in the prompt.
    pub quality_reminders: Vec<String>,
    /// Total match score (for debugging).
    pub total_score: f32,
}

impl InjectionResult {
    /// Create an empty result.
    pub fn empty() -> Self {
        Self {
            skills: Vec::new(),
            dev_skill_ratio: 0.0,
            quality_reminders: default_quality_reminders(),
            total_score: 0.0,
        }
    }
}

/// Default quality reminders injected into all subagents.
fn default_quality_reminders() -> Vec<String> {
    vec![
        "Run tests after code changes".to_string(),
        "Follow existing code patterns".to_string(),
        "Check for type errors with pyright/mypy".to_string(),
        "Ensure 90%+ test coverage".to_string(),
        "Use descriptive variable names".to_string(),
    ]
}

/// Skill injection engine using Aho-Corasick pattern matching.
pub struct SkillInjector {
    /// Aho-Corasick automaton for keyword matching.
    ac: AhoCorasick,
    /// Mapping from keyword index to skill index.
    keyword_to_skill: Vec<usize>,
    /// Skill definitions.
    skills: Vec<Skill>,
    /// Quality reminders to inject.
    quality_reminders: Vec<String>,
}

impl SkillInjector {
    /// Create a new skill injector from skill definitions.
    ///
    /// # Arguments
    /// * `skills` - Vector of skill definitions with keywords
    ///
    /// # Example
    /// ```
    /// use kazuba_hooks::subagent::{Skill, SkillCategory, SkillInjector};
    ///
    /// let skills = vec![
    ///     Skill {
    ///         name: "python-pro".to_string(),
    ///         category: SkillCategory::Development,
    ///         keywords: vec!["python".to_string(), "async".to_string()],
    ///         priority: 0.9,
    ///         description: "Python expert".to_string(),
    ///     },
    /// ];
    /// let injector = SkillInjector::new(skills);
    /// ```
    pub fn new(skills: Vec<Skill>) -> Self {
        Self::with_reminders(skills, default_quality_reminders())
    }

    /// Create a skill injector with custom quality reminders.
    pub fn with_reminders(skills: Vec<Skill>, quality_reminders: Vec<String>) -> Self {
        // Build flattened keyword list and mapping
        let mut all_keywords = Vec::new();
        let mut keyword_to_skill = Vec::new();

        for (skill_idx, skill) in skills.iter().enumerate() {
            for keyword in &skill.keywords {
                all_keywords.push(keyword.to_lowercase());
                keyword_to_skill.push(skill_idx);
            }
        }

        // Build Aho-Corasick automaton
        let ac = if all_keywords.is_empty() {
            // Handle empty case
            build_ac_case_insensitive(&[])
        } else {
            let refs: Vec<&str> = all_keywords.iter().map(|s| s.as_str()).collect();
            build_ac_case_insensitive(&refs)
        };

        Self {
            ac,
            keyword_to_skill,
            skills,
            quality_reminders,
        }
    }

    /// Get the skill definitions.
    pub fn skills(&self) -> &[Skill] {
        &self.skills
    }

    /// Inject skills based on prompt content.
    ///
    /// # Arguments
    /// * `prompt` - The subagent prompt to analyze
    /// * `max_skills` - Maximum number of skills to inject
    ///
    /// # Returns
    /// `InjectionResult` with matched skills and quality reminders
    ///
    /// # Example
    /// ```
    /// use kazuba_hooks::subagent::{Skill, SkillCategory, SkillInjector};
    ///
    /// let skills = vec![
    ///     Skill {
    ///         name: "python-pro".to_string(),
    ///         category: SkillCategory::Development,
    ///         keywords: vec!["python".to_string(), "async".to_string()],
    ///         priority: 0.9,
    ///         description: "Python expert".to_string(),
    ///     },
    ///     Skill {
    ///         name: "research".to_string(),
    ///         category: SkillCategory::Research,
    ///         keywords: vec!["research".to_string(), "investigate".to_string()],
    ///         priority: 0.5,
    ///         description: "Research skill".to_string(),
    ///     },
    /// ];
    ///
    /// let injector = SkillInjector::new(skills);
    /// let result = injector.inject("optimize python async performance", 5);
    ///
    /// assert!(!result.skills.is_empty());
    /// assert!(result.skills.contains(&"python-pro".to_string()));
    /// ```
    pub fn inject(&self, prompt: &str, max_skills: usize) -> InjectionResult {
        if prompt.trim().is_empty() || self.skills.is_empty() {
            return InjectionResult::empty();
        }

        let prompt_lower = prompt.to_lowercase();

        // Count keyword matches per skill
        let mut skill_scores: HashMap<usize, f32> = HashMap::new();

        for mat in self.ac.find_iter(&prompt_lower) {
            let keyword_idx = mat.pattern().as_usize();
            let skill_idx = self.keyword_to_skill[keyword_idx];
            let skill = &self.skills[skill_idx];

            // Score = base priority + keyword match bonus
            let match_bonus = 1.0 / (skill.keywords.len() as f32).max(1.0);
            *skill_scores.entry(skill_idx).or_insert(skill.priority) += match_bonus;
        }

        if skill_scores.is_empty() {
            return InjectionResult::empty();
        }

        // Sort by score and take top_k
        let mut scored: Vec<(usize, f32)> = skill_scores.into_iter().collect();
        scored.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        scored.truncate(max_skills);

        // Calculate development skill ratio
        let dev_count = scored
            .iter()
            .filter(|(idx, _)| self.skills[*idx].category.is_development())
            .count();
        let dev_ratio = if scored.is_empty() {
            0.0
        } else {
            dev_count as f32 / scored.len() as f32
        };

        // Total score
        let total_score: f32 = scored.iter().map(|(_, s)| s).sum();

        // Build skill names list
        let skill_names: Vec<String> = scored
            .iter()
            .map(|(idx, _)| self.skills[*idx].name.clone())
            .collect();

        InjectionResult {
            skills: skill_names,
            dev_skill_ratio: dev_ratio,
            quality_reminders: self.quality_reminders.clone(),
            total_score,
        }
    }

    /// Check if a prompt matches any skill keywords.
    pub fn has_matches(&self, prompt: &str) -> bool {
        let prompt_lower = prompt.to_lowercase();
        self.ac.is_match(&prompt_lower)
    }
}

// ============================================================================
// Tests
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    fn create_test_skills() -> Vec<Skill> {
        vec![
            Skill {
                name: "python-pro".to_string(),
                category: SkillCategory::Development,
                keywords: vec![
                    "python".to_string(),
                    "async".to_string(),
                    "performance".to_string(),
                    "fastapi".to_string(),
                ],
                priority: 0.9,
                description: "Python expert".to_string(),
            },
            Skill {
                name: "rust-pro".to_string(),
                category: SkillCategory::Development,
                keywords: vec!["rust".to_string(), "cargo".to_string(), "tokio".to_string()],
                priority: 0.9,
                description: "Rust expert".to_string(),
            },
            Skill {
                name: "research".to_string(),
                category: SkillCategory::Research,
                keywords: vec![
                    "research".to_string(),
                    "investigate".to_string(),
                    "analyze".to_string(),
                ],
                priority: 0.5,
                description: "Research skill".to_string(),
            },
            Skill {
                name: "test-automator".to_string(),
                category: SkillCategory::Quality,
                keywords: vec![
                    "test".to_string(),
                    "testing".to_string(),
                    "coverage".to_string(),
                    "pytest".to_string(),
                ],
                priority: 0.8,
                description: "Testing expert".to_string(),
            },
            Skill {
                name: "generic-helper".to_string(),
                category: SkillCategory::Generic,
                keywords: vec!["help".to_string(), "assist".to_string()],
                priority: 0.3,
                description: "Generic helper".to_string(),
            },
        ]
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Basic Injection Tests
    // ─────────────────────────────────────────────────────────────────────────

    #[test]
    fn test_injects_matching_skills() {
        let skills = create_test_skills();
        let injector = SkillInjector::new(skills);
        let result = injector.inject("optimize python async performance", 5);

        assert!(!result.skills.is_empty());
        assert!(result.skills.contains(&"python-pro".to_string()));
    }

    #[test]
    fn test_respects_max_skills() {
        let skills = create_test_skills();
        let injector = SkillInjector::new(skills);
        let result = injector.inject("python rust research testing help", 2);

        assert_eq!(result.skills.len(), 2);
    }

    #[test]
    fn test_orders_by_score() {
        let skills = create_test_skills();
        let injector = SkillInjector::new(skills);
        let result = injector.inject("python async fastapi performance", 5);

        // Python should be first (multiple keyword matches + high priority)
        assert_eq!(result.skills.first().unwrap(), "python-pro");
    }

    #[test]
    fn test_calculates_dev_skill_ratio() {
        let skills = create_test_skills();
        let injector = SkillInjector::new(skills);

        // Only dev skills matched
        let result = injector.inject("python rust cargo", 5);
        assert!(result.dev_skill_ratio >= 0.8);

        // Mixed skills
        let result = injector.inject("python research", 5);
        assert!(result.dev_skill_ratio > 0.0);
        assert!(result.dev_skill_ratio < 1.0);
    }

    #[test]
    fn test_includes_quality_reminders() {
        let skills = create_test_skills();
        let injector = SkillInjector::new(skills);
        let result = injector.inject("python", 5);

        assert!(!result.quality_reminders.is_empty());
        assert!(result.quality_reminders.iter().any(|r| r.contains("test")));
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Edge Case Tests
    // ─────────────────────────────────────────────────────────────────────────

    #[test]
    fn test_empty_prompt_returns_empty_skills() {
        let skills = create_test_skills();
        let injector = SkillInjector::new(skills);
        let result = injector.inject("", 5);

        assert!(result.skills.is_empty());
    }

    #[test]
    fn test_whitespace_prompt_returns_empty() {
        let skills = create_test_skills();
        let injector = SkillInjector::new(skills);
        let result = injector.inject("   \t\n  ", 5);

        assert!(result.skills.is_empty());
    }

    #[test]
    fn test_no_matching_keywords() {
        let skills = create_test_skills();
        let injector = SkillInjector::new(skills);
        let result = injector.inject("completely unrelated xyz topic abc", 5);

        assert!(result.skills.is_empty());
    }

    #[test]
    fn test_empty_skills_list() {
        let injector = SkillInjector::new(Vec::new());
        let result = injector.inject("python rust testing", 5);

        assert!(result.skills.is_empty());
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Case Insensitivity Tests
    // ─────────────────────────────────────────────────────────────────────────

    #[test]
    fn test_case_insensitive_matching() {
        let skills = create_test_skills();
        let injector = SkillInjector::new(skills);

        let result_lower = injector.inject("python async", 5);
        let result_upper = injector.inject("PYTHON ASYNC", 5);
        let result_mixed = injector.inject("PyThOn AsynC", 5);

        assert_eq!(result_lower.skills, result_upper.skills);
        assert_eq!(result_lower.skills, result_mixed.skills);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Helper Method Tests
    // ─────────────────────────────────────────────────────────────────────────

    #[test]
    fn test_has_matches() {
        let skills = create_test_skills();
        let injector = SkillInjector::new(skills);

        assert!(injector.has_matches("python code"));
        assert!(injector.has_matches("RUST PROJECT"));
        assert!(!injector.has_matches("unrelated content"));
    }

    #[test]
    fn test_skills_accessor() {
        let skills = create_test_skills();
        let skill_count = skills.len();
        let injector = SkillInjector::new(skills);

        assert_eq!(injector.skills().len(), skill_count);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Category Tests
    // ─────────────────────────────────────────────────────────────────────────

    #[test]
    fn test_skill_category_is_development() {
        assert!(SkillCategory::Development.is_development());
        assert!(SkillCategory::Quality.is_development());
        assert!(!SkillCategory::Generic.is_development());
        assert!(!SkillCategory::Research.is_development());
        assert!(!SkillCategory::Domain.is_development());
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Custom Reminders Tests
    // ─────────────────────────────────────────────────────────────────────────

    #[test]
    fn test_custom_quality_reminders() {
        let skills = create_test_skills();
        let custom_reminders = vec![
            "Custom reminder 1".to_string(),
            "Custom reminder 2".to_string(),
        ];
        let injector = SkillInjector::with_reminders(skills, custom_reminders.clone());

        let result = injector.inject("python", 5);
        assert_eq!(result.quality_reminders, custom_reminders);
    }
}

// ============================================================================
// Property-Based Tests
// ============================================================================

#[cfg(test)]
mod proptests {
    use super::*;
    use proptest::prelude::*;

    fn arb_skill_category() -> impl Strategy<Value = SkillCategory> {
        prop_oneof![
            Just(SkillCategory::Development),
            Just(SkillCategory::Generic),
            Just(SkillCategory::Domain),
            Just(SkillCategory::Research),
            Just(SkillCategory::Quality),
        ]
    }

    fn arb_skill() -> impl Strategy<Value = Skill> {
        (
            "[a-z]{3,10}",                             // name
            arb_skill_category(),                      // category
            prop::collection::vec("[a-z]{2,8}", 1..5), // keywords
            0.1f32..1.0f32,                            // priority
        )
            .prop_map(|(name, category, keywords, priority)| Skill {
                name,
                category,
                keywords,
                priority,
                description: String::new(),
            })
    }

    proptest! {
        #[test]
        fn never_crashes_on_arbitrary_prompt(prompt in ".*") {
            let skills = vec![
                Skill {
                    name: "test".to_string(),
                    category: SkillCategory::Development,
                    keywords: vec!["test".to_string()],
                    priority: 0.5,
                    description: String::new(),
                },
            ];
            let injector = SkillInjector::new(skills);
            let _ = injector.inject(&prompt, 5);
        }

        #[test]
        fn respects_max_skills_limit(
            skills in prop::collection::vec(arb_skill(), 1..10),
            prompt in "[a-z ]{10,50}",
            max_skills in 1usize..10,
        ) {
            let injector = SkillInjector::new(skills);
            let result = injector.inject(&prompt, max_skills);
            prop_assert!(result.skills.len() <= max_skills);
        }

        #[test]
        fn dev_ratio_always_valid(
            skills in prop::collection::vec(arb_skill(), 1..10),
            prompt in "[a-z ]{10,50}",
        ) {
            let injector = SkillInjector::new(skills);
            let result = injector.inject(&prompt, 10);
            prop_assert!(result.dev_skill_ratio >= 0.0);
            prop_assert!(result.dev_skill_ratio <= 1.0);
        }
    }
}
