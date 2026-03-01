# Gravando o Demo do Kazuba

Instrucoes para gravar o demo com `asciinema` e converter para GIF.

## Requisitos

```bash
# asciinema (gravacao)
pip install asciinema

# agg (conversao para GIF — precisa de Rust)
cargo install agg
# ou via pre-built: https://github.com/asciinema/agg/releases
```

## Script de Demo Recomendado

O demo ideal mostra o fluxo em ~90 segundos:
1. Instalar Kazuba em um projeto existente (20s)
2. Claude Code tentando escrever uma credencial — hook bloqueia (15s)
3. Claude Code tentando um `rm -rf` — bash safety bloqueia (15s)
4. Prompt enhancement em acao (10s)
5. `/verify` command executando quality gate completo (30s)

## Gravar

```bash
# 1. Preparar ambiente demo
cd /path/to/demo-project
git init
touch requirements.txt  # projeto Python vazio

# 2. Iniciar gravacao
asciinema rec kazuba-demo.cast --title "Kazuba — Claude Code Protection in Action" --idle-time-limit 2

# 3. Dentro da sessao (digitar devagar para o demo):
cd /path/to/claude-code-kazuba
./install.sh --preset professional --target /path/to/demo-project

# Simular secrets_scanner bloqueando:
python .claude/hooks/secrets_scanner.py <<'EOF'
{"tool": "Write", "tool_input": {"path": "config.py", "content": "DATABASE_URL = \"postgresql://admin:Secret123@prod.db:5432/app\""}}
EOF

# Simular bash_safety bloqueando:
python .claude/hooks/bash_safety.py <<'EOF'
{"tool": "Bash", "tool_input": {"command": "rm -rf /tmp/old_logs /var/log/app*"}}
EOF

# 4. Parar gravacao
exit  # ou Ctrl+D
```

## Converter para GIF

```bash
# GIF para README (largura 120 colunas, velocidade 1.5x)
agg kazuba-demo.cast kazuba-demo.gif \
  --cols 120 \
  --rows 30 \
  --speed 1.5 \
  --font-size 14

# Versao menor para badges/docs
agg kazuba-demo.cast kazuba-demo-small.gif \
  --cols 100 \
  --rows 25 \
  --speed 2.0
```

## Hospedar o GIF

Opcoes:
1. **GitHub**: Adicionar o GIF em `docs/demo/` e referenciar no README como imagem
2. **Asciinema.org**: `asciinema upload kazuba-demo.cast` → link publico
3. **vhs (alternativa)**: https://github.com/charmbracelet/vhs — script declarativo para demos

## Adicionar ao README

Apos gravar, adicionar logo apos o hero no README.md:

```markdown
<!-- Demo: adicionar GIF aqui -->
![Kazuba Demo](docs/demo/kazuba-demo.gif)
```

Ou linkar para o asciinema.org:

```markdown
[![Kazuba Demo](https://asciinema.org/a/SEU_ID.svg)](https://asciinema.org/a/SEU_ID)
```

## Script VHS (Alternativo)

Para um demo reprodutivel e animado via [vhs](https://github.com/charmbracelet/vhs):

```tape
# kazuba-demo.tape
Output docs/demo/kazuba-demo.gif

Set Shell "bash"
Set FontSize 14
Set Width 1200
Set Height 600

Type "# Instalando Kazuba em projeto Python"
Enter
Sleep 1s

Type "./install.sh --preset professional --target /tmp/demo-project"
Enter
Sleep 3s

Type "# Testando secrets scanner — deve bloquear"
Enter
Sleep 1s

Type `python .claude/hooks/secrets_scanner.py <<'EOF'`
Enter
Type `{"tool": "Write", "tool_input": {"path": "config.py", "content": "API_KEY = 'sk-prod-abc123'"}}`
Enter
Type "EOF"
Enter
Sleep 2s
```
