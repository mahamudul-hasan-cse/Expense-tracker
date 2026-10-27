import { execSync } from "node:child_process";
import path from "node:path";
import { expect, Page, test } from "@playwright/test";

const OUT = path.resolve(__dirname, "../../docs/screenshots");
const DEMO = { email: "demo@example.com", password: "demo-password-123" };
const databaseUrl =
  process.env.E2E_DATABASE_URL ??
  "postgresql://wallet_user:wallet_pass@localhost:5432/wallet_agent_e2e";

test.describe.configure({ mode: "serial" });

test.beforeAll(() => {
  // Fresh, deterministic demo data (the backend web server has already migrated the DB)
  execSync("uv run python -m scripts.seed_demo --reset", {
    cwd: path.resolve(__dirname, "../../backend"),
    env: { ...process.env, DATABASE_URL: databaseUrl, APP_ENV: "development" },
    stdio: "inherit",
  });
});

async function shot(page: Page, name: string, { settle = 300 } = {}) {
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(settle); // let toasts/animations land
  const project = test.info().project.name;
  await page.screenshot({ path: path.join(OUT, `${project}-${name}.png`), fullPage: true });
}

async function login(page: Page, email: string, password: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/dashboard/);
}

test("public pages", async ({ page }) => {
  await page.goto("/");
  await shot(page, "landing");
  await page.goto("/login");
  await shot(page, "login");
  await page.goto("/register");
  await shot(page, "register");

  // Validation: short password on register
  await page.getByLabel("Email").fill("someone@example.com");
  await page.getByLabel("Password").fill("short");
  await page.getByRole("button", { name: "Create account" }).click();
  await shot(page, "register-validation-error");

  // Wrong password on login
  await page.goto("/login");
  await page.getByLabel("Email").fill(DEMO.email);
  await page.getByLabel("Password").fill("wrong-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText("Invalid email or password")).toBeVisible();
  await shot(page, "login-error");
});

test("demo user: every page", async ({ page }) => {
  await login(page, DEMO.email, DEMO.password);
  await shot(page, "dashboard", { settle: 1800 }); // Recharts animates for ~1.5s

  for (const [href, name] of [
    ["/expenses", "expenses"],
    ["/income", "income"],
    ["/goals", "goals"],
    ["/settings", "settings"],
  ] as const) {
    await page.goto(href);
    await shot(page, name);
  }

  // Dialogs and a validation error
  await page.goto("/dashboard");
  await page.getByRole("button", { name: "New Expense" }).click();
  await shot(page, "expense-dialog");
  await page
    .getByRole("dialog")
    .getByLabel(/Amount/)
    .fill("120");
  await page.getByRole("dialog").getByRole("button", { name: "Save Expense" }).click();
  await shot(page, "expense-validation-error");
  await page.keyboard.press("Escape");

  await page.goto("/goals");
  await page.getByRole("button", { name: "New Goal" }).first().click();
  await page.getByRole("dialog").getByLabel("Name *").fill("Trip to Cox's Bazar");
  await page.getByRole("dialog").getByRole("button", { name: "Create Goal" }).click();
  await shot(page, "goal-validation-error");
  await page.keyboard.press("Escape");

  // Dark mode
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/dashboard");
  await shot(page, "dashboard-dark", { settle: 1800 });
});

test("brand-new user: empty states", async ({ page }) => {
  const project = test.info().project.name;
  await page.goto("/register");
  await page.getByLabel("Email").fill(`empty-${project}-${Date.now()}@example.com`);
  await page.getByLabel("Password").fill("empty-state-password");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/dashboard/);
  await shot(page, "empty-dashboard", { settle: 800 });
  for (const [href, name] of [
    ["/expenses", "empty-expenses"],
    ["/income", "empty-income"],
    ["/goals", "empty-goals"],
  ] as const) {
    await page.goto(href);
    await shot(page, name);
  }
});
