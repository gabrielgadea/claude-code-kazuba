//! # Code Quality Validation Engine
//!
//! High-performance code quality validation using pattern matching.
//! Detects anti-patterns, style issues, and security concerns.

use aho_corasick::AhoCorasick;
use std::collections::HashMap;

/// Issue severity level
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Severity {
    Error,
    Warning,
    Info,
}

/// Code quality issue
#[derive(Debug, Clone)]
pub struct Issue {
    pub line: usize,
    pub column: usize,
    pub severity: Severity,
    pub message: String,
    pub code: String,
}

/// Validation result
#[derive(Debug, Clone)]
pub struct ValidationResult {
    pub passed: bool,
    pub issues: Vec<Issue>,
    pub score: f32,
}

/// Validation rules for specific file types
#[derive(Debug, Clone)]
pub struct ValidationRules {
    pub max_line_length: usize,
    pub require_docstring: bool,
    pub banned_imports: Vec<String>,
}

/// High-performance code quality validator
pub struct CodeQualityValidator {
    /// Anti-patterns to detect
    anti_pattern_matcher: AhoCorasick,
    /// Anti-pattern strings for lookup
    anti_patterns: Vec<&'static str>,
    /// Anti-pattern descriptions
    anti_pattern_descriptions: Vec<&'static str>,
    /// File extension validators
    extension_rules: HashMap<String, ValidationRules>,
}

impl CodeQualityValidator {
    /// Create a new code quality validator with default rules
    pub fn new() -> Self {
        let anti_patterns: Vec<&'static str> = vec![
            "TODO",
            "FIXME",
            "HACK",
            "XXX",
            "print(",
            "console.log(",
            "import pdb",
            "debugger",
            "password =",
            "secret =",
        ];

        let anti_pattern_descriptions = vec![
            "TODO comment found",
            "FIXME comment found",
            "HACK comment found",
            "XXX comment found",
            "Debug print statement",
            "Debug console.log statement",
            "Debug pdb import",
            "Debug debugger statement",
            "Potential hardcoded password",
            "Potential hardcoded secret",
        ];

        let anti_pattern_matcher = AhoCorasick::new(&anti_patterns).unwrap();

        Self {
            anti_pattern_matcher,
            anti_patterns,
            anti_pattern_descriptions,
            extension_rules: Self::default_rules(),
        }
    }

    fn default_rules() -> HashMap<String, ValidationRules> {
        let mut rules = HashMap::new();

        rules.insert(
            "py".to_string(),
            ValidationRules {
                max_line_length: 100,
                require_docstring: true,
                banned_imports: vec!["import *".to_string()],
            },
        );

        rules.insert(
            "rs".to_string(),
            ValidationRules {
                max_line_length: 100,
                require_docstring: false,
                banned_imports: vec![],
            },
        );

        rules.insert(
            "js".to_string(),
            ValidationRules {
                max_line_length: 100,
                require_docstring: false,
                banned_imports: vec![],
            },
        );

        rules.insert(
            "ts".to_string(),
            ValidationRules {
                max_line_length: 100,
                require_docstring: false,
                banned_imports: vec![],
            },
        );

        rules
    }

    /// Get file extension from path
    fn get_extension(file_path: &str) -> Option<String> {
        std::path::Path::new(file_path)
            .extension()
            .and_then(|e| e.to_str())
            .map(|s| s.to_lowercase())
    }

    /// Validate code content
    pub fn validate(&self, content: &str, file_path: &str) -> ValidationResult {
        let mut issues = Vec::new();
        let extension = Self::get_extension(file_path);
        let rules = extension
            .as_ref()
            .and_then(|ext| self.extension_rules.get(ext));

        // Check anti-patterns using Aho-Corasick
        for mat in self.anti_pattern_matcher.find_iter(content) {
            let pattern_idx = mat.pattern().as_usize();
            let start = mat.start();

            let line = content[..start].matches('\n').count() + 1;
            let line_start = content[..start].rfind('\n').map(|i| i + 1).unwrap_or(0);
            let column = start - line_start;

            // Find description for this pattern
            let description = self
                .anti_pattern_descriptions
                .get(pattern_idx)
                .copied()
                .unwrap_or("Anti-pattern detected");

            let matched_text = self.anti_patterns[pattern_idx];

            issues.push(Issue {
                line,
                column,
                severity: Severity::Warning,
                message: format!("{}: '{}'", description, matched_text),
                code: "ANTI_PATTERN".to_string(),
            });
        }

        // Check line length
        let max_line_length = rules.map(|r| r.max_line_length).unwrap_or(100);
        for (i, line) in content.lines().enumerate() {
            if line.len() > max_line_length {
                issues.push(Issue {
                    line: i + 1,
                    column: max_line_length,
                    severity: Severity::Warning,
                    message: format!("Line too long ({} > {})", line.len(), max_line_length),
                    code: "LINE_LENGTH".to_string(),
                });
            }
        }

        // Check banned imports (for Python files)
        if let Some(rules) = rules {
            for banned in &rules.banned_imports {
                if content.contains(banned) {
                    let line = content
                        .lines()
                        .enumerate()
                        .find(|(_, l)| l.contains(banned))
                        .map(|(i, _)| i + 1)
                        .unwrap_or(1);

                    issues.push(Issue {
                        line,
                        column: 0,
                        severity: Severity::Error,
                        message: format!("Banned import: {}", banned),
                        code: "BANNED_IMPORT".to_string(),
                    });
                }
            }
        }

        // Calculate score and determine pass/fail
        let error_count = issues
            .iter()
            .filter(|i| matches!(i.severity, Severity::Error))
            .count();
        let passed = error_count == 0;
        let score = if issues.is_empty() {
            100.0
        } else {
            (100.0 - (issues.len() as f32 * 5.0)).max(0.0)
        };

        ValidationResult {
            passed,
            issues,
            score,
        }
    }
}

