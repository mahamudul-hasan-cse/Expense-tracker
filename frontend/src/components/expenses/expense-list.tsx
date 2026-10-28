"use client";

import { useState, useDeferredValue } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
import { formatCurrency } from "@/lib/utils";
import { Expense } from "@/types";
import { ExpenseListSkeleton } from "@/components/shared/skeletons";
import { ErrorState } from "@/components/shared/error-state";
import { PageHeader } from "@/components/shared/page-header";
import { TransactionRow } from "@/components/shared/transaction-row";
import { useToast } from "@/hooks/use-toast";
import { Plus, ChevronLeft, ChevronRight, X, Search, Receipt } from "lucide-react";
import { ExpenseFormDialog } from "./expense-form-dialog";
import { useExpenses, useCategories, useDeleteExpense } from "@/lib/queries";
import { buildExpenseQuery } from "./expense-filters";

export function ExpenseList() {
  const { toast } = useToast();

  // Filters
  const [categoryFilter, setCategoryFilter] = useState<string>("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const deferredSearch = useDeferredValue(searchQuery);
  const [page, setPage] = useState(1);

  // Dialog states
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingExpense, setEditingExpense] = useState<Expense | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deletingExpense, setDeletingExpense] = useState<Expense | null>(null);

  // React Query hooks
  const {
    data: expensesData,
    isLoading: expensesLoading,
    isError: expensesError,
    refetch: refetchExpenses,
  } = useExpenses(
    buildExpenseQuery({ page, categoryFilter, startDate, endDate, search: deferredSearch })
  );
  const { data: categoriesData, isLoading: categoriesLoading } = useCategories();
  const deleteExpenseMutation = useDeleteExpense();

  const expenses = expensesData?.expenses ?? [];
  const pagination = expensesData?.pagination ?? null;
  const categories = categoriesData?.categories ?? [];
  const loading = expensesLoading || categoriesLoading;

  const handleEdit = (expense: Expense) => {
    setEditingExpense(expense);
    setDialogOpen(true);
  };

  const handleDelete = async () => {
    if (!deletingExpense) return;

    deleteExpenseMutation.mutate(deletingExpense.id, {
      onSuccess: () => {
        toast({
          title: "Success",
          description: "Expense deleted successfully",
        });
        setDeleteDialogOpen(false);
        setDeletingExpense(null);
      },
      onError: () => {
        toast({
          title: "Error",
          description: "Failed to delete expense",
          variant: "destructive",
        });
      },
    });
  };

  const handleDialogClose = () => {
    setDialogOpen(false);
    setEditingExpense(null);
    // No need to manually refetch - React Query handles invalidation
  };

  const clearFilters = () => {
    setCategoryFilter("");
    setStartDate("");
    setEndDate("");
    setSearchQuery("");
    setPage(1);
  };

  const hasFilters = categoryFilter || startDate || endDate || searchQuery;

  if (loading && expenses.length === 0 && !expensesError) {
    return <ExpenseListSkeleton />;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Expenses"
        description="Everything you've spent, with search and filters"
        actions={
          <Button
            onClick={() => {
              setEditingExpense(null);
              setDialogOpen(true);
            }}
            className="gap-2"
          >
            <Plus className="h-4 w-4" />
            Add Expense
          </Button>
        }
      />

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Filters</CardTitle>
        </CardHeader>
        <CardContent>
          {/* Stacked full-width on phones, side by side from sm up */}
          <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:gap-4">
            {/* Search */}
            <div className="relative w-full sm:w-64">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                type="text"
                placeholder="Search notes..."
                aria-label="Search notes"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setPage(1);
                }}
                className="pl-9"
              />
            </div>
            <div className="w-full sm:w-48">
              <Select
                value={categoryFilter || "all"}
                onValueChange={(v) => {
                  setCategoryFilter(v === "all" ? "" : v);
                  setPage(1);
                }}
              >
                <SelectTrigger aria-label="Category filter">
                  <SelectValue placeholder="All Categories" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Categories</SelectItem>
                  {categories.map((category) => (
                    <SelectItem key={category.id} value={category.id}>
                      <span className="flex items-center gap-2">
                        <span>{category.icon}</span>
                        {category.name}
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid w-full grid-cols-[1fr_auto_1fr] items-center gap-2 sm:flex sm:w-auto">
              <Input
                type="date"
                aria-label="From date"
                placeholder="From"
                value={startDate}
                max={endDate || undefined}
                onChange={(e) => {
                  setStartDate(e.target.value);
                  setPage(1);
                }}
                className="w-full min-w-0 sm:w-40"
              />
              <span className="text-muted-foreground">to</span>
              <Input
                type="date"
                aria-label="To date"
                placeholder="To"
                value={endDate}
                min={startDate || undefined}
                onChange={(e) => {
                  setEndDate(e.target.value);
                  setPage(1);
                }}
                className="w-full min-w-0 sm:w-40"
              />
            </div>
            {hasFilters && (
              <Button variant="ghost" onClick={clearFilters} className="gap-1">
                <X className="h-4 w-4" />
                Clear Filters
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Expense Table */}
      <Card>
        <CardContent className="p-0">
          {expensesError ? (
            <ErrorState
              className="m-4"
              message="Couldn't load your expenses."
              onRetry={() => refetchExpenses()}
            />
          ) : expenses.length > 0 ? (
            <ul className="divide-y">
              {expenses.map((expense) => (
                <TransactionRow
                  key={expense.id}
                  icon={expense.category.icon}
                  amount={formatCurrency(Number(expense.amount))}
                  category={expense.category.name}
                  note={expense.note}
                  date={expense.expense_date}
                  label={`${expense.category.name} expense, ${formatCurrency(Number(expense.amount))}`}
                  onEdit={() => handleEdit(expense)}
                  onDelete={() => {
                    setDeletingExpense(expense);
                    setDeleteDialogOpen(true);
                  }}
                />
              ))}
            </ul>
          ) : hasFilters ? (
            <div className="flex flex-col items-center gap-3 py-12 text-center text-muted-foreground">
              <p>No expenses match these filters.</p>
              <Button variant="outline" size="sm" onClick={clearFilters}>
                Clear filters
              </Button>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3 py-12 text-center text-muted-foreground">
              <Receipt className="h-8 w-8" aria-hidden />
              <p>No expenses yet.</p>
              <Button
                size="sm"
                onClick={() => {
                  setEditingExpense(null);
                  setDialogOpen(true);
                }}
              >
                Add your first expense
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Pagination */}
      {pagination && pagination.total_pages > 1 && (
        <div className="flex items-center justify-center gap-4">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
          >
            <ChevronLeft className="h-4 w-4" />
            Prev
          </Button>
          <span className="text-sm text-muted-foreground">
            Page {page} of {pagination.total_pages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.min(pagination.total_pages, p + 1))}
            disabled={page === pagination.total_pages}
          >
            Next
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}

      {/* Form Dialog */}
      <ExpenseFormDialog
        open={dialogOpen}
        onClose={handleDialogClose}
        categories={categories}
        expense={editingExpense}
      />

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Expense</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this expense? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setDeletingExpense(null)}>Cancel</AlertDialogCancel>
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
