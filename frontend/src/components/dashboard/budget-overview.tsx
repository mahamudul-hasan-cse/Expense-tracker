"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { formatCurrency } from "@/lib/utils";
import { useBudgetSummary } from "@/lib/queries";
import { Skeleton } from "@/components/ui/skeleton";
import { AlertTriangle, CheckCircle2 } from "lucide-react";

export function BudgetOverview() {
  const today = new Date();
  const { data, isLoading } = useBudgetSummary(today.getMonth() + 1, today.getFullYear());

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
          <p className="text-center text-muted-foreground py-4">
            No budgets set for this month. Go to Settings to create budgets.
          </p>
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
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium">Total</span>
            <span className={data.percentage > 100 ? "text-destructive font-semibold" : ""}>
              {formatCurrency(data.total_spent)} / {formatCurrency(data.total_budget)}
            </span>
          </div>
          <Progress
            value={Math.min(data.percentage, 100)}
            className={
              data.percentage > 90
                ? "[&>div]:bg-destructive"
                : data.percentage > 75
                  ? "[&>div]:bg-yellow-500"
                  : ""
            }
          />
          <p className="text-xs text-muted-foreground text-right">
            {data.percentage.toFixed(1)}% used
          </p>
        </div>

        {/* Per Category */}
        <div className="space-y-3 pt-2">
          {data.budgets.map((budget) => (
            <div key={budget.id} className="space-y-1">
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <span>{budget.category.icon}</span>
                  <span>{budget.category.name}</span>
                  {budget.percentage > 100 && (
                    <AlertTriangle className="h-3 w-3 text-destructive" />
                  )}
                  {budget.percentage <= 75 && budget.spent > 0 && (
                    <CheckCircle2 className="h-3 w-3 text-green-500" />
                  )}
                </div>
                <span
                  className={budget.percentage > 100 ? "text-destructive" : "text-muted-foreground"}
                >
                  {formatCurrency(budget.spent)} / {formatCurrency(budget.amount)}
                </span>
              </div>
              <Progress
                value={Math.min(budget.percentage, 100)}
                className={`h-2 ${budget.percentage > 90 ? "[&>div]:bg-destructive" : budget.percentage > 75 ? "[&>div]:bg-yellow-500" : ""}`}
              />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
