import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { format, parseISO } from "date-fns";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(amount: number): string {
  return `৳${amount.toLocaleString("en-BD", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  })}`;
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
