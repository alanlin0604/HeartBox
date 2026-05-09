---
name: context7
description: Pull up-to-date documentation for a third-party library / framework / API before generating code that uses it. Trigger when the user asks for code that depends on a specific library version (e.g. "using React Router v7", "with Tailwind 4", "django-celery-beat 2.9 syntax") and the assistant's training cutoff might be stale, or when there's an API surface the assistant is uncertain about.
---

# context7

Goal: avoid hallucinating outdated or wrong API signatures by fetching the actual current docs for a library before writing code that touches it.

When invoked:

1. Identify the library / framework / version the user mentioned (or that the task requires).
2. If the Context7 MCP server is configured (`mcp__context7__resolve-library-id` + `mcp__context7__get-library-docs` tools available in this session), use them:
   - First resolve the library name to a Context7 ID.
   - Then fetch the docs for the topic the user is asking about.
3. If Context7 MCP is NOT configured, fall back to WebFetch on the library's official documentation URL.
4. Cite the version number you read so the user can verify against their installed version.

Apply the docs to the code you write, not the docs the model "remembers". When the docs disagree with the model's prior knowledge, the docs win.
