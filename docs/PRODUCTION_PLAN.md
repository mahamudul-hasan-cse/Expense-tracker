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
5. ~~Next.js 15.5 upgrade~~: done (Phase N15). **Frontend host: Vercel** (decided 2026-10-27, see below).
8. ~~Replacing the old `main`~~: **approved 2026-10-27**: option A (`-s ours` merge + PR `production-ready → main`), **on deploy day only, after the backend is live**.
9. **Rulesets (owner, 2026-10-27):** "protect-main" on `main` = require PR (0 approvals) + the 3 CI checks + block force pushes + restrict deletions. "protect-production-ready" = block force pushes + restrict deletions only (direct pushes allowed). Secret scanning and push protection on.

## GitHub and hosting facts (2026-10-27)

- **Repository:** https://github.com/mahamudul-hasan-cse/Expense-tracker, **public**.
  - `main` holds 1 commit (`640b6ad`, "Initial commit", 2026-01-20), the original code, and is unrelated to our local history.
  - Our work is on the branch **`production-ready`**. It was pushed without force, and `main` is untouched.
- **Secret scan of the public `main` commit:** gitleaks found nothing in all 83 files. A manual search for keys, tokens, `.env` files and DB URLs found only the local development defaults `wallet_user` / `wallet_pass` @ `localhost` (alembic.ini, config.py, the spec, docker-compose). Those are placeholders for a local Docker database, not real secrets. **They only need rotating if those exact credentials were ever used on a real, reachable database.** gitleaks across all 20+ local commits: no leaks.
- **Frontend: Vercel**, deploying `main` to https://expense-tracker-orcin-pi.vercel.app. Every other branch (including `production-ready`) gets a **preview** deployment.
  - **Preview builds need `BACKEND_URL`** (build time). Without it the `/api` rewrite points at `http://localhost:8000`, so previews load pages but every API call fails. This is harmless.
  - If `NEXT_PUBLIC_API_URL` is set on the Vercel project, the browser calls that URL directly and bypasses the proxy. It must be **removed** for the new frontend (see "Deployment architecture" below).
- **CI:** GitHub Actions runs on pushes and PRs to `main` and `production-ready`. The first real run (`a1ec24b`) passed all three jobs: Backend, Frontend, End-to-end.
6. ~~AI assistant~~: design approved 2026-10-26 (decisions in `docs/ASSISTANT_DESIGN.md` §12).
7. ~~Income and savings goals~~: approved, built before the assistant. Data model proposed under Phase F1 below.

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

## npm audit: remaining advisories (Next 14.2.35, checked 2026-10-26). *Superseded: resolved by the Next 15.5.28 upgrade (Phase N15); only 4 moderate Tailwind 3 build-time findings remain.*

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
2. **Create a separate production OpenRouter key** in the OpenRouter dashboard with its own credit limit, sized to `ASSISTANT_GLOBAL_DAILY_BUDGET_USD` × days between top-ups. Never reuse the development key. Set it only in the backend host's secret env vars as `OPENROUTER_API_KEY`.
3. **Generate a strong `SECRET_KEY`** (64 random characters) and store it in the host's secret settings, never in git:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```
4. **Set every production env var.** Backend:
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
5. **Run the migration with only `OWNER_EMAIL`**, so no password goes on a command line or into shell history:
   ```bash
   cd backend
   OWNER_EMAIL=you@example.com uv run alembic upgrade head
   ```
6. **Set the owner password interactively.** It prompts twice and the input isn't echoed:
   ```bash
   uv run python -m app.cli set-password you@example.com
   ```
7. **Deploy backend and frontend together.** The old frontend can't talk to the authed API, and the new frontend needs the proxy and `BACKEND_URL`. Deploy the backend first, then right away the frontend built with `BACKEND_URL`.
8. **Smoke test production:**
   - Log in as the owner and confirm the old data is there.
   - Register a second account and confirm it sees only the defaults.
   - In DevTools → Application → Cookies, `refresh_token` shows HttpOnly, Secure, Strict, and Path `/api/v1/auth` on the frontend domain.
   - Reload the page and confirm you stay signed in.
   - Log out, then reload: you should land on `/login`.

## Order (approved 2026-10-26)

Done: Phases 0–3. Proposed from here:

