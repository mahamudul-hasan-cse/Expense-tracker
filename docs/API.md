# Wallet Agent API

The backend is a FastAPI app. Interactive docs with every request and response schema are generated from the code:

- **Swagger UI:** `http://localhost:8000/docs`
- **OpenAPI JSON:** `http://localhost:8000/openapi.json`

This page is the overview: how to authenticate, the conventions shared by all endpoints, and the full route list.

## Base URL
- Local: `http://localhost:8000/api/v1`
- In production the browser calls the **website's own** `/api/v1/...`, which Vercel forwards to the API (see `docs/DEPLOYMENT.md`).

## Authentication
1. `POST /auth/register` or `POST /auth/login` with `{"email", "password"}` returns `{"access_token", "token_type": "bearer", "user"}` and sets a **refresh cookie** (`refresh_token`: HttpOnly, Secure in production, SameSite=Strict, Path `/api/v1/auth`).
2. Send the access token on every other call: `Authorization: Bearer <access_token>`. It expires after **15 minutes**.
3. When a call returns `401`, call `POST /auth/refresh` once. The browser sends the cookie automatically, you get a new access token, and the cookie rotates. If that also fails, the session is over: sign in again.
4. `POST /auth/logout` revokes **every** token of the user (all devices) and clears the cookie.

Passwords: at least 8 characters, hashed with Argon2. Every data endpoint only ever returns the signed-in user's own data; another user's ids return `404`.

## Conventions
- **Money** is a decimal with at most 2 places, more than 0, at most 99,999,999.99. Responses return numbers.
- **Dates** are `YYYY-MM-DD`. "Today" is the **Asia/Dhaka** date (`APP_TIMEZONE`). Expense, income and contribution dates can't be in the future.
- **Lists** take `page` (from 1) and `limit`, and return `{"<items>": [...], "pagination": {"page", "limit", "total_items", "total_pages"}}`.
- **Errors** always look like this:
  ```json
  {"error": {"code": "validation_error", "message": "...", "details": [{"field": "amount", "message": "..."}], "request_id": "9f3c..."}}
  ```
  Codes include `bad_request`, `unauthorized`, `not_found`, `conflict`, `validation_error` (422), `rate_limited` (429) and `internal_error` (500, with no internal details). `request_id` matches the `X-Request-ID` response header and the server log line.
- **Rate limits:** 120 requests/minute per IP by default. Login and register get 5/minute and 20/hour per IP, plus **10 failed logins per hour per account** from any IP. Over a limit you get `429` (`rate_limited`); wait and try again.

## Assistant streaming
`POST /assistant/chat` with `{"message", "conversation_id"?}` answers with **server-sent events** (`text/event-stream`):

| Event | Data |
|---|---|
| `conversation` | `{"id", "title"}`, sent first |
| `status` | `{"text", "tool"}`: what it's looking up, in the user's language |
| `token` | `{"text"}`: the next piece of the answer |
| `proposal` | a quick-add expense to confirm (amount, category, date, note). Nothing is saved yet. |
| `done` | `{"message_id", "model", "proposal"}` |
| `error` | `{"code", "message", "retry_after"?}` |

If the assistant can't be used (turned off, daily limit, global budget), the endpoint returns a normal JSON error instead of a stream, with the reason in `details` (`disabled`, `daily_limit`, `daily_budget_reached`, `not_configured`).

Save a proposal with `POST /assistant/messages/{message_id}/proposal/confirm` (optional body: corrected `amount`, `category_id`, `expense_date`, `note`). It's idempotent: repeating it returns the same expense. Proposals expire after 24 hours.

## Routes
All paths below start with `/api/v1` except `/health`.

### Auth
| Method | Path | What it does |
|---|---|---|
| POST | `/auth/register` | Create an account (with the default categories) and sign in |
| POST | `/auth/login` | Sign in with email and password |
| POST | `/auth/refresh` | New access token from the refresh cookie (rotates the cookie) |
| POST | `/auth/logout` | Sign out everywhere: revokes all tokens, clears the cookie |
| GET | `/auth/me` | The signed-in user |

### Expenses and categories
| Method | Path | What it does | Query |
|---|---|---|---|
| GET | `/expenses` | List with filters, search and sorting | `page`, `limit`, `category_id`, `start_date`, `end_date`, `search` (in notes), `sort` (`date_desc`, `date_asc`, `amount_desc`, `amount_asc`) |
| POST | `/expenses` | Create (`amount`, `category_id`, `note`?, `expense_date`? = today) | |
| PUT | `/expenses/{id}` | Update any field (`note: null` clears it) | |
| DELETE | `/expenses/{id}` | Delete | |
| GET | `/categories` | Expense categories (defaults first) | `page`, `limit` |
| POST | `/categories` | Create (`name`, `icon`?) | |
| PUT | `/categories/{id}` | Rename or change the icon | |
| DELETE | `/categories/{id}` | Delete a non-default category that no expense uses | |

