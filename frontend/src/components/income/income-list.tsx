"use client";

import { useState } from "react";
import { Edit2, Plus, Trash2, Wallet } from "lucide-react";
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
import { formatCurrency, formatDateFull } from "@/lib/utils";
import { Income } from "@/types";
import { IncomeFormDialog } from "./income-form-dialog";

export function IncomeList() {
  const { toast } = useToast();
  const [month, setMonth] = useState(currentMonth());
  const { start, end } = monthRange(month);
  const { data, isLoading } = useIncomes({ start_date: start, end_date: end, limit: 100 });
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
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Income</h1>
          <p className="text-muted-foreground">Money in: salary, freelance, gifts and more</p>
        </div>
        <Button onClick={() => openDialog()} className="gap-2">
          <Plus className="h-4 w-4" />
          Add Income
        </Button>
      </div>

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
            <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
              {formatCurrency(cashflow?.income ?? 0)}
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="space-y-2 p-4">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          ) : incomes.length > 0 ? (
            <ul className="divide-y">
              {incomes.map((income) => (
                <li key={income.id} className="flex items-center justify-between gap-4 p-4">
                  <div className="flex items-center gap-4">
                    <span className="text-2xl" aria-hidden="true">
                      {income.category.icon}
                    </span>
                    <div>
                      <p className="font-medium">{formatCurrency(Number(income.amount))}</p>
                      <p className="text-sm text-muted-foreground">
                        {income.category.name}
                        {income.note && ` · ${income.note}`}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">
                      {formatDateFull(income.income_date)}
                    </span>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={`Edit income ${income.note ?? income.category.name}`}
                      onClick={() => openDialog(income)}
                    >
                      <Edit2 className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={`Delete income ${income.note ?? income.category.name}`}
                      onClick={() => setDeleting(income)}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </li>
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
