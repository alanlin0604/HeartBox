---
name: log-analyzer
description: Parse and summarize logs to find error patterns, regressions, or hot endpoints. Inputs can be Cloud Run logs, Sentry exports, browser console dumps, Django request logs, or text files. Trigger on "what's in this log", "why are users hitting 500s", "find the error pattern", "summarize Sentry".
---

# log-analyzer

When invoked:

1. **Get the log source**:
   - File path the user pasted.
   - `gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=heartbox-api' --limit=500 --format=json --project=heartbox-app`
   - Sentry export (if URL provided, fetch with WebFetch).
   - Browser console (paste from DevTools).

2. **Parse**:
   - Group by error class / message (collapse stack traces of identical errors).
   - Count occurrences per group.
   - Sort by count desc, then by recency.
   - Find the smallest representative example per group (one full message + stack).

3. **Identify patterns**:
   - **Error spike** — sudden increase compared to baseline; correlate with recent deploys (`git log --since="<date>"`).
   - **Slow endpoint** — p95 latency > 1s; suggest profiling.
   - **N+1 indicator** — same SQL query repeated in burst per request.
   - **Cascade failure** — one upstream error triggering many downstream ones.
   - **Memory creep** — climbing baseline memory; suggest leak hunt.

4. **Output**:
   - Top 10 error groups with counts + example.
   - Suspected root causes for the top 3.
   - Suggested next steps (fix in code / add alert / dig deeper).

Don't:
- Dump the full log back to the user — they already have it.
- Guess at root cause without evidence; if unclear, recommend what data to collect next.
- Treat warnings as errors unless they correlate with user impact.
