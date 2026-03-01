//! # Unified Pattern Matching Utilities
//!
//! Shared pattern matching utilities used across all kazuba-hooks modules.
//! Provides Aho-Corasick automaton builders and common text extraction functions.

use aho_corasick::{AhoCorasick, AhoCorasickBuilder, MatchKind};
use regex::Regex;
use std::sync::LazyLock;

/// Build an optimized Aho-Corasick automaton for pattern matching.
///
/// Uses `LeftmostFirst` match kind which returns the leftmost match
/// and gives preference to patterns based on their order in the input.
///
/// # Arguments
/// * `patterns` - Slice of pattern strings to match
///
/// # Panics
/// Panics if pattern compilation fails (should never happen with valid strings).
pub fn build_ac(patterns: &[&str]) -> AhoCorasick {
    AhoCorasickBuilder::new()
        .match_kind(MatchKind::LeftmostFirst)
        .build(patterns)
        .expect("Failed to build Aho-Corasick automaton")
}

/// Build a case-insensitive Aho-Corasick automaton.
///
/// Useful for matching error messages, log entries, or user input
/// where case shouldn't matter.
///
/// # Arguments
/// * `patterns` - Slice of pattern strings to match
pub fn build_ac_case_insensitive(patterns: &[&str]) -> AhoCorasick {
    AhoCorasickBuilder::new()
        .match_kind(MatchKind::LeftmostFirst)
        .ascii_case_insensitive(true)
        .build(patterns)
        .expect("Failed to build case-insensitive Aho-Corasick automaton")
}

/// Build Aho-Corasick from owned String patterns.
///
/// Useful when patterns come from configuration files or runtime sources.
pub fn build_ac_from_strings(patterns: &[String]) -> AhoCorasick {
    AhoCorasickBuilder::new()
        .match_kind(MatchKind::LeftmostFirst)
        .build(patterns)
        .expect("Failed to build Aho-Corasick automaton from strings")
}

/// Regex for extracting module names from Python import errors.
static MODULE_NAME_REGEX: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"No module named ['"]?(\w+)"#).expect("Invalid module name regex")
});

/// Extract module name from Python import error message.
///
/// # Arguments
/// * `error` - Error message containing import failure
///
/// # Returns
/// * `Some(module_name)` if a module name was found
/// * `None` if no module name could be extracted
pub fn extract_module_name(error: &str) -> Option<String> {
    MODULE_NAME_REGEX
        .captures(error)
        .and_then(|c| c.get(1))
        .map(|m| m.as_str().to_string())
}

/// Extract directory path from file path.
///
/// Returns the parent directory of the given path, or "." if no directory separator found.
pub fn extract_directory(path: &str) -> &str {
    path.rsplit_once('/').map(|(dir, _)| dir).unwrap_or(".")
}

/// Extract file extension from path.
pub fn extract_extension(path: &str) -> Option<&str> {
    path.rsplit_once('.').map(|(_, ext)| ext)
}

/// Regex for extracting line numbers from error messages.
static LINE_NUMBER_REGEX: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?:line |:)(\d+)").expect("Invalid line number regex"));

/// Extract line number from error message.
pub fn extract_line_number(error: &str) -> Option<u32> {
    LINE_NUMBER_REGEX
        .captures(error)
        .and_then(|c| c.get(1))
        .and_then(|m| m.as_str().parse().ok())
}

/// Normalize path separators to forward slashes.
///
/// Useful for cross-platform path handling.
pub fn normalize_path(path: &str) -> String {
    path.replace('\\', "/")
}

/// Check if a string contains any dangerous shell metacharacters.
///
/// These characters can be used for command injection attacks.
pub fn has_shell_metacharacters(s: &str) -> bool {
    s.contains(['`', '$', '&', ';', '|', '\n'])
}

#[cfg(test)]
mod tests {
    use super::*;

    // =========================================================================
    // Aho-Corasick Builder Tests
    // =========================================================================

    #[test]
    fn test_build_ac_basic() {
        let ac = build_ac(&["hello", "world"]);
        assert!(ac.is_match("hello world"));
        assert!(!ac.is_match("goodbye"));
    }

    #[test]
    fn test_build_ac_empty_patterns() {
        let ac = build_ac(&[]);
        assert!(!ac.is_match("anything"));
    }

