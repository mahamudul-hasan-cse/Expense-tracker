import { describe, expect, it, vi } from "vitest";
import {
  currentMonth,
  describeSaved,
  formatSavingsRate,
  goalMonthlyNeed,
  goalStatus,
  monthRange,
} from "./cashflow";

describe("describeSaved", () => {
  it("shows a positive month as Saved", () => {
    expect(describeSaved(7500)).toEqual({ label: "Saved", amount: 7500, overspent: false });
  });

  it('shows a negative month as "Overspent by" with a positive amount', () => {
    expect(describeSaved(-500.5)).toEqual({
      label: "Overspent by",
      amount: 500.5,
      overspent: true,
    });
  });

  it("treats exactly zero as saved, not overspent", () => {
    expect(describeSaved(0).overspent).toBe(false);
  });
});

describe("formatSavingsRate", () => {
  it('shows "—" when there was no income (null), never a divide-by-zero', () => {
    expect(formatSavingsRate(null)).toBe("—");
  });

  it.each([
    [75, "75.0%"],
    [33.33, "33.3%"],
    [-50, "-50.0%"],
    [0, "0.0%"],
  ])("formats %s as %s", (rate, expected) => {
    expect(formatSavingsRate(rate)).toBe(expected);
  });
});

describe("months", () => {
  it("currentMonth follows Dhaka time before 6 AM", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-10-31T19:30:00Z")); // 01:30 Nov 1 in Dhaka
    expect(currentMonth()).toBe("2026-11");
  });

  it.each([
    ["2026-02", "2026-02-28"],
    ["2028-02", "2028-02-29"],
    ["2026-04", "2026-04-30"],
    ["2026-12", "2026-12-31"],
  ])("monthRange(%s) ends on %s", (month, end) => {
    expect(monthRange(month)).toEqual({ start: `${month}-01`, end });
  });
});

describe("goal status", () => {
  it.each([
    ["completed", "Completed", "success"],
    ["on_track", "On track", "success"],
    ["behind", "Behind", "warning"],
    ["no_deadline", "No deadline", "neutral"],
  ] as const)("%s", (state, text, tone) => {
    expect(goalStatus({ state, remaining: 0 })).toEqual({ text, tone });
  });

  it("overdue goals say how much is left", () => {
    expect(goalStatus({ state: "overdue", remaining: 600 })).toEqual({
      text: "Deadline passed, ৳600 to go",
      tone: "danger",
    });
  });

  it("only shows a monthly amount while a deadline is ahead", () => {
    expect(goalMonthlyNeed({ state: "behind", required_per_month: 1285.72 })).toBe(
      "৳1,285.72/month needed"
    );
    expect(goalMonthlyNeed({ state: "completed", required_per_month: 0 })).toBeNull();
    expect(goalMonthlyNeed({ state: "no_deadline", required_per_month: null })).toBeNull();
    expect(goalMonthlyNeed({ state: "overdue", required_per_month: 600 })).toBeNull();
  });
});
