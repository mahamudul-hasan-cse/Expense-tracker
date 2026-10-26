# UI improvements found in the screenshot review (for Phase 6)

Source: `docs/screenshots/` (36 captures, desktop 1440px and mobile 375px), taken 2026-10-26 from a production build with the seeded demo user (`backend/scripts/seed_demo.py`) and a brand-new user. Regenerate with `cd frontend && npm run screenshots`.

**Nothing in this list is fixed yet.** Priority: **P1** = broken or misleading, **P2** = clearly visible polish problem, **P3** = nice to have.

## P1: broken or misleading

| # | Where | Problem | Screenshot |
|---|---|---|---|
| 1 | Dashboard → Daily Spending Trend | **The bars are squeezed into the first ~2 days of the x-axis**, while the labels run 1–31. The chart is unreadable on desktop and mobile. This may be a regression from the React 19 / Recharts 2.15 upgrade (Phase N15); no pre-upgrade screenshot exists to compare. Investigate first. | `desktop-dashboard`, `mobile-dashboard` |
| 2 | Expenses (mobile) | **Horizontal overflow: the page is 392px wide at 375px.** The "to" date input sits outside the Filters card. | `mobile-expenses`, `mobile-empty-expenses` |
| 3 | Settings (mobile) | **Horizontal overflow: the page is 502px wide.** The Monthly Budgets header (title + month + year + "Add Budget") doesn't wrap, and "Add Budget" is pushed outside the card. | `mobile-settings` |
| 4 | Dashboard → Recent Expenses (touch) | The edit button only appears on **hover** (`opacity-0 group-hover:opacity-100`), so **phone users can't edit from the dashboard**. | `mobile-dashboard` |
| 5 | Dashboard → "Daily Average" | Divides the month's total by **every day of the month** (31), including days that haven't happened yet, so it understates the average mid-month (৳1,474 shown, about ৳1,758 actual on Oct 26). | `desktop-dashboard` |
| 6 | Dashboard → "Upcoming Bills" stat card | Now counts **income** items as bills ("4 Upcoming Bills" includes Salary and tuition). Rename it to "Upcoming", or count only bills. | `desktop-dashboard` |

## P2: visible polish problems

| # | Where | Problem | Screenshot |
|---|---|---|---|
| 7 | Navbar (mobile) | Seven bare icons with no labels. The logo and the active page are two adjacent purple squares that look like one control. Needs a proper mobile nav (bottom bar or menu). | all `mobile-*` |
| 8 | Dashboard (mobile) | The four stat cards stack full-width, so it takes about **1,300px of scrolling** before reaching the "This month" row. Use a 2×2 grid. | `mobile-dashboard` |
| 9 | Spending by Category legend | Desktop truncates names ("Ran…", "Groc…", "Tran…", "Elect…"). Only the **top 6 of 11** categories appear in the legend, with no "Other" or "+5 more". | `desktop-dashboard` |
| 10 | Daily Spending Trend y-axis | Labels like `৳16000` have no thousands separators, unlike everywhere else (৳16,000). For a new user it shows a ৳0–৳4 axis with no bars instead of an empty state. | `desktop-dashboard`, `mobile-empty-dashboard` |
| 11 | Expenses / Income rows (mobile) | Dates wrap onto two lines ("Oct / 26"), and the edit/delete icons shift position row to row depending on the note's length, so amounts and actions don't line up. | `mobile-expenses`, `mobile-income` |
| 12 | Dashboard → Recent Expenses (mobile) | Amounts aren't right-aligned; each row's amount starts at a different x position. | `mobile-dashboard` |
| 13 | Settings → Monthly Budgets (mobile) | "৳3,205 / ৳2,500" wraps mid-value and collides with the category name. | `mobile-settings` |
| 14 | Budget colours | Groceries at **90.8%** (under budget) shows the same **red** as over-budget items. Use amber for "close" and red only for over 100%, matching the warning icon logic. | `desktop-dashboard`, `mobile-settings` |
| 15 | Goals cards | The secondary actions row (Archive, edit, delete) is indented and spaced differently from the primary buttons above it; ghost "Archive" vs icon-only edit/delete is inconsistent. | `mobile-goals` |
| 16 | Goal dialog | The Icon field's placeholder (💻) looks like an entered value. | `mobile-goal-validation-error` |
| 17 | Recurring income "Other" category | Its default icon ➕ looks like an "add" button in the Upcoming list ("Weekend tuition"). Pick a neutral icon (e.g. 💰). | `desktop-dashboard` |
| 18 | Page headers | Inconsistent: Dashboard/Income/Goals have a subtitle, Expenses/Settings don't. Primary buttons sit on the right on desktop but wrap below the title on mobile for Income/Goals, while Expenses keeps it on the right. | various |

## P3: nice to have

| # | Where | Suggestion |
|---|---|---|
| 19 | Quick Add | 11 category buttons + "New Expense" wrap to two rows; show the most-used ~5 and put the rest in a "More" menu. |
| 20 | Expense validation | "Amount and category are required" appears only as a toast; Phase 6 item 8 (inline field errors) should replace it. |
| 21 | Dark mode | Works and is readable (`*-dashboard-dark`); check chart grid and tooltip contrast in the Phase 6 accessibility pass. |
| 22 | Landing page (mobile) | Very long (about 4,200px); check hero spacing and feature-card density in Phase 6. |

## What looked fine
- Login, register, the validation errors (register password, wrong password, goal form) and the session-expired notice are clear on both widths.
- The "This month" row: Income · Spent · Saved · Savings rate, with **"—" and "No income recorded yet"** for a new user, and "Add your income".
- Empty states for Expenses, Income and Goals have a call to action.
- The Budget Overview and Savings Goals cards read well on both widths.
