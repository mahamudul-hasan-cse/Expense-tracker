import { execSync } from "node:child_process";
import path from "node:path";
import { expect, Page, test } from "@playwright/test";

/**
 * Layout regressions found in the screenshot review (docs/IMPROVEMENTS.md, P1 items).
 * Uses the seeded demo user so charts and lists have realistic data.
 */
const DEMO = { email: "demo@example.com", password: "demo-password-123" };
const databaseUrl =
  process.env.E2E_DATABASE_URL ??
  "postgresql://wallet_user:wallet_pass@localhost:5432/wallet_agent_e2e";

test.describe.configure({ mode: "serial" });

test.beforeAll(() => {
  execSync("uv run python -m scripts.seed_demo --reset", {
    cwd: path.resolve(__dirname, "../../backend"),
    env: { ...process.env, DATABASE_URL: databaseUrl, APP_ENV: "development" },
    stdio: "inherit",
  });
});

async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(DEMO.email);
  await page.getByLabel("Password").fill(DEMO.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/dashboard/);
}

test("daily spending bars spread across the whole chart, even right after a resize", async ({
  page,
}) => {
  // Screenshots showed every bar bunched into the first ~2 days: full-page capture
  // resizes the viewport and Recharts re-animated the bars from stale positions.
  // With reduced motion the chart must be correct immediately, with no waiting.
  await page.emulateMedia({ reducedMotion: "reduce" });
  await login(page);
  const chart = page.getByRole("region", { name: "Daily Spending Trend" });
  const bars = chart.locator(".recharts-bar-rectangle path");
  await expect(bars.first()).toBeVisible();
  await page.setViewportSize({ width: 1440, height: 2400 });

  const { spread, plotWidth, barCount } = await chart.evaluate((el) => {
    const svg = el.querySelector("svg.recharts-surface") as SVGSVGElement;
    const xs = Array.from(el.querySelectorAll(".recharts-bar-rectangle path"))
      .map((p) => (p as SVGGraphicsElement).getBBox())
      .filter((b) => b.height > 0)
      .map((b) => b.x);
    return {
      spread: Math.max(...xs) - Math.min(...xs),
      plotWidth: svg.getBoundingClientRect().width,
      barCount: xs.length,
    };
  });
  expect(barCount).toBeGreaterThan(5);
  expect(spread).toBeGreaterThan(plotWidth * 0.5);
});

test.describe("phone width (375px)", () => {
  test.use({ viewport: { width: 375, height: 812 }, hasTouch: true, isMobile: true });

  const pages = ["/dashboard", "/expenses", "/income", "/goals", "/settings"];

  test("no page is wider than the screen", async ({ page }) => {
    for (const publicPath of ["/", "/login", "/register"]) {
      await page.goto(publicPath);
      await assertNoHorizontalOverflow(page, publicPath);
    }
    await login(page);
    for (const appPath of pages) {
      await page.goto(appPath);
      await page.waitForLoadState("networkidle");
      await assertNoHorizontalOverflow(page, appPath);
    }
  });

  test("row actions are visible without hover on touch screens", async ({ page }) => {
    await login(page);
    // Nothing in the app may hide actions until hover
    const hoverOnly = await page.locator('[class*="group-hover:opacity"]').count();
    expect(hoverOnly).toBe(0);

    const recent = page.getByRole("region", { name: "Recent Expenses" });
    const edit = recent.getByRole("button", { name: /^Edit/ }).first();
    await expect(edit).toBeVisible();
    expect(await edit.evaluate((el) => getComputedStyle(el).opacity)).toBe("1");
    await edit.tap();
    await expect(page.getByRole("dialog").getByText("Edit Expense")).toBeVisible();
  });
});

async function assertNoHorizontalOverflow(page: Page, label: string) {
  // Compare with the configured width, not window.innerWidth: mobile browsers widen
  // the layout viewport to fit overflowing content, so innerWidth would grow with it
  const screenWidth = page.viewportSize()!.width;
  const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
  expect(
    scrollWidth,
    `${label} is ${scrollWidth}px wide on a ${screenWidth}px screen`
  ).toBeLessThanOrEqual(screenWidth);
}
