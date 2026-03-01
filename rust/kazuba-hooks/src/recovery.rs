//! # Failure Recovery Pattern Matcher
//!
//! High-performance error pattern matching for PostToolUseFailure events.
//! Uses Aho-Corasick for O(n) keyword matching combined with recovery strategies.
//!
//! ## Recovery Strategies
//! - **AutoFix**: Automatically apply a fix command (e.g., ruff --fix)
//! - **Suggest**: Provide a suggestion to the user
//! - **Escalate**: Require user intervention
//! - **VerifyPath**: Check if file/directory exists
//! - **Analyze**: Deeper analysis needed
//! - **TypeCheck**: Run type checker
//! - **RerunTests**: Re-run test suite
//! - **GitRecovery**: Git-related recovery
//! - **Retry**: Simple retry the operation

use crate::patterns::{build_ac_case_insensitive, extract_module_name};
use aho_corasick::AhoCorasick;
use serde::{Deserialize, Serialize};
use std::sync::LazyLock;

/// Recovery strategy types.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RecoveryStrategy {
    AutoFix,
    Suggest,
    Escalate,
    VerifyPath,
    Analyze,
    TypeCheck,
    RerunTests,
    GitRecovery,
    Retry,
    None,
}

/// A recovery pattern definition.
#[derive(Debug, Clone)]
pub struct RecoveryPattern {
    /// Keywords that trigger this recovery pattern (Aho-Corasick matched).
    pub keywords: &'static [&'static str],
    /// Recovery strategy to apply.
    pub strategy: RecoveryStrategy,
    /// Human-readable description.
    pub description: &'static str,
    /// Optional command template (supports {file_path}, {module_name}).
    pub command: Option<&'static str>,
    /// Optional suggestion message.
    pub suggestion: Option<&'static str>,
    /// Whether to automatically apply without user confirmation.
    pub auto_apply: bool,
}

/// Result of recovery analysis.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecoveryResult {
    /// Whether a recovery strategy was found.
    pub recovery_available: bool,
    /// The recovery strategy to use.
    pub strategy: RecoveryStrategy,
    /// Description of the recovery action.
    pub description: String,
    /// Formatted command to execute (if applicable).
    pub command: Option<String>,
    /// Suggestion message for the user.
    pub suggestion: Option<String>,
    /// Whether to auto-apply without confirmation.
    pub auto_apply: bool,
}

impl RecoveryResult {
    /// Create a "no recovery" result.
    pub fn none() -> Self {
        Self {
            recovery_available: false,
            strategy: RecoveryStrategy::None,
            description: "No recovery pattern matched".to_string(),
            command: None,
            suggestion: None,
            auto_apply: false,
        }
    }

    /// Create a recovery result from a pattern.
    pub fn from_pattern(pattern: &RecoveryPattern, file_path: &str, error: &str) -> Self {
        let command = pattern.command.map(|cmd| {
            let mut formatted = cmd.to_string();
            formatted = formatted.replace("{file_path}", file_path);

            // Extract module name if needed
            if formatted.contains("{module_name}") {
                let module = extract_module_name(error).unwrap_or_default();
                formatted = formatted.replace("{module_name}", &module);
            }

            formatted
        });

        Self {
            recovery_available: true,
            strategy: pattern.strategy,
            description: pattern.description.to_string(),
            command,
            suggestion: pattern.suggestion.map(|s| s.to_string()),
            auto_apply: pattern.auto_apply,
        }
    }
}

// ============================================================================
// Recovery Pattern Definitions
// ============================================================================

