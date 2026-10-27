# Contributing

Thanks for helping! This guide gets you from a fresh clone to a pull request.

## Set up
You need **Python 3.11+** with [uv](https://docs.astral.sh/uv/), **Node 22**, and **Postgres 16** (Docker is the easiest way to get it).

```bash
git clone https://github.com/mahamudul-hasan-cse/Expense-tracker.git
cd Expense-tracker
docker compose up -d                   # Postgres on localhost:5432

cd backend
cp .env.example .env                   # local defaults work as they are
uv sync
uv run alembic upgrade head
uv run python -m scripts.seed_demo --reset   # optional: demo@example.com / demo-password-123
uv run uvicorn app.main:app --reload --port 8000

cd ../frontend                         # in a second terminal
cp .env.example .env.local
npm install
npm run dev                            # http://localhost:3000
```

Install the git hooks once. They format, lint and scan for secrets on every commit:
```bash
uvx pre-commit install
```

## Making a change
1. Create a branch from `main`: `git switch -c fix/short-description`.
2. Keep each pull request to one change.
3. **Add or update tests:**
   - backend: `backend/tests`
   - frontend logic: `*.test.ts(x)` next to the code
   - user flows: `frontend/e2e`

   See `docs/TESTING.md`.
4. Run the checks locally before pushing:
   ```bash
   cd backend  && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
   cd frontend && npm run lint && npm run format:check && npm run typecheck && npm test
   ```
5. **Database changes** need an Alembic migration:
   - `uv run alembic revision --autogenerate -m "describe it"`
   - Review the generated file, then upgrade/downgrade it locally.
   - Prefer additive changes; anything that deletes data needs a note in the PR.
6. **New settings** go in `backend/.env.example` or `frontend/.env.example`, with a placeholder value and a comment. Never commit real secrets. The `gitleaks` hook and GitHub's push protection both block keys.
7. Open a pull request into `main`. CI must pass:
   - Backend
   - Frontend
   - End-to-end
   - Docker

## House rules
- **Dates:** "today" is the Asia/Dhaka date. Use `app.timeutil.today()` in the backend and `todayISO()` in the frontend, never `date.today()` (ruff blocks it).
- **Money:**
  - format it with `formatCurrency()`, with English digits and the ৳ sign;
  - validate with the same rules as the backend (`frontend/src/lib/validation.ts`).
- **Every endpoint** filters by the signed-in user. Add an isolation test for new data.
- **The AI assistant's tools are read-only.** Writing data always needs the user's confirmation.
- **Tests never call real external APIs.** The OpenRouter client refuses to run when `APP_ENV=test`.
- **Accessibility:** labelled inputs, buttons with names, enough contrast. `e2e/a11y.spec.ts` checks every page.
- **Writing in the UI:** short, plain sentences.

## Reporting a security problem
Please don't open a public issue. Email the maintainer (see the GitHub profile) with the details, and allow time for a fix before disclosing it.