impl Default for CodeQualityValidator {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_detect_todo() {
        let validator = CodeQualityValidator::new();
        let content = "# TODO: implement this function";
        let result = validator.validate(content, "test.py");

        assert!(result.issues.iter().any(|i| i.code == "ANTI_PATTERN"));
        assert!(result.issues.iter().any(|i| i.message.contains("TODO")));
    }

    #[test]
    fn test_detect_fixme() {
        let validator = CodeQualityValidator::new();
        let content = "// FIXME: broken code here";
        let result = validator.validate(content, "test.js");

        assert!(result.issues.iter().any(|i| i.message.contains("FIXME")));
    }

    #[test]
    fn test_detect_print() {
        let validator = CodeQualityValidator::new();
        let content = "print(\"debug output\")";
        let result = validator.validate(content, "test.py");

        assert!(result.issues.iter().any(|i| i.message.contains("print")));
    }

    #[test]
    fn test_line_length() {
        let validator = CodeQualityValidator::new();
        let long_line = "x".repeat(150);
        let result = validator.validate(&long_line, "test.py");

        assert!(result.issues.iter().any(|i| i.code == "LINE_LENGTH"));
    }

    #[test]
    fn test_clean_code() {
        let validator = CodeQualityValidator::new();
        let content = r#"
def hello():
    """Say hello."""
    return "Hello, World!"
"#;
        let result = validator.validate(content, "test.py");

        assert!(result.passed);
        assert!(result.issues.is_empty());
        assert_eq!(result.score, 100.0);
    }

    #[test]
    fn test_banned_import() {
        let validator = CodeQualityValidator::new();
        let content = "from module import *";
        let result = validator.validate(content, "test.py");

        assert!(!result.passed);
        assert!(result.issues.iter().any(|i| i.code == "BANNED_IMPORT"));
        assert!(result
            .issues
            .iter()
            .any(|i| matches!(i.severity, Severity::Error)));
    }

    #[test]
    fn test_score_calculation() {
        let validator = CodeQualityValidator::new();
        let content = "# TODO\n# FIXME\n# HACK";
        let result = validator.validate(content, "test.py");

        // 3 issues * 5 points = 15 points deducted
        assert!(result.score < 100.0);
        assert!(result.score >= 85.0);
    }
}
