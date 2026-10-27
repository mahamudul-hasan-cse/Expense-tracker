import { execSync } from "node:child_process";
import path from "node:path";
import AxeBuilder from "@axe-core/playwright";
import { expect, Page, test } from "@playwright/test";
import { mockAssistant } from "./assistant-mock";

/**
 * Automated accessibility check (axe-core, WCAG 2.1 A/AA) of every page, light and dark,
 * desktop and phone width. Fails on serious or critical problems (e.g. contrast, missing
 * labels, buttons without names). The assistant API is faked in the browser.
 */
const DEMO = { email: "demo@example.com", password: "demo-password-123" };
const databaseUrl =
  process.env.E2E_DATABASE_URL ??
  "postgresql://wallet_user:wallet_pass@localhost:5432/wallet_agent_e2e";

const PUBLIC_PAGES = ["/", "/login", "/register", "/this-page-does-not-exist"];
const APP_PAGES = ["/dashboard", "/expenses", "/income", "/goals", "/settings", "/assistant"];

test.describe.configure({ mode: "serial" });

test.beforeAll(() => {
  execSync("uv run python -m scripts.seed_demo --reset", {
    cwd: path.resolve(__dirname, "../../backend"),
    env: { ...process.env, DATABASE_URL: databaseUrl, APP_ENV: "development" },
    stdio: "inherit",
  });
});

async function expectNoSeriousViolations(page: Page, label: string) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  const serious = results.violations.filter(
    (v) => v.impact === "serious" || v.impact === "critical"
  );
  const report = serious
    .map(
      (v) =>
        `${v.id} (${v.impact}): ${v.help}\n    ${v.nodes
          .slice(0, 4)
          .map((n) => n.target.join(" "))
          .join("\n    ")}`
    )
    .join("\n");
  expect(serious, `${label}\n${report}`).toEqual([]);
}

async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(DEMO.email);
  await page.getByLabel("Password").fill(DEMO.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/dashboard/);
}

async function scanAll(page: Page, scheme: "light" | "dark") {
  await page.emulateMedia({ colorScheme: scheme, reducedMotion: "reduce" });
  for (const url of PUBLIC_PAGES) {
    await page.goto(url);
    await page.waitForLoadState("networkidle");
    await expectNoSeriousViolations(page, `${url} (${scheme})`);
  }
  await mockAssistant(page);
  await login(page);
  for (const url of APP_PAGES) {
    await page.goto(url);
    await page.waitForLoadState("networkidle");
    await expectNoSeriousViolations(page, `${url} (${scheme})`);
  }
  // A dialog, with a validation error showing
  await page.goto("/dashboard");
  await page.getByRole("button", { name: "New Expense" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Save Expense" }).click();
  await expect(page.getByRole("dialog").getByText("Enter an amount")).toBeVisible();
  await expectNoSeriousViolations(page, `expense dialog (${scheme})`);
}

for (const scheme of ["light", "dark"] as const) {
  test(`every page meets WCAG 2.1 AA basics (${scheme}, desktop)`, async ({ page }) => {
    await scanAll(page, scheme);
  });

  test.describe(`phone width (${scheme})`, () => {
    test.use({ viewport: { width: 375, height: 812 }, hasTouch: true, isMobile: true });
    test(`every page meets WCAG 2.1 AA basics (${scheme}, 375px)`, async ({ page }) => {
      await scanAll(page, scheme);
    });
  });
}
