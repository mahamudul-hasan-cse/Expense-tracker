import { Goal } from "@/types";
import { formatCurrency, todayISO } from "./utils";

/** "Saved ৳X", or "Overspent by ৳X" for a negative month. */
export function describeSaved(saved: number): {
  label: string;
  amount: number;
  overspent: boolean;
} {
  return saved < 0
    ? { label: "Overspent by", amount: -saved, overspent: true }
    : { label: "Saved", amount: saved, overspent: false };
}

/** "75.0%", or "—" when there was no income (the API sends null). */
export function formatSavingsRate(rate: number | null): string {
  return rate === null ? "—" : `${rate.toFixed(1)}%`;
}

/** Current month in the user's timezone, as "YYYY-MM". */
export function currentMonth(): string {
  return todayISO().slice(0, 7);
}

/** First and last day ("YYYY-MM-DD") of a "YYYY-MM" month. */
export function monthRange(month: string): { start: string; end: string } {
  const [year, mon] = month.split("-").map(Number);
  const lastDay = new Date(year, mon, 0).getDate(); // day 0 of next month = last day of this one
  return { start: `${month}-01`, end: `${month}-${String(lastDay).padStart(2, "0")}` };
}

export type GoalTone = "success" | "warning" | "danger" | "neutral";

/** Badge text and tone for a goal's computed state. */
export function goalStatus(goal: Pick<Goal, "state" | "remaining">): {
  text: string;
  tone: GoalTone;
} {
  switch (goal.state) {
    case "completed":
      return { text: "Completed", tone: "success" };
    case "on_track":
      return { text: "On track", tone: "success" };
    case "behind":
      return { text: "Behind", tone: "warning" };
    case "overdue":
      return { text: `Deadline passed, ${formatCurrency(goal.remaining)} to go`, tone: "danger" };
    case "no_deadline":
      return { text: "No deadline", tone: "neutral" };
  }
}

/** "৳X/month needed" while a deadline is ahead and the goal isn't done; otherwise null. */
export function goalMonthlyNeed(goal: Pick<Goal, "state" | "required_per_month">): string | null {
  if ((goal.state === "on_track" || goal.state === "behind") && goal.required_per_month) {
    return `${formatCurrency(goal.required_per_month)}/month needed`;
  }
  return null;
}
