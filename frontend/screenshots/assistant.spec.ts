import { execSync } from "node:child_process";
import path from "node:path";
import { expect, Page, test } from "@playwright/test";
import { mockAssistant } from "../e2e/assistant-mock";

/**
 * Assistant screens (Phase A2) for review, light and dark. The assistant API is faked
 * in the browser with real answers for the demo data (no model is called).
 */
const OUT = path.resolve(__dirname, "../../docs/screenshots");
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

async function shot(page: Page, name: string, scheme: "light" | "dark") {
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(300);
  const project = test.info().project.name;
  const suffix = scheme === "dark" ? "-dark" : "";
  await page.screenshot({
    path: path.join(OUT, `${project}-assistant-${name}${suffix}.png`),
    fullPage: true,
  });
}

async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(DEMO.email);
  await page.getByLabel("Password").fill(DEMO.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/dashboard/);
}

const input = (page: Page) => page.getByRole("textbox", { name: "Message the assistant" });

for (const scheme of ["light", "dark"] as const) {
  test(`assistant screens (${scheme})`, async ({ page }) => {
    await page.emulateMedia({ colorScheme: scheme, reducedMotion: "reduce" });

    // Opt-in card (assistant is off by default)
    await page.unrouteAll();
    await mockAssistant(page, { enabled: false });
    await login(page);
    await page.goto("/assistant");
    await expect(page.getByRole("button", { name: "Turn on assistant" })).toBeVisible();
    await shot(page, "opt-in", scheme);

    // Empty state with suggestion chips
    await page.getByRole("button", { name: "Turn on assistant" }).click();
    await expect(page.getByRole("button", { name: "Where can I save money?" })).toBeVisible();
    await shot(page, "empty", scheme);

    // A streamed answer (English), then a Bangla follow-up in the same chat
    await page.getByRole("button", { name: "How much did I spend this month?" }).click();
    await expect(page.locator("strong", { hasText: "Where you can save" })).toBeVisible();
    await shot(page, "answer", scheme);
    await input(page).fill("এই মাসে আমার বাজেটের অবস্থা কেমন?");
    await input(page).press("Enter");
    await expect(page.locator("strong", { hasText: "বাজেটের অবস্থা" })).toBeVisible();
    await shot(page, "answer-bangla", scheme);

    // Quick-add card: pending, then saved
    // Sidebar button on desktop, header icon on phones
    await page.getByRole("button", { name: "New chat" }).filter({ visible: true }).first().click();
    await input(page).fill("আজ দুপুরের খাবার ২৫০ টাকা");
    await input(page).press("Enter");
    const card = page.getByRole("region", { name: "Expense to confirm" });
    await expect(card.getByRole("button", { name: /Save expense/ })).toBeEnabled();
    await shot(page, "quick-add", scheme);
    await card.getByRole("button", { name: /Save expense/ }).click();
    await expect(card.getByRole("status")).toContainText("Saved");
    await shot(page, "quick-add-saved", scheme);

    // Daily limit reached
    await page.unrouteAll();
    await mockAssistant(page, { messagesToday: 20 });
    await page.goto("/assistant");
    await expect(page.getByText("You've used all 20 assistant messages")).toBeVisible();
    await shot(page, "daily-limit", scheme);
  });
}
