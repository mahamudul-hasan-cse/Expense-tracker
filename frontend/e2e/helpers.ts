import { expect, Page } from "@playwright/test";

let counter = 0;

/** Register a brand-new user (unique email) and land on the dashboard. */
export async function registerNewUser(page: Page, prefix = "e2e") {
  const email = `${prefix}-${Date.now()}-${counter++}@example.com`;
  const password = "e2e-test-password";
  await page.goto("/register");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  return { email, password };
}

/** Add an expense through the dashboard's "New Expense" dialog. */
export async function addExpense(
  page: Page,
  {
    amount,
    category,
    note,
    date,
  }: { amount: string; category: string; note: string; date?: string }
) {
  await page.getByRole("button", { name: "New Expense" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel(/Amount/).fill(amount);
  await dialog.getByRole("combobox").click();
  await page.getByRole("option", { name: new RegExp(category) }).click();
  await dialog.getByLabel(/Note/).fill(note);
  if (date) await dialog.getByLabel("Date").fill(date);
  await dialog.getByRole("button", { name: "Save Expense" }).click();
  await expect(dialog).toBeHidden();
}