static RECOVERY_PATTERNS: &[RecoveryPattern] = &[
    // Linting / Formatting Errors
    RecoveryPattern {
        keywords: &["ruff", "E501", "E302", "E303", "W291", "W292", "W293"],
        strategy: RecoveryStrategy::AutoFix,
        description: "Auto-fix with ruff",
        command: Some("ruff check --fix {file_path}"),
        suggestion: None,
        auto_apply: true,
    },
    RecoveryPattern {
        keywords: &["black", "would reformat", "reformatting"],
        strategy: RecoveryStrategy::AutoFix,
        description: "Auto-format with black",
        command: Some("black {file_path}"),
        suggestion: None,
        auto_apply: true,
    },
    RecoveryPattern {
        keywords: &["isort", "import order", "imports sorted"],
        strategy: RecoveryStrategy::AutoFix,
        description: "Sort imports with isort",
        command: Some("isort {file_path}"),
        suggestion: None,
        auto_apply: true,
    },
    RecoveryPattern {
        keywords: &["prettier", "formatting"],
        strategy: RecoveryStrategy::AutoFix,
        description: "Format with prettier",
        command: Some("prettier --write {file_path}"),
        suggestion: None,
        auto_apply: true,
    },
    RecoveryPattern {
        keywords: &["eslint", "eslint error"],
        strategy: RecoveryStrategy::AutoFix,
        description: "Auto-fix with eslint",
        command: Some("eslint --fix {file_path}"),
        suggestion: None,
        auto_apply: true,
    },
    RecoveryPattern {
        keywords: &["rustfmt", "cargo fmt"],
        strategy: RecoveryStrategy::AutoFix,
        description: "Format with rustfmt",
        command: Some("cargo fmt"),
        suggestion: None,
        auto_apply: true,
    },
    // Import / Module Errors
    RecoveryPattern {
        keywords: &["ModuleNotFoundError", "No module named", "ImportError"],
        strategy: RecoveryStrategy::Suggest,
        description: "Missing Python module",
        command: None,
        suggestion: Some("Install with: uv add {module_name} or pip install {module_name}"),
        auto_apply: false,
    },
    RecoveryPattern {
        keywords: &[
            "Cannot find module",
            "Module not found",
            "ERR_MODULE_NOT_FOUND",
        ],
        strategy: RecoveryStrategy::Suggest,
        description: "Missing Node.js module",
        command: None,
        suggestion: Some("Install with: npm install or pnpm install"),
        auto_apply: false,
    },
    RecoveryPattern {
        keywords: &["unresolved import", "cannot resolve"],
        strategy: RecoveryStrategy::Suggest,
        description: "Unresolved import",
        command: None,
        suggestion: Some("Check import path or install missing package"),
        auto_apply: false,
    },
    // Permission Errors
    RecoveryPattern {
        keywords: &["PermissionError", "Permission denied", "EACCES"],
        strategy: RecoveryStrategy::Escalate,
        description: "Permission denied",
        command: None,
        suggestion: Some("Check file permissions or run with elevated privileges"),
        auto_apply: false,
    },
    // File Not Found
    RecoveryPattern {
        keywords: &["FileNotFoundError", "No such file", "ENOENT"],
        strategy: RecoveryStrategy::VerifyPath,
        description: "File not found",
        command: None,
        suggestion: Some("Verify the file path exists and is correct"),
        auto_apply: false,
    },
    RecoveryPattern {
        keywords: &["directory not found", "path not found"],
        strategy: RecoveryStrategy::VerifyPath,
        description: "Directory not found",
        command: None,
        suggestion: Some("Create the directory or verify the path"),
        auto_apply: false,
    },
    // Syntax Errors
    RecoveryPattern {
        keywords: &["SyntaxError", "invalid syntax", "unexpected token"],
        strategy: RecoveryStrategy::Analyze,
        description: "Syntax error detected",
        command: None,
        suggestion: Some("Review the code for syntax errors"),
        auto_apply: false,
    },
    RecoveryPattern {
        keywords: &["IndentationError", "unexpected indent", "expected indent"],
        strategy: RecoveryStrategy::Analyze,
        description: "Indentation error",
        command: None,
        suggestion: Some("Check indentation consistency (spaces vs tabs)"),
        auto_apply: false,
    },
    // Type Errors
    RecoveryPattern {
        keywords: &["TypeError", "type mismatch", "incompatible type"],
        strategy: RecoveryStrategy::TypeCheck,
        description: "Type error",
        command: Some("pyright {file_path}"),
        suggestion: Some("Run type checker for detailed analysis"),
        auto_apply: false,
    },
    RecoveryPattern {
        keywords: &["pyright error", "mypy error", "type:"],
        strategy: RecoveryStrategy::TypeCheck,
        description: "Type checking error",
        command: None,
        suggestion: Some("Fix type annotations or add type: ignore comment"),
        auto_apply: false,
    },
    // Test Failures
    RecoveryPattern {
        keywords: &["FAILED", "AssertionError", "test failed", "tests failed"],
        strategy: RecoveryStrategy::RerunTests,
        description: "Test failure",
        command: Some("pytest {file_path} -v"),
        suggestion: Some("Review failed test and fix the implementation"),
        auto_apply: false,
    },
    RecoveryPattern {
        keywords: &["cargo test", "test result: FAILED"],
        strategy: RecoveryStrategy::RerunTests,
        description: "Rust test failure",
        command: Some("cargo test"),
        suggestion: Some("Review failed tests"),
        auto_apply: false,
    },
    // Git Errors
    RecoveryPattern {
        keywords: &["merge conflict", "CONFLICT", "Automatic merge failed"],
        strategy: RecoveryStrategy::GitRecovery,
        description: "Git merge conflict",
        command: None,
        suggestion: Some("Resolve conflicts manually in the affected files"),
        auto_apply: false,
    },
    RecoveryPattern {
        keywords: &["not a git repository", "fatal: not a git"],
        strategy: RecoveryStrategy::GitRecovery,
        description: "Not a git repository",
        command: Some("git init"),
        suggestion: Some("Initialize a git repository"),
        auto_apply: false,
    },
    RecoveryPattern {
        keywords: &["detached HEAD", "HEAD detached"],
        strategy: RecoveryStrategy::GitRecovery,
        description: "Git detached HEAD state",
        command: None,
        suggestion: Some("Create a branch or checkout an existing branch"),
        auto_apply: false,
    },
    // Network / Connection Errors
    RecoveryPattern {
        keywords: &["ConnectionError", "ECONNREFUSED", "connection refused"],
        strategy: RecoveryStrategy::Retry,
        description: "Connection refused",
        command: None,
        suggestion: Some("Check if the server is running and retry"),
        auto_apply: false,
    },
    RecoveryPattern {
        keywords: &["TimeoutError", "ETIMEDOUT", "timed out"],
        strategy: RecoveryStrategy::Retry,
        description: "Connection timeout",
        command: None,
        suggestion: Some("Check network connectivity and retry"),
        auto_apply: false,
    },
    // Build Errors
    RecoveryPattern {
        keywords: &["cargo build", "error[E", "cannot find crate"],
        strategy: RecoveryStrategy::Analyze,
        description: "Rust build error",
        command: Some("cargo check"),
        suggestion: Some("Review compiler error messages"),
        auto_apply: false,
    },
    RecoveryPattern {
        keywords: &["npm ERR!", "npm error"],
        strategy: RecoveryStrategy::Suggest,
        description: "npm error",
        command: Some("rm -rf node_modules && npm install"),
        suggestion: Some("Try clearing node_modules and reinstalling"),
        auto_apply: false,
    },
];