### Income
| Method | Path | What it does | Query |
|---|---|---|---|
| GET | `/incomes` | List with filters, search and sorting (same options as expenses) | `page`, `limit`, `income_category_id`, `start_date`, `end_date`, `search`, `sort` |
| POST | `/incomes` | Record money received (`amount`, `income_category_id`, `note`?, `income_date`?) | |
| PUT | `/incomes/{id}` | Update | |
| DELETE | `/incomes/{id}` | Delete | |
| GET | `/income-categories` | Income categories (defaults first) | `page`, `limit` |
| POST | `/income-categories` | Create | |
| PUT | `/income-categories/{id}` | Rename or change the icon | |
| DELETE | `/income-categories/{id}` | Delete one that nothing uses | |

### Budgets
| Method | Path | What it does | Query |
|---|---|---|---|
| GET | `/budgets` | Budgets for a month, with spent and % used | `month`, `year` (default: this month), `page`, `limit` |
| POST | `/budgets` | Create (`category_id`, `amount`, `month`, `year`) | |
| GET | `/budgets/summary` | Totals for a month | `month`, `year` |
| PUT | `/budgets/{id}` | Change the amount | |
| DELETE | `/budgets/{id}` | Delete | |

### Recurring bills and income
| Method | Path | What it does | Query |
|---|---|---|---|
| GET | `/recurring` | Recurring items | `kind` (`expense`/`income`), `page`, `limit` |
| POST | `/recurring` | Create (`name`, `amount`, `kind`, category, `frequency` `weekly`/`monthly`, `due_day`) | |
| PUT | `/recurring/{id}` | Update, pause/resume (`is_active`) | |
| DELETE | `/recurring/{id}` | Delete | |
| POST | `/recurring/{id}/mark-paid` | Record this cycle as paid (creates the expense) or received (creates the income) | |

### Savings goals
| Method | Path | What it does | Query |
|---|---|---|---|
| GET | `/goals` | Goals with progress, state and the monthly amount needed | `status` (`active`/`archived`/`all`), `page`, `limit` |
| POST | `/goals` | Create (`name`, `target_amount`, `target_date`?, `icon`?) | |
| PUT | `/goals/{id}` | Edit, remove the deadline, archive/restore | |
| DELETE | `/goals/{id}` | Delete with its contributions | |
| GET | `/goals/{id}/contributions` | Contributions | `page`, `limit` |
| POST | `/goals/{id}/contributions` | Add money (positive) or take it back (negative) | |
| DELETE | `/goals/{id}/contributions/{contribution_id}` | Remove a contribution | |

### Statistics and export
| Method | Path | What it does | Query |
|---|---|---|---|
| GET | `/stats/summary` | Spending total, by category and by day | `period` (`weekly`/`monthly`), `date` |
| GET | `/stats/cashflow` | Income, spent, saved and savings rate for a month | `month` (`YYYY-MM`) |
| GET | `/stats/upcoming-recurring` | Bills and income due in the next 7 days | |
| GET | `/export/csv` | Expenses and income as CSV (a Type column says which) | `start_date`, `end_date` |

### AI assistant (opt-in)
| Method | Path | What it does |
|---|---|---|
| GET | `/assistant/status` | Can it be used now, and why not; messages used today and the daily limit |
| PUT | `/assistant/settings` | Turn it on or off for this user (`{"enabled": true}`) |
| POST | `/assistant/chat` | Ask a question; the answer streams back (see above) |
| GET | `/assistant/conversations` | Chat history (`page`, `limit`) |
| GET | `/assistant/conversations/{id}` | One conversation with its messages |
| DELETE | `/assistant/conversations/{id}` | Delete one conversation |
| DELETE | `/assistant/conversations` | Delete all chats and saved insights |
| GET | `/assistant/insights/weekly` | This week's short insight (written at most once a day) |
| POST | `/assistant/messages/{id}/proposal/confirm` | Save a quick-add expense (idempotent) |
| POST | `/assistant/messages/{id}/proposal/cancel` | Dismiss a quick-add expense |

### Health
| Method | Path | What it does |
|---|---|---|
| GET | `/health` | `200 {"status": "healthy", "database": "ok"}`, or `503` when the database is unreachable. No login, not rate limited. |
