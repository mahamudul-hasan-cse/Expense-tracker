import { describe, expect, it } from "vitest";
import { errorMessage } from "./api";

describe("errorMessage", () => {
  it("reads the backend's uniform error format", () => {
    expect(errorMessage({ error: { message: "Expense not found" } })).toBe("Expense not found");
  });

  it("falls back to FastAPI's legacy string detail", () => {
    expect(errorMessage({ detail: "Category not found" })).toBe("Category not found");
  });

  it("joins legacy validation error lists and strips the 'Value error' prefix", () => {
    expect(
      errorMessage({
        detail: [{ msg: "Value error, Expense date cannot be in the future" }, { msg: "Field required" }],
      })
    ).toBe("Expense date cannot be in the future; Field required");
  });

  it("has a generic fallback", () => {
    expect(errorMessage({})).toBe("API request failed");
  });
});
