import { defineConfig, devices } from "@playwright/test";

/**
 * E2E tests run against a production build of the frontend (next build + next
 * start) talking to a real FastAPI backend and Postgres.
 *
 * E2E_DATABASE_URL must point at a dedicated, migratable database (it gets
 * test users written to it). Default: wallet_agent_e2e on localhost:5432.
 * Ports 3100/8100 are used so a normal dev setup on 3000/8000 keeps running.
 */
const FRONTEND_PORT = 3100;
const BACKEND_PORT = 8100;
const databaseUrl =
  process.env.E2E_DATABASE_URL ??
  "postgresql://wallet_user:wallet_pass@localhost:5432/wallet_agent_e2e";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  timeout: 60_000,
  use: {
    baseURL: `http://127.0.0.1:${FRONTEND_PORT}`,
    trace: "retain-on-failure",
    // Users are in Bangladesh; dates in the UI follow the browser timezone
    timezoneId: "Asia/Dhaka",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: `uv run alembic upgrade head && uv run uvicorn app.main:app --host 127.0.0.1 --port ${BACKEND_PORT}`,
      cwd: "../backend",
      url: `http://127.0.0.1:${BACKEND_PORT}/health`,
      env: {
        DATABASE_URL: databaseUrl,
        APP_ENV: "development",
        ALLOWED_ORIGINS: `http://127.0.0.1:${FRONTEND_PORT}`,
        // Each run registers fresh users; IP limits would make reruns flaky
        RATE_LIMIT_ENABLED: "false",
        // The assistant must never call the real API from tests
        OPENROUTER_API_KEY: "",
      },
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: `npm run build && npx next start -H 127.0.0.1 -p ${FRONTEND_PORT}`,
      url: `http://127.0.0.1:${FRONTEND_PORT}/login`,
      env: {
        BACKEND_URL: `http://127.0.0.1:${BACKEND_PORT}`,
        NEXT_DIST_DIR: ".next-e2e",
      },
      reuseExistingServer: !process.env.CI,
      timeout: 300_000,
    },
  ],
});