// ============================================================================
// Compiled Patterns (Lazy Static)
// ============================================================================

/// All keywords flattened for Aho-Corasick matching.
static ALL_KEYWORDS: LazyLock<Vec<&'static str>> = LazyLock::new(|| {
    RECOVERY_PATTERNS
        .iter()
        .flat_map(|p| p.keywords.iter().copied())
        .collect()
});

/// Aho-Corasick automaton for all keywords.
static KEYWORDS_AC: LazyLock<AhoCorasick> =
    LazyLock::new(|| build_ac_case_insensitive(&ALL_KEYWORDS));

/// Mapping from keyword index to pattern index.
static KEYWORD_TO_PATTERN: LazyLock<Vec<usize>> = LazyLock::new(|| {
    let mut mapping = Vec::new();
    for (pattern_idx, pattern) in RECOVERY_PATTERNS.iter().enumerate() {
        for _ in pattern.keywords {
            mapping.push(pattern_idx);
        }
    }
    mapping
});

// ============================================================================
// Matcher Implementation
// ============================================================================

/// High-performance recovery pattern matcher.
///
/// Matches error messages to recovery strategies in O(n) time.
pub struct RecoveryMatcher {
    _private: (), // Prevent external construction
}

impl Default for RecoveryMatcher {
    fn default() -> Self {
        Self::new()
    }
}

impl RecoveryMatcher {
    /// Create a new recovery matcher.
    pub fn new() -> Self {
        // Force lazy initialization
        let _ = &*KEYWORDS_AC;
        let _ = &*KEYWORD_TO_PATTERN;
        Self { _private: () }
    }

