import { describe, expect, it } from "vitest";
import { amountError, notFutureError, requiredError } from "./validation";

describe("amountError (mirrors the backend's MoneyIn)", () => {
  it.each(["250", "99.5", "99.50", "99999999.99", "0.01"])("accepts %s", (v) => {
    expect(amountError(v)).toBeNull();
  });

  it.each([
    ["", "Enter an amount"],
    ["abc", "Enter a number, like 250 or 99.50"],
    ["0", "The amount must be more than 0"],
    ["-5", "The amount must be more than 0"],
    ["1.234", "Use at most 2 decimal places"],
    ["100000000", "The amount is too large"],
  ])("rejects %j", (v, message) => {
    expect(amountError(v)).toBe(message);
  });

  it("allows negative amounts where the backend does (goal withdrawals), but not 0", () => {
    expect(amountError("-500", { allowNegative: true })).toBeNull();
    expect(amountError("0", { allowNegative: true })).toBe("The amount can't be 0");
  });
});

describe("other rules", () => {
  it("requires text", () => {
    expect(requiredError("  ", "Name")).toBe("Name is required");
    expect(requiredError("Rent", "Name")).toBeNull();
  });

  it("rejects future dates", () => {
    expect(notFutureError("2026-10-29", "2026-10-28")).toBe("The date can't be in the future");
    expect(notFutureError("2026-10-28", "2026-10-28")).toBeNull();
    expect(notFutureError("", "2026-10-28")).toBeNull();
  });
});
