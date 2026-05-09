---
name: dependency-manager
description: Audit, upgrade, or downgrade project dependencies. Handles npm (frontend) and pip / requirements.txt (backend). Trigger on "update dependencies", "upgrade X", "is X up to date", "downgrade Y", "what's outdated", or after a CVE alert.
---

# dependency-manager

When invoked:

1. **Survey** what's outdated:
   - JS: `cd frontend && npm outdated`
   - Python: `cd backend && ./venv/Scripts/python.exe -m pip list --outdated` (Windows) or `./venv/bin/python -m pip list --outdated` (Linux/macOS)
2. **Categorize** by risk:
   - **Patch** (1.2.3 → 1.2.4): bugfixes, almost always safe. Batch them all.
   - **Minor** (1.2.x → 1.3.x): new features, usually safe. Check changelog for deprecations.
   - **Major** (1.x → 2.x): breaking changes. Read the upgrade guide; do one at a time, run full test suite after.
3. **Prioritize**:
   - Security advisories first (run `npm audit`, check Python CVE feeds).
   - Things blocking other upgrades (e.g. peer-dep conflicts).
   - Frequently-updated frameworks (Django, React) — staying close to current saves pain later.
   - Defer: huge framework rewrites (`langchain 0.x → 1.x`) unless the new version is required.
4. **Execute**:
   - JS: `npm install <pkg>@<version>` — let the install reconcile peer deps. Run `npm test` + `npm run build` after each major bump.
   - Python: edit `requirements.txt`, then `./venv/Scripts/python.exe -m pip install -r requirements.txt`. Run `python manage.py check` and `python manage.py test api.tests --settings=moodnotes_pro.test_settings` after each major bump.
5. **Verify** prod still builds: trigger CI on a branch before merging.

Don't:
- Do an "update everything" PR. Group by package, commit per major version.
- Update lockfiles by hand.
- Skip the test run because "it's just a patch".
- Pin to exact versions (`==`) unless there's a known broken version above; prefer ranges.

Tools to suggest if not installed:
- `npm-check-updates` (`ncu`) for JS one-shot bulk update.
- `pip-tools` (`pip-compile`) for reproducible Python pins.
- Dependabot or Renovate for automation.