    /// Match an error message to a recovery strategy.
    ///
    /// # Arguments
    /// * `error` - The error message to analyze
    ///
    /// # Returns
    /// `RecoveryResult` with the matched strategy and actions
    ///
    /// # Example
    /// ```
    /// use kazuba_hooks::recovery::RecoveryMatcher;
    ///
    /// let matcher = RecoveryMatcher::new();
    /// let result = matcher.match_error("ModuleNotFoundError: No module named 'requests'");
    /// assert!(result.recovery_available);
    /// ```
    pub fn match_error(&self, error: &str) -> RecoveryResult {
        self.match_error_with_path(error, "")
    }

    /// Match an error message with file path context.
    ///
    /// The file path is used to format recovery commands.
    pub fn match_error_with_path(&self, error: &str, file_path: &str) -> RecoveryResult {
        // Find first matching keyword
        if let Some(mat) = KEYWORDS_AC.find(error) {
            let keyword_idx = mat.pattern().as_usize();
            let pattern_idx = KEYWORD_TO_PATTERN[keyword_idx];
            let pattern = &RECOVERY_PATTERNS[pattern_idx];
            return RecoveryResult::from_pattern(pattern, file_path, error);
        }

        RecoveryResult::none()
    }

    /// Format a command template with context.
    ///
    /// # Arguments
    /// * `template` - Command template with placeholders
    /// * `file_path` - File path to substitute
    /// * `error` - Error message (for module name extraction)
    ///
    /// # Example
    /// ```
    /// use kazuba_hooks::recovery::RecoveryMatcher;
    ///
    /// let matcher = RecoveryMatcher::new();
    /// let cmd = matcher.format_command(
    ///     "ruff check --fix {file_path}",
    ///     "/src/main.py",
    ///     "",
    /// );
    /// assert_eq!(cmd, "ruff check --fix /src/main.py");
    /// ```
    pub fn format_command(&self, template: &str, file_path: &str, error: &str) -> String {
        let mut result = template.replace("{file_path}", file_path);

        if result.contains("{module_name}") {
            let module = extract_module_name(error).unwrap_or_default();
            result = result.replace("{module_name}", &module);
        }

        result
    }
}

