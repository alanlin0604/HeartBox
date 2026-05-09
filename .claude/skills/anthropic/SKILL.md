---
name: anthropic
description: Build, debug, or modify Anthropic API / Claude SDK code in this project. Triggers when files import `anthropic` / `@anthropic-ai/sdk`, when the user mentions Claude API, prompt caching, tool use, batches, files API, citations, memory, thinking, or wants to migrate model versions (4.5 → 4.6 → 4.7). Defer to the built-in `claude-api` skill if available — this is a project-local pointer.
---

# anthropic

This project's wrapper around Anthropic SDK work. The built-in Claude Code `claude-api` skill already covers the heavy lifting (caching, model migration, thinking mode, etc); this skill exists to make sure tasks in this repo go through it consistently.

When invoked:

1. If the built-in `claude-api` skill is listed in this session, hand off to it via the `Skill` tool.
2. Otherwise, follow the canonical Anthropic best practices yourself:
   - Default to the latest models: `claude-opus-4-7`, `claude-sonnet-4-6`, `claude-haiku-4-5-20251001`.
   - Add `cache_control` to system prompts and stable tool definitions; aim for 80%+ cache hit rate on multi-turn flows.
   - Use `extra_headers={"anthropic-beta": "interleaved-thinking-2025-05-14"}` for tasks that benefit from reasoning between tool calls.
   - For long-running batch work (>10 requests), use the Message Batches API.
3. When migrating model versions, audit the prompt for hard-coded model strings, max_tokens that may need bumping, and tool schemas that newer models handle differently.
