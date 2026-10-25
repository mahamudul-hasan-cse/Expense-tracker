# Production Plan — Wallet Agent

Status legend: `[x]` done and verified · `[~]` done but not fully verified (see notes) · `[ ]` not started

## Current state (inspected 2026-10-25)

- **Backend:** FastAPI + SQLAlchemy 2.0 + Alembic (uv). Routers: categories, expenses, recurring, stats, export, budgets. `GET /health` exists but doesn't check the DB. CORS reads `CORS_ORIGINS` from env (comma-separated). No auth, no user model, no tests, no lint/type config, no logging setup.
- **Frontend:** Next.js 14.2.3 (vulnerable) + React Query + shadcn/ui + Recharts. Pages: marketing `/`, `/dashboard`, `/expenses`, `/settings`. Already has skeletons, toasts, delete confirmations, and a dark-mode toggle (next-themes, system default). No ESLint/Prettier config, no tests, no `public/` (no favicon/manifest), no 404 page.
- **Infra:** `docker-compose.yml` runs Postgres only. No Dockerfiles, no CI.
- **Repo:** **not a git repository.** Per-phase commits need either `git init` here or a clone of the original GitHub repo (decision needed — see Open questions).
- **Docker:** not running on this machine, so nothing touching Postgres has been run yet.

## Open questions (need your decision)

1. **Git:** `git init` a fresh repo here, or move this work into a clone of the original repo (keeps history and the remote the deployed frontend uses)?
2. **Auth approach** (Phase 2).
3. **Hosting** for backend + database (Phase 8).
4. **License** (Phase 9) — suggested MIT.

## Phase 0 — Verify current state and security fix
- [ ] Run the API against Postgres and smoke-test budgets, category delete (400), expense and recurring create/edit — **blocked: Docker not running.** Commands to run yourself are in the Phase 0 report.
- [x] Upgrade Next.js 14.2.3 → 14.2.35 (latest 14.2.x)
- [x] `npm audit fix` (non-breaking) applied: 9 → 6 findings. Remaining (each needs a major upgrade, so needs your approval):
  - `next` (critical): advisories with no 14.x fix (image optimizer DoS, RSC deserialization DoS, rewrite request smuggling, image cache growth). Fix is Next 16.
  - `postcss` (high): the copy bundled inside `next@14` (8.4.31). Fixed by upgrading Next.
  - `postcss-selector-parser`, `postcss-nested`, `tailwindcss`, `tailwindcss-animate` (moderate): via Tailwind 3, no non-breaking fix; Tailwind 4 is a major upgrade. Build-time only, not shipped to browsers.
- [x] `tsc --noEmit` and `npm run build` pass on 14.2.35

## Phase 1 — Finish missing features
- [ ] Category editing (`PUT /categories/{id}`): rename + icon. **The model has no color field**; adding one is optional. "Unique per user" becomes possible only after Phase 2. Until then names stay globally unique (case-insensitive).
- [ ] "+ Add new category" inline in the expense form dropdown
- [ ] Active/inactive toggle for recurring expenses in the UI (the API already supports `is_active`, and `/stats/upcoming-recurring` already filters inactive items)
- [ ] Audit React Query invalidation for every mutation (categories → expenses/stats/budgets/recurring, recurring → upcoming)

## Phase 2 — Authentication and data isolation (ASK FIRST)
- [ ] Propose options; wait for your choice
- [ ] `users` table + migration adding `user_id` to expenses, categories, budgets, recurring_expenses. Existing rows are assigned to a first user created by the migration (explained before running)
- [ ] Unique constraints become per-user: category name `(user_id, lower(name))`, budget `(user_id, category_id, month, year)`. Default categories are seeded per user at registration
- [ ] Register / login / logout, argon2 hashing, expiring tokens, `SECRET_KEY` from env
- [ ] Every endpoint requires auth and every query is user-filtered; isolation tests
- [ ] Frontend login/register, protected routes, token on requests, redirect on 401, logout button. **Note:** the marketing page at `/` stays public

