---
name: api-documentation-generator
description: Generate or update API / function documentation — OpenAPI specs, JSDoc, Python docstrings, README endpoint tables. Trigger on "document this API", "add docstring", "update OpenAPI", "write README for the auth flow".
---

# api-documentation-generator

Write docs that answer "how do I call this and what do I get back" without reading the source.

When invoked:

1. Identify the surface to document:
   - REST endpoint (DRF view) → update OpenAPI via `drf_spectacular`. Add `@extend_schema(...)` decorator.
   - Public Python function → add docstring (Google or NumPy style, match what's already in the file).
   - Public JS function → add JSDoc with `@param`, `@returns`, `@throws`.
   - Module / package → README in the same folder.
2. For each item, document:
   - **What it does** in one sentence (not "this function calls X" — describe the goal).
   - **Inputs** — types, required vs optional, valid range, examples.
   - **Outputs** — type, success shape, error shape.
   - **Side effects** — what state it mutates, what external systems it touches.
   - **Failure modes** — what exceptions / status codes, when.
3. Cite a one-line example call where it isn't obvious from types alone.
4. For OpenAPI specifically, run `python manage.py spectacular --no-color --file /tmp/schema.yaml` afterward to verify zero warnings.

Don't:
- Restate what the parameter name already tells you (`@param userId — the user ID` is noise).
- Document private helpers (the docstring is for the public surface).
- Write tutorials in docstrings (those go in README).
