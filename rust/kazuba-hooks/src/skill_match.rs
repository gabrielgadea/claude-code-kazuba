//! # Skill Matching Engine
//!
//! Hybrid skill matching using:
//! 1. Pattern matching (Aho-Corasick) for keyword extraction
//! 2. Basic semantic matching (word overlap) for meaning-based matching
//!
//! Score fusion: 0.6 * semantic + 0.4 * pattern

use aho_corasick::AhoCorasick;
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};

/// Skill complexity level
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Complexity {
    Low,
    Medium,
    High,
}

/// Skill pattern definition
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct SkillPattern {
    pub name: String,
    pub keywords: Vec<String>,
    pub description: String,
    pub complexity: Complexity,
    #[serde(default)]
    pub orchestration_benefit: bool,
}

/// Match result from Aho-Corasick
#[allow(dead_code)]
struct PatternMatch {
    pattern_id: usize,
    matched_text: String,
}

/// Hybrid skill matcher using pattern + semantic matching
pub struct SkillMatcher {
    /// Fast keyword matcher using Aho-Corasick
    keyword_matcher: AhoCorasick,
    /// All keywords for pattern ID lookup
    all_keywords: Vec<String>,
    /// Skill patterns with metadata
    skills: Vec<SkillPattern>,
    /// Keyword to skill index mapping
    keyword_to_skill: HashMap<String, Vec<usize>>,
}

impl SkillMatcher {
    /// Create a new skill matcher from skill patterns
    pub fn new(skills: Vec<SkillPattern>) -> Self {
        // Build list of all keywords (lowercase)
        let all_keywords: Vec<String> = skills
            .iter()
            .flat_map(|s| s.keywords.iter().map(|k| k.to_lowercase()))
            .collect();

        // Build Aho-Corasick matcher
        let keyword_matcher = AhoCorasick::new(&all_keywords).unwrap();

        // Build keyword to skill mapping
        let mut keyword_to_skill: HashMap<String, Vec<usize>> = HashMap::new();
        for (skill_idx, skill) in skills.iter().enumerate() {
            for kw in &skill.keywords {
                let kw_lower = kw.to_lowercase();
                keyword_to_skill
                    .entry(kw_lower)
                    .or_default()
                    .push(skill_idx);
            }
        }

        Self {
            keyword_matcher,
            all_keywords,
            skills,
            keyword_to_skill,
        }
    }

    /// Get skills reference
    pub fn skills(&self) -> &[SkillPattern] {
        &self.skills
    }

    /// Find all pattern matches in text
    fn find_all(&self, text: &str) -> Vec<PatternMatch> {
        self.keyword_matcher
            .find_iter(text)
            .map(|m| PatternMatch {
                pattern_id: m.pattern().as_usize(),
                matched_text: self.all_keywords[m.pattern().as_usize()].clone(),
            })
            .collect()
    }

    /// Match skills to prompt using hybrid approach
    ///
    /// # Arguments
    /// * `prompt` - User prompt to match
    /// * `top_k` - Number of top matches to return
    ///
    /// # Returns
    /// List of (skill_index, score) tuples, sorted by score descending
    pub fn match_skills(&self, prompt: &str, top_k: usize) -> Vec<(usize, f32)> {
        let pattern_scores = self.pattern_match(prompt);
        let semantic_scores = self.semantic_match(prompt);

        // Fuse scores: 0.6*semantic + 0.4*pattern
        let mut fused: Vec<(usize, f32)> = (0..self.skills.len())
            .map(|i| {
                let pattern = pattern_scores.get(&i).copied().unwrap_or(0.0);
                let semantic = semantic_scores.get(&i).copied().unwrap_or(0.0);
                (i, 0.6 * semantic + 0.4 * pattern)
            })
            .filter(|(_, s)| *s > 0.1)
            .collect();

        fused.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        fused.truncate(top_k);
        fused
    }

