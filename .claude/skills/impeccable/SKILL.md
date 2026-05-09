---
name: impeccable
description: Multi-pass top-to-bottom audit of the project — combines security, UI/UX, performance, dependency, lint, and i18n checks into one coordinated sweep. Heavyweight; use sparingly. Trigger on "impeccable check", "全面健檢", "做最徹底的檢查", or before a major release / Play Store submission / investor demo.
---

# impeccable

Highest-cost, highest-coverage audit. Coordinates the other audit skills + adds cross-cutting checks they miss individually.

When invoked, run these in order. Each one can spawn its own Agent to keep context manageable:

1. **Security pass** — invoke the `security-scanner` skill. Block on Critical findings.
2. **Dependency pass** — invoke `dependency-manager`. Note CVEs, defer big upgrades to their own task.
3. **Lint + types pass** —
   - `cd frontend && npx eslint src --ext .js,.jsx` → 0 errors required.
   - `cd backend && ./venv/Scripts/python.exe manage.py check` → 0 issues required.
4. **Test pass** —
   - `cd frontend && npx vitest run` → all green.
   - `cd backend && ./venv/Scripts/python.exe manage.py test api.tests --settings=moodnotes_pro.test_settings` → all green.
5. **Build pass** — `cd frontend && npm run build` → no warnings about chunk size > 1MB or missing source maps.
6. **i18n pass** — invoke an Explore agent to find every `t('xxx')` call and diff against `frontend/src/locales/{zh-TW,en,ja}.json`. Zero missing keys, zero drift.
7. **UI/UX pass** — invoke `ui-ux-pro-max`. Fix all P0 immediately.
8. **Race condition pass** — Explore agent looks for `useEffect` blocks with non-empty deps that do `something.then(setX)` without `cancelled`/`AbortController` guard.
9. **Pagination pass** — Explore agent checks for DRF list endpoints consumed by frontend without `.results` unwrapping.
10. **Accessibility pass** — keyboard nav on every interactive element, alt text on images, aria-label on icon-only buttons, color contrast ≥ 4.5:1.
11. **Performance pass** — bundle size analysis (`stats.html`), check for chunks > 500KB; backend N+1 detection (`django-debug-toolbar` if installed).
12. **Cross-pass synthesis** — the most valuable findings are issues that span layers. Examples already seen in this project:
    - `/habits` 404 in frontend was actually a backend deploy gap, not a frontend bug.
    - `/friends` leaderboard "操作失敗" was caused by 3 layers: missing i18n key + missing endpoint + frontend conflating "no data" with "fetch failed".
    Look for those.

Output: a punch list grouped by severity, each item linked to evidence (file:line, log line, screenshot location). End with a one-paragraph executive summary the user can paste into a release notes / standup update.

Don't:
- Run this on every commit — it's expensive.
- Auto-fix Critical security findings without surfacing them first.
- Bundle wildly different categories into one giant commit.
