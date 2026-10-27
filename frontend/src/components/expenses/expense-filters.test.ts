import { describe, expect, it } from "vitest";
import { buildExpenseQuery, EXPENSES_PAGE_SIZE } from "./expense-filters";

const empty = { page: 1, categoryFilter: "", startDate: "", endDate: "", search: "" };

describe("buildExpenseQuery", () => {
  it("drops every empty filter", () => {
    expect(buildExpenseQuery(empty)).toEqual({
      page: 1,
      limit: EXPENSES_PAGE_SIZE,
      category_id: undefined,
      start_date: undefined,
      end_date: undefined,
      search: undefined,
    });
  });

  it('treats the "All Categories" option as no filter (regression: used to send category_id=all)', () => {
    expect(buildExpenseQuery({ ...empty, categoryFilter: "all" }).category_id).toBeUndefined();
  });

  it("passes real filters through", () => {
    const q = buildExpenseQuery({
      page: 3,
      categoryFilter: "cat-uuid",
      startDate: "2026-01-01",
      endDate: "2026-01-31",
      search: "lunch",
    });
    expect(q).toMatchObject({
      page: 3,
      category_id: "cat-uuid",
      start_date: "2026-01-01",
      end_date: "2026-01-31",
      search: "lunch",
    });
  });

  it("trims search and ignores whitespace-only input", () => {
    expect(buildExpenseQuery({ ...empty, search: "  tea  " }).search).toBe("tea");
    expect(buildExpenseQuery({ ...empty, search: "   " }).search).toBeUndefined();
  });
});
