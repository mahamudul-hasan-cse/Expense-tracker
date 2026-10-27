"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { budgetLevel, formatCurrency, formatPercent } from "@/lib/utils";
import { useBudgetSummary } from "@/lib/queries";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/shared/error-state";
import { AlertTriangle, CheckCircle2 } from "lucide-react";
import Link from "next/link";
import { LEVEL_BAR, LEVEL_TEXT } from "@/components/shared/budget-levels";

export function BudgetOverview() {
  const today = new Date();
  const { data, isLoading, isError, refetch } = useBudgetSummary(
    today.getMonth() + 1,
    today.getFullYear()
  );

  if (isError) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Budget Overview</CardTitle>
        </CardHeader>
        <CardContent>
          <ErrorState message="Couldn't load your budgets." onRetry={() => refetch()} />
        </CardContent>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-32" />
        </CardHeader>
        <CardContent className="space-y-4">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-20 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (!data || data.budgets.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Budget Overview</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center gap-3 py-4 text-center">
            <p className="text-muted-foreground">No budgets set for this month.</p>
            <Link
              href="/settings#budgets"
              className="text-sm font-medium text-primary underline-offset-4 hover:underline"
            >
              Set a monthly budget
            </Link>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg flex items-center justify-between">
          <span>Budget Overview</span>
          <span className="text-sm font-normal text-muted-foreground">
            {new Date().toLocaleDateString("en-US", { month: "long", year: "numeric" })}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Overall Progress */}
        <div className="space-y-2">
          <div className="flex items-center justify-between gap-2 text-sm">
            <span className="font-medium">Total</span>
            <span
              className={`whitespace-nowrap ${LEVEL_TEXT[budgetLevel(data.percentage)]} ${budgetLevel(data.percentage) === "over" ? "font-semibold" : ""}`}
            >
              {formatCurrency(data.total_spent)} / {formatCurrency(data.total_budget)}
            </span>
          </div>
          <Progress
            value={Math.min(data.percentage, 100)}
            className={LEVEL_BAR[budgetLevel(data.percentage)]}
            aria-label={`Total budget, ${formatPercent(data.percentage)} used`}
          />
          <p className="text-xs text-muted-foreground text-right">
            {formatPercent(data.percentage)} used
          </p>
        </div>

        {/* Per Category */}
        <div className="space-y-3 pt-2">
          {data.budgets.map((budget) => {
            const level = budgetLevel(budget.percentage);
            return (
              <div key={budget.id} className="space-y-1">
                <div className="flex items-center justify-between gap-2 text-sm">
                  <div className="flex min-w-0 items-center gap-2">
                    <span aria-hidden>{budget.category.icon}</span>
                    <span className="truncate">{budget.category.name}</span>
                    {level !== "ok" && (
                      <AlertTriangle
                        className={`h-3 w-3 shrink-0 ${level === "over" ? "text-destructive" : "text-amber-500"}`}
                        aria-label={level === "over" ? "Over budget" : "Close to the limit"}
                      />
                    )}
                    {level === "ok" && budget.spent > 0 && (
                      <CheckCircle2
                        className="h-3 w-3 shrink-0 text-green-500"
                        aria-label="On track"
                      />
                    )}
                  </div>
                  <span className={`shrink-0 whitespace-nowrap ${LEVEL_TEXT[level]}`}>
                    {formatCurrency(budget.spent)} / {formatCurrency(budget.amount)}
                  </span>
                </div>
                <Progress
                  value={Math.min(budget.percentage, 100)}
                  className={`h-2 ${LEVEL_BAR[level]}`}
                  aria-label={`${budget.category.name}, ${formatPercent(budget.percentage)} used`}
                />
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
