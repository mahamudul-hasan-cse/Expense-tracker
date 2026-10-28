import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { format, parseISO } from "date-fns";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// The one place money is formatted: Taka sign, English digits, thousands separators
const MONEY = new Intl.NumberFormat("en-BD", {
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
});
const COMPACT = new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 });

export function formatCurrency(amount: number): string {
  return `৳${MONEY.format(amount)}`;
}

/** Short Taka amounts for chart axes: ৳950, ৳16K, ৳1.2M. */
export function formatCurrencyCompact(amount: number): string {
  return `৳${COMPACT.format(amount)}`;
}

export function formatPercent(value: number, digits = 1): string {
  return `${value.toFixed(digits)}%`;
}

/** Budget usage state: amber once 80% is used, red only when over budget. */
export function budgetLevel(percentage: number): "ok" | "close" | "over" {
  if (percentage > 100) return "over";
  if (percentage >= 80) return "close";
  return "ok";
}

// Date-only strings ("YYYY-MM-DD") are parsed as local dates, not UTC
export function formatDate(dateStr: string): string {
  return format(parseISO(dateStr), "MMM d");
}

export function formatDateFull(dateStr: string): string {
  return format(parseISO(dateStr), "MMM d, yyyy");
}

export function formatDateForInput(date: Date): string {
  return format(date, "yyyy-MM-dd");
}

// Today's date in the user's local timezone, as "YYYY-MM-DD"
export function todayISO(): string {
  return formatDateForInput(new Date());
}
