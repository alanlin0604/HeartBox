---
name: web-design-guidelines
description: Apply or check the project's design system rules — brand colors, typography, spacing, component patterns. Trigger on "make this match the brand", "use the design system", "what's the right color/spacing for X", "/web-design-guidelines".
---

# web-design-guidelines

The HeartBox design system. Use this when you're writing UI from scratch or correcting drift.

## Brand colors

- **Primary:** Tailwind `orange` scale (`#fb923c` / `orange-400` for highlights, `#f97316` / `orange-500` for buttons, `#ea580c` / `orange-600` for hover).
- **Secondary:** `rose` scale (`#f43f5e` / `rose-500`). Use as the second stop of a brand gradient: `from-orange-500 to-rose-500`.
- **Surface:** glass tokens via `var(--surface-primary)` / `var(--surface-secondary)` — already theme-aware.
- **Text:** `var(--text-primary)` / `var(--text-secondary)` / `var(--text-muted)` — never hardcode `text-slate-*` or `text-gray-*`.

### Reserved semantic colors (don't replace with brand)
- `green-*` for success states only — completed habits, "已分享" pills, mood-positive scale.
- `red-*` for errors / destructive actions.
- `yellow-*` for warnings / pending states.
- Mood scale: `green-500` → `yellow-500` → `red-500` for positive → neutral → negative.

### Forbidden
- `purple-*`, `pink-*`, `indigo-*`, `violet-*` in JSX (we replaced these in commit history).
- Hex literals like `#a78bfa`, `#a855f7`, `#8b5cf6`, `#1a1440`, `#1e1b4b` — these are the old indigo / purple palette. Replace with brand orange or warm dark.

## Typography

- Headings: `font-bold` (`<h1>` 3xl, `<h2>` 2xl, `<h3>` lg).
- Body: default weight, `text-sm` for dense info, `text-base` for primary content.
- Never `<small>`; use `text-xs text-[var(--text-muted)]`.
- Truncate user-generated text in lists: `truncate` + `min-w-0` on the flex parent.

## Spacing (Tailwind default scale only)

Valid: `0 0.5 1 1.5 2 2.5 3 3.5 4 5 6 7 8 9 10 11 12 14 16 20 24 28 32 36 40 44 48 ...`.
Invalid (drop to 0): `13 15 17 18 19 21 22 23 25 26 27 29 30 31 33 34 35 37 38 39`.

If you need a value not on the scale, use arbitrary-value syntax: `ml-[52px]`.

## Component patterns

- **Modal:** `fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4` wrapping `popup-panel w-full max-w-Xxl max-h-[80vh] flex flex-col`.
- **Tab bar:** `flex gap-2` parent; each tab `flex-1 min-w-0 px-3 py-3 rounded-lg font-medium text-sm transition-all truncate`. Active: `bg-orange-500/20 text-orange-400`. Inactive: `text-[var(--text-secondary)] hover:bg-white/5`.
- **Touch targets:** ≥ 40×40px (`w-10 h-10`); WCAG-strict ≥ 44px (`w-11 h-11` or use `min-w-[44px] min-h-[44px]`).
- **Empty state:** `<EmptyState>` component, never roll a custom one.
- **Error state:** distinct from empty state — show "load failed + retry button", not the empty-state copy. The user just complained about this on the leaderboard.
- **Form:** `<input>` should have `aria-label`, validation message under the field with `text-red-400 text-xs mt-1`.

## i18n

- Every user-visible string goes through `t('namespace.key')`.
- Keep all 3 locales (zh-TW, en, ja) in sync — same key set, same count.
- Use `friends.share.sharedWithMe` style namespacing, not `friends.sharedWithMe`.

## Animations

- Use `framer-motion` for entrance / exit (already in deps).
- Default transition: `transition-colors`/`transition-transform` 200-300ms ease.
- No spinning loaders inside the user's primary content area — overlay them.
