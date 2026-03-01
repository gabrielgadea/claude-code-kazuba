# Exemplo: Python API (FastAPI)

Demonstra como o Kazuba intercepta credenciais e valida qualidade em um projeto FastAPI real.

## Setup

```bash
# A partir do root do claude-code-kazuba:
./install.sh --preset professional --target examples/python-api
cd examples/python-api
```

## Antes do Kazuba — O Que Passa Despercebido

O Claude Code sem configuracao pode gerar e salvar codigo como este sem nenhum aviso:

```python
# database.py — codigo gerado pelo Claude sem Kazuba
import psycopg2

# Credencial hardcoded vai direto para o git
DB_URL = "postgresql://admin:S3cr3tP@ssw0rd@prod.db.example.com/myapp"

conn = psycopg2.connect(DB_URL)
```

```python
# users.py — PII sem tratamento
def get_user_debug(user_id: int):
    user = db.query(User).filter(User.id == user_id).first()
    print(f"DEBUG: user={user.__dict__}")   # CPF, email, telefone no log
    return user
```

```bash
# Comando bash executado sem verificacao
rm -rf /tmp/old_data /var/log/app*   # pode destruir logs de producao
```

## Depois do Kazuba — Interceptacao em Tempo Real

```
[PreToolUse] secrets_scanner: BLOCKED
  File: database.py
  Pattern: postgresql://.*:.*@
  Match: "postgresql://admin:S3cr3tP@ssw0rd@prod..."
  Action: Write BLOCKED (exit 2)
  Suggestion: Use environment variables — os.getenv('DATABASE_URL')

[PreToolUse] pii_scanner: WARNING
  File: users.py
  Pattern: CPF/email in print() — potential PII leak in logs
  Action: Warning added to context (exit 0, not blocking)

[PreToolUse] bash_safety: BLOCKED
  Command: rm -rf /tmp/old_data /var/log/app*
  Pattern: rm -rf with wildcards
  Severity: HIGH
  Action: Bash BLOCKED (exit 2)
```

## Instalacao no Seu Projeto FastAPI

```bash
./install.sh --preset professional --target /path/to/your/fastapi-project
```

O que e instalado:

```
your-project/
└── .claude/
    ├── settings.json           # hooks registrados automaticamente
    ├── hooks/
    │   ├── secrets_scanner.py  # bloqueia credenciais
    │   ├── pii_scanner.py      # detecta CPF, email, SSN (BR/US/EU)
    │   ├── bash_safety.py      # bloqueia rm -rf, fork bombs, curl|bash
    │   └── quality_gate.py     # debug prints, docstrings ausentes
    ├── skills/
    │   └── verification-loop/  # checklist pre-PR automatizado
    └── agents/
        └── security-auditor/   # audit OWASP Top 10 sob demanda
```

## Configuracao Gerada (`.claude/settings.json`)

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {"type": "command", "command": "python .claude/hooks/secrets_scanner.py"},
          {"type": "command", "command": "python .claude/hooks/pii_scanner.py"},
          {"type": "command", "command": "python .claude/hooks/quality_gate.py"}
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {"type": "command", "command": "python .claude/hooks/bash_safety.py"}
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {"type": "command", "command": "python .claude/hooks/prompt_enhancer.py"},
          {"type": "command", "command": "python .claude/hooks/cila_router.py"}
        ]
      }
    ]
  }
}
```

## Testar a Protecao

```bash
# Verificar se os hooks estao ativos
python .claude/hooks/secrets_scanner.py <<'EOF'
{"tool": "Write", "tool_input": {"path": "config.py", "content": "API_KEY = 'sk-abc123secretkey'"}}
EOF
# Saida esperada: exit 2 + mensagem de bloqueio

# Verificar bash safety
python .claude/hooks/bash_safety.py <<'EOF'
{"tool": "Bash", "tool_input": {"command": "rm -rf /tmp/*"}}
EOF
# Saida esperada: exit 2 + motivo
```

## Stack Detectado

Ao rodar `./install.sh`, o instalador detecta automaticamente:
- `requirements.txt` ou `pyproject.toml` → Python
- `fastapi` nas dependencias → FastAPI stack
- `.env.example` → projeto usa variaveis de ambiente

Templates Jinja2 sao renderizados com essas variaveis, gerando configuracoes
especificas para FastAPI (ex: checagem de CORS, validacao de Pydantic models).
