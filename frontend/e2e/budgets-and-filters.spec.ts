import { expect, test } from "@playwright/test";
import { addExpense, registerNewUser } from "./helpers";

test("create a budget and watch it fill up as expenses are added", async ({ page }) => {
  await registerNewUser(page, "budget");

  await test.step("create a ৳500 Rickshaw budget for this month", async () => {
    await page.getByRole("link", { name: "Settings" }).click();
    await page.getByRole("button", { name: "Add Budget" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByLabel("Category").click();
    await page.getByRole("option", { name: /Rickshaw/ }).click();
    await dialog.getByLabel("Monthly Budget Amount").fill("500");
    await dialog.getByRole("button", { name: "Create" }).click();
    await expect(dialog).toBeHidden();
    await expect(page.getByText("Budget created successfully").first()).toBeVisible();
  });

  await test.step("dashboard shows it, empty", async () => {
    await page.getByRole("link", { name: "Dashboard" }).click();
    await expect(page.getByText("Budget Overview")).toBeVisible();
    // Shown twice: the overall total and the Rickshaw row
    await expect(page.getByText("৳0 / ৳500").first()).toBeVisible();
  });

  await test.step("a Rickshaw expense updates the budget immediately", async () => {
    await page.getByRole("button", { name: /Rickshaw/ }).first().click(); // quick add
    const dialog = page.getByRole("dialog");
    await dialog.getByLabel(/Amount/).fill("120");
    await dialog.getByRole("button", { name: "Save Expense" }).click();
    await expect(dialog).toBeHidden();
    await expect(page.getByText("৳120 / ৳500").first()).toBeVisible();
    await expect(page.getByText("24.0% used")).toBeVisible();
  });
});

test("filter the expense list by search, category and date", async ({ page }) => {
  await registerNewUser(page, "filters");
  const lastWeek = await page.evaluate(() => {
    const d = new Date(Date.now() - 7 * 24 * 3600 * 1000);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  });
  await addExpense(page, { amount: "30", category: "Rickshaw", note: "campus ride" });
  await addExpense(page, { amount: "40", category: "Random", note: "morning tea" });
  await addExpense(page, { amount: "800", category: "Wifi Bill", note: "old wifi bill", date: lastWeek });

  await page.getByRole("link", { name: "Expenses" }).click();
  const rows = page.getByText(/campus ride|morning tea|old wifi bill/);
  await expect(rows).toHaveCount(3);

  await test.step("search notes", async () => {
    await page.getByPlaceholder("Search notes...").fill("TEA");
    await expect(rows).toHaveCount(1);
    await expect(page.getByText("morning tea")).toBeVisible();
    await page.getByRole("button", { name: "Clear Filters" }).click();
    await expect(rows).toHaveCount(3);
  });

  await test.step("category, then back to All Categories (regression)", async () => {
    await page.getByRole("combobox").click();
    await page.getByRole("option", { name: /Rickshaw/ }).click();
    await expect(rows).toHaveCount(1);
    await expect(page.getByText("campus ride")).toBeVisible();
    await page.getByRole("combobox").click();
    await page.getByRole("option", { name: "All Categories" }).click();
    await expect(rows).toHaveCount(3);
  });

  await test.step("date range hides older expenses", async () => {
    const today = await page.evaluate(() => {
      const d = new Date();
      return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    });
    await page.locator('input[type="date"]').first().fill(today);
    await expect(rows).toHaveCount(2);
    await expect(page.getByText("old wifi bill")).toBeHidden();
  });
});
