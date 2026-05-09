---
name: ui-ux-pro-max
description: Comprehensive UI/UX audit of the frontend — text overflow, touch targets, modal sizing, theme parity, focus states, loading/empty/error states, brand color consistency. Trigger on "UI 全面檢查", "audit the UI", "check UX", "/ui-audit", or after the user reports "字被切掉" / "點不到" / "顏色怪怪的".
---

# ui-ux-pro-max

Find UI/UX issues that cause real user complaints, not just style nits.

When invoked:

1. **Spawn an Explore agent** for the heavy grep work — give it this brief:

> Audit `frontend/src` for the following categories. Report each finding as `file:line | category | description | suggested fix`, grouped by P0 (user-visible now) / P1 (edge cases like long CJK text or small screens) / P2 (polish).
>
> **Categories**
> - **Text overflow** — `flex-1` without `min-w-0`, headings without `truncate`, missing `whitespace-nowrap` where it would break.
> - **Modal sizing** — `max-w-*` too small for longest CJK label, `max-h-[Xvh]` cutting on phone, missing `overflow-y-auto`.
> - **Touch targets** — buttons under 44×44 (specifically `w-8 h-8`, `p-1` on icon-only buttons). WCAG AA target.
> - **Theme parity** — hardcoded `text-slate-*` / `bg-white/*` that ignore `[data-theme="light"]` overrides; should use `var(--text-*)` / `var(--surface-*)` tokens.
> - **Focus states** — missing `focus-visible:outline-*` on interactive elements.
> - **Brand color drift** — stray `text-purple-*`, `bg-purple-*`, `text-green-*` (non-semantic), `text-pink-*` that should be rose. Project brand is orange + rose.
> - **Empty / error / loading parity** — pages that have only happy path; empty states that look like errors; spinners that hide rather than overlay content.
> - **Invalid Tailwind tokens** — spacing values not on the default scale (`ml-13`, `ml-15`, `p-9.5` etc — fall through to 0).

2. **Triage** the findings:
   - **P0** — fix immediately. User can see the bug.
   - **P1** — fix when you touch the file anyway, or in a deliberate cleanup pass.
   - **P2** — backlog; low impact.

3. **Apply fixes** in one commit per category, smallest possible diff:
   - Text overflow: add `min-w-0` to flex parent + `truncate` to child span.
   - Touch targets: bump `w-8 h-8` to `w-10 h-10` minimum, prefer `min-w-[44px] min-h-[44px]`.
   - Theme tokens: replace `text-slate-400` with `text-[var(--text-secondary)]`.
   - Brand drift: replace purple/green hex with `#fb923c` (orange-400) or `#f43f5e` (rose-500); replace `text-green-400` (non-semantic) with `text-orange-400`.
   - Invalid tokens: switch to a valid Tailwind value or use the arbitrary-value syntax `ml-[52px]`.

4. **Verify** with a quick `npm run build` — if any fix breaks the build, it's wrong.

5. **Don't** fix:
   - Mood-sentiment color scales (red-yellow-green for negative-neutral-positive — that's intentional semantic meaning).
   - Success-state greens (`text-green-400` on a "已完成" / "checked" indicator).
   - Light-theme-only changes that would regress dark theme.
