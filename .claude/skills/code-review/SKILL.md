---
name: code-review
description: Review staged / committed / branch code for correctness, security, performance, style, and test coverage. Trigger on "review this", "code review", "check my changes", "/review", or before opening a PR. Different from the built-in `review` slash command — this one is repo-aware and uses the project's own conventions.
---

# code-review

Multi-pass review of the diff, biased toward catching bugs that would actually break in production rather than style nits.

When invoked:

1. Identify scope:
   - If a PR number / branch name is given, diff that against `main`.
   - Otherwise diff `HEAD` against `main` (or `git diff --staged` if there are staged changes).
2. Make 5 passes, in order:
   - **Correctness** — off-by-one, null deref, race conditions (especially fetch effects without `cancelled` guards in React), pagination shape mismatches in DRF list responses, missing await, stale closures in `useEffect`.
   - **Security** — injection (SQL/XSS/command), auth/authz bypass, exposed secrets, unsafe deserialization, missing CSRF, weak crypto.
   - **Performance** — N+1 queries (look for `.filter(...)` in loops without `select_related` / `prefetch_related`), oversized renders, unnecessary re-renders, missing memo.
   - **Tests** — does new code have coverage? do existing tests still apply or are they testing a now-renamed behavior?
   - **Style consistency** — does the code match nearby conventions? Does it use the project's i18n pattern (`t('...')`), brand colors (orange/rose, no purple/green), cache invalidation pattern?
3. Output as a punch list grouped by severity (Blocker / Should-fix / Nit), each with file:line and a one-line diagnosis.

Don't review what the diff doesn't touch. Don't restate what the code does — explain only what's wrong.
