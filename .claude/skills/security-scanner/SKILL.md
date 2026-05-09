---
name: security-scanner
description: Scan the codebase for security vulnerabilities — exposed secrets, OWASP Top 10 issues, vulnerable dependencies, weak crypto, missing auth checks. Trigger on "security check", "scan for vulnerabilities", "is this safe to commit", "audit dependencies", or before a release.
---

# security-scanner

Multi-layer security audit. Surface real risks first, ignore theoretical ones.

When invoked:

1. **Secret exposure**
   - Grep tracked files for API key shapes: `sk-[A-Za-z0-9]{20,}`, `AKIA[A-Z0-9]{16}`, hex strings ≥ 32 chars in source files (not config).
   - Check `.env*` files aren't committed (`.gitignore` contains `.env`, `.env.local` etc).
   - Check `git log --all -p` for accidentally-committed-then-removed secrets — if found, recommend `git-filter-repo` and key rotation.

2. **Dependency vulnerabilities**
   - JS: `npm audit --omit=dev` for production deps; only flag high/critical.
   - Python: `pip list --outdated` plus check known-vulnerable packages against PyPI advisories.

3. **Code patterns (OWASP)**
   - SQL injection: raw `execute(f"..." + ...)` or string-concatenated queries.
   - XSS: `dangerouslySetInnerHTML`, Django `mark_safe(user_input)`.
   - CSRF: DRF views without auth that mutate state.
   - Auth bypass: views with `permission_classes = []` or missing `IsAuthenticated`.
   - Path traversal: `os.path.join(MEDIA_ROOT, user_input)` without normalization.
   - Weak crypto: `md5`, `sha1`, plaintext passwords, hardcoded crypto keys.

4. **Backend-specific (Django)**
   - `DEBUG = True` in prod settings.
   - `ALLOWED_HOSTS = ['*']`.
   - `SECURE_SSL_REDIRECT = False` when serving HTTPS.
   - Missing rate limiting on auth endpoints (login, register, password reset).

5. **Frontend-specific**
   - JWT tokens stored in localStorage without size/expiry checks.
   - `eval` / `Function(...)` on user input.
   - postMessage handlers without origin check.

Output: a punch list grouped by severity (Critical / High / Medium / Info), each item linking to the file:line and suggesting the minimal fix.

Defer to specialized tools where they exist: `bandit` for Python, `semgrep` if installed, `trufflehog` for git-history secrets.
