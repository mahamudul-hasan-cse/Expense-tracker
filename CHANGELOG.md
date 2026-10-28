# Changelog

All notable changes to this project. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] - 2026-10-28

The first production-ready release: accounts, income and goals, an AI assistant, tests, CI, monitoring and deployment.

### Added
- **Accounts:**
  - register and sign in (Argon2 passwords, 15-minute access tokens, rotating refresh cookie);
  - sign out everywhere;
  - every record belongs to one user, with isolation tests on every endpoint.
- **Income:** income categories, the "This month" row (income, spent, saved, savings rate) and recurring income with "mark received".
- **Savings goals:** contributions and withdrawals, progress, deadline state and the monthly amount needed.
- **AI assistant (opt-in, off by default):**
  - streaming chat in English, Bangla and Banglish about your own data, through OpenRouter with zero-data-retention providers;
  - read-only tools and quick add with confirmation (idempotent);
  - a weekly insight;
  - per-user and global daily limits;
  - model chosen by an 18-question eval: Claude Haiku 5.5, with Gemini 3.5 Flash Lite as fallback.
- **Mobile:** a bottom tab bar, a 2×2 dashboard, and fixed-column lists that fit a 375px screen.
- **Installable app (PWA):** manifest, original icons and theme colour. Also per-page titles, a custom 404 and error pages with "Try again".
- **Inline form validation** with the backend's rules in every form.
- **Monitoring:** optional Sentry for the API and the website (no personal data sent), uptime monitoring guide for `/health`.
- **Deployment:**
  - Dockerfiles for the API and the website, and a full-stack docker compose;
  - migrations on start (under a lock);
  - a Render Blueprint and a beginner's guide (Render + Neon + Vercel);
  - real client IPs for rate limits behind the Vercel proxy.
- **Quality:**
  - about 280 backend tests (96% coverage) and about 100 frontend unit tests;
  - Playwright end-to-end, layout and accessibility (WCAG 2.1 AA) checks;
  - ruff, mypy, ESLint, Prettier, pre-commit with gitleaks;
  - GitHub Actions CI (backend, frontend, e2e, docker); Dependabot.
- **Docs:** README, API, deployment, monitoring, testing, assistant design and evaluation, contributing.

### Changed
- **Next.js 14 → 15.5** (React 19), and up-to-date dependencies:
  - SQLAlchemy 2.1, pydantic 2.14, uvicorn 0.54, alembic 1.20;
  - the psycopg 3 driver;
  - date-fns 4.
- **Dashboard:**
  - "Daily Average" divides by the days so far;
  - "Bills Due" counts only bills;
  - budget colours are amber at 80% and red only when over 100%;
  - the chart legend shows full names and shares.
- **Landing page:** rewritten to describe the app accurately.
- **One error format** for the whole API; rate limits on every route, with stricter limits on login.

### Security
- **FastAPI 0.109 → 0.162 (Starlette 0.35 → 1.10):** fixes known vulnerabilities, including an unvalidated Host header and request path, and unbounded form parsing. Also anyio, certifi and Mako. `pip-audit` and `npm audit` now report nothing.
- **Security headers** on the website (no framing, nosniff, referrer and permissions policies, HSTS) and the API.
- **A test requires authentication on every API route** (it enumerates them, so new routes are covered automatically).
- **Secret scan** of the full git history: clean.

### Fixed
- **"Today" now uses the Asia/Dhaka date.** Before, an expense dated today was rejected between midnight and 6 AM in Dhaka.
- **Streaming responses no longer crash under the rate limiter.** This affected CSV export and assistant answers.
- **Phone layouts:**
  - pages wider than the screen at 375px;
  - edit buttons that only appeared on hover;
  - truncated labels.
- **Accessibility:** colour contrast in light and dark mode, unlabelled inputs, and keyboard focus in charts.
- **Tests:** they used the machine's date instead of the Dhaka date and failed in CI between 18:00 and 24:00 UTC.

## [0.1.0] - 2026-01-20
- **First version:** expenses, categories, budgets, recurring bills, charts and CSV export.
