import { expect, Page, test } from "@playwright/test";
import { addExpense, registerNewUser } from "./helpers";

async function thisMonth(page: Page) {
  await page.getByRole("link", { name: "Dashboard", exact: true }).click();
  const card = page.getByRole("region", { name: "This month" });
  await expect(card).toBeVisible();
  return card;
}

test("income drives Saved; goal contributions never reduce it; overspending is shown", async ({
  page,
}) => {
  await registerNewUser(page, "income");

  await test.step("no income yet: savings rate is — and the dashboard prompts for income", async () => {
    const card = await thisMonth(page);
    await expect(card.getByText("—")).toBeVisible();
    await expect(card.getByRole("button", { name: "Add your income" })).toBeVisible();
  });

  await test.step("add ৳10,000 salary on the Income page", async () => {
    await page.getByRole("link", { name: "Income", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Income" })).toBeVisible();
    await page.getByRole("button", { name: "Add Income" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByLabel(/Amount/).fill("10000");
    await dialog.getByLabel("Category *").click();
    await page.getByRole("option", { name: /Salary/ }).click();
    await dialog.getByLabel(/Note/).fill("October salary");
    await dialog.getByRole("button", { name: "Save Income" }).click();
    await expect(dialog).toBeHidden();
    await expect(page.getByText("October salary")).toBeVisible();
    await expect(page.getByText("৳10,000").first()).toBeVisible();
  });

  await test.step("spend ৳2,500: Saved ৳7,500 and 75.0%", async () => {
    await page.getByRole("link", { name: "Dashboard", exact: true }).click();
    await addExpense(page, { amount: "2500", category: "Random", note: "groceries" });
    const card = await thisMonth(page);
    await expect(card).toContainText("৳10,000");
    await expect(card).toContainText("Saved");
    await expect(card).toContainText("৳7,500");
    await expect(card).toContainText("75.0%");
  });

  await test.step("put ৳3,000 toward a goal: Saved stays ৳7,500", async () => {
    await page.getByRole("link", { name: "Goals", exact: true }).click();
    await page.getByRole("button", { name: "New Goal" }).first().click();
    let dialog = page.getByRole("dialog");
    await dialog.getByLabel("Name *").fill("Laptop");
    await dialog.getByLabel(/Target amount/).fill("50000");
    await dialog.getByRole("button", { name: "Create Goal" }).click();
    await expect(dialog).toBeHidden();

    await page.getByRole("button", { name: "Add money" }).click();
    dialog = page.getByRole("dialog");
    await dialog.getByLabel(/Amount/).fill("3000");
    await dialog.getByRole("button", { name: "Add", exact: true }).click();
    await expect(dialog).toBeHidden();
    await expect(page.getByText("৳3,000 of ৳50,000")).toBeVisible();

    const card = await thisMonth(page);
    await expect(card).toContainText("৳7,500");
    await expect(card).toContainText("৳3,000 set aside for goals");
    // Spending is unchanged by the contribution
    await expect(card).toContainText("৳2,500");
  });

  await test.step("spend ৳9,000 more: Overspent by ৳1,500", async () => {
    await addExpense(page, { amount: "9000", category: "Random", note: "phone repair" });
    const card = await thisMonth(page);
    await expect(card).toContainText("Overspent by");
    await expect(card).toContainText("৳1,500");
  });
});

test("recurring income can be marked received from the dashboard", async ({ page }) => {
  await registerNewUser(page, "recurring-income");
  const dayOfMonth = await page.evaluate(() => String(new Date().getDate()));

  await page.getByRole("link", { name: "Settings", exact: true }).click();
  await page.getByRole("button", { name: "Add Recurring" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Type *").click();
  await page.getByRole("option", { name: /Income/ }).click();
  await dialog.getByPlaceholder("e.g., Monthly Wifi").fill("Tuition fee");
  await dialog.getByPlaceholder("0.00").fill("5000");
  await dialog.getByLabel("Category *").click();
  await page.getByRole("option", { name: /Freelance/ }).click();
  await dialog.getByPlaceholder("1-31").fill(dayOfMonth);
  await dialog.getByRole("button", { name: "Add", exact: true }).click();
  await expect(dialog).toBeHidden();

  await page.getByRole("link", { name: "Dashboard", exact: true }).click();
  const markReceived = page.getByRole("button", { name: "Mark received: Tuition fee" });
  await expect(markReceived).toBeVisible();
  await markReceived.click();
  await expect(page.getByText("Tuition fee recorded as income").first()).toBeVisible();
  // Paid for this cycle: it leaves Upcoming, and the income shows up this month
  await expect(markReceived).toBeHidden();
  const card = await thisMonth(page);
  await expect(card).toContainText("৳5,000");
});