    #[test]
    fn test_build_ac_overlapping_patterns() {
        let ac = build_ac(&["rm", "rm -rf", "rm -rf /"]);
        assert!(ac.is_match("rm -rf /"));
        assert!(ac.is_match("rm file.txt"));
    }

    #[test]
    fn test_build_ac_case_insensitive_basic() {
        let ac = build_ac_case_insensitive(&["error", "warning"]);
        assert!(ac.is_match("ERROR"));
        assert!(ac.is_match("Warning"));
        assert!(ac.is_match("error"));
    }

    #[test]
    fn test_build_ac_from_strings() {
        let patterns: Vec<String> = vec!["foo".into(), "bar".into()];
        let ac = build_ac_from_strings(&patterns);
        assert!(ac.is_match("foobar"));
    }

    // =========================================================================
    // Module Name Extraction Tests
    // =========================================================================

    #[test]
    fn test_extract_module_name_quoted() {
        let error = "ModuleNotFoundError: No module named 'requests'";
        assert_eq!(extract_module_name(error), Some("requests".to_string()));
    }

    #[test]
    fn test_extract_module_name_double_quoted() {
        let error = r#"No module named "numpy""#;
        assert_eq!(extract_module_name(error), Some("numpy".to_string()));
    }

    #[test]
    fn test_extract_module_name_unquoted() {
        let error = "ImportError: No module named pandas";
        assert_eq!(extract_module_name(error), Some("pandas".to_string()));
    }

    #[test]
    fn test_extract_module_name_none() {
        let error = "SyntaxError: invalid syntax";
        assert_eq!(extract_module_name(error), None);
    }

    // =========================================================================
    // Directory Extraction Tests
    // =========================================================================

    #[test]
    fn test_extract_directory_unix_path() {
        assert_eq!(
            extract_directory("/home/user/project/src/main.py"),
            "/home/user/project/src"
        );
    }

    #[test]
    fn test_extract_directory_relative() {
        assert_eq!(extract_directory("src/main.py"), "src");
    }

    #[test]
    fn test_extract_directory_no_separator() {
        assert_eq!(extract_directory("main.py"), ".");
    }

    #[test]
    fn test_extract_directory_root() {
        assert_eq!(extract_directory("/main.py"), "");
    }

    // =========================================================================
    // Extension Extraction Tests
    // =========================================================================

    #[test]
    fn test_extract_extension_py() {
        assert_eq!(extract_extension("/src/main.py"), Some("py"));
    }

    #[test]
    fn test_extract_extension_rs() {
        assert_eq!(extract_extension("lib.rs"), Some("rs"));
    }

    #[test]
    fn test_extract_extension_none() {
        assert_eq!(extract_extension("Makefile"), None);
    }

    #[test]
    fn test_extract_extension_multiple_dots() {
        assert_eq!(extract_extension("archive.tar.gz"), Some("gz"));
    }

    // =========================================================================
    // Line Number Extraction Tests
    // =========================================================================

    #[test]
    fn test_extract_line_number_line_prefix() {
        assert_eq!(extract_line_number("Error at line 42"), Some(42));
    }

    #[test]
    fn test_extract_line_number_colon_prefix() {
        assert_eq!(extract_line_number("main.py:15: error"), Some(15));
    }

    #[test]
    fn test_extract_line_number_none() {
        assert_eq!(extract_line_number("Something went wrong"), None);
    }

    // =========================================================================
    // Path Normalization Tests
    // =========================================================================

    #[test]
    fn test_normalize_path_windows() {
        assert_eq!(
            normalize_path(r"C:\Users\test\file.py"),
            "C:/Users/test/file.py"
        );
    }

    #[test]
    fn test_normalize_path_unix() {
        assert_eq!(normalize_path("/home/user/file.py"), "/home/user/file.py");
    }

    // =========================================================================
    // Shell Metacharacter Tests
    // =========================================================================

    #[test]
    fn test_has_shell_metacharacters_backtick() {
        assert!(has_shell_metacharacters("echo `whoami`"));
    }

    #[test]
    fn test_has_shell_metacharacters_dollar() {
        assert!(has_shell_metacharacters("echo $HOME"));
    }

    #[test]
    fn test_has_shell_metacharacters_pipe() {
        assert!(has_shell_metacharacters("ls | grep foo"));
    }

    #[test]
    fn test_has_shell_metacharacters_safe() {
        assert!(!has_shell_metacharacters("ls -la"));
    }
}
