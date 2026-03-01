//! Benchmarks for kazuba-hooks crate

use criterion::{black_box, criterion_group, criterion_main, Criterion};
use kazuba_hooks::{CodeQualityValidator, SecretsDetector};

fn bench_secrets_detection(c: &mut Criterion) {
    let detector = SecretsDetector::new();
    let content = r#"
    api_key = "sk-1234567890abcdefghijklmnopqrstuvwxyz123456"
    password = "my_secret_password_123"
    normal_text = "Hello, this is a normal string without secrets."
    "#;

    c.bench_function("secrets_detect", |b| {
        b.iter(|| detector.detect(black_box(content)))
    });
}

fn bench_secrets_no_match(c: &mut Criterion) {
    let detector = SecretsDetector::new();
    let content = "Hello, world! This is a normal string without any secrets or sensitive data.";

    c.bench_function("secrets_no_match", |b| {
        b.iter(|| detector.detect(black_box(content)))
    });
}

fn bench_code_quality(c: &mut Criterion) {
    let validator = CodeQualityValidator::new();
    let content = r#"
def hello():
    """Say hello."""
    # TODO: add more functionality
    print("debug")
    return "Hello, World!"

def long_function():
    x = "this is a very long line that exceeds the maximum line length of 100 characters and should trigger a warning"
    return x
"#;

    c.bench_function("code_quality_validate", |b| {
        b.iter(|| validator.validate(black_box(content), black_box("test.py")))
    });
}

criterion_group!(
    benches,
    bench_secrets_detection,
    bench_secrets_no_match,
    bench_code_quality,
);

criterion_main!(benches);