| # | Phase | Why here |
|---|---|---|
| 0 | **Phase S0 — Playwright smoke suite** | Added at your request: register/login, add expense, dashboard + list load, logout. Run against a production build on 14.2.35, then again after the upgrade to prove nothing broke. |
| 1 | **Phase N15 — Next.js 15.5.28+ upgrade** | Moved up from "after the assistant". The assistant adds a lot of new React code (chat UI, streaming, markdown). Writing it on React 18 and then moving to React 19 means doing that work twice. Doing it now also clears every Next advisory before anything ships. Small phase on today's code. |
| 2 | **Phase 4 — Tests (existing app)** | Moved before the features. It sets up Vitest/RTL and Playwright and fills backend coverage now, so the new features ship *with* tests instead of being retrofitted. |
| 3 | **Phase 5 — Code quality and CI** | Also moved earlier. Lint/format churn lands before the big feature diffs, and CI catches regressions while income and the assistant are built. |
| 4 | **Phase F1 — Income and savings goals** *(if approved)* | Schema changes the assistant depends on (savings rate, goals). |
| 5 | **Phase A1–A4 — AI assistant** (below) | Built on a tested, linted, React 19 base. Every A-phase ships with its own tests. |
| 6 | Phase 6 — UX polish | Last, so it also covers the new screens (chat, income, goals). |
| 7 | Phase 7 — Monitoring | Sentry also captures assistant errors (without content). |
| 8 | Phase 8 — Docker and deployment | |
| 9 | Phase 9 — Documentation | |
| 10 | Phase 10 — Final review | |
| later | Phase R1 — Receipt photo → expense | After deploy (assessed in the design doc §11). |

**Differences from your suggested order:**
- **The Next 15 upgrade goes before the features, not after:** it avoids rewriting new UI code for React 19.
- **Tests and CI go before the features instead of after the assistant:** the assistant is the riskiest change, with security (isolation), money (cost caps) and streaming, so it should land into an existing test harness and CI. Its own tests are part of each A-phase either way.

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
*Verified: 51 pytest tests against Postgres. Ran uvicorn in production mode and saw JSON logs, `/health`, the error body, and the client IP taken from a trusted proxy. Ran the fail-fast startup with missing vars. `alembic upgrade` + `alembic check` (no drift). `tsc` and `npm run build`.*
- [x] CORS: `ALLOWED_ORIGINS` (legacy `CORS_ORIGINS` accepted). Methods and headers are listed explicitly. Production refuses `*` or an empty list. Tested: the allowed origin gets ACAO plus credentials, other origins get nothing. (The browser now goes through the same-origin proxy, so CORS is defense in depth.)
- [x] Rate limiting (slowapi): 120/min per IP by default. `/auth/login` and `/auth/register` get 5/min and 20/hour per IP. **Plus 10 failed logins/hour per account, whatever the IP** (see the client-IP note below). `/health` is exempt. Tested: 6th login → 429; 11th failed login on one account → 429 even with the right password, other accounts unaffected. Storage is in-memory per process; use `RATE_LIMIT_STORAGE_URI=redis://…` with several instances.
- [x] `GET /health` runs `SELECT 1` and returns `{"status":"healthy","database":"ok"}`, or 503 with the error body. Tested both.
- [x] One error format everywhere: `{"error":{"code","message","details","request_id"}}`. This covers HTTP errors, 422 (with per-field `details`), unknown routes, 429, IntegrityError → 409, and unhandled → 500 with a generic message (traceback goes only to the logs; tested that nothing leaks). The frontend parses the new shape. `X-Request-ID` is returned on every response and accepted from callers.
- [x] Logging: one line per request (method, path, status, duration_ms, client_ip, request_id). JSON in production, readable text in development. `LOG_LEVEL` from env. Uvicorn's duplicate access log is off.
- [x] Settings via pydantic-settings (`SettingsConfigDict`). `APP_ENV` switch. Production fails at startup with a clear list of problems: SECRET_KEY missing or short, DATABASE_URL not set, insecure cookie, bad origins.
- [x] Indexes (migration `c3a9d5e7f8b1`): `expenses(user_id, expense_date, created_at)`, `recurring_expenses(user_id, is_active)`, `budgets(user_id, year, month)`. The single-column `user_id` indexes they make redundant are dropped (no data touched). Budget "spent" now uses a date range (index-friendly) in one grouped query instead of one query per budget. Not benchmarked: the test data is too small for meaningful EXPLAIN plans.
- [x] Pagination: `page`/`limit` plus a `pagination` object on categories (default 200), recurring (100) and budgets (100), matching expenses. `/budgets/summary` and `/stats/*` stay unpaginated because their totals must cover everything and they're bounded by categories and days. Response change is additive.

