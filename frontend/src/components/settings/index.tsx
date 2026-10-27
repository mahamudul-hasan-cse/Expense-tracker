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
import { api } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import { Category, RecurringExpense, RecurringKind } from "@/types";
import { SettingsSkeleton } from "@/components/shared/skeletons";
import { useToast } from "@/hooks/use-toast";
import { Plus, Edit2, Trash2, Download } from "lucide-react";
import {
  useCategories,
  useIncomeCategories,
  useCreateCategory,
  useUpdateCategory,
  useDeleteCategory,
  useRecurring,
  useCreateRecurring,
  useUpdateRecurring,
  useDeleteRecurring,
} from "@/lib/queries";
import { AssistantSettings } from "./assistant-settings";
import { BudgetSettings } from "./budget-settings";
import { IncomeCategories } from "./income-categories";

export function Settings() {
  const { toast } = useToast();

  // React Query hooks
  const { data: categoriesData, isLoading: categoriesLoading } = useCategories();
  const { data: recurringData, isLoading: recurringLoading } = useRecurring();
  const { data: incomeCategoriesData } = useIncomeCategories();
  const incomeCategories = incomeCategoriesData?.income_categories ?? [];
  const createCategoryMutation = useCreateCategory();
  const updateCategoryMutation = useUpdateCategory();
  const deleteCategoryMutation = useDeleteCategory();
  const createRecurringMutation = useCreateRecurring();
  const updateRecurringMutation = useUpdateRecurring();
  const deleteRecurringMutation = useDeleteRecurring();

  const categories = categoriesData?.categories ?? [];
  const recurring = recurringData?.recurring_expenses ?? [];
  const loading = categoriesLoading || recurringLoading;

  // Category dialog
  const [categoryDialogOpen, setCategoryDialogOpen] = useState(false);
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  const [categoryName, setCategoryName] = useState("");
  const [categoryIcon, setCategoryIcon] = useState("");

  // Recurring dialog
  const [recurringDialogOpen, setRecurringDialogOpen] = useState(false);
  const [editingRecurring, setEditingRecurring] = useState<RecurringExpense | null>(null);
  const [recurringName, setRecurringName] = useState("");
  const [recurringAmount, setRecurringAmount] = useState("");
  const [recurringKind, setRecurringKind] = useState<RecurringKind>("expense");
  // Expense category id, or income category id when the kind is "income"
  const [recurringCategoryId, setRecurringCategoryId] = useState("");
  const [recurringFrequency, setRecurringFrequency] = useState<"weekly" | "monthly">("monthly");
  const [recurringDueDay, setRecurringDueDay] = useState("");

  // Delete dialogs
  const [deleteCategoryDialogOpen, setDeleteCategoryDialogOpen] = useState(false);
  const [deletingCategory, setDeletingCategory] = useState<Category | null>(null);
  const [deleteRecurringDialogOpen, setDeleteRecurringDialogOpen] = useState(false);
  const [deletingRecurring, setDeletingRecurring] = useState<RecurringExpense | null>(null);

  // Export
  const [exportStartDate, setExportStartDate] = useState("");
  const [exportEndDate, setExportEndDate] = useState("");

  if (loading) {
    return <SettingsSkeleton />;
  }

  // Category handlers
  const openCategoryDialog = (category?: Category) => {
    setEditingCategory(category ?? null);
    setCategoryName(category?.name ?? "");
    setCategoryIcon(category?.icon ?? "");
    setCategoryDialogOpen(true);
  };

  const handleSaveCategory = () => {
    const name = categoryName.trim();
    if (!name) {
      toast({ title: "Error", description: "Category name is required", variant: "destructive" });
      return;
    }
    const onSuccess = (message: string) => {
      toast({ title: "Success", description: message });
      setCategoryDialogOpen(false);
      setEditingCategory(null);
      setCategoryName("");
      setCategoryIcon("");
    };
    const onError = (error: Error) => {
      toast({
        title: "Error",
        description: error.message || "Failed to save category",
        variant: "destructive",
      });
    };
    if (editingCategory) {
      updateCategoryMutation.mutate(
        { id: editingCategory.id, data: { name, icon: categoryIcon.trim() || null } },
        { onSuccess: () => onSuccess("Category updated successfully"), onError }
      );
    } else {
      createCategoryMutation.mutate(
        { name, icon: categoryIcon.trim() || undefined },
        { onSuccess: () => onSuccess("Category added successfully"), onError }
      );
    }
  };

  const handleToggleRecurring = (rec: RecurringExpense) => {
    updateRecurringMutation.mutate(
      { id: rec.id, data: { is_active: !rec.is_active } },
      {
        onSuccess: () =>
          toast({
            title: "Success",
            description: `${rec.name} ${rec.is_active ? "paused" : "resumed"}`,
          }),
        onError: (error) =>
          toast({ title: "Error", description: error.message, variant: "destructive" }),
      }
    );
  };

  const handleDeleteCategory = () => {
    if (!deletingCategory) return;
    deleteCategoryMutation.mutate(deletingCategory.id, {
      onSuccess: () => {
        toast({ title: "Success", description: "Category deleted successfully" });
        setDeleteCategoryDialogOpen(false);
        setDeletingCategory(null);
      },
      onError: (error) => {
        toast({
          title: "Error",
          description: error instanceof Error ? error.message : "Failed to delete category",
          variant: "destructive",
        });
      },
    });
  };

  // Recurring handlers
  const openRecurringDialog = (rec?: RecurringExpense) => {
    if (rec) {
      setEditingRecurring(rec);
      setRecurringName(rec.name);
      setRecurringAmount(rec.amount.toString());
      setRecurringKind(rec.kind);
      setRecurringCategoryId(
        (rec.kind === "income" ? rec.income_category : rec.category)?.id ?? ""
      );
      setRecurringFrequency(rec.frequency);
      setRecurringDueDay(rec.due_day.toString());
    } else {
      setEditingRecurring(null);
      setRecurringName("");
      setRecurringAmount("");
      setRecurringKind("expense");
      setRecurringCategoryId("");
      setRecurringFrequency("monthly");
      setRecurringDueDay("");
    }
    setRecurringDialogOpen(true);
  };

  const handleSaveRecurring = () => {
    if (!recurringName || !recurringAmount || !recurringCategoryId || !recurringDueDay) {
      toast({ title: "Error", description: "All fields are required", variant: "destructive" });
      return;
    }
    const dueDay = parseInt(recurringDueDay);
    const maxDueDay = recurringFrequency === "weekly" ? 7 : 31;
    if (!(dueDay >= 1 && dueDay <= maxDueDay)) {
      toast({
        title: "Error",
        description: `Due day must be 1-${maxDueDay}`,
        variant: "destructive",
      });
      return;
    }
    const categoryField =
      recurringKind === "income"
        ? { income_category_id: recurringCategoryId }
        : { category_id: recurringCategoryId };
    const data = {
      name: recurringName,
      amount: parseFloat(recurringAmount),
      ...categoryField,
      frequency: recurringFrequency,
      due_day: dueDay,
    };
    const onSuccess = (message: string) => {
      toast({ title: "Success", description: message });
      setRecurringDialogOpen(false);
    };
    const onError = (error: Error) => {
      toast({
        title: "Error",
        description: error.message || "Failed to save",
        variant: "destructive",
      });
    };
    if (editingRecurring) {
      updateRecurringMutation.mutate(
        { id: editingRecurring.id, data },
        { onSuccess: () => onSuccess("Recurring expense updated successfully"), onError }
      );
    } else {
      createRecurringMutation.mutate(
        { ...data, kind: recurringKind },
        {
          onSuccess: () => onSuccess("Recurring expense added successfully"),
          onError,
        }
      );
    }
  };

  const handleDeleteRecurring = () => {
    if (!deletingRecurring) return;
    deleteRecurringMutation.mutate(deletingRecurring.id, {
      onSuccess: () => {
        toast({ title: "Success", description: "Recurring expense deleted successfully" });
        setDeleteRecurringDialogOpen(false);
        setDeletingRecurring(null);
      },
      onError: () => {
        toast({ title: "Error", description: "Failed to delete", variant: "destructive" });
      },
    });
  };

  // Export handler
  const handleExport = () => {
    if (!exportStartDate || !exportEndDate) {
      toast({ title: "Error", description: "Please select date range", variant: "destructive" });
      return;
    }
    if (exportStartDate > exportEndDate) {
      toast({
        title: "Error",
        description: "From date must be before To date",
        variant: "destructive",
      });
      return;
    }
    api.exportCSV(exportStartDate, exportEndDate).catch((error: Error) =>
      toast({
        title: "Error",
        description: error.message || "Export failed",
        variant: "destructive",
      })
    );
  };

  if (loading) {
    return <SettingsSkeleton />;
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Settings</h1>
      {/* Budget Settings */}
      <BudgetSettings />
      {/* Categories */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-lg">Categories</CardTitle>
          <Button size="sm" onClick={() => openCategoryDialog()} className="gap-1">
            <Plus className="h-4 w-4" />
            Add Category
          </Button>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {categories.map((category) => (
              <div
                key={category.id}
                className="flex items-center justify-between rounded-lg border p-3"
              >
                <div className="flex items-center gap-3">
                  <span className="text-xl">{category.icon}</span>
                  <span>{category.name}</span>
                  {category.is_default && (
                    <span className="text-xs text-muted-foreground">(default)</span>
                  )}
                </div>
                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label={`Edit ${category.name}`}
                    onClick={() => openCategoryDialog(category)}
                  >
                    <Edit2 className="h-4 w-4" />
                  </Button>
                  {!category.is_default && (
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={`Delete ${category.name}`}
                      onClick={() => {
                        setDeletingCategory(category);
                        setDeleteCategoryDialogOpen(true);
                      }}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Income categories */}
      <IncomeCategories />

      {/* Recurring Expenses */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-lg">Recurring Bills &amp; Income</CardTitle>
          <Button size="sm" onClick={() => openRecurringDialog()} className="gap-1">
            <Plus className="h-4 w-4" />
            Add Recurring
          </Button>
        </CardHeader>
        <CardContent>
          {recurring.length > 0 ? (
            <div className="space-y-2">
              {recurring.map((rec) => (
                <div
                  key={rec.id}
                  className={`flex items-center justify-between rounded-lg border p-3 ${rec.is_active ? "" : "opacity-60"}`}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-xl">
                      {(rec.kind === "income" ? rec.income_category : rec.category)?.icon}
                    </span>
                    <div>
                      <p className="font-medium">
                        {rec.name}
                        {rec.kind === "income" && (
                          <span className="ml-2 rounded bg-emerald-500/10 px-1.5 py-0.5 text-xs font-normal text-emerald-700 dark:text-emerald-400">
                            Income
                          </span>
                        )}
                        {!rec.is_active && (
                          <span className="ml-2 text-xs font-normal text-muted-foreground">
                            (paused)
                          </span>
                        )}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {formatCurrency(Number(rec.amount))} · {rec.frequency} · Day {rec.due_day}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    <Button
                      variant="outline"
                      size="sm"
                      aria-pressed={rec.is_active}
                      disabled={updateRecurringMutation.isPending}
                      onClick={() => handleToggleRecurring(rec)}
                    >
                      {rec.is_active ? "Active" : "Paused"}
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={`Edit ${rec.name}`}
                      onClick={() => openRecurringDialog(rec)}
                    >
                      <Edit2 className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={`Delete ${rec.name}`}
                      onClick={() => {
                        setDeletingRecurring(rec);
                        setDeleteRecurringDialogOpen(true);
                      }}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center text-muted-foreground py-8">No recurring expenses</p>
          )}
        </CardContent>
      </Card>

      {/* Export */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Export Data</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-end gap-4">
            <div className="space-y-2">
              <Label>From Date</Label>
              <Input
                type="date"
                value={exportStartDate}
                onChange={(e) => setExportStartDate(e.target.value)}
                className="w-40"
              />
            </div>
            <div className="space-y-2">
              <Label>To Date</Label>
              <Input
                type="date"
                value={exportEndDate}
                onChange={(e) => setExportEndDate(e.target.value)}
                className="w-40"
              />
            </div>
            <Button onClick={handleExport} className="gap-2">
              <Download className="h-4 w-4" />
              Download CSV
            </Button>
          </div>
        </CardContent>
      </Card>

      <AssistantSettings />

      {/* Add Category Dialog */}
      <Dialog open={categoryDialogOpen} onOpenChange={setCategoryDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingCategory ? "Edit Category" : "Add Category"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Name *</Label>
              <Input
                value={categoryName}
                onChange={(e) => setCategoryName(e.target.value)}
                placeholder="e.g., Food"
              />
            </div>
            <div className="space-y-2">
              <Label>Icon (emoji)</Label>
              <Input
                value={categoryIcon}
                onChange={(e) => setCategoryIcon(e.target.value)}
                placeholder="e.g., 🍔"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCategoryDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleSaveCategory}
              disabled={createCategoryMutation.isPending || updateCategoryMutation.isPending}
            >
              {editingCategory ? "Save" : "Add Category"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Recurring Dialog */}
      <Dialog open={recurringDialogOpen} onOpenChange={setRecurringDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingRecurring
                ? `Edit Recurring ${editingRecurring.kind === "income" ? "Income" : "Expense"}`
                : "Add Recurring Item"}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Name *</Label>
              <Input
                value={recurringName}
                onChange={(e) => setRecurringName(e.target.value)}
                placeholder="e.g., Monthly Wifi"
              />
            </div>
            <div className="space-y-2">
              <Label>Amount (৳) *</Label>
              <Input
                type="number"
                step="0.01"
                value={recurringAmount}
                onChange={(e) => setRecurringAmount(e.target.value)}
                placeholder="0.00"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="recurring-kind">Type *</Label>
              <Select
                value={recurringKind}
                onValueChange={(v) => {
                  setRecurringKind(v as RecurringKind);
                  setRecurringCategoryId("");
                }}
                disabled={!!editingRecurring}
              >
                <SelectTrigger id="recurring-kind">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="expense">Expense (a bill)</SelectItem>
                  <SelectItem value="income">Income (e.g. salary)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="recurring-category">Category *</Label>
              <Select value={recurringCategoryId} onValueChange={setRecurringCategoryId}>
                <SelectTrigger id="recurring-category">
                  <SelectValue placeholder="Select category" />
                </SelectTrigger>
                <SelectContent>
                  {(recurringKind === "income" ? incomeCategories : categories).map((cat) => (
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
            <div className="space-y-2">
              <Label>Frequency *</Label>
              <Select
                value={recurringFrequency}
                onValueChange={(v) => setRecurringFrequency(v as "weekly" | "monthly")}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="weekly">Weekly</SelectItem>
                  <SelectItem value="monthly">Monthly</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Due Day *</Label>
              <Input
                type="number"
                min={1}
                max={recurringFrequency === "weekly" ? 7 : 31}
                value={recurringDueDay}
                onChange={(e) => setRecurringDueDay(e.target.value)}
                placeholder={recurringFrequency === "weekly" ? "1-7 (Mon=1)" : "1-31"}
              />
              <p className="text-xs text-muted-foreground">
                {recurringFrequency === "weekly" ? "1=Monday, 7=Sunday" : "Day of month (1-31)"}
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRecurringDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSaveRecurring}>{editingRecurring ? "Update" : "Add"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Category Dialog */}
      <AlertDialog open={deleteCategoryDialogOpen} onOpenChange={setDeleteCategoryDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Category</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this category? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteCategory}
              className="bg-destructive text-destructive-foreground"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Delete Recurring Dialog */}
      <AlertDialog open={deleteRecurringDialogOpen} onOpenChange={setDeleteRecurringDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Recurring Expense</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this recurring expense?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteRecurring}
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
