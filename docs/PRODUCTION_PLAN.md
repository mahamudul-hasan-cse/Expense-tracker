# Production Plan — Wallet Agent

Status legend: `[x]` done and verified · `[~]` done but not fully verified (see notes) · `[ ]` not started

## Current state (inspected 2026-10-25)

- **Backend:** FastAPI + SQLAlchemy 2.0 + Alembic (uv). Routers: categories, expenses, recurring, stats, export, budgets. `GET /health` exists but doesn't check the DB. CORS reads `CORS_ORIGINS` from env (comma-separated). No auth, no user model, no tests, no lint/type config, no logging setup.
- **Frontend:** Next.js 14.2.3 (vulnerable) + React Query + shadcn/ui + Recharts. Pages: marketing `/`, `/dashboard`, `/expenses`, `/settings`. Already has skeletons, toasts, delete confirmations, and a dark-mode toggle (next-themes, system default). No ESLint/Prettier config, no tests, no `public/` (no favicon/manifest), no 404 page.
- **Infra:** `docker-compose.yml` runs Postgres only. No Dockerfiles, no CI.
- **Repo:** **not a git repository.** Per-phase commits need either `git init` here or a clone of the original GitHub repo (decision needed — see Open questions).
- **Docker:** not running on this machine. **Workaround used for verification:** a throwaway local Postgres 16.2 from the `pgserver` Python package (run from the scratchpad and not a project dependency). Migrations, the smoke tests and pytest ran against it. Docker Compose itself is still unverified.

## Open questions (need your decision)

1. ~~Git~~: decided, `git init` here.
2. ~~Auth approach~~: decided, self-built JWT; existing rows go to a first owner user.
3. **Hosting** for backend + database (Phase 8).
4. **License** (Phase 9) — suggested MIT.
5. **Next.js 15.5 upgrade** as its own phase before Phase 8 (recommended; see below). Also: where is the frontend hosted (Vercel or self-hosted)? The answer decides how urgent the upgrade is.

## Deployment architecture: API proxy and auth cookie

The browser only ever talks to the frontend's own origin. `frontend/next.config.mjs` rewrites `/api/*` to `${BACKEND_URL}/api/*`:

```
Browser ──https──▶ app.example.com (Next.js) ──/api/* rewrite──▶ api.example.com (FastAPI) ──▶ Postgres
         cookie set by app.example.com (first-party)
```

- **Why:** the refresh-token cookie is set by the response the browser received from `app.example.com`, so it's a first-party, host-only cookie. Safari ITP and Chrome's third-party cookie blocking never apply. Browser calls are same-origin, so CORS isn't involved.
- **Cookie flags in production** (checked through the proxy with `APP_ENV=production`): `HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth; Max-Age=2592000`, no `Domain`.
  - `HttpOnly`: JavaScript can't read it.
  - `Secure`: on automatically when `APP_ENV=production`; production refuses `COOKIE_SECURE=false`.
  - `Strict`: works because every refresh is a same-site `fetch`.
  - `Path`: the cookie is only sent to the auth endpoints.
  - The access token lives only in memory.
- **Local development:** `npm run dev` on :3000 proxies to `BACKEND_URL` (default `http://localhost:8000`). Cookies are non-Secure because `APP_ENV` isn't production, which works over plain http.
- **Config:** `BACKEND_URL` is read when you **build** the frontend, because rewrites are baked into the output. Set it in the frontend host's build environment, and rebuild when it changes. Leave `NEXT_PUBLIC_API_URL` unset. Setting it makes the browser call the backend cross-site, which brings the cookie problem back.
- **Backend CORS:** no longer needed for the browser. `CORS_ORIGINS` can stay set to the frontend origin as defense in depth.
- **Proxy hop:** the backend sees the Next.js server as the client. Phase 3's rate limiter has to read the client IP from `X-Forwarded-For`, and only trust it from the proxy.
- **Caveat:** on Next 14, self-hosted rewrites are affected by GHSA-ggv3-7p47-pfv8 (request smuggling, see below). Vercel isn't affected because it handles rewrites at its CDN.

## npm audit: remaining advisories (Next 14.2.35, checked 2026-10-26)

What the app actually uses:
- App Router with React Server Components, a static rewrite to the backend, client-side `fetch` only.
- Not used: `next/image`, Server Actions, middleware, i18n, CSP nonces, `beforeInteractive` scripts, server-side `fetch` with bodies, the Edge runtime, or WebSockets.
- **Mitigation added now:** `images: { unoptimized: true }` turns off the Image Optimization API. Checked: `/_next/image` now falls through to the 404 page instead of reaching the optimizer.

