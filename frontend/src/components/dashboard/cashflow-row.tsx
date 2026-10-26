"use client";

import Link from "next/link";
import { ArrowDownCircle, ArrowUpCircle, PiggyBank, Percent } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { describeSaved, formatSavingsRate } from "@/lib/cashflow";
import { useCashflow } from "@/lib/queries";
import { cn, formatCurrency } from "@/lib/utils";

/** This month's Income · Spent · Saved (or Overspent) · Savings rate. */
export function CashflowRow() {
  const { data, isLoading } = useCashflow();

  if (isLoading) {
    return <Skeleton className="h-28 w-full rounded-xl" />;
  }
  if (!data) return null;

  const saved = describeSaved(data.saved);

  return (
    <Card role="region" aria-label="This month">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-lg">This month</CardTitle>
        {data.income === 0 && (
          <Link href="/income">
            <Button size="sm" variant="outline">
              Add your income
            </Button>
          </Link>
        )}
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <Stat
            icon={<ArrowDownCircle className="h-4 w-4 text-emerald-600" aria-hidden="true" />}
            label="Income"
            value={formatCurrency(data.income)}
          />
          <Stat
            icon={<ArrowUpCircle className="h-4 w-4 text-rose-500" aria-hidden="true" />}
            label="Spent"
            value={formatCurrency(data.spent)}
          />
          <Stat
            icon={<PiggyBank className="h-4 w-4 text-primary" aria-hidden="true" />}
            label={saved.label}
            value={formatCurrency(saved.amount)}
            valueClassName={saved.overspent ? "text-destructive" : undefined}
            hint={
              data.allocated_to_goals > 0
                ? `${formatCurrency(data.allocated_to_goals)} set aside for goals`
                : undefined
            }
          />
          <Stat
            icon={<Percent className="h-4 w-4 text-amber-500" aria-hidden="true" />}
            label="Savings rate"
            value={formatSavingsRate(data.savings_rate)}
            valueClassName={
              data.savings_rate !== null && data.savings_rate < 0 ? "text-destructive" : undefined
            }
            hint={data.savings_rate === null ? "No income recorded yet" : undefined}
          />
        </dl>
      </CardContent>
    </Card>
  );
}

function Stat({
  icon,
  label,
  value,
  valueClassName,
  hint,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  valueClassName?: string;
  hint?: string;
}) {
  return (
    <div className="space-y-1">
      <dt className="flex items-center gap-1.5 text-sm text-muted-foreground">
        {icon}
        {label}
      </dt>
      <dd className={cn("text-2xl font-bold", valueClassName)}>{value}</dd>
      {hint && <dd className="text-xs text-muted-foreground">{hint}</dd>}
    </div>
  );
}
