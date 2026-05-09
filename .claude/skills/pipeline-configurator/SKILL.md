---
name: pipeline-configurator
description: Set up or tune CI/CD pipelines — GitHub Actions workflows, Cloud Run deploy scripts, Cloudflare Pages, Husky pre-commit hooks. Trigger on "set up CI", "add a workflow", "the deploy is broken", "add a job that runs X on push", "speed up my CI".
---

# pipeline-configurator

When invoked:

1. Identify the pipeline target:
   - GitHub Actions (`.github/workflows/*.yml`) — most common
   - Husky local hooks (`.husky/pre-commit`, `.husky/commit-msg`)
   - Cloud Run (`Dockerfile` + `deploy-backend.ps1`)
   - Cloudflare Pages (auto-deploy on push, optional `wrangler.toml`)

2. For new workflows, set up the minimum that works:
   - **Trigger:** `push: branches: [main]` + `pull_request: branches: [main]` for the canonical case. Add `workflow_dispatch` if humans should be able to trigger manually.
   - **Concurrency:** add a concurrency group so PR pushes cancel old runs.
   - **Caching:** `actions/setup-node` + `cache: npm` for JS; `actions/setup-python` + `cache: pip` for Python.
   - **Secrets:** never paste secrets into the workflow file. Reference `${{ secrets.NAME }}` and document which secrets need setting.

3. For existing pipelines that are slow / flaky:
   - Look for un-cached install steps (most common slow point).
   - Look for tests that are run multiple times across jobs (pre-commit + CI both running full suite).
   - Look for matrix builds running things that should only run once.
   - Look for `continue-on-error` that's hiding actual failures.

4. For deploy issues:
   - Check the deploy script's prerequisites are clearly documented (e.g., `deploy-backend.ps1` needs Docker Desktop + gcloud auth).
   - Verify the deployed image / build hash matches what was supposed to ship.

Test the workflow with `act` (if available) or by pushing to a throwaway branch before merging. Don't merge a workflow change that hasn't run.
