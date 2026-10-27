import { describe, expect, it, vi } from "vitest";
import { formatCurrency, formatDate, formatDateForInput, formatDateFull, todayISO } from "./utils";

describe("todayISO (Asia/Dhaka)", () => {
  it("returns the Dhaka date before 6 AM, when UTC is still on the previous day", () => {
    vi.useFakeTimers();
    // 05:30 on Oct 26 in Dhaka == 23:30 on Oct 25 UTC
    vi.setSystemTime(new Date("2026-10-25T23:30:00Z"));
    expect(todayISO()).toBe("2026-10-26");
  });

  it("returns the Dhaka date just before midnight", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-10-25T17:59:00Z")); // 23:59 Oct 25 in Dhaka
    expect(todayISO()).toBe("2026-10-25");
  });

  it("handles the new year boundary", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-12-31T18:30:00Z")); // 00:30 Jan 1 in Dhaka
    expect(todayISO()).toBe("2027-01-01");
  });
});

describe("date formatting", () => {
  it("does not shift date-only strings by a day", () => {
    expect(formatDate("2026-01-17")).toBe("Jan 17");
    expect(formatDate("2026-03-01")).toBe("Mar 1");
    expect(formatDateFull("2026-12-31")).toBe("Dec 31, 2026");
  });

  it("formats a local date for <input type=date>", () => {
    expect(formatDateForInput(new Date(2026, 0, 5))).toBe("2026-01-05");
  });
});

describe("formatCurrency", () => {
  it.each([
    [0, "৳0"],
    [250.5, "৳250.5"],
    [1234.5, "৳1,234.5"],
    [1234567, "৳1,234,567"],
    [99.999, "৳100"],
  ])("formats %s as %s", (amount, expected) => {
    expect(formatCurrency(amount)).toBe(expected);
  });
});
