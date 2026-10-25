"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
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
import { Progress } from "@/components/ui/progress";
import { formatCurrency } from "@/lib/utils";
import { Budget, Category } from "@/types";
import { useToast } from "@/hooks/use-toast";
import { Plus, Edit2, Trash2, Target } from "lucide-react";
import {
  useBudgets,
  useCategories,
  useCreateBudget,
  useUpdateBudget,
  useDeleteBudget,
} from "@/lib/queries";

export function BudgetSettings() {
  const { toast } = useToast();
  const today = new Date();
  const [selectedMonth, setSelectedMonth] = useState(today.getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(today.getFullYear());

  // Dialog states
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingBudget, setEditingBudget] = useState<Budget | null>(null);
  const [budgetCategoryId, setBudgetCategoryId] = useState("");
  const [budgetAmount, setBudgetAmount] = useState("");
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deletingBudget, setDeletingBudget] = useState<Budget | null>(null);

  // React Query hooks
  const { data: budgetsData, isLoading: budgetsLoading } = useBudgets(selectedMonth, selectedYear);
  const { data: categoriesData } = useCategories();
  const createBudgetMutation = useCreateBudget();
  const updateBudgetMutation = useUpdateBudget();
  const deleteBudgetMutation = useDeleteBudget();

  const budgets = budgetsData?.budgets ?? [];
  const categories = categoriesData?.categories ?? [];

  // Filter out categories that already have budgets (for creating new ones)
  const availableCategories = categories.filter(
    (cat) => !budgets.some((b) => b.category.id === cat.id)
  );

  const months = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ];

  const years = Array.from({ length: 5 }, (_, i) => today.getFullYear() - 2 + i);

  const openDialog = (budget?: Budget) => {
    if (budget) {
      setEditingBudget(budget);
      setBudgetCategoryId(budget.category.id);
      setBudgetAmount(budget.amount.toString());
    } else {
      setEditingBudget(null);
      setBudgetCategoryId("");
      setBudgetAmount("");
    }
    setDialogOpen(true);
  };

  const handleSave = () => {
    if (!budgetAmount || parseFloat(budgetAmount) <= 0) {
      toast({ title: "Error", description: "Please enter a valid amount", variant: "destructive" });
      return;
    }

    if (editingBudget) {
      updateBudgetMutation.mutate(
        { id: editingBudget.id, data: { amount: parseFloat(budgetAmount) } },
        {
          onSuccess: () => {
            toast({ title: "Success", description: "Budget updated successfully" });
            setDialogOpen(false);
          },
          onError: () => {
            toast({ title: "Error", description: "Failed to update budget", variant: "destructive" });
          },
        }
      );
    } else {
      if (!budgetCategoryId) {
        toast({ title: "Error", description: "Please select a category", variant: "destructive" });
        return;
      }
      createBudgetMutation.mutate(
        {
          category_id: budgetCategoryId,
          amount: parseFloat(budgetAmount),
          month: selectedMonth,
          year: selectedYear,
        },
        {
          onSuccess: () => {
            toast({ title: "Success", description: "Budget created successfully" });
            setDialogOpen(false);
          },
          onError: (error) => {
            toast({
              title: "Error",
              description: error instanceof Error ? error.message : "Failed to create budget",
              variant: "destructive",
            });
          },
        }
      );
    }
  };

  const handleDelete = () => {
    if (!deletingBudget) return;
    deleteBudgetMutation.mutate(deletingBudget.id, {
      onSuccess: () => {
        toast({ title: "Success", description: "Budget deleted successfully" });
        setDeleteDialogOpen(false);
        setDeletingBudget(null);
      },
      onError: () => {
        toast({ title: "Error", description: "Failed to delete budget", variant: "destructive" });
      },
    });
  };

  return (
    <>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div className="flex items-center gap-2">
            <Target className="h-5 w-5" />
            <CardTitle className="text-lg">Monthly Budgets</CardTitle>
          </div>
          <div className="flex items-center gap-2">
            <Select value={selectedMonth.toString()} onValueChange={(v) => setSelectedMonth(parseInt(v))}>
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {months.map((month, i) => (
                  <SelectItem key={i} value={(i + 1).toString()}>{month}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={selectedYear.toString()} onValueChange={(v) => setSelectedYear(parseInt(v))}>
              <SelectTrigger className="w-24">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {years.map((year) => (
                  <SelectItem key={year} value={year.toString()}>{year}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button size="sm" onClick={() => openDialog()} className="gap-1" disabled={availableCategories.length === 0}>
              <Plus className="h-4 w-4" />
              Add Budget
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {budgetsLoading ? (
            <p className="text-center text-muted-foreground py-8">Loading...</p>
          ) : budgets.length > 0 ? (
            <div className="space-y-4">
              {budgets.map((budget) => (
                <div key={budget.id} className="space-y-2 rounded-lg border p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xl">{budget.category.icon}</span>
                      <span className="font-medium">{budget.category.name}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={budget.percentage > 100 ? "text-destructive font-semibold" : "text-muted-foreground"}>
                        {formatCurrency(budget.spent)} / {formatCurrency(budget.amount)}
                      </span>
                      <Button variant="ghost" size="icon" onClick={() => openDialog(budget)}>
                        <Edit2 className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => {
                          setDeletingBudget(budget);
                          setDeleteDialogOpen(true);
                        }}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </div>
                  <Progress
                    value={Math.min(budget.percentage, 100)}
                    className={budget.percentage > 90 ? "[&>div]:bg-destructive" : budget.percentage > 75 ? "[&>div]:bg-yellow-500" : ""}
                  />
                  <p className="text-xs text-muted-foreground text-right">
                    {budget.percentage.toFixed(1)}% used
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center text-muted-foreground py-8">
              No budgets set for {months[selectedMonth - 1]} {selectedYear}
            </p>
          )}
        </CardContent>
      </Card>

      {/* Budget Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingBudget ? "Edit Budget" : "Create Budget"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {!editingBudget && (
              <div className="space-y-2">
                <Label>Category</Label>
                <Select value={budgetCategoryId} onValueChange={setBudgetCategoryId}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select category" />
                  </SelectTrigger>
                  <SelectContent>
                    {availableCategories.map((cat) => (
                      <SelectItem key={cat.id} value={cat.id}>
                        <span className="flex items-center gap-2">
                          <span>{cat.icon}</span>
                          {cat.name}
                        </span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
            {editingBudget && (
              <div className="flex items-center gap-2 p-3 bg-muted rounded-lg">
                <span className="text-xl">{editingBudget.category.icon}</span>
                <span className="font-medium">{editingBudget.category.name}</span>
              </div>
            )}
            <div className="space-y-2">
              <Label>Monthly Budget Amount</Label>
              <Input
                type="number"
                placeholder="Enter amount"
                value={budgetAmount}
                onChange={(e) => setBudgetAmount(e.target.value)}
                min="0"
                step="0.01"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleSave} disabled={createBudgetMutation.isPending || updateBudgetMutation.isPending}>
              {editingBudget ? "Update" : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Budget</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete the budget for {deletingBudget?.category.name}? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setDeletingBudget(null)}>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="bg-destructive text-destructive-foreground">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