    /// Pattern-based matching using Aho-Corasick
    fn pattern_match(&self, prompt: &str) -> HashMap<usize, f32> {
        let prompt_lower = prompt.to_lowercase();
        let matches = self.find_all(&prompt_lower);

        let mut skill_scores: HashMap<usize, f32> = HashMap::new();

        for m in matches {
            // Find which skill(s) this keyword belongs to
            if let Some(skill_indices) = self.keyword_to_skill.get(&m.matched_text) {
                for &skill_idx in skill_indices {
                    *skill_scores.entry(skill_idx).or_insert(0.0) += 1.0;
                }
            }
        }

        // Normalize by keyword count
        for (skill_idx, score) in skill_scores.iter_mut() {
            let keyword_count = self.skills[*skill_idx].keywords.len() as f32;
            if keyword_count > 0.0 {
                *score /= keyword_count;
            }
        }

        skill_scores
    }

    /// Simple semantic matching using word overlap (Jaccard similarity)
    fn semantic_match(&self, prompt: &str) -> HashMap<usize, f32> {
        let prompt_words: HashSet<String> = prompt
            .to_lowercase()
            .split_whitespace()
            .map(|s| s.trim_matches(|c: char| !c.is_alphanumeric()).to_string())
            .filter(|s| !s.is_empty())
            .collect();

        let mut scores: HashMap<usize, f32> = HashMap::new();

        for (idx, skill) in self.skills.iter().enumerate() {
            // Combine keywords and description words
            // Convert &String to &str before chaining with split_whitespace
            let skill_words: HashSet<String> = skill
                .keywords
                .iter()
                .map(|s| s.as_str())
                .chain(skill.description.split_whitespace())
                .map(|s| {
                    s.to_lowercase()
                        .trim_matches(|c: char| !c.is_alphanumeric())
                        .to_string()
                })
                .filter(|s| !s.is_empty())
                .collect();

            // Jaccard similarity
            let intersection = prompt_words.intersection(&skill_words).count() as f32;
            let union = prompt_words.union(&skill_words).count() as f32;

            if union > 0.0 {
                scores.insert(idx, intersection / union);
            }
        }

        scores
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_skills() -> Vec<SkillPattern> {
        vec![
            SkillPattern {
                name: "backend".to_string(),
                keywords: vec![
                    "api".to_string(),
                    "backend".to_string(),
                    "database".to_string(),
                ],
                description: "Backend development".to_string(),
                complexity: Complexity::Medium,
                orchestration_benefit: false,
            },
            SkillPattern {
                name: "frontend".to_string(),
                keywords: vec![
                    "react".to_string(),
                    "ui".to_string(),
                    "frontend".to_string(),
                ],
                description: "Frontend development".to_string(),
                complexity: Complexity::Medium,
                orchestration_benefit: false,
            },
            SkillPattern {
                name: "qa".to_string(),
                keywords: vec![
                    "test".to_string(),
                    "testing".to_string(),
                    "coverage".to_string(),
                ],
                description: "Quality assurance".to_string(),
                complexity: Complexity::Medium,
                orchestration_benefit: false,
            },
        ]
    }

    #[test]
    fn test_pattern_match_backend() {
        let matcher = SkillMatcher::new(sample_skills());
        let matches = matcher.match_skills("create an api endpoint for users", 3);

        assert!(!matches.is_empty());
        assert_eq!(matches[0].0, 0, "Backend skill should match first");
    }

    #[test]
    fn test_pattern_match_frontend() {
        let matcher = SkillMatcher::new(sample_skills());
        let matches = matcher.match_skills("build a react component for the ui", 3);

        assert!(!matches.is_empty());
        assert_eq!(matches[0].0, 1, "Frontend skill should match first");
    }

    #[test]
    fn test_pattern_match_multiple() {
        let matcher = SkillMatcher::new(sample_skills());
        let matches = matcher.match_skills("create api with react frontend and tests", 3);

        // Should match all three skills
        assert_eq!(matches.len(), 3);
    }

    #[test]
    fn test_no_match() {
        let matcher = SkillMatcher::new(sample_skills());
        let matches = matcher.match_skills("hello world", 3);

        assert!(matches.is_empty());
    }

    #[test]
    fn test_case_insensitive() {
        let matcher = SkillMatcher::new(sample_skills());
        let matches_lower = matcher.match_skills("create an api", 3);
        let matches_upper = matcher.match_skills("CREATE AN API", 3);

        assert_eq!(matches_lower.len(), matches_upper.len());
        assert_eq!(matches_lower[0].0, matches_upper[0].0);
    }
}
