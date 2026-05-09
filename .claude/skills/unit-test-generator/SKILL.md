---
name: unit-test-generator
description: Write unit tests for an existing function, module, or component that lacks coverage. Trigger on "write tests for X", "add tests", "I need test coverage on Y", or after implementing a non-trivial function.
---

# unit-test-generator

Generate tests that catch real bugs, not tests that just exercise lines for coverage.

When invoked:

1. Detect the test framework from the project:
   - JS / React: vitest in `frontend/` (look at existing `*.test.jsx` files)
   - Python: Django `unittest` (`backend/api/tests.py`) or pytest if configured
2. Read the function under test. Identify:
   - **Happy path** — typical input → expected output
   - **Boundaries** — empty / null / max-size / exactly-zero / off-by-one
   - **Error paths** — invalid input, network failure, permission denied
   - **State-dependent paths** — does the function behave differently based on shared state? cache?
3. Write one test per case. Each test:
   - Has a descriptive name (what behavior, not what method)
   - Uses the project's existing test helpers (e.g. `APITestCase`, `renderHook`)
   - Asserts on observable behavior, not internal implementation
   - Doesn't mock what you don't have to (mocking the DB defeats integration tests)
4. Run the new tests immediately. If they pass first try, double-check — they might be tautological. A good unit test should fail when you break the function.

Avoid:
- Testing private helpers directly (test the public surface)
- One mega-test that runs through every code path
- Mocking the system-under-test
- Snapshot tests for things that change frequently
