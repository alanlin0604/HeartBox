---
name: refactoring-assistant
description: Identify and execute safe refactors — extract function, rename, move file, replace conditional with polymorphism, collapse duplicate code, modernize legacy patterns. Trigger on "refactor", "clean up", "this is getting messy", "break this apart", or when reviewing a function over ~100 lines / a file over ~500 lines.
---

# refactoring-assistant

Apply safe, behavior-preserving transformations. Each refactor must:
- Keep tests green at every step (commit-by-commit if requested).
- Not silently change behavior.
- Reduce duplication or increase clarity — no abstraction for its own sake.

When invoked:

1. Identify the smell:
   - Long function (>80 lines, multiple responsibilities)
   - Duplicate code (3+ near-identical blocks)
   - Deep nesting (>3 levels of `if` / `for`)
   - Magic numbers / strings (regex pattern, threshold, config) used in multiple places
   - Mixed concerns (data fetch + business logic + UI in one function)
   - God object / module (>500 lines, unfocused exports)
2. Pick the smallest refactor that fixes it. Common moves:
   - **Extract function** — pull a chunk into a named helper
   - **Extract module** — move related helpers into their own file
   - **Replace nested conditionals with guard clauses** — early return on the unhappy path
   - **Replace duplicate string with const** — define once, reference everywhere
   - **Replace boolean parameter with two functions** — `do(x, true)` → `doForCase1(x)` / `doForCase2(x)`
3. Run tests after each step. If they fail, the refactor changed behavior — back out and try smaller.
4. Don't refactor and add a feature in the same commit. Commit the refactor, then commit the feature on top.

Avoid:
- Premature abstraction (3 similar lines is not a pattern; 5+ is).
- Renaming public APIs without grep'ing all call sites.
- "While I'm here" cleanup of unrelated code.
