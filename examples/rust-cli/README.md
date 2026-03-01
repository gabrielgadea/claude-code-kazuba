# Exemplo: Rust CLI

Demonstra como o Kazuba protege um projeto Rust CLI — bash safety em acao durante build
e quality gates especificos para Rust (unsafe blocks, unwrap() excessivo).

## Setup

```bash
# A partir do root do claude-code-kazuba:
./install.sh --preset standard --target examples/rust-cli
```

## Antes do Kazuba

O Claude Code pode sugerir e executar comandos como:

```bash
# Script de build gerado pelo Claude — sem verificacao
rm -rf target/
cargo build --release
cp target/release/mycli /usr/local/bin/mycli   # escrita em diretorio do sistema
chmod 777 /usr/local/bin/mycli                   # permissao aberta demais
```

```rust
// main.rs — problemas que o quality gate detecta
fn load_config() -> Config {
    let content = std::fs::read_to_string("config.toml").unwrap();  // panic em producao
    let api_key = "sk-hardcoded-key-12345";  // credencial hardcoded
    toml::from_str(&content).expect("invalid config")
}
```

## Depois do Kazuba

```
[PreToolUse] bash_safety: BLOCKED
  Command: chmod 777 /usr/local/bin/mycli
  Pattern: chmod 777
  Severity: MEDIUM
  Reason: World-writable permissions — use chmod 755 instead
  Action: Bash BLOCKED (exit 2)

[PreToolUse] bash_safety: BLOCKED
  Command: cp target/release/mycli /usr/local/bin/mycli
  Pattern: write to /usr/local
  Severity: MEDIUM
  Reason: Writing to system binary directory
  Action: Bash BLOCKED (exit 2)

[PreToolUse] secrets_scanner: BLOCKED
  File: src/main.rs
  Pattern: sk-[a-zA-Z0-9]{20,}
  Match: "sk-hardcoded-key-12345"
  Action: Write BLOCKED (exit 2)

[PreToolUse] quality_gate: WARNING
  File: src/main.rs
  Pattern: .unwrap() — potential panic in production code
  Count: 1 occurrence
  Action: Warning in context (exit 0)
```

## Instalacao

```bash
./install.sh --preset standard --target /path/to/your/rust-project
```

O instalador detecta `Cargo.toml` e aplica templates especificos para Rust:
- Quality gate ajustado para `unwrap()`, `expect()` em contextos criticos
- Bash safety com patterns especificos de `cargo` e toolchain
- Templates CLAUDE.md com instrucoes de idioms Rust (RAII, ownership, error handling)

## Configuracao para Rust

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {"type": "command", "command": "python .claude/hooks/secrets_scanner.py"},
          {"type": "command", "command": "python .claude/hooks/quality_gate.py"}
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {"type": "command", "command": "python .claude/hooks/bash_safety.py"}
        ]
      }
    ]
  }
}
```

## Comparativo de Qualidade

| Cenario | Sem Kazuba | Com Kazuba |
|---------|-----------|-----------|
| `.unwrap()` em funcao critica | Passa sem aviso | Warning no contexto |
| `chmod 777` em script de deploy | Executa | Bloqueado (exit 2) |
| API key hardcoded em `main.rs` | Commit no git | Bloqueado antes de escrever |
| `rm -rf target/` acidental com `/*` | Pode destruir projeto | Bloqueado (pattern rm -rf + wildcard) |
