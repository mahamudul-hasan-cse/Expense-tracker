"use client";

import { useState } from "react";
import { Archive, ArchiveRestore, Edit2, Minus, Plus, Target, Trash2 } from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/shared/error-state";
import { PageHeader } from "@/components/shared/page-header";
import { useToast } from "@/hooks/use-toast";
import { goalMonthlyNeed } from "@/lib/cashflow";
import { useDeleteGoal, useGoals, useUpdateGoal } from "@/lib/queries";
import { formatCurrency, formatDateFull } from "@/lib/utils";
import { Goal } from "@/types";
import { ContributionDialog, ContributionMode } from "./contribution-dialog";
import { GoalFormDialog } from "./goal-form-dialog";
import { GoalStatusBadge } from "./goal-status-badge";

export function GoalsPage() {
  const { toast } = useToast();
  const { data, isLoading, isError, refetch } = useGoals();
  const updateGoal = useUpdateGoal();
  const deleteGoal = useDeleteGoal();

  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Goal | null>(null);
  const [contributing, setContributing] = useState<{ goal: Goal; mode: ContributionMode } | null>(
    null
  );
  const [deleting, setDeleting] = useState<Goal | null>(null);

  const goals = data?.goals ?? [];
  const active = goals.filter((g) => g.status === "active");
  const archived = goals.filter((g) => g.status === "archived");

  const onError = (error: Error) =>
    toast({ title: "Error", description: error.message, variant: "destructive" });

  const setArchived = (goal: Goal, archive: boolean) =>
    updateGoal.mutate(
      { id: goal.id, data: { status: archive ? "archived" : "active" } },
      {
        onSuccess: () =>
          toast({
            title: "Success",
            description: `${goal.name} ${archive ? "archived" : "restored"}`,
          }),
        onError,
      }
    );

  const handleDelete = () => {
    if (!deleting) return;
    deleteGoal.mutate(deleting.id, {
      onSuccess: () => {
        toast({ title: "Success", description: `${deleting.name} deleted` });
        setDeleting(null);
      },
      onError,
    });
  };

  const openForm = (goal?: Goal) => {
    setEditing(goal ?? null);
    setFormOpen(true);
  };

  const renderGoal = (goal: Goal) => {
    const need = goalMonthlyNeed(goal);
    const isArchived = goal.status === "archived";
    return (
      <Card key={goal.id} className={isArchived ? "opacity-70" : undefined}>
        <CardHeader className="space-y-2 pb-3">
          <div className="flex items-start justify-between gap-2">
            <CardTitle className="flex items-center gap-2 text-lg">
              <span aria-hidden="true">{goal.icon ?? "🎯"}</span>
              {goal.name}
            </CardTitle>
            <GoalStatusBadge goal={goal} />
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <Progress
            value={Math.min(goal.progress_pct, 100)}
            aria-label={`${goal.name}: ${goal.progress_pct}% saved`}
          />
          <div className="flex flex-wrap justify-between gap-2 text-sm">
            <span className="font-medium">
              {formatCurrency(goal.saved)} of {formatCurrency(goal.target_amount)}
            </span>
            <span className="text-muted-foreground">{goal.progress_pct.toFixed(0)}%</span>
          </div>
          <div className="space-y-0.5 text-sm text-muted-foreground">
            {goal.target_date && <p>Deadline: {formatDateFull(goal.target_date)}</p>}
            {need && <p>{need}</p>}
            {goal.state === "completed" && !isArchived && (
              <p className="text-emerald-700 dark:text-emerald-400">
                Target reached. Archive it to keep your list tidy.
              </p>
            )}
          </div>
          {/* Main actions on the left; archive/edit/delete as one group of icon buttons */}
          <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
            <div className="flex flex-wrap gap-2">
              {isArchived ? (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setArchived(goal, false)}
                  className="gap-1"
                >
                  <ArchiveRestore className="h-4 w-4" />
                  Restore
                </Button>
              ) : goal.state === "completed" ? (
                <Button size="sm" onClick={() => setArchived(goal, true)} className="gap-1">
                  <Archive className="h-4 w-4" />
                  Archive
                </Button>
              ) : (
                <>
                  <Button
                    size="sm"
                    onClick={() => setContributing({ goal, mode: "add" })}
                    className="gap-1"
                  >
                    <Plus className="h-4 w-4" />
                    Add money
                  </Button>
                  {goal.saved > 0 && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setContributing({ goal, mode: "withdraw" })}
                      className="gap-1"
                    >
                      <Minus className="h-4 w-4" />
                      Take back
                    </Button>
                  )}
                </>
              )}
            </div>
            <div className="flex items-center">
              {!isArchived && goal.state !== "completed" && (
                <Button
                  size="icon"
                  variant="ghost"
                  aria-label={`Archive ${goal.name}`}
                  title="Archive"
                  onClick={() => setArchived(goal, true)}
                >
                  <Archive className="h-4 w-4" />
                </Button>
              )}
              <Button
                size="icon"
                variant="ghost"
                aria-label={`Edit ${goal.name}`}
                title="Edit"
                onClick={() => openForm(goal)}
              >
                <Edit2 className="h-4 w-4" />
              </Button>
              <Button
                size="icon"
                variant="ghost"
                aria-label={`Delete ${goal.name}`}
                title="Delete"
                onClick={() => setDeleting(goal)}
              >
                <Trash2 className="h-4 w-4 text-destructive" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Savings Goals"
        description="Earmark your savings for the things you're working toward"
        actions={
          <Button onClick={() => openForm()} className="gap-2">
            <Plus className="h-4 w-4" />
            New Goal
          </Button>
        }
      />

      {isError ? (
        <ErrorState message="Couldn't load your goals." onRetry={() => refetch()} />
      ) : isLoading ? (
        <div className="grid gap-4 md:grid-cols-2">
          <Skeleton className="h-48" />
          <Skeleton className="h-48" />
        </div>
      ) : active.length === 0 && archived.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12 text-center text-muted-foreground">
            <Target className="h-10 w-10" aria-hidden="true" />
            <p>No goals yet — create one for a laptop, a trip, an emergency fund…</p>
            <Button onClick={() => openForm()}>Create your first goal</Button>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2">{active.map(renderGoal)}</div>
          {archived.length > 0 && (
            <section className="space-y-3">
              <h2 className="text-lg font-semibold text-muted-foreground">Archived</h2>
              <div className="grid gap-4 md:grid-cols-2">{archived.map(renderGoal)}</div>
            </section>
          )}
        </>
      )}

      <GoalFormDialog
        open={formOpen}
        onClose={() => {
          setFormOpen(false);
          setEditing(null);
        }}
        goal={editing}
      />

      <ContributionDialog
        goal={contributing?.goal ?? null}
        mode={contributing?.mode ?? "add"}
        onClose={() => setContributing(null)}
      />

      <AlertDialog open={!!deleting} onOpenChange={(open) => !open && setDeleting(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete &ldquo;{deleting?.name}&rdquo;?</AlertDialogTitle>
            <AlertDialogDescription>
              {deleting && deleting.saved > 0
                ? `Its ${formatCurrency(deleting.saved)} of contributions are removed from the goal. `
                : ""}
              This doesn&apos;t change your income, expenses or Saved total; the money simply stops
              being earmarked. This can&apos;t be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground"
            >
              Delete goal
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