## Phase 3 — Backend hardening
- [ ] CORS from env (`ALLOWED_ORIGINS`); reject `*` when `APP_ENV=production`
- [ ] slowapi rate limiting; stricter on auth routes
- [ ] `/health` checks DB connectivity
- [ ] Uniform error body `{ "error": { "code", "message", "details" } }`; no stack traces in production. **Note:** the frontend reads `detail` today, so it will be updated to match
- [ ] Structured (JSON) logging, `LOG_LEVEL` from env
- [ ] `APP_ENV` switch; fail fast on missing required vars (e.g. `SECRET_KEY` in production)
- [ ] Indexes on `user_id` (+ composite with date) via migration. Date and category indexes already exist
- [ ] Pagination: expenses already paginated. Categories, recurring and budgets are small per-user lists, so they get optional `limit/offset` params with backward-compatible defaults

## Phase 4 — Tests
- [ ] Backend pytest against a separate Postgres test DB (models use Postgres UUID, so SQLite is not an option). Coverage target 80%+
- [ ] Frontend Vitest + RTL: date helpers (Asia/Dhaka, before 6 AM), currency, filters, form validation
- [ ] Playwright E2E: login → add expense → dashboard; create budget; filter expenses
- [ ] One-command scripts for each suite, documented

## Phase 5 — Code quality and CI
- [ ] ruff (lint + format), mypy; fix findings
- [ ] ESLint (`next/core-web-vitals`) + Prettier; fix findings
- [ ] pre-commit (ruff, prettier, eslint)
- [ ] `.github/workflows/ci.yml` with a Postgres service; cached deps; README badge
- [ ] Dependabot (npm, uv/pip, github-actions)

## Phase 6 — UX polish
Partially present: skeletons, toasts, delete confirmations, dark mode.
- [ ] Error states with retry; empty states with CTA
- [ ] One `Intl.NumberFormat('en-BD', { style: 'currency', currency: 'BDT' })` helper everywhere
- [ ] Mobile nav at 375px (current navbar overflows)
- [ ] Accessibility pass (labels, focus, aria, contrast)
- [ ] Inline validation matching backend rules; keep input on failure (submit already disabled while saving in the expense form only)
- [ ] PWA manifest + original icons + theme color
- [ ] Per-page titles/meta, favicon, custom 404

## Phase 7 — Monitoring
- [ ] Sentry backend + frontend, enabled only when `SENTRY_DSN` / `NEXT_PUBLIC_SENTRY_DSN` is set
- [ ] README section on UptimeRobot against `/health`

## Phase 8 — Docker and deployment (ASK FIRST about hosting)
- [ ] Backend multi-stage Dockerfile (uv, non-root); frontend Dockerfile (`output: 'standalone'` is already set)
- [ ] docker-compose: Postgres + backend + frontend with healthchecks
- [ ] Migrations on start (entrypoint)
- [ ] Host-specific config + `docs/DEPLOYMENT.md` (after your choice)

## Phase 9 — Documentation
- [ ] README rewrite (Mermaid architecture, env tables, tests, badge, screenshot list)
- [ ] `docs/API.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `LICENSE` (after your choice)

## Phase 10 — Final review
- [ ] Clean-state run of everything (fresh DB, migrations from zero, all suites, builds, compose up)
- [ ] Secret scan (repo + history), auth on every endpoint, CORS and rate limits on, `npm audit`, `pip-audit`
- [ ] Final report + suggested next features (not built)

## Doesn't apply / adjusted
- "Change color" when editing categories: there's no color column. Icon (emoji) editing is supported; adding color is an optional extra.
- "Unique per user" category names: depends on Phase 2.
- Dark mode toggle that follows system preference: already implemented. Will only be checked.
- `expense-spec.md` routes `/` to the dashboard, but the code serves a marketing page at `/`. Keeping the code's behaviour.
