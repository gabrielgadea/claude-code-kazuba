# Security Rules

Security principles and practices. Every developer is responsible for
security — it is not delegated to a separate team or phase.

---

## OWASP Top 10 Awareness

Be aware of and actively guard against:

1. **Broken Access Control** — Enforce least privilege. Verify authorization on every request.
2. **Cryptographic Failures** — Use strong algorithms (AES-256, SHA-256+). Never roll your own crypto.
3. **Injection** — Parameterize all queries. Never concatenate user input into SQL, shell commands, or templates.
4. **Insecure Design** — Threat model early. Security is a design concern, not a patch.
5. **Security Misconfiguration** — No default credentials. Disable unnecessary features. Review configs.
6. **Vulnerable Components** — Audit dependencies regularly. Pin versions. Update promptly.
7. **Authentication Failures** — Use proven libraries. Enforce strong passwords. Implement MFA where possible.
8. **Data Integrity Failures** — Verify integrity of updates, CI/CD pipelines, and serialized data.
9. **Logging Failures** — Log security events. Never log secrets, tokens, or PII.
10. **SSRF** — Validate and sanitize all URLs. Restrict outbound requests to known hosts.

---

## Secrets Management

- **NEVER commit secrets** to version control. Not even "temporarily."
  - API keys, tokens, passwords, private keys, certificates.
  - Use `.gitignore` and pre-commit hooks to prevent accidental commits.
- **Use environment variables** for runtime secrets.
  - Load from `.env` files (gitignored) in development.
  - Use secret managers (AWS Secrets Manager, Vault, etc.) in production.
- **Rotate secrets regularly.** Automate rotation where possible.
- **Audit git history** if a secret was ever committed. Rotation is mandatory.
- **Never log secrets.** Mask or redact in all output, including error messages.
- **Never hardcode secrets** in source code, config files, or documentation.

---

## PII Handling

- **Minimize collection.** Only collect PII that is strictly necessary.
- **Encrypt at rest and in transit.** TLS for transport, encryption for storage.
- **Access control on PII.** Role-based access, audit logs for access.
- **Anonymize or pseudonymize** for development, testing, and analytics.
- **Data retention policies.** Define and enforce how long PII is kept.
- **Right to deletion.** Design systems so PII can be fully removed.
- **Never log PII.** Not in application logs, error reports, or analytics.

---

## Input Validation at Boundaries

- **Validate ALL external input** — user input, API responses, file contents,
  environment variables, command-line arguments.
- **Validate at the boundary**, not deep inside business logic.
  - Parse and validate early, then pass validated/typed data inward.
- **Whitelist over blacklist.** Define what IS allowed, not what is NOT.
- **Type coercion is not validation.** `int("42")` succeeds, but is "42" a valid age?
- **Length limits on all strings.** Prevent buffer overflows and DoS via large payloads.
- **Sanitize for the output context** — HTML-encode for web, parameterize for SQL,
  escape for shell commands.

---

## Dependency Security

- **Pin exact versions** in production (`==` not `>=`). Use lock files.
- **Audit dependencies** before adding. Check maintenance status, known vulnerabilities.
- **Minimize dependencies.** Every dependency is an attack surface.
- **Run security scanners** regularly — `pip-audit`, `npm audit`, `cargo audit`, etc.
- **Update promptly** when security advisories are published.
- **Verify package integrity.** Use checksums and signed packages where available.
- **No wild imports.** Only import what you need from a dependency.

---

## Secure Defaults

- **Fail closed.** When in doubt, deny access. Errors should not grant permissions.
- **Principle of least privilege.** Grant minimum permissions necessary.
- **Defense in depth.** Multiple layers of security. No single point of failure.
- **Security headers** on all HTTP responses (CSP, HSTS, X-Content-Type-Options).
- **HTTPS everywhere.** No exceptions in production.
- **Disable debug mode** in production. No stack traces in user-facing errors.
