# Exemplo: TypeScript Web (Next.js)

Demonstra o Kazuba em um projeto Next.js — PII scanner detectando dados de usuario em logs,
quality gate checando `console.log` em producao, e prompt enhancement para debugging.

## Setup

```bash
# A partir do root do claude-code-kazuba:
./install.sh --preset professional --target examples/typescript-web
```

## Antes do Kazuba

```typescript
// app/api/users/route.ts — gerado pelo Claude sem Kazuba
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const email = searchParams.get('email')

  const user = await db.user.findUnique({ where: { email } })

  // PII em log de producao — CPF, email, telefone
  console.log(`DEBUG: user found = ${JSON.stringify(user)}`)

  return Response.json(user)
}
```

```typescript
// lib/config.ts — credenciais hardcoded
const STRIPE_KEY = "sk_live_abc123secretkey"  // chave de producao no codigo
const DB_PASSWORD = "SuperSecret123!"
```

```bash
# Deploy script que o Claude sugere
rm -rf .next/ node_modules/   # pode ser rm -rf com wildcards perigosos
npm run build
```

## Depois do Kazuba

```
[PreToolUse] pii_scanner: WARNING
  File: app/api/users/route.ts
  Pattern: email in console.log — potential PII exposure in logs
  Context: Production API route
  Action: Warning added to context (exit 0)

[PreToolUse] quality_gate: WARNING
  File: app/api/users/route.ts
  Pattern: console.log() in production route
  Action: Warning — use structured logger in production

[PreToolUse] secrets_scanner: BLOCKED
  File: lib/config.ts
  Pattern: sk_live_[a-zA-Z0-9]{20,}
  Match: "sk_live_abc123secretkey" — Stripe live key
  Severity: CRITICAL
  Action: Write BLOCKED (exit 2)
  Suggestion: Use process.env.STRIPE_SECRET_KEY

[UserPromptSubmit] prompt_enhancer: enhanced
  Original: "por que meu fetch nao funciona"
  Intent: debug
  Techniques: chain_of_thought + few_shot_reasoning + self_validation
  CILA Level: L2 (simple debug)
```

## Instalacao

```bash
./install.sh --preset professional --target /path/to/your/nextjs-project
```

Deteccao automatica de TypeScript/Next.js via `package.json`:
- Templates CLAUDE.md com instrucoes TypeScript (tipos explícitos, no `any`)
- Quality gate ajustado para `console.log`, `any` type, funcoes sem retorno tipado
- Secrets scanner com patterns de Stripe, GitHub tokens, etc.

## Comparativo

| Cenario | Sem Kazuba | Com Kazuba |
|---------|-----------|-----------|
| Stripe live key hardcoded | Commit no git | Bloqueado imediatamente |
| `console.log(user)` em API route | Passa sem aviso | Warning: PII em log |
| `any` type espalhado | Sem controle | Quality gate detecta |
| Prompt vago "nao funciona" | Resposta generica | Enhanced: chain-of-thought + debugging estruturado |
| Sessao perdida por compactacao | Contexto perdido | Checkpoint salvo automaticamente |

## Workflow com Skills

Apos instalacao, o Claude Code tem acesso ao `/verify` command:

```
/verify
→ Invoca verification-loop skill
→ 6 fases: build, typecheck, lint, test, security, git diff
→ Relatorio estruturado antes de qualquer PR
```