| Advisory | Sev. | Affects | Applies to this app? |
|---|---|---|---|
| GHSA-2464-fhr4-w9xw, GHSA-2xp9-vwfh-vxw4 | critical | RCE in Image Optimization API (SVG / AVIF) | **No longer** — optimizer disabled |
| GHSA-p293-qw3h-jr36 | critical | RCE when the Next server runs on **Windows** | Only if hosted on Windows. Production should be Linux. Note that `next dev`/`next start` on this Windows machine listen on all interfaces. |
| GHSA-h25m-26qc-wcjf, GHSA-q4gf-8mx6-v5v3, GHSA-8h8q-6873-q5fj | high | DoS via crafted RSC requests | **Yes** (App Router) — availability only |
| GHSA-ggv3-7p47-pfv8 | moderate | Request smuggling through external rewrites | **Yes if self-hosted** (our `/api` proxy); not on Vercel |
| GHSA-wfc6-r584-vfw7, GHSA-vfv6-92ff-j949 | mod/low | RSC response cache poisoning | Possible if a CDN caches RSC responses |
| GHSA-c4j6-fc7j-m34r | high | SSRF via WebSocket upgrades | Unlikely (no WebSockets); self-hosted only |
| GHSA-p9j2-gv94-2wf4 | high | SSRF in rewrites with **dynamic hostnames** | No — destination host is a fixed env value |
| GHSA-m99w-x7hq-7vfj, GHSA-p3m5-59mp-jv5r, GHSA-89xv-2m56-2m9x, GHSA-4c39-4ccg-62r3, GHSA-955p-x3mx-jcvp | high/mod | Server Actions / Server Functions (DoS, SSRF, payload, disclosure) | No Server Actions |
| GHSA-36qx-fr4f-26g5, GHSA-3g8h-86w9-wvmq | high/low | Middleware bypass (Pages+i18n), middleware redirect cache poisoning | No middleware, no Pages Router |
| GHSA-ffhc-5mcf-pf4q, GHSA-gx5p-jg67-6x7h | moderate | XSS with CSP nonces / `beforeInteractive` | Not used |
| GHSA-68g3-v927-f742, GHSA-4633-3j49-mh5q | moderate | Server-side `fetch` cache confusion | No server-side fetch |
| GHSA-9g9p-9gw9-jx7f, GHSA-h64f-5h5j-jqjh, GHSA-3x4c-7xq6-9pq8 | moderate | Image optimizer DoS / disk growth | **No longer** — optimizer disabled |
| postcss (4 advisories, bundled in next + tailwind) | high/mod | Source-map file read, XSS in CSS stringify | No — build-time only, processes our own CSS |
| postcss-selector-parser / postcss-nested / tailwindcss(-animate) | moderate | CPU exhaustion parsing selectors | No — build-time only |

**Recommendation:** make **Next.js 15.5.x (15.5.28+)** its own phase, *before Phase 8 (deploy)*. It clears every `next` advisory, and Next 16 isn't needed for that. Expect React 18 → 19 (Next 15's App Router requires it), async `cookies()`/`headers()` (unused here), changed fetch caching defaults (irrelevant), and checking that Recharts, Radix and next-themes work with React 19. That's moderate effort and fits in one phase. **If the frontend is self-hosted, don't ship the `/api` proxy to production on 14.2.35** because of the request-smuggling advisory. On Vercel the remaining real exposure is RSC DoS, which is availability-only. Next 16 can come later as a separate decision.

## Pre-deploy checklist

Do these in order for the first deploy with auth (Phase 2+):

1. **Back up the database** before migrating:
   ```bash
   pg_dump --format=custom --no-owner --file=wallet_agent_$(date +%Y%m%d_%H%M).dump "$DATABASE_URL"
   # restore if needed: pg_restore --clean --no-owner --dbname="$DATABASE_URL" wallet_agent_YYYYMMDD_HHMM.dump
   ```
   Check the file isn't empty and keep it somewhere other than the server.
2. **Generate a strong `SECRET_KEY`** (64 random characters) and store it in the host's secret settings, never in git:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```
3. **Set every production env var.** Backend:
   - `APP_ENV=production`
   - `DATABASE_URL`
   - `SECRET_KEY`
   - `CORS_ORIGINS=https://<frontend-domain>`
   - Leave `COOKIE_SECURE` unset (defaults to true) and `COOKIE_SAMESITE=strict`
   - Optionally `ACCESS_TOKEN_EXPIRE_MINUTES` / `REFRESH_TOKEN_EXPIRE_DAYS`
   - Phase 3+ adds `LOG_LEVEL`, rate-limit settings, and later `SENTRY_DSN`

   Frontend (**build-time**):
   - `BACKEND_URL=https://<backend-domain>`
   - Make sure `NEXT_PUBLIC_API_URL` is **not** set
4. **Run the migration with only `OWNER_EMAIL`**, so no password goes on a command line or into shell history:
   ```bash
   cd backend
   OWNER_EMAIL=you@example.com uv run alembic upgrade head
   ```
