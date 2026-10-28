"use client";

import { useState } from "react";
import { Plus, Wallet } from "lucide-react";
import { ErrorState } from "@/components/shared/error-state";
import { PageHeader } from "@/components/shared/page-header";
import { TransactionRow } from "@/components/shared/transaction-row";
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
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";
import { currentMonth, monthRange } from "@/lib/cashflow";
import { useCashflow, useDeleteIncome, useIncomeCategories, useIncomes } from "@/lib/queries";
import { formatCurrency } from "@/lib/utils";
import { Income } from "@/types";
import { IncomeFormDialog } from "./income-form-dialog";

export function IncomeList() {
  const { toast } = useToast();
  const [month, setMonth] = useState(currentMonth());
  const { start, end } = monthRange(month);
  const { data, isLoading, isError, refetch } = useIncomes({
    start_date: start,
    end_date: end,
    limit: 100,
  });
  const { data: cashflow } = useCashflow(month);
  const { data: categoriesData } = useIncomeCategories();
  const deleteIncome = useDeleteIncome();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Income | null>(null);
  const [deleting, setDeleting] = useState<Income | null>(null);

  const incomes = data?.incomes ?? [];
  const categories = categoriesData?.income_categories ?? [];

  const openDialog = (income?: Income) => {
    setEditing(income ?? null);
    setDialogOpen(true);
  };

  const handleDelete = () => {
    if (!deleting) return;
    deleteIncome.mutate(deleting.id, {
      onSuccess: () => {
        toast({ title: "Success", description: "Income deleted" });
        setDeleting(null);
      },
      onError: (error) =>
        toast({ title: "Error", description: error.message, variant: "destructive" }),
    });
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Income"
        description="Money in: salary, freelance, gifts and more"
        actions={
          <Button onClick={() => openDialog()} className="gap-2">
            <Plus className="h-4 w-4" />
            Add Income
          </Button>
        }
      />

      <Card>
        <CardContent className="flex flex-wrap items-end justify-between gap-4 pt-6">
          <div className="space-y-2">
            <Label htmlFor="income-month">Month</Label>
            <Input
              id="income-month"
              type="month"
              value={month}
              max={currentMonth()}
              onChange={(e) => e.target.value && setMonth(e.target.value)}
              className="w-44"
            />
          </div>
          <div className="text-right">
            <p className="text-sm text-muted-foreground">Total this month</p>
            <p className="text-2xl font-bold text-emerald-700 dark:text-emerald-400">
              {formatCurrency(cashflow?.income ?? 0)}
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          {isError ? (
            <ErrorState
              className="m-4"
              message="Couldn't load your income."
              onRetry={() => refetch()}
            />
          ) : isLoading ? (
            <div className="space-y-2 p-4">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          ) : incomes.length > 0 ? (
            <ul className="divide-y">
              {incomes.map((income) => (
                <TransactionRow
                  key={income.id}
                  icon={income.category.icon}
                  amount={formatCurrency(Number(income.amount))}
                  amountClassName="text-emerald-700 dark:text-emerald-400"
                  category={income.category.name}
                  note={income.note}
                  date={income.income_date}
                  label={`income ${income.note ?? income.category.name}`}
                  onEdit={() => openDialog(income)}
                  onDelete={() => setDeleting(income)}
                />
              ))}
            </ul>
          ) : (
            <div className="flex flex-col items-center gap-3 py-12 text-center text-muted-foreground">
              <Wallet className="h-8 w-8" aria-hidden="true" />
              <p>No income recorded for this month.</p>
              <Button size="sm" onClick={() => openDialog()}>
                Add your first income
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      <IncomeFormDialog
        open={dialogOpen}
        onClose={() => {
          setDialogOpen(false);
          setEditing(null);
        }}
        categories={categories}
        income={editing}
      />

      <AlertDialog open={!!deleting} onOpenChange={(open) => !open && setDeleting(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete income?</AlertDialogTitle>
            <AlertDialogDescription>
              {deleting && `${formatCurrency(deleting.amount)} from ${deleting.category.name}`} will
              be removed. This can&apos;t be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
