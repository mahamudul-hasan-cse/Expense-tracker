"use client";

import Link from "next/link";
import { ArrowRight, Target } from "lucide-react";
import { GoalStatusBadge } from "@/components/goals/goal-status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { goalMonthlyNeed } from "@/lib/cashflow";
import { useGoals } from "@/lib/queries";
import { formatCurrency } from "@/lib/utils";

/** Up to 3 active goals with progress, for the dashboard. */
export function GoalsCard() {
  const { data, isLoading } = useGoals();
  const goals = (data?.goals ?? []).filter((g) => g.status === "active").slice(0, 3);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-lg">Savings Goals</CardTitle>
        <Link href="/goals">
          <Button variant="ghost" size="sm" className="gap-1 text-muted-foreground">
            Manage <ArrowRight className="h-4 w-4" />
          </Button>
        </Link>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-20 w-full" />
        ) : goals.length === 0 ? (
          <div className="flex flex-col items-center gap-3 py-4 text-center text-muted-foreground">
            <Target className="h-8 w-8" aria-hidden="true" />
            <p>No savings goals yet — set one to track what you&apos;re saving for.</p>
            <Link href="/goals">
              <Button size="sm">Create a goal</Button>
            </Link>
          </div>
        ) : (
          <ul className="space-y-4">
            {goals.map((goal) => {
              const need = goalMonthlyNeed(goal);
              return (
                <li key={goal.id} className="space-y-1.5">
                  <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
                    <span className="flex items-center gap-2 font-medium">
                      <span aria-hidden="true">{goal.icon}</span>
                      {goal.name}
                    </span>
                    <GoalStatusBadge goal={goal} />
                  </div>
                  <Progress
                    value={Math.min(goal.progress_pct, 100)}
                    aria-label={`${goal.name}: ${goal.progress_pct}% saved`}
                  />
                  <div className="flex flex-wrap justify-between gap-2 text-xs text-muted-foreground">
                    <span>
                      {formatCurrency(goal.saved)} of {formatCurrency(goal.target_amount)}
                    </span>
                    {need && <span>{need}</span>}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
