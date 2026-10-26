# Testing

Three suites, one command each. None of them call OpenRouter or any other external API.

| Suite | Command | Needs |
|---|---|---|
| Backend (pytest, coverage gate 80%) | `cd backend && uv run pytest` | Postgres test database |
| Frontend unit (Vitest + Testing Library) | `cd frontend && npm test` | nothing |
| End-to-end (Playwright, production build) | `cd frontend && npm run test:e2e` | Postgres e2e database, `uv` |

## Databases

Tests use **separate databases**, never your development one, because they're wiped and migrated during runs.

```bash
docker-compose up -d    # Postgres on localhost:5432 (wallet_user / wallet_pass)
docker exec -it wallet_agent_db psql -U wallet_user -d wallet_agent \
  -c "CREATE DATABASE wallet_agent_test" -c "CREATE DATABASE wallet_agent_e2e"
```

The defaults point at those names on `localhost:5432`. Override them with:
- `TEST_DATABASE_URL`: backend pytest. The schema is rebuilt from the Alembic migrations (down to base and up again) once per run, and every table is truncated between tests.
- `E2E_DATABASE_URL`: Playwright. Migrated to head on start. Each run registers fresh users with unique emails.

## Backend: `uv run pytest`
- Coverage is printed automatically, and the run **fails below 80%**.
- What's covered: auth and tokens, cross-user isolation on every endpoint, money/date/note validation, recurring due-date rules (weekly, monthly, 31st in February, leap years, December rollover, due today), Asia/Dhaka "today" on a UTC server, stats totals and breakdowns, budgets, CSV export, rate limits, error format, CORS, `/health`, config validation, the admin CLI.
- Useful variants:
  - `uv run pytest tests/test_recurring.py -q`
  - `uv run pytest -k isolation`
  - `uv run pytest --no-cov` (faster)

## Frontend unit: `npm test`
- Vitest with jsdom. **The timezone is forced to Asia/Dhaka**, so the results don't depend on the machine.
- `npm run test:watch` for watch mode.
- What's covered: date helpers (Dhaka before 6 AM, midnight, New Year, no off-by-one), currency formatting, expense filter params (including the "All Categories" regression), API error parsing, the expense form (required fields, max date, clearing the note, keeping input after a failed save, inline new category), the auth form (password rule, errors, safe `next` redirects, session-expired notice).

## End-to-end: `npm run test:e2e`
- `playwright.config.ts` starts both servers itself:
  - the backend on :8100 (runs migrations first)
  - a **production build** of the frontend on :3100, built into `.next-e2e` so a running `next dev` is left alone
- The browser runs in the Asia/Dhaka timezone. Rate limiting is off and the assistant key is blanked for these runs.
- First time only: `npx playwright install chromium`.
- Flows: register → add expense → dashboard and list → logout → login → session restored on reload; wrong password; budget creation updating live as expenses are added; expense filters (search, category, back to All Categories, date range).
- On failure: `npx playwright show-trace test-results/<test>/trace.zip`.

## Lint, format, types

| | Backend (`cd backend`) | Frontend (`cd frontend`) |
|---|---|---|
| Lint | `uv run ruff check .` | `npm run lint` |
| Format | `uv run ruff format .` | `npm run format` (`format:check` in CI) |
| Types | `uv run mypy` | `npm run typecheck` |

**Pre-commit hooks** (ruff, Prettier, ESLint, whitespace/YAML checks, private-key and **gitleaks secret scanning**): run `uvx pre-commit install` once. Then they run on every commit; to run them on everything, use `uvx pre-commit run --all-files`.

**CI** (`.github/workflows/ci.yml`) runs on every push to `main` and on every PR:
- **backend**: ruff, format check, mypy, pytest against a Postgres 16 service
- **frontend**: ESLint, Prettier check, `tsc`, Vitest, production build
- **e2e**: Playwright against a production build, with a Postgres service. Runs after the first two pass; the report is uploaded on failure.

Dependencies are cached (uv, npm, Playwright browsers). `OPENROUTER_API_KEY` is empty in CI.
