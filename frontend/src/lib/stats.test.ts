import { describe, expect, it, vi } from "vitest";
import { UpcomingReminder } from "@/types";
import { dailyAverage, daysElapsed, splitUpcoming } from "./stats";

describe("daysElapsed", () => {
  it("counts start..today inclusive for the current period", () => {
    expect(daysElapsed("2026-10-01", "2026-10-31", "2026-10-26")).toBe(26);
    expect(daysElapsed("2026-10-01", "2026-10-31", "2026-10-01")).toBe(1);
  });

  it("uses the whole period once it is over", () => {
    expect(daysElapsed("2026-09-01", "2026-09-30", "2026-10-26")).toBe(30);
    expect(daysElapsed("2026-02-01", "2026-02-28", "2026-03-01")).toBe(28);
  });

  it("is 0 for a period that hasn't started", () => {
    expect(daysElapsed("2026-11-01", "2026-11-30", "2026-10-26")).toBe(0);
  });

  it("works for weeks (Monday..Sunday)", () => {
    expect(daysElapsed("2026-10-26", "2026-11-01", "2026-10-28")).toBe(3);
  });

  it("defaults to today in Asia/Dhaka (before 6 AM is already the next day)", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-10-25T23:30:00Z")); // 05:30 Oct 26 in Dhaka
    expect(daysElapsed("2026-10-01", "2026-10-31")).toBe(26);
  });
});

describe("dailyAverage", () => {
  it("divides by days elapsed, not days in the month (regression)", () => {
    // Was ৳45,700 / 31 = ৳1,474.19 on Oct 26; correct is / 26
    expect(dailyAverage(45700, "2026-10-01", "2026-10-31", "2026-10-26")).toBeCloseTo(1757.69, 2);
  });

  it("uses the full month for past months", () => {
    expect(dailyAverage(41715, "2026-09-01", "2026-09-30", "2026-10-26")).toBeCloseTo(1390.5, 2);
  });

  it("is 0 rather than dividing by zero", () => {
    expect(dailyAverage(500, "2026-11-01", "2026-11-30", "2026-10-26")).toBe(0);
  });
});

describe("splitUpcoming", () => {
  const item = (id: string, kind: "expense" | "income"): UpcomingReminder => ({
    id,
    kind,
    name: id,
    amount: 100,
    due_date: "2026-10-28",
    days_until: 2,
    category: { name: "x", icon: null },
  });

  it("separates bills from expected income (regression: income was counted as bills)", () => {
    const { bills, income } = splitUpcoming([
      item("rent", "expense"),
      item("salary", "income"),
      item("wifi", "expense"),
    ]);
    expect(bills.map((b) => b.id)).toEqual(["rent", "wifi"]);
    expect(income.map((i) => i.id)).toEqual(["salary"]);
  });
});