// ============================================================================
// Tests
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    // ─────────────────────────────────────────────────────────────────────────
    // Linting / Formatting Recovery Tests
    // ─────────────────────────────────────────────────────────────────────────

    #[test]
    fn test_matches_ruff_error() {
        let matcher = RecoveryMatcher::new();
        let result = matcher.match_error("ruff check error: E501 line too long");
        assert!(result.recovery_available);
        assert_eq!(result.strategy, RecoveryStrategy::AutoFix);
        assert!(result.auto_apply);
    }

    #[test]
    fn test_matches_ruff_with_file_path() {
        let matcher = RecoveryMatcher::new();
        let result = matcher.match_error_with_path("ruff error", "/src/main.py");
        assert!(result.recovery_available);
        assert_eq!(
            result.command,
            Some("ruff check --fix /src/main.py".to_string())
        );
    }

    #[test]
    fn test_matches_black_error() {
        let matcher = RecoveryMatcher::new();
        let result = matcher.match_error("black would reformat main.py");
        assert!(result.recovery_available);
        assert_eq!(result.strategy, RecoveryStrategy::AutoFix);
    }

    #[test]
    fn test_matches_eslint_error() {
        let matcher = RecoveryMatcher::new();
        let result = matcher.match_error("eslint error in app.js");
        assert!(result.recovery_available);
        assert_eq!(result.strategy, RecoveryStrategy::AutoFix);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Import Error Recovery Tests
    // ─────────────────────────────────────────────────────────────────────────

    #[test]
    fn test_matches_module_not_found() {
        let matcher = RecoveryMatcher::new();
        let result = matcher.match_error("ModuleNotFoundError: No module named 'requests'");
        assert!(result.recovery_available);
        assert_eq!(result.strategy, RecoveryStrategy::Suggest);
        assert!(!result.auto_apply);
    }

    #[test]
    fn test_matches_import_error() {
        let matcher = RecoveryMatcher::new();
        let result = matcher.match_error("ImportError: cannot import name 'foo'");
        assert!(result.recovery_available);
        assert_eq!(result.strategy, RecoveryStrategy::Suggest);
    }

    #[test]
    fn test_matches_node_module_not_found() {
        let matcher = RecoveryMatcher::new();
        let result = matcher.match_error("Error: Cannot find module 'express'");
        assert!(result.recovery_available);
        assert_eq!(result.strategy, RecoveryStrategy::Suggest);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Permission / File Error Tests
    // ─────────────────────────────────────────────────────────────────────────

    #[test]
    fn test_matches_permission_error() {
        let matcher = RecoveryMatcher::new();
        let result = matcher.match_error("PermissionError: [Errno 13] Permission denied");
        assert!(result.recovery_available);
        assert_eq!(result.strategy, RecoveryStrategy::Escalate);
    }

    #[test]
    fn test_matches_file_not_found() {
        let matcher = RecoveryMatcher::new();
        let result = matcher.match_error("FileNotFoundError: No such file or directory");
        assert!(result.recovery_available);
        assert_eq!(result.strategy, RecoveryStrategy::VerifyPath);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Syntax Error Tests
    // ─────────────────────────────────────────────────────────────────────────

    #[test]
    fn test_matches_syntax_error() {
        let matcher = RecoveryMatcher::new();
        let result = matcher.match_error("SyntaxError: invalid syntax at line 10");
        assert!(result.recovery_available);
        assert_eq!(result.strategy, RecoveryStrategy::Analyze);
    }

    #[test]
    fn test_matches_indentation_error() {
        let matcher = RecoveryMatcher::new();
        let result = matcher.match_error("IndentationError: unexpected indent");
        assert!(result.recovery_available);
        assert_eq!(result.strategy, RecoveryStrategy::Analyze);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Type Error Tests
    // ─────────────────────────────────────────────────────────────────────────

    #[test]
    fn test_matches_type_error() {
        let matcher = RecoveryMatcher::new();
        let result = matcher.match_error("TypeError: expected str, got int");
        assert!(result.recovery_available);
        assert_eq!(result.strategy, RecoveryStrategy::TypeCheck);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Test Failure Tests
    // ─────────────────────────────────────────────────────────────────────────

    #[test]
    fn test_matches_test_failure() {
        let matcher = RecoveryMatcher::new();
        let result = matcher.match_error("FAILED test_foo.py::test_bar - AssertionError");
        assert!(result.recovery_available);
        assert_eq!(result.strategy, RecoveryStrategy::RerunTests);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Git Error Tests
    // ─────────────────────────────────────────────────────────────────────────

    #[test]
    fn test_matches_merge_conflict() {
        let matcher = RecoveryMatcher::new();
        let result = matcher.match_error("CONFLICT (content): Merge conflict in main.py");
        assert!(result.recovery_available);
        assert_eq!(result.strategy, RecoveryStrategy::GitRecovery);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // No Match Tests
    // ─────────────────────────────────────────────────────────────────────────

    #[test]
    fn test_no_match_returns_none() {
        let matcher = RecoveryMatcher::new();
        let result = matcher.match_error("Some random error message");
        assert!(!result.recovery_available);
        assert_eq!(result.strategy, RecoveryStrategy::None);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Format Command Tests
    // ─────────────────────────────────────────────────────────────────────────

    #[test]
    fn test_format_command_with_file_path() {
        let matcher = RecoveryMatcher::new();
        let cmd = matcher.format_command("ruff check --fix {file_path}", "/src/main.py", "");
        assert_eq!(cmd, "ruff check --fix /src/main.py");
    }

    #[test]
    fn test_format_command_with_module_name() {
        let matcher = RecoveryMatcher::new();
        let cmd = matcher.format_command(
            "pip install {module_name}",
            "",
            "No module named 'requests'",
        );
        assert_eq!(cmd, "pip install requests");
    }

    #[test]
    fn test_format_command_missing_module() {
        let matcher = RecoveryMatcher::new();
        let cmd = matcher.format_command("pip install {module_name}", "", "Some other error");
        assert_eq!(cmd, "pip install ");
    }
}

// ============================================================================
// Property-Based Tests
// ============================================================================

#[cfg(test)]
mod proptests {
    use super::*;
    use proptest::prelude::*;

    proptest! {
        #[test]
        fn never_crashes_on_error_input(s in ".*") {
            let matcher = RecoveryMatcher::new();
            let _ = matcher.match_error(&s);
        }

        #[test]
        fn format_command_never_crashes(
            template in ".*",
            file_path in ".*",
            error in ".*"
        ) {
            let matcher = RecoveryMatcher::new();
            let _ = matcher.format_command(&template, &file_path, &error);
        }
    }
}
