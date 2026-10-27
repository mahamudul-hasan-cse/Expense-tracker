# Monitoring

Three things tell you the app is healthy in production:

| What | Tool | Cost | What it catches |
|---|---|---|---|
| **Uptime** | UptimeRobot (or Better Stack) pinging `/health` | Free | The API is down, or it can't reach the database |
| **Errors** | Sentry (backend and frontend) | Free tier: 5,000 errors/month | Crashes and unexpected errors, with the stack trace |
| **Logs** | Your host's log viewer | Included | Every request (one JSON line each, with a request id) |

Sentry is **off unless you set a DSN**, so local development and CI never send anything.

---

## 1. Uptime monitoring for `/health` (5 minutes, free)

`GET /health` on the backend returns:
- `200 {"status": "healthy", "database": "ok"}` when the API and the database work;
- `503` when the database can't be reached.

It isn't rate limited, needs no login, and returns no user data.

**UptimeRobot (recommended: free, 50 monitors, checks every 5 minutes):**
1. Sign up at https://uptimerobot.com and verify your email.
2. Click **+ New monitor**.
3. **Monitor type:** choose **Keyword**.
4. **URL:** `https://YOUR-BACKEND-HOST/health` (your backend's address, for example `https://wallet-agent-api.onrender.com/health`).
5. **Keyword:** `healthy`, and choose **Alert when keyword does not exist**. The monitor then fails both when the API is down and when the database is down (the 503 response doesn't contain "healthy").
6. **Monitoring interval:** 5 minutes.
7. Under **Alert contacts**, tick your email. Click **Create monitor**.
8. Add a second monitor of type **HTTP(s)** for the website itself: `https://expense-tracker-orcin-pi.vercel.app`.

> **Free hosting note:** if the backend runs on a plan that sleeps when idle (see `docs/DEPLOYMENT.md`), the 5-minute ping also keeps it awake. That's allowed on Render's free plan, but it uses your free hours (one always-on service fits in the monthly allowance).

**Alternative:** Better Stack (https://betterstack.com/uptime) has a similar free plan with a status page.

---

## 2. Error tracking with Sentry

### Create the projects (free)
1. Sign up at https://sentry.io (the **Developer** plan is free).
2. Create a project → platform **FastAPI** → name it `wallet-agent-api`. Copy the **DSN** it shows (looks like `https://abc123@o123456.ingest.sentry.io/789`).
3. Create a second project → platform **Next.js** → name it `wallet-agent-web`. Copy its DSN.

A DSN only lets someone *send* events to your project, not read them. It's normal for the frontend DSN to be visible in the browser.

### Backend (FastAPI)
Set these environment variables on the backend host:

| Variable | Value |
|---|---|
| `SENTRY_DSN` | the `wallet-agent-api` DSN |
| `SENTRY_ENVIRONMENT` | `production` (optional; defaults to `APP_ENV`) |
| `SENTRY_RELEASE` | optional: the git commit, e.g. Render's `RENDER_GIT_COMMIT` |
| `SENTRY_TRACES_SAMPLE_RATE` | `0` (errors only; fits the free tier). `0.05` = trace 5% of requests |

Restart the backend. The log shows `Sentry enabled`.

### Frontend (Next.js on Vercel)
In Vercel → Project → **Settings → Environment Variables**, add (Production and Preview):

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_SENTRY_DSN` | the `wallet-agent-web` DSN (browser errors) |
| `SENTRY_DSN` | the same DSN (errors while rendering on the server) |
| `NEXT_PUBLIC_SENTRY_ENVIRONMENT` | `production` (optional) |

Redeploy (Deployments → ⋯ → **Redeploy**). The `NEXT_PUBLIC_` value is read at build time, so a redeploy is required.

### What is sent (and what isn't)
- **Sent:** the error message and stack trace, the page or API route, browser/OS, the release, and the request id (`X-Request-ID`), which matches the backend log line for that request.
- **Never sent:**
  - request bodies (expenses, notes, chat messages, passwords), cookies, `Authorization` headers and query strings;
  - IP addresses (`send_default_pii` is off, and the backend also removes them);
  - the AI assistant's conversations;
  - session replays (not enabled).

The backend rules live in `backend/app/monitoring.py` (`scrub_event`, with tests in `tests/test_monitoring.py`), and the frontend rules in `frontend/src/lib/sentry.ts`.

### Test it
- **Backend:** temporarily stop the database (or point `DATABASE_URL` at a wrong host), open `/health`, and an "health check: database unreachable" error appears in Sentry within a minute.
- **Frontend:** in the browser console on the live site, run `setTimeout(() => { throw new Error("Sentry test") })`. The error appears in the `wallet-agent-web` project.

### Alerts
Sentry emails you about **new** issues by default (Settings → Alerts). For a small app, keep that default; add a rule "more than 10 events in an hour" if you want to hear about spikes.

---

## 3. Logs
The backend writes one JSON line per request in production: method, path, status, duration and request id. Errors include the stack trace.
- On Render: your service → **Logs** (search by request id).
- AI assistant usage and cost: `uv run python -m app.cli assistant-usage --days 7` (on the server's shell).