### Client IPs behind the proxy (checked 2026-10-26)
- A self-hosted `next start` rewrite **passes `X-Forwarded-For` through unchanged and doesn't add the client IP** (checked with a header-echo server). Vercel's behaviour wasn't checked here.
- Uvicorn with `--proxy-headers --forwarded-allow-ips=<trusted proxy IPs>` sets the client IP to the **last** `X-Forwarded-For` entry, but only when the direct peer is trusted (checked).
- So the per-IP limits are only accurate when something you trust in front of Next.js (the platform's load balancer or CDN) **appends** the real client IP, and the backend trusts only the IPs it's reached through. If you can't guarantee that, the per-IP limits fall back to the proxy's IP (everyone shares one bucket) or can be spoofed. The **per-account failed-login limit** is the backstop that doesn't depend on IPs. This gets settled for the chosen host in Phase 8.

## Phase 4 — Tests
*Verified: backend **122 passed, 98% coverage** (gate 80%). Frontend **31 passed** (Vitest). E2E **4 passed** (Playwright, production build of Next 15). `tsc` clean. Commands are in `docs/TESTING.md`.*
- [x] Backend pytest against a separate Postgres DB (`TEST_DATABASE_URL`; migrations down/up per run, truncate per test). New suites: expenses (money ranges incl. 0.01 / 99,999,999.99 / 3 decimals / over the max, future dates, note length, update/delete rules, filters, case-insensitive search with escaped `%`/`_`, 4 sort orders, pagination bounds), categories (trim, uniqueness, defaults first, rename, default/in-use delete blocked step by step), recurring (16 due-date cases incl. 31st in Feb and leap years, December rollover, due today; validation; update rules; upcoming window and paused items), stats (monthly/weekly totals, breakdown %, daily series, December, empty), budgets (spent/% incl. over budget, summary totals, duplicates, validation, defaults), CSV export (columns, range, quoting), admin CLI.
- [x] **Bug found and fixed:** the backend used the *server's* date (`date.today()`). On a UTC server, between 00:00 and 06:00 in Dhaka, an expense dated "today" was **rejected as a future date**, the default date was yesterday, and due-today/current-month were a day behind. Now `app.timeutil.today()` uses `APP_TIMEZONE` (default `Asia/Dhaka`) everywhere. Regression test `test_timezone.py` **fails on the old code (2 failures) and passes on the fix**.
- [x] Frontend Vitest + Testing Library (timezone forced to Asia/Dhaka): date helpers (before 6 AM, midnight, New Year, no off-by-one), currency formatting, filter params (extracted to `expense-filters.ts`; "All Categories" regression), API error parsing, expense form validation (required category, Dhaka max date, note → null regression, input kept on failure, inline category with Enter), auth form (password rule, server error + retry, `next` redirect, **open-redirect attempts ignored**, session-expired notice).
- [x] Playwright: smoke (register → expense → dashboard/list → logout → login → reload) + wrong password + **budget creation that fills up live** + **expense filters** (search, category, back to All Categories, date range). The budget dialog's labels are now linked to their inputs (an accessibility fix the tests needed).
- [x] One command per suite: `uv run pytest`, `npm test`, `npm run test:e2e`, documented in `docs/TESTING.md`.

## Phase 5 — Code quality and CI
*Verified locally: ruff + format + mypy clean, pytest 124 passed (97.7%), ESLint 0 warnings, Prettier clean, `tsc`, Vitest 31 passed, production build, `uv sync --locked`, all 11 pre-commit hooks pass, `actionlint` clean on the workflow. **Not verified: an actual GitHub Actions run** (no GitHub remote yet).*
- [x] **ruff** (lint E/F/W/I/B, line length 120, quote style preserved to minimise churn) and **mypy** (pydantic plugin, `check_untyped_defs`). The 40 mypy errors were fixed properly:
  - Models moved to SQLAlchemy 2.0 typed `Mapped[...]` declarations; `alembic check` confirms **no schema change**.
  - Stats grouping is now typed, implicit `Optional` is gone, the login `None` path is narrowed, and exception handlers are typed.
  - 90 ruff auto-fixes (unused imports, import order, whitespace) plus `== True` → `.is_(True)`.
- [x] **Bug caught:** ruff's unused-import fix removed the model imports from `alembic/env.py`, which made autogenerate want to **drop every table**. Fixed with a model registry (`app/models/__init__.py`) imported by env.py. New test `test_migrations.py` runs `alembic check` **in a fresh process**: it fails with the broken env.py and passes with the fix.
- [x] **ESLint 9** flat config (`next/core-web-vitals` + `next/typescript` + `prettier`) and **Prettier** (double quotes, semicolons, width 100). The 5 lint findings are fixed and 43 files were formatted (formatting only; tests and build re-checked). New scripts: `lint`, `format`, `format:check`, `typecheck`.
- [x] **pre-commit** (`.pre-commit-config.yaml`): whitespace/EOF/YAML/merge-conflict/large-file/private-key checks, **gitleaks** (checked: it **blocks a staged fake `sk-or-…` key**), ruff check + format, Prettier, ESLint.
- [x] **GitHub Actions** `.github/workflows/ci.yml`: backend, frontend and e2e jobs with Postgres 16 services; uv/npm/Playwright caching; concurrency cancel; read-only permissions; empty `OPENROUTER_API_KEY`.
- [x] **Dependabot** for npm, uv and GitHub Actions, weekly, with grouped minor/patch updates. Majors for tailwindcss/lucide/next are ignored, per the decisions.
- [~] **CI badge**: added to the README with an `OWNER/REPO` placeholder. **Needs your GitHub repository path.**

## Phase F1 — Income and savings goals (approved 2026-10-26, revised to meet your requirements)

### Requirements check
| # | Your requirement | First proposal | Revised design |
|---|---|---|---|
| 1 | Income: amount, date, source/category (Salary, Freelance, Business, Gift, Other + user-defined), note, same money rules | Free-text `source` | **Changed:** a per-user `income_categories` table, seeded with the 5 defaults, plus user-defined ones (same model and uniqueness as expense categories). Money/date validation reuses `MoneyIn` and the no-future-date rule. |
| 2 | Recurring income via the existing recurring mechanism + "Mark paid"/due logic | Out of scope | **Changed:** `recurring_expenses` gains `kind` (`expense`/`income`) and an `income_category_id`, so it's one mechanism. **Note: "Mark paid" doesn't exist yet**; today the app only computes due dates and reminders. It's added once, for both kinds: `POST /recurring/{id}/mark-paid` creates the expense or income through the normal validation and stores `last_paid_on`, which moves `next_due` to the next cycle and hides the item from "Upcoming" until then. |
| 3 | Saved = income − expenses; contributions are allocations, never spending | ✅ same | Unchanged. Contributions live only in `goal_contributions`. Expense totals, charts, budgets and stats never read that table. A test asserts that adding a contribution leaves spending, budgets and Saved unchanged. |
| 4 | Negative month shows "Overspent by ৳X"; savings rate "—" without income | Partly ("red when negative") | **Clarified:** the API returns `saved` (may be negative) and `savings_rate: null` when income is 0. The UI shows **"Overspent by ৳X"** for negative months and **"—"** for a null rate. Tests cover zero income, zero spending and negative months. |
| 5 | Goals: name, target, optional deadline, optional icon; archive completed; delete asks and explains | ✅ fields + status | **Clarified:** archiving is offered once a goal is complete (and allowed any time). The delete dialog says: *"Its ৳X of contributions are removed from the goal. This doesn't change your income, expenses or Saved total; the money simply stops being earmarked."* |
| 6 | Monthly-needed / on-track handle no deadline, past deadline, completed | Only the deadline case | **Changed:** an explicit `state` with five values (see "Computed fields" below). |
| 7 | Per-user isolation tests; export includes income | Separate income export | **Changed:** the CSV export includes income. A **`Type` column (`Expense`/`Income`) is appended** as the last column, so existing columns keep their position. Isolation tests mirror the expense ones for every new table and endpoint. |
| 8 | Assistant can read them later | Implied | **Explicit:** cashflow and goal calculations live in `app/services/cashflow.py` and `app/services/goals.py`. API endpoints and the future assistant tools (`get_cashflow`, `get_savings_goals`) call the same functions, so the numbers always match. |

### Data model
Conventions as before: UUID PKs, `user_id → users ON DELETE CASCADE`, `NUMERIC(12,2)` money via `MoneyIn`/`Money`, no future dates (Asia/Dhaka), case-insensitive names unique per user.

**`income_categories`**: id, user_id, name VARCHAR(100), icon VARCHAR(50) NULL, is_default BOOL, created_at. Seeded on registration (and for existing users by the migration): Salary 💼, Freelance 💻, Business 🏪, Gift 🎁, Other ➕. Deleting is blocked while the category is in use, the same as expense categories.

**`incomes`**: id, user_id, amount, income_category_id FK, income_date DATE (default today), note VARCHAR(500) NULL, created_at, updated_at. Index (user_id, income_date).

**`recurring_expenses`** (extended, not renamed, so existing rows and the API keep working):
- `kind` VARCHAR(10) NOT NULL DEFAULT 'expense', with a CHECK of `expense|income`
- `income_category_id` UUID NULL FK
- `category_id` becomes nullable
- CHECK: exactly one of `category_id` / `income_category_id`, matching `kind`
- `last_paid_on` DATE NULL (`last_reminded_at` stays unused)
- Existing rows become `kind='expense'` with no data loss. The API defaults `kind` to `expense`.

**`savings_goals`**: id, user_id, name VARCHAR(100), icon VARCHAR(50) NULL, target_amount, target_date DATE NULL, status `active|archived` (completion is computed, not stored), created_at, updated_at.

**`goal_contributions`**: id, goal_id FK CASCADE, user_id, amount (non-zero; negative = withdrawal, refused if the goal would go below 0), contributed_on DATE, note VARCHAR(200) NULL, created_at.

### Computed fields (services, shared with the assistant)
- **Cashflow(period):**
  - `income`, `spent`, `saved = income − spent`
  - `savings_rate = saved ÷ income × 100`, or **null** when income = 0
  - `allocated_to_goals` = contributions in the period
  - `unallocated = saved − allocated_to_goals`
- **Goal progress:** `saved`, `remaining = max(target − saved, 0)`, `progress_pct` (capped display at 100, raw value kept), plus `state`:
  - `completed`: saved ≥ target. `required_per_month = 0`. The UI suggests archiving.
  - `no_deadline`: `required_per_month = null` and `on_track = null`. The UI shows "No deadline".
  - `overdue`: the deadline has passed and the goal isn't complete. `required_per_month = remaining` (due now). The UI shows "Deadline passed, ৳X to go".
  - `on_track` / `behind`: saved compared with the target pro-rated over the time from creation to the deadline. `required_per_month = remaining ÷ months left` (at least 1 month).

### How it shows up
- **Dashboard:**
  - A "This month" row: **Income · Spent · Saved** (or **"Overspent by ৳X"**) · **Savings rate** (or "—"). Before the first income is added it shows an "Add your income" prompt.
  - A Goals card with up to 3 active goals: progress bar, state badge, "৳Z/month needed".
- **Pages:**
  - `/income`: list with month filter, add/edit/delete, category select with "+ Add new category…" (same pattern as expenses).
  - `/goals`: goal cards, add/edit/archive/delete (with the explanation above), add or withdraw contribution.
  - Settings: an income categories list, and recurring items gain an Expense/Income type.
  - Upcoming bills: also shows expected income, with a **Mark paid** / **Mark received** button.
- **API:**
  - `/income-categories` CRUD
  - `/incomes` CRUD (paginated, filters like expenses)
  - `/goals` CRUD + `/goals/{id}/contributions`
  - `/recurring/{id}/mark-paid`
  - `/stats/cashflow?month=YYYY-MM`
- **Out of scope:** multiple currencies, and splitting one income across goals automatically.

### Checklist
*Verified: backend **179 passed, 98.3% coverage**, ruff/mypy clean, `alembic check` (no drift), migration up/down/up in the test run and applied to an existing DB (5 users → 25 default income categories, the existing recurring item → `kind='expense'`). Frontend: `tsc`, ESLint, Prettier, **50 unit tests**, production build. **E2E 6/6** on a production build. All pre-commit hooks pass. Not checked by hand in a browser.*
- [x] Migration `e5a1c7d9b2f4`: `income_categories`, `incomes`, `savings_goals`, `goal_contributions` + `recurring_expenses` (`kind`, `income_category_id`, nullable `category_id`, `last_paid_on`, CHECK that the category matches the kind). Default income categories seeded for existing users. Nothing changed or removed in existing data.
- [x] Models (typed `Mapped`), schemas, routers (`/income-categories`, `/incomes`, `/goals` + `/contributions`, `/recurring/{id}/mark-paid`, `/stats/cashflow`), all user-scoped. Logic lives in `app/services/cashflow.py` and `app/services/goals.py` for the assistant to reuse.
- [x] **Mark paid / received**: creates the expense or income through the normal validation, records `last_paid_on` = that cycle's due date, and `next_due` and Upcoming skip paid cycles (paying early included). Changing the schedule resets it. Paused items refuse.
- [x] CSV export includes income, with `Type` appended as the last column.
- [x] Tests:
  - CRUD and validation (same money and date rules as expenses)
  - isolation for every new table and endpoint, including mark-paid and the export
  - cashflow: positive month, negative month (`saved` −500.5), no income (`savings_rate: null`), empty month, leap February, month format
  - **a contribution leaves spending, budgets and Saved unchanged**, and deleting a goal frees its allocation
  - goal states: completed (incl. no or past deadline), no deadline, overdue, deadline today, on track vs behind, at least 1 month, round-up
  - withdrawals: can't take a goal below 0, including by deleting a contribution
  - `next_unpaid_due` for monthly / 31st in Feb / leap year / December / weekly / New Year
- [x] UI:
  - `/income` (month filter, total, add/edit/delete, inline new category)
  - `/goals` (cards, state badge, ৳/month needed, add money / take back, archive / restore, delete dialog that explains contributions)
  - dashboard "This month" row (Income · Spent · **Saved / "Overspent by ৳X"** · savings rate **"—"** without income, "Add your income" prompt) + Goals card
  - Upcoming shows bills and income with **Mark paid / Mark received**
  - Settings: Income Categories card; recurring dialog with an Expense/Income type
  - Navbar: Income, Goals (icon-only below `lg`, names kept for screen readers)
- [x] Playwright: income → Saved 75.0%, goal contribution leaves Saved at ৳7,500 with "৳3,000 set aside for goals", overspend shows "Overspent by ৳1,500", and recurring income → Mark received → income ৳5,000 and gone from Upcoming.

## Phase A1 — Assistant backend core (see docs/ASSISTANT_DESIGN.md)
*Verified: backend **241 passed, 96.4% coverage**, ruff/mypy clean, `alembic check`. Real API: 3 example conversations (`docs/ASSISTANT_EXAMPLES.md`) and SSE streaming measured through the Next.js `/api` rewrite in **dev and a production build** (incremental, not buffered, not compressed). **Real spend $0.0135 of $2.***
- [x] `app/assistant/llm_client.py` (OpenRouter via the `openai` SDK; the only provider-aware file):
  - fallbacks through `models`, `provider: {data_collection: deny, require_parameters, zdr}`
  - attribution headers `HTTP-Referer` and `X-OpenRouter-Title`, plus `X-OpenRouter-App-Visibility: hidden`
  - `session_id` for cache-sticky routing
  - usage, cost, cached and reasoning tokens
  - typed errors for 402, 429 (with Retry-After), 408, 401/403, 5xx, mid-stream errors and timeouts
  - refuses to construct in `APP_ENV=test`; the key is a `SecretStr`
- [x] 10 read-only tools (`app/assistant/tools.py`), defined in OpenAI function-calling JSON schema:
  - user_id is bound on the server; unknown args are rejected, so a model-supplied `user_id` fails
  - date ranges are clamped to today, at most 366 days, nothing before 2015; limits are at most 50
  - user text is flattened and truncated
  - all maths in SQL or Python
  - `propose_expense` never writes
- [x] Migration `f7b3d2a8c6e1`: conversations, messages, usage (no content), insights, `users.assistant_enabled` (opt-in, default false)
- [x] SSE `POST /assistant/chat`:
  - events: conversation, status, token, proposal, done/error
  - at most 8 tool calls, then tools are switched off to force an answer
  - one retry for malformed tool calls
  - an interrupted turn is saved on disconnect
  - "answer cut short" note when the model hits the length limit
  - history: status, opt-in toggle, conversations list/get/delete/clear-all, proposal confirm/cancel
- [x] Limits:
  - per-user daily cap (20) and global daily USD budget ($1), both by Asia/Dhaka day
  - max output tokens 1600, raised from 800 after real testing: Haiku's hidden reasoning used up to 464 tokens and cut answers short
- [x] Disabled mode without a key; `uv run python -m app.cli assistant-usage --days N`
- [x] Tests with a fake LLM (no network), 15 `LLMClient` parsing/error tests with a fake SDK stream, and tool tests against Postgres including isolation
- [x] **Bugs found with the real API:**
  1. **slowapi's ASGI middleware re-sent `http.response.start` for every chunk of a streaming response.** Real uvicorn crashed the request (TestClient tolerated it). This broke the assistant stream, and **every CSV export since Phase 3 logged a crash**. Replaced with a stream-safe `RateLimitMiddleware`; a strict-ASGI regression test fails on the old middleware and passes on the fix.
  2. Answers cut off by the 800-token limit (reasoning tokens). Raised the limit, added the cut-short note, and a test.
  3. `detect_unusual_spending` flagged monthly bills (rent) over short windows. Now needs at least 3 expenses unless the category is new; regression test added.
  4. `assistant-usage` relied on the DB knowing the `Asia/Dhaka` name. Now grouped in Python.
- Dev tools: `scripts/try_assistant.py` (real calls with a full trace), `scripts/check_streaming.py` (SSE timing through a proxy)

### Assistant hardening (2026-10-27)
*Verified: backend tests green (new: idempotent/concurrent confirm, edits validated like manual entry, cancel, 24h expiry, deleted expense, English digits, round separation, reasoning param). Real spend this step **$0.0133**.*
- [x] **English digits everywhere.** Prompt rule added, but real Bangla answers still used ০-৯ under every reasoning setting, so the server now converts ০-৯ → 0-9 in every streamed token (and the saved text). Confirmation cards format with `en-BD` (0-9).
- [x] **Quick-add confirm is done by the server:** `POST /assistant/messages/{id}/proposal/confirm` locks the row (`SELECT … FOR UPDATE`), creates the expense through the same validation and category check as `POST /expenses` (shared `add_expense`), stores `proposal_expense_id` (migration `a3c5e7f9b1d2`, additive), and returns the same expense on a retry or double click (5 parallel confirms → 1 expense). Optional edits in the body are validated the same way.
- [x] `POST …/proposal/cancel` (cancelling twice is fine; a saved one can't be cancelled). Proposals **expire after 24 hours** (`proposal_status: "expired"`, confirm returns 409). The old `PATCH …/proposal` is removed (no client used it).
- [x] Text before a tool call and the answer after it are kept as separate paragraphs (they used to run together: "…unusual items.Your spending…").
- [x] Prompt: suggest splitting a catch-all category ("Random", "Other") when it's ≥15% of spending or in the top 3.
- [x] **Latency and reasoning** (`scripts/measure_latency.py`, real API, Haiku 5.5, 1 run each — small sample):

  | Reasoning | #1 EN compare | #2 BN budgets | #3 BN quick add | Notes |
  |---|---|---|---|---|
  | default (unset) | first token 9.5s, total 13.0s | 7.8s / 12.0s | 4.3s / 4.8s | ~610 reasoning tokens on #1/#2 |
  | `low` | 11.2s / 12.5s | 13.2s / 13.6s | 4.5s / 5.3s | no faster; ~25% cheaper |
  | `none` | 2.1s / 7.7s | 1.3s / 9.7s | 2.1s / 7.2s | "first token" is filler ("I'll check…") before tool calls; **answered Bangla questions in English** |

  Most of the wait is 2–3 tool rounds, each with hidden reasoning. **Recommendation: keep the default** (`ASSISTANT_REASONING_EFFORT` unset): `low` doesn't help Haiku, `none` hurts language-matching. The UI shows tool status lines ("Checking your spending…") during the wait. New setting `ASSISTANT_REASONING_EFFORT` (none|minimal|low|medium|high) is sent as OpenRouter `reasoning: {effort, exclude: true}` only when set; re-measure per model in A4.

## Phase A2 — Assistant frontend
- [x] `/assistant` page + floating button (only when the server has a key; adds bottom space so it never covers row actions)
- [x] Streamed answers rendered by a small Markdown renderer that builds React elements only (no HTML from the model, ever); tool status line ("Checking your spending…"); Stop (aborts the stream; the server saves it as interrupted) and Retry
- [x] Suggested chips (EN/BN/Banglish); conversation list (sidebar on desktop, panel on phones), continue, delete, delete all
- [x] Opt-in card (off by default; what's shared, ZDR, read-only, daily limit); daily-limit / daily-budget message replaces the input; "N of 20 left today"
- [x] Quick-add card: Save / Don't save → server confirm (idempotent; double click = one request, also guarded in the UI), states saved / not saved / expired shown clearly, English digits
- [x] Tests: Vitest (SSE parser across chunk boundaries, Markdown incl. HTML-injection, proposal card) and Playwright `e2e/assistant.spec.ts` with the assistant API faked in the browser (opt-in → chip → formatted answer, quick add double click → 1 confirm, daily limit, stop → retry, 375px no overflow + history panel). No model is called.
- [x] Screenshots `docs/screenshots/*-assistant-*` (desktop + 375px, light + dark) from the same fake with real demo-data answers
- [x] SSE through the Next.js rewrite measured in A1 (dev + production build): not buffered
- [ ] Later (A3): "Edit" on the card (opens the expense form prefilled; the confirm endpoint already accepts edits)

## Phase A3 — Quick add, weekly insight, settings
- [ ] `propose_expense` → confirmation card → existing `POST /expenses`; Edit opens the expense form; proposal status saved
- [ ] Weekly insight card (once per Asia/Dhaka day per user, cached)
- [ ] Settings: opt-in toggle, data-sharing notice, delete chat history

## Phase A4 — Evaluation and E2E
- [ ] `scripts/eval_assistant.py` (seeded demo user, 18 EN/BN/Banglish questions, numeric checks against SQL, `--models` comparison table: accuracy, **time to first token, total time**, cost, reply language matches, no Bangla digits before the server fix-up)
- [ ] Per model, compare reasoning effort default vs `low` vs `none` on the 3 example conversations (`scripts/measure_latency.py`) and record the chosen `ASSISTANT_REASONING_EFFORT`
- [ ] Playwright: chips → message (mocked) → confirm quick-add → expense in list
- [ ] You run the eval with your key; pick the final default model

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

## Phase 8 — Docker and deployment (ASK FIRST about the backend/database host)
**Frontend host: Vercel** (decided). Backend and database host: still to choose.
- [ ] Backend multi-stage Dockerfile (uv, non-root). The frontend doesn't need one on Vercel; an optional one for self-hosting (`output: 'standalone'`).
- [ ] docker-compose: Postgres + backend + frontend with healthchecks (local "everything" run)
- [ ] Migrations on start (entrypoint)
- [ ] Host-specific config + `docs/DEPLOYMENT.md` (after your choice of backend/database host)

### Switching `main` to production-ready (approved: option A, on deploy day after the backend is live)
`main` (1 old commit) and `production-ready` have **unrelated histories**. GitHub can't open a PR between them ("entirely different commit histories").

| Option | How | Verdict |
|---|---|---|
| **A. "ours" merge, then a normal PR (recommended)** | On `production-ready`: `git merge origin/main --allow-unrelated-histories -s ours -m "Adopt production-ready as main"`. This records the old commit as a parent but keeps **our tree exactly**. Push (no force), then open a PR `production-ready → main`; its diff is the full replacement. CI runs on the PR, and merging is a normal fast-forward or merge. | No force-push, no rewritten public history, the old commit stays in history, and it works with branch protection (PR + required checks) |
| B. Merge with real conflict resolution | `--allow-unrelated-histories` without `-s ours`: nearly every file conflicts, and each one is resolved to our version by hand | Same result as A with far more work and risk of mistakes |
| C. Replace `main` | Force-push `production-ready` to `main` | Rewrites public history, breaks clones and needs protection turned off. **Not recommended.** |

**Deploy-day order** (the live Vercel site stays on the old code until the last step):
1. Deploy the backend and run migrations (see the pre-deploy checklist), then smoke-test it directly (`/health`, register/login).
2. Vercel → Project → Settings → Environment Variables:
   - set **`BACKEND_URL`** = the backend's https URL, for Production *and* Preview
   - **delete `NEXT_PUBLIC_API_URL`** if it exists
   - check Root Directory = `frontend`
3. Check a `production-ready` preview deployment against the real backend: login, add an expense, the assistant if enabled, and the refresh cookie (HttpOnly, Secure, Strict, Path `/api/v1/auth`).
4. Option A above: `-s ours` merge commit on `production-ready` → PR to `main` → CI green → merge. Vercel deploys `main`.
5. Smoke-test production. Rollback: Vercel → Deployments → previous deployment → "Instant Rollback". The backend stays compatible because the old frontend never used auth.

### Client IPs and rate limits on Vercel
- With Vercel as the proxy, the backend sees **Vercel's egress IPs**, which aren't fixed or published per project. So uvicorn's `--forwarded-allow-ips` can't safely trust a list of proxy IPs.
- Vercel is documented to set `X-Forwarded-For` / `x-real-ip` / `x-vercel-forwarded-for` with the client IP for external rewrites. **That's unverified here.** Check it on the first preview with `backend/scripts/check_streaming.py`-style header echoing.
- **Recommended:** a small Next.js middleware for `/api/*` that forwards the request with two added headers:
  - `X-Client-IP`, from Vercel's client IP
  - `X-Proxy-Secret`, a shared secret held only in Vercel and backend env vars

  The backend uses `X-Client-IP` for rate limiting **only** when the secret matches, and otherwise falls back to the peer IP.
- The **per-account failed-login limit** (Phase 3) stays as the backstop that doesn't depend on IPs.

## Phase 9 — Documentation
- [ ] README rewrite (Mermaid architecture, env tables, tests, badge, screenshot list)
- [ ] `docs/API.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `LICENSE` (after your choice)

## Phase 10 — Final review
- [ ] Clean-state run of everything (fresh DB, migrations from zero, all suites, builds, compose up)
- [ ] Secret scan (repo + history), auth on every endpoint, CORS and rate limits on, `npm audit`, `pip-audit`
- [ ] Final report + suggested next features (not built)

## Optional later cleanups (not scheduled)
- **Tailwind 4** (clears the last 4 moderate, build-time-only `npm audit` findings). Major upgrade: new config format, and shadcn component class changes.
- **lucide-react 1.x**: major; possible icon renames. Skipped for now.

## Doesn't apply / adjusted
- "Change color" when editing categories: there's no color column. Icon (emoji) editing is supported; adding color is an optional extra.
- "Unique per user" category names: depends on Phase 2.
- Dark mode toggle that follows system preference: already implemented. Will only be checked.
- `expense-spec.md` routes `/` to the dashboard, but the code serves a marketing page at `/`. Keeping the code's behaviour.
