import { expect, Page, test } from "@playwright/test";

// Unique per run so reruns never collide with existing accounts
const email = `smoke-${Date.now()}@example.com`;
const password = "smoke-test-password";
const note = `Smoke lunch ${Date.now()}`;

async function signOut(page: Page) {
  await page.getByRole("button", { name: /sign out/i }).click();
  await expect(page).toHaveURL(/\/login/);
}

test("register, add an expense, see it everywhere, log out and back in", async ({ page }) => {
  await test.step("register lands on the dashboard", async () => {
    await page.goto("/register");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(password);
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
    // New accounts get the default categories as quick-add buttons
    await expect(page.getByRole("button", { name: /Rickshaw/ })).toBeVisible();
  });

  await test.step("add an expense from the dashboard", async () => {
    await page.getByRole("button", { name: "New Expense" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByLabel(/Amount/).fill("250.50");
    await dialog.getByRole("combobox").click();
    await page.getByRole("option", { name: /Random/ }).click();
    await dialog.getByLabel(/Note/).fill(note);
    await dialog.getByRole("button", { name: "Save Expense" }).click();
    await expect(dialog).toBeHidden();
    await expect(page.getByText("Expense added successfully").first()).toBeVisible();
  });

  await test.step("dashboard shows it in recent expenses and totals", async () => {
    await expect(page.getByText(note)).toBeVisible();
    await expect(page.getByText("৳250.5").first()).toBeVisible();
  });

  await test.step("expense list shows it", async () => {
    await page.getByRole("link", { name: "Expenses" }).click();
    await expect(page).toHaveURL(/\/expenses/);
    await expect(page.getByRole("heading", { name: "Expenses" })).toBeVisible();
    await expect(page.getByText(note)).toBeVisible();
  });

  await test.step("logout protects app pages", async () => {
    await signOut(page);
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login/);
  });

  await test.step("login again restores the data", async () => {
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(password);
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.getByText(note)).toBeVisible();
  });

  await test.step("session survives a reload (refresh cookie)", async () => {
    await page.reload();
    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.getByText(note)).toBeVisible();
  });
});

test("wrong password shows an error and stays on login", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill("nobody@example.com");
  await page.getByLabel("Password").fill("definitely-wrong");
  await page.getByRole("button", { name: "Sign in" }).click();
  // Next.js renders its own empty role="alert" route announcer, so match by text
  await expect(page.getByRole("alert").filter({ hasText: "Invalid email or password" })).toBeVisible();
  await expect(page).toHaveURL(/\/login/);
});
