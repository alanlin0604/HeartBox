---
name: find-skills
description: List all installed skills in this project (.claude/skills/) and the user-level skills (~/.claude/skills/), plus the names of built-in Claude Code skills. Use when the user asks "what skills do I have", "list skills", "which skill should I use for X", or wants a directory of available capabilities.
---

# find-skills

When invoked:

1. List entries under `.claude/skills/` (project-level) and `~/.claude/skills/` (user-level).
2. For each, read the SKILL.md frontmatter and surface its `description` so the user sees what each does without opening files.
3. Mention the built-in Claude Code skills available in this session (they appear in the system's available-skills listing).
4. If the user asked "which skill for X", match X against the descriptions and recommend the closest fit.

Output template:

```
## Project skills (.claude/skills/)
- <name> — <description first line>

## User skills (~/.claude/skills/)
- <name> — <description first line>

## Built-in (this Claude Code session)
- <names from the live skill listing>
```

Keep short — descriptions only, not the body of each skill.