5. **Set the owner password interactively.** It prompts twice and the input isn't echoed:
   ```bash
   uv run python -m app.cli set-password you@example.com
   ```
6. **Deploy backend and frontend together.** The old frontend can't talk to the authed API, and the new frontend needs the proxy and `BACKEND_URL`. Deploy the backend first, then right away the frontend built with `BACKEND_URL`.
7. **Smoke test production:**
   - Log in as the owner and confirm the old data is there.
   - Register a second account and confirm it sees only the defaults.
   - In DevTools → Application → Cookies, `refresh_token` shows HttpOnly, Secure, Strict, and Path `/api/v1/auth` on the frontend domain.
   - Reload the page and confirm you stay signed in.
   - Log out, then reload: you should land on `/login`.

## Phase 0 — Verify current state and security fix
- [x] Migrations from zero, then smoke-tested against Postgres 16 (pgserver, not Docker): create/list budget (spent 400, 40%), deleting a category in use gives 400 with a clear message, expense create/edit (clearing the note works, 3-decimal amount gives 422), recurring create, due-today shows days_until 0, switching to weekly with due_day>7 gives 400, pause removes it from upcoming, rename and duplicate rename gives 400, stats return numbers, CSV export works. Not yet run through `docker-compose`.
- [x] Upgrade Next.js 14.2.3 → 14.2.35 (latest 14.2.x)
- [x] `npm audit fix` (non-breaking) applied: 9 → 6 findings. Remaining (each needs a major upgrade, so needs your approval):
  - `next` (critical): advisories with no 14.x fix. All are fixed in **15.5.28**, so Next 16 isn't required. See "npm audit: remaining advisories" below.
  - `postcss` (high): the copy bundled inside `next@14` (8.4.31). Fixed by upgrading Next.
  - `postcss-selector-parser`, `postcss-nested`, `tailwindcss`, `tailwindcss-animate` (moderate): via Tailwind 3, no non-breaking fix; Tailwind 4 is a major upgrade. Build-time only, not shipped to browsers.
- [x] `tsc --noEmit` and `npm run build` pass on 14.2.35

## Phase 1 — Finish missing features
*Verified: `tsc --noEmit`, `npm run build`, backend import, schema validation. **Not run against Postgres or clicked through in a browser** (Docker down).*
- [~] Category editing: `PUT /categories/{id}` (name + icon, trimmed, case-insensitive uniqueness excluding itself) and an Edit button and dialog in Settings. Names are globally unique until Phase 2 makes them per-user. No color column exists, so none was added.
- [~] "+ Add new category…" option in the expense form dropdown opens an inline name and icon row; the new category is selected automatically
- [~] Active/Paused toggle on each recurring item in Settings (`aria-pressed`). Paused items are dimmed. The backend already excludes inactive items from `/stats/upcoming-recurring`.
- [x] Cache invalidation audit: category rename now also refreshes expenses, stats, budgets, recurring and upcoming. Expense changes refresh expenses, stats and budgets. Recurring changes refresh recurring and upcoming. Budget changes refresh budgets and budget summary. Category create/delete refreshes categories (delete only succeeds when the category is unused).

## Phase 2 — Authentication and data isolation (ASK FIRST)
*Verified: 23 pytest tests against Postgres, migration upgrade/downgrade/re-upgrade on a DB with existing data, `alembic check` (no model/migration drift), the CORS + cookie flow over HTTP with curl, `tsc`, `npm run build`. **Not verified: the login UI in a real browser.***
- [x] Chose self-built JWT
- [x] `users` table + migration `b7d4e8f1a2c3` adding `user_id` (FK, CASCADE, indexed) to all four tables. Existing rows were assigned to an owner account (`OWNER_EMAIL`, optional `OWNER_PASSWORD`); without a password the owner can't log in until `uv run python -m app.cli set-password <email>`. Checked on real data: every row got the single owner id.
- [x] Category names unique per user and case-insensitive (`uq_categories_user_name`). Budget uniqueness stays `(category_id, month, year)`, which is already per-user because categories are. The 4 default categories are seeded for each new user.
- [x] Register / login / logout / refresh / me. Argon2 hashing, 15-minute access JWT, 30-day refresh JWT in an httpOnly cookie scoped to `/api/v1/auth`. Logout bumps `token_version`, which revokes every token. `SECRET_KEY` comes from env; production refuses the dev default.
- [x] All 19 data endpoints require a Bearer token and filter by `user_id`. Tests prove another user gets 401 or 404 and can't read, edit, delete or reference the first user's data.
- [~] Frontend: `/login` and `/register`, `RequireAuth` guard on the app pages, token sent with every call, one silent refresh on 401, then redirect to `/login?reason=expired`. Logout button in the navbar. CSV export now uses an authed fetch. Builds, but not clicked through in a browser.
- **Deploy note:** the deployed frontend must be redeployed with this version, or it will get 401s everywhere.

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
