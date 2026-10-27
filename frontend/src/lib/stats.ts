import { differenceInCalendarDays, parseISO } from "date-fns";
import { UpcomingReminder } from "@/types";
import { todayISO } from "./utils";

/**
 * Days of a period that have happened so far (inclusive), in the user's timezone.
 * Current period: start..today. Past period: the whole period. Future: 0.
 */
export function daysElapsed(
  startDate: string,
  endDate: string,
  today: string = todayISO()
): number {
  const start = parseISO(startDate);
  const end = parseISO(endDate);
  const now = parseISO(today);
  if (now < start) return 0;
  const last = now > end ? end : now;
  return differenceInCalendarDays(last, start) + 1;
}

/** Average spent per elapsed day (not per calendar day of the whole period). */
export function dailyAverage(
  total: number,
  startDate: string,
  endDate: string,
  today: string = todayISO()
): number {
  const days = daysElapsed(startDate, endDate, today);
  return days > 0 ? total / days : 0;
}

/** Upcoming recurring items split into bills to pay and income to expect. */
export function splitUpcoming(upcoming: UpcomingReminder[]): {
  bills: UpcomingReminder[];
  income: UpcomingReminder[];
} {
  return {
    bills: upcoming.filter((u) => u.kind !== "income"),
    income: upcoming.filter((u) => u.kind === "income"),
  };
}
