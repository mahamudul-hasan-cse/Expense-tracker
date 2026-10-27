import { expect, Page, test } from "@playwright/test";
import { mockAssistant } from "./assistant-mock";

/**
 * Assistant chat UI. The assistant API is faked in the browser (assistant-mock.ts):
 * no model is ever called. Sign-in and the rest of the app use the real backend.
 */
const password = "assistant-test-password";

async function signUp(page: Page) {
  await page.goto("/register");
  await page.getByLabel("Email").fill(`assistant-${Date.now()}-${Math.random()}@example.com`);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/dashboard/);
}

const chat = (page: Page) => page.getByRole("region", { name: "Assistant chat" });
const input = (page: Page) => page.getByRole("textbox", { name: "Message the assistant" });

test("opt in, ask with a chip, get a formatted answer", async ({ page }) => {
  await mockAssistant(page, { enabled: false });
  await signUp(page);

  // The floating button opens the assistant
  await page.getByRole("link", { name: "Open assistant" }).click();
  await expect(page).toHaveURL(/\/assistant/);

  await page.getByRole("button", { name: "Turn on assistant" }).click();
  const chip = chat(page).getByRole("button", { name: "How much did I spend this month?" });
  await expect(chip).toBeVisible();
  await expect(chat(page).getByRole("button", { name: "এই মাসে কত খরচ হলো?" })).toBeVisible();

  await chip.click();
  const log = chat(page).getByRole("log");
  await expect(log.getByText("How much did I spend this month?")).toBeVisible();
  // Markdown rendered as elements, not raw asterisks
  await expect(log.locator("strong", { hasText: "Short answer:" })).toBeVisible();
  await expect(
    log.locator("li", { hasText: "September: ৳41,715 across 90 expenses" })
  ).toBeVisible();
  await expect(log).not.toContainText("**");
  await expect(chat(page).getByText("16 of 20 left today").first()).toBeAttached();
  // It shows up in the history list
  await expect(
    page.getByRole("complementary", { name: "Chat history" }).getByText("How much did I spend")
  ).toBeAttached();
});

test("quick add: one save even on a double click, then a clear saved state", async ({ page }) => {
  const mock = await mockAssistant(page);
  await signUp(page);
  await page.goto("/assistant");

  await input(page).fill("আজ দুপুরের খাবার ২৫০ টাকা");
  await input(page).press("Enter");

  const card = page.getByRole("region", { name: "Expense to confirm" });
  await expect(card).toContainText("৳250");
  await expect(card).toContainText("Food");
  await expect(card).not.toContainText(/[০-৯]/); // English digits on the card

  await card.getByRole("button", { name: /Save expense/ }).dblclick();
  await expect(card.getByRole("status")).toContainText("Saved to your expenses");
  await expect(card.getByRole("button", { name: /Save expense/ })).toHaveCount(0);
  expect(mock.confirmCalls).toBe(1);
});

test("the daily limit replaces the message box with an explanation", async ({ page }) => {
  await mockAssistant(page, { messagesToday: 20 });
  await signUp(page);
  await page.goto("/assistant");
  await expect(chat(page).getByRole("status")).toContainText(
    "You've used all 20 assistant messages for today"
  );
  await expect(input(page)).toHaveCount(0);
});

test("stop keeps the partial state and offers retry", async ({ page }) => {
  await mockAssistant(page, { replyDelayMs: 3000 });
  await signUp(page);
  await page.goto("/assistant");
  await input(page).fill("Where can I save money?");
  await input(page).press("Enter");
  await expect(chat(page).getByText("Thinking…")).toBeVisible();
  await chat(page).getByRole("button", { name: "Stop" }).click();
  await expect(chat(page).getByText("Stopped.")).toBeVisible();
  await expect(chat(page).getByRole("button", { name: "Retry" })).toBeVisible();
});

test("the live status line follows the question's language", async ({ page }) => {
  await mockAssistant(page, { replyDelayMs: 1500 });
  await signUp(page);
  await page.goto("/assistant");
  await input(page).fill("এই মাসে কত খরচ হলো?");
  await input(page).press("Enter");
  await expect(chat(page).getByText("ভাবছি…")).toBeVisible();
  // Replaced by the answer once it starts
  await expect(chat(page).locator("strong", { hasText: "বাজেটের অবস্থা" })).toBeVisible();
  await expect(chat(page).getByText("ভাবছি…")).toHaveCount(0);
});

test.describe("phone width (375px)", () => {
  test.use({ viewport: { width: 375, height: 812 }, hasTouch: true, isMobile: true });

  test("the chat fits the screen and history opens as a panel", async ({ page }) => {
    await mockAssistant(page);
    await signUp(page);
    await page.goto("/assistant");
    await chat(page).getByRole("button", { name: "Where can I save money?" }).tap();
    await expect(chat(page).locator("strong", { hasText: "Short answer:" })).toBeVisible();
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(scrollWidth).toBeLessThanOrEqual(375);

    await page.getByRole("button", { name: "Chat history" }).tap();
    await expect(
      page.getByRole("complementary", { name: "Chat history" }).getByText("Where can I save money?")
    ).toBeVisible();
  });
});
