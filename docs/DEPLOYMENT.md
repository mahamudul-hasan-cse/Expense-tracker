# Deploying Wallet Agent

A click-by-click guide for a first deployment. It takes about 45 minutes and costs **$0/month** to start.

| Part | Where | Why |
|---|---|---|
| Website (Next.js) | **Vercel** (already set up) | It already deploys this repo's `main` branch to https://expense-tracker-orcin-pi.vercel.app |
| API (FastAPI) | **Render**, Singapore region, Docker | Free plan, a Singapore region near Bangladesh, deploys from GitHub after CI passes, built-in health checks and logs |
| Database (Postgres) | **Neon**, Singapore region | Free plan that doesn't expire, 1 GB, backups by point-in-time restore |

```
Browser ──> Vercel (website + /api proxy) ──> Render (API) ──> Neon (Postgres)
            adds X-Client-IP + secret          runs migrations on start
```

The browser only ever talks to Vercel. Vercel forwards `/api/*` to the API, so the login cookie stays on your website's domain.

---

## Why these hosts (checked 2026-10-28)

| Option | Free plan | Paid from | Cold start | Notes |
|---|---|---|---|---|
| **Render** web service | 750 instance hours/month; sleeps after **15 min** without traffic | **$7/month** (Starter, 512 MB, always on) | About **1 minute** to wake | Singapore region; Docker; health checks |
| Railway | $5 one-time trial credit (30 days), then $1/month credit | $5/month (Hobby, includes $5 usage) | None (doesn't sleep) | No permanent free plan |
| Koyeb | No free compute listed any more | Pay per use | — | Free Postgres is limited to 5 hours |
| **Neon** Postgres | **1 GB**, 100 compute-hours/project; sleeps after 5 min idle | Pay as you go (from about $0.11/compute-hour) | A short pause on the first query after sleeping | Singapore region; **doesn't expire** |
| Render Postgres | 1 GB | — | — | **Free databases are deleted 30 days after creation**, so not suitable |
| Supabase Postgres | 500 MB | $25/month (Pro) | — | Free projects **pause after 1 week** without activity |

**Recommendation: Render (API) + Neon (database), both in Singapore.**
- **To start:** Render's free plan. One service fits in the 750 free hours (a month has at most 744). An uptime monitor pinging `/health` every 5 minutes keeps it awake (step 6), so users don't wait a minute for the API to wake up.
- **Once real people use it:** upgrade the API to **Render Starter ($7/month)**. It's always on, with no cold starts and more CPU. The database can stay on Neon's free plan until you pass 1 GB, which is many years of expenses for a few users.

Prices and limits change. Check https://render.com/pricing and https://neon.com/pricing before you start.

---

## Before you start
- The pull request from `production-ready` into `main` is merged. Render deploys `main`, and `main` must contain `render.yaml` and `backend/Dockerfile`.
- You can sign in to GitHub and Vercel.
- **Optional (AI assistant):** create a **new** OpenRouter key for production with a monthly limit (e.g. $10): openrouter.ai → Keys → Create key → set **Credit limit**. Don't reuse the key from development.
- Generate the shared proxy secret. Run this once and keep the output for steps 3 and 4:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```

---

## Step 1: Create the database (Neon), 5 minutes
1. Go to https://neon.com and click **Sign up**. Signing up with GitHub is easiest.
2. Click **New project**.
   - **Project name:** `wallet-agent`
   - **Postgres version:** 16 (the version the tests run on)
   - **Region:** **AWS Asia Pacific (Singapore)**
   - Click **Create project**.
3. On the project dashboard, click **Connect**.
   - Turn **Connection pooling OFF**: you want the **direct** connection, whose host has no `-pooler`.
   - Copy the connection string. It looks like:
     `postgresql://neondb_owner:abc123@ep-cool-name-123456.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require`
4. Keep it somewhere private (a password manager). This is your `DATABASE_URL`. **Never put it in git or a chat.**

You don't need to create tables: the API creates them on its first start.

---

## Step 2: Deploy the API (Render), 15 minutes
1. Go to https://render.com and click **Get Started**. Sign up with **GitHub**.
2. Allow Render to access the **Expense-tracker** repository (only that repository is enough).
3. In the Render dashboard, click **New +** → **Blueprint**.
4. Pick the **mahamudul-hasan-cse/Expense-tracker** repository and branch **main**. Render reads `render.yaml` and shows one service, **wallet-agent-api** (Docker, Singapore, Free).
5. Fill in the values Render asks for:

   | Key | Value |
   |---|---|
   | `DATABASE_URL` | the Neon connection string from step 1 |
   | `ALLOWED_ORIGINS` | `https://expense-tracker-orcin-pi.vercel.app` (your website's address, no trailing slash) |
   | `PROXY_SHARED_SECRET` | the secret you generated |
   | `OPENROUTER_API_KEY` | your **production** OpenRouter key, or leave empty to keep the assistant off |
   | `SENTRY_DSN` | leave empty for now (see `docs/MONITORING.md`) |

   `SECRET_KEY` is generated by Render automatically. Don't change it later, or everyone gets logged out.
6. Click **Apply**. The first build takes 3–6 minutes. Open the service → **Logs**. You should see:
   - `Applying database migrations...` and lines like `Running upgrade ... -> c7e9a1b3d5f2`
   - `API started`
7. Find the service's address at the top of its page, e.g. `https://wallet-agent-api.onrender.com`. Open `https://wallet-agent-api.onrender.com/health` in your browser. You should see:
   ```json
   {"status":"healthy","database":"ok"}
   ```
   If the page takes about a minute the first time, that's the free plan waking up.

Render deploys again automatically after every push to `main`, but **only after GitHub CI passes** (`autoDeployTrigger: checksPass`).

---

## Step 3: Point the website at the API (Vercel), 5 minutes
1. Go to https://vercel.com → your **expense-tracker** project → **Settings**.
2. **General → Root Directory:** make sure it is `frontend`. If not, click **Edit**, enter `frontend` and click **Save**.
3. **Environment Variables:**
   - If `NEXT_PUBLIC_API_URL` exists, click ⋯ → **Remove**. It would make the browser skip the proxy and break login cookies.
   - Click **Add New** for each of these, ticking **Production** and **Preview**:

   | Key | Value |
   |---|---|
   | `BACKEND_URL` | `https://wallet-agent-api.onrender.com` (your Render address, no trailing slash) |
   | `PROXY_SHARED_SECRET` | the **same** secret as on Render |

4. Go to **Deployments**, open the latest **Production** deployment → ⋯ → **Redeploy**. `BACKEND_URL` is read at build time, so a redeploy is required.

---

## Step 4: Check that it works, 5 minutes
On https://expense-tracker-orcin-pi.vercel.app:
1. Click **Create account**, register with your email, and land on the dashboard.
2. Add an expense (for example: Rickshaw ৳80). It appears under Recent Expenses.
3. Reload the page and check that you're still signed in.
4. Check the cookie in Chrome: **F12** → **Application** → **Cookies** → your site. `refresh_token` should show **HttpOnly ✓, Secure ✓, SameSite Strict**, Path `/api/v1/auth`.
5. Sign out, then reload: you should land on the sign-in page.
6. **If you set an OpenRouter key:** Settings → AI Assistant → turn it on, then ask "How much did I spend this month?".
7. On Render → your service → **Logs**: requests show your own IP as `client_ip`, not a Vercel address. That means the proxy secret works.

---

## Step 5: Set up monitoring, 10 minutes
Follow `docs/MONITORING.md`:
- **UptimeRobot** keyword monitor on `https://wallet-agent-api.onrender.com/health` every 5 minutes. On the free plan this also keeps the API awake.
- **Sentry** (optional): set `SENTRY_DSN` on Render, and `NEXT_PUBLIC_SENTRY_DSN` + `SENTRY_DSN` on Vercel, then redeploy.

---

## Step 6: After deploying
- **Rotate the development OpenRouter key** if it was ever pasted into a chat or a file: openrouter.ai → Keys → delete it and create a new one for development.
- **Backups:** Neon keeps a restore window (point-in-time restore; the free plan's window is short). For your own copy, run this now and then from your computer:
  ```bash
  pg_dump --format=custom --no-owner --file=wallet_agent_$(date +%Y%m%d).dump "YOUR_NEON_DATABASE_URL"
  ```
- **Upgrade when needed:**
  - Render → service → **Settings → Instance Type → Starter** to remove cold starts.
  - Neon → **Billing** if you pass 1 GB.

---

## Rolling back
- **Website:** Vercel → **Deployments** → pick the previous Production deployment → ⋯ → **Instant Rollback**. It takes seconds.
- **API:** Render → service → **Events** → pick an earlier deploy → **Rollback**.
- **Database:** migrations only add things, so an older API version still works with a newer database. To undo data changes, use Neon → **Restore** (point in time).

---

## Troubleshooting
| Symptom | Likely cause | Fix |
|---|---|---|
| The website loads but signing in fails ("Something went wrong") | `BACKEND_URL` missing or wrong, or no redeploy after setting it | Check the variable in Vercel, then Redeploy |
| `/health` shows "Database unavailable" | Wrong `DATABASE_URL`, or the pooled string was used | Copy the **direct** connection string from Neon again |
| First request after a while is very slow or times out | Free Render plan was asleep | Set up the UptimeRobot monitor, or upgrade to Starter |
| Logged out after every reload | `NEXT_PUBLIC_API_URL` still set in Vercel | Remove it and Redeploy |
| Render deploy fails with "Invalid production configuration" | A required variable is missing or too short | The log lists exactly which one (e.g. `ALLOWED_ORIGINS`, `PROXY_SHARED_SECRET` < 32 characters) |
| Everyone shares one rate limit / logs show Vercel IPs | `PROXY_SHARED_SECRET` missing or different on one side | Set the same value on Render and Vercel, then redeploy both |

---

## Running everything locally in Docker (optional)
With Docker Desktop running:
```bash
docker compose --profile full up --build
```
Then open http://localhost:3000. This starts Postgres, the API (which runs its migrations on start) and the website. CI runs the same stack on every push (the "Docker" job).
