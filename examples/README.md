# Examples — Projetos Demo

Cada pasta demonstra o Kazuba em um stack real, com cenarios concretos de antes/depois.

| Exemplo | Stack | Foco |
|---------|-------|------|
| [python-api/](python-api/) | FastAPI + Python | Secrets scanner + PII detector + bash safety |
| [rust-cli/](rust-cli/) | Rust CLI | Bash safety + quality gate Rust-specific |
| [typescript-web/](typescript-web/) | Next.js + TypeScript | Secrets Stripe + PII em logs + prompt enhancement |

## Como Usar

```bash
# Instalar Kazuba em qualquer um dos exemplos
cd claude-code-kazuba
./install.sh --preset professional --target examples/python-api

# Ver plano sem instalar
./install.sh --preset standard --target examples/rust-cli --dry-run
```

## O Que Cada Exemplo Mostra

### python-api — Cenario Mais Comum

Foco: credenciais hardcoded em projetos Python/FastAPI. O cenario mais frequente de vazamento
acidental de secrets no git.

**Interceptacao-chave**: `secrets_scanner` bloqueia `postgresql://user:pass@host` antes de
qualquer `git add`.

### rust-cli — Bash Safety em Build Scripts

Foco: scripts de deploy que usam `rm -rf`, `chmod 777`, ou escrita em `/usr/local/bin`.
O Kazuba bloqueia antes de executar — nao depois.

**Interceptacao-chave**: `bash_safety` bloqueia `chmod 777` e writes em `/usr/` antes da execucao.

### typescript-web — PII em Logs de Producao

Foco: dados de usuario (email, CPF, nome) expostos em `console.log` de rotas de API.
O PII scanner detecta padroes de dados pessoais mesmo em logs de debug.

**Interceptacao-chave**: `pii_scanner` detecta email/CPF em `console.log()` dentro de API routes.

## Gravar Seu Proprio Demo

Para gravar o Kazuba em acao com `asciinema`:

```bash
# Instalar asciinema
pip install asciinema

# Gravar sessao
asciinema rec demo.cast

# Dentro da sessao gravada:
./install.sh --preset professional --target examples/python-api
cd examples/python-api
python .claude/hooks/secrets_scanner.py <<'EOF'
{"tool": "Write", "tool_input": {"path": "config.py", "content": "API_KEY = 'sk-prod-abc123'"}}
EOF

# Parar gravacao: Ctrl+D

# Converter para GIF (requer agg: https://github.com/asciinema/agg)
agg demo.cast demo.gif
```

Veja [docs/demo/RECORDING.md](../docs/demo/RECORDING.md) para instrucoes detalhadas.
