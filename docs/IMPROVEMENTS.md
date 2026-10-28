# UI improvements found in the screenshot review (for Phase 6)

Source: `docs/screenshots/` (36 captures, desktop 1440px and mobile 375px), taken 2026-10-26 from a production build with the seeded demo user (`backend/scripts/seed_demo.py`) and a brand-new user. Regenerate with `cd frontend && npm run screenshots`.

Priority: **P1** = broken or misleading, **P2** = clearly visible polish problem, **P3** = nice to have.

**Every item is fixed:** P1 on 2026-10-27, P2 and P3 in Phase 6 (2026-10-28). Screenshots re-captured after the fixes.

## P1: broken or misleading (fixed)

| # | Where | Problem | Fix and regression test |
|---|---|---|---|
| 1 | Dashboard → Daily Spending Trend | **The bars were squeezed into the first ~2 days of the x-axis.** | **Not a React 19 regression.** The data and layout were correct; the full-page screenshot resizes the viewport and Recharts re-animates the bars from their old positions, so the capture caught them mid-animation. Real users only saw it briefly on resize. Fix: charts respect `prefers-reduced-motion`, and screenshots emulate it. Test: `e2e/layout.spec.ts` resizes the page and checks the bars span the chart immediately. |
| 2 | Expenses (mobile) | **Horizontal overflow: the page was 392px wide at 375px.** | Filters stack on phones; the date range is a 3-column grid. Test: `e2e/layout.spec.ts` checks no page (public and signed-in) is wider than a 375px screen. |
| 3 | Settings (mobile) | **Horizontal overflow: the page was 502px wide.** | Monthly Budgets header wraps. Same test as #2. |
| 4 | Dashboard → Recent Expenses (touch) | The edit button only appeared on **hover**, so phone users couldn't edit from the dashboard. | Always visible, with an accessible name. Test: no `group-hover:opacity` anywhere, and tapping Edit on a touch device opens the dialog. |
| 5 | Dashboard → "Daily Average" | Divided by **every day of the month**, understating the average mid-month. | Divides by days elapsed in the period (Asia/Dhaka); label "Per day so far". Test: `src/lib/stats.test.ts` (the Oct 26 case: ৳45,700 / 26 ≈ ৳1,757.69). |
| 6 | Dashboard → "Upcoming Bills" stat card | Counted **income** items as bills. | Card counts bills only ("Bills Due") and shows "N income expected" underneath. Test: `src/lib/stats.test.ts`. |

## P2: visible polish problems (fixed in Phase 6, 2026-10-28)

| # | Where | Problem | Fix |
|---|---|---|---|
| 7 | Navbar (mobile) | Seven bare icons with no labels; the logo and the active page looked like one control | Phones get a **bottom tab bar** with an icon and a label for each page; the top bar keeps the logo, theme and sign-out. Pages say which link is current (`aria-current`). |
| 8 | Dashboard (mobile) | Four stat cards stacked full-width (~1,300px of scrolling) | **2×2 grid** with compact cards on phones |
| 9 | Spending by Category legend | Truncated names; only the top 6 of 11 with no hint of the rest | Full names with each category's share (%), the top 6 and "+N more" |
| 10 | Daily Spending Trend | `৳16000` without separators; a ৳0–৳4 axis with no bars for a new user | Axis labels `৳16K`; an empty state with "Add an expense" when there's no spending |
| 11 | Expenses / Income rows (mobile) | Dates wrapped; edit/delete moved row to row | One shared row layout with fixed columns: the note truncates, the date never wraps (on phones it moves into the second line), actions always in the same place |
| 12 | Recent Expenses (mobile) | Amounts not aligned | Fixed right-hand column for amounts |
| 13 | Settings → Monthly Budgets (mobile) | "৳3,205 / ৳2,500" wrapped into the name | Name and actions on the first line; amounts and % used on their own line |
| 14 | Budget colours | 90.8% (under budget) was red like over-budget | One rule everywhere (`budgetLevel`): amber from 80%, red only above 100%, matching the warning icons. Unit-tested. |
| 15 | Goals cards | Inconsistent secondary actions | Main money actions on the left; archive/edit/delete as one group of labelled icon buttons on the right. A completed goal shows a highlighted "Archive". |
| 16 | Goal dialog | Icon placeholder looked like a value | No placeholder; a hint under the field ("an emoji… leave empty for 🎯") |
| 17 | Recurring income "Other" | ➕ looked like an "add" button | 💰, for new users and (by data migration `c7e9a1b3d5f2`) existing ones who kept the default |
| 18 | Page headers | Inconsistent subtitles and button placement | One `PageHeader` on every page: title, one-line description, actions on the right (wrap below on phones) |
| 23 | Assistant input (mobile) | Placeholder wrapped onto two lines | Shorter placeholder: "Ask, or add an expense…" |

## P3: nice to have (done in Phase 6)

| # | Where | Done |
|---|---|---|
| 19 | Quick Add | The 5 most-used categories this period first; the rest behind "More (N)" |
| 20 | Expense validation | Inline field errors (amount, category, date) with the backend's exact rules, in every form: expense, income, goal, budget, category, recurring, CSV export. The input is kept. |
| 21 | Dark mode | Chart tooltips readable in both themes; and the accessibility check found and fixed low-contrast purple, red, green and amber text in light and dark mode |
| 22 | Landing page (mobile) | Shorter (tighter spacing, compact feature list) and **accurate**: it claimed "no signup required" and "join thousands", showed `$` prices and had dead Privacy/Terms links. Now it shows the real dashboard, real features (income, goals, assistant) and links to sign up, sign in and the source code. |

## Also done in Phase 6
- Error states with **Try again** on every page that loads data, and an error page for crashes (`error.tsx`, reported to Sentry when enabled); empty states with a call to action.
- **Accessibility:** `e2e/a11y.spec.ts` runs axe-core (WCAG 2.1 A/AA) on every page and a dialog, **light and dark, desktop and 375px**, and fails on serious or critical problems. Fixed with it: tab markup without panels (now a toggle), focusable chart slices inside hidden charts, low-contrast colours, unlabelled inputs in Settings. Also a "Skip to content" link and text summaries for charts.
- `e2e/layout.spec.ts` now names the elements that stick out when a page is too wide (it found a grid that grew with unwrapped text).
- **PWA:** web app manifest, original icons (192/512/maskable/Apple), theme colour; per-page titles and descriptions, an SVG favicon and a custom 404 page.
- One money formatter (`Intl.NumberFormat`) everywhere.

## What looked fine
- Login, register, the validation errors (register password, wrong password, goal form) and the session-expired notice are clear on both widths.
- The "This month" row: Income · Spent · Saved · Savings rate, with **"—" and "No income recorded yet"** for a new user, and "Add your income".
- Empty states for Expenses, Income and Goals have a call to action.
- The Budget Overview and Savings Goals cards read well on both widths.
