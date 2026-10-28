// Client-side checks that mirror the backend rules (backend/app/schemas), so users see
// the problem next to the field instead of a toast after a round trip.

export const MAX_AMOUNT = 99_999_999.99;

/** MoneyIn: more than 0, at most 99,999,999.99, at most 2 decimal places. */
export function amountError(value: string, { allowNegative = false } = {}): string | null {
  const text = value.trim();
  if (!text) return "Enter an amount";
  if (!/^-?\d+(\.\d+)?$/.test(text)) return "Enter a number, like 250 or 99.50";
  const amount = Number(text);
  if (!allowNegative && amount <= 0) return "The amount must be more than 0";
  if (allowNegative && amount === 0) return "The amount can't be 0";
  if (Math.abs(amount) > MAX_AMOUNT) return "The amount is too large";
  if ((text.split(".")[1] ?? "").length > 2) return "Use at most 2 decimal places";
  return null;
}

export function requiredError(value: string, label: string): string | null {
  return value.trim() ? null : `${label} is required`;
}

/** Dates can't be in the future (expenses, income, contributions). */
export function notFutureError(value: string, today: string): string | null {
  return value && value > today ? "The date can't be in the future" : null;
}
