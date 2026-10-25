"use client";

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useCreateCategory, useCreateExpense, useUpdateExpense } from "@/lib/queries";
import { todayISO } from "@/lib/utils";
import { Category, Expense, ExpenseCreate, ExpenseUpdate } from "@/types";
import { useToast } from "@/hooks/use-toast";
import { Plus } from "lucide-react";

// Sentinel Select value for the "+ Add new category" option
const NEW_CATEGORY = "__new__";

interface ExpenseFormDialogProps {
  open: boolean;
  onClose: () => void;
  categories: Category[];
  expense?: Expense | null;
  preselectedCategory?: Category | null;
}

export function ExpenseFormDialog({
  open,
  onClose,
  categories,
  expense,
  preselectedCategory,
}: ExpenseFormDialogProps) {
  const { toast } = useToast();
  const createExpense = useCreateExpense();
  const updateExpense = useUpdateExpense();
  const loading = createExpense.isPending || updateExpense.isPending;
  const [amount, setAmount] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [note, setNote] = useState("");
  const [expenseDate, setExpenseDate] = useState("");

  // Inline "add new category"
  const createCategory = useCreateCategory();
  const [addingCategory, setAddingCategory] = useState(false);
  const [newCategoryName, setNewCategoryName] = useState("");
  const [newCategoryIcon, setNewCategoryIcon] = useState("");
  const [createdCategory, setCreatedCategory] = useState<Category | null>(null);

  const isEditing = !!expense;

  useEffect(() => {
    setAddingCategory(false);
    setNewCategoryName("");
    setNewCategoryIcon("");
  }, [open]);

  const handleCategoryChange = (value: string) => {
    if (value === NEW_CATEGORY) {
      setAddingCategory(true);
    } else {
      setCategoryId(value);
    }
  };

  const handleCreateCategory = async () => {
    const name = newCategoryName.trim();
    if (!name) {
      toast({ title: "Error", description: "Category name is required", variant: "destructive" });
      return;
    }
    try {
      const category = await createCategory.mutateAsync({
        name,
        icon: newCategoryIcon.trim() || undefined,
      });
      setCreatedCategory(category);
      setCategoryId(category.id);
      setAddingCategory(false);
      setNewCategoryName("");
      setNewCategoryIcon("");
      toast({ title: "Success", description: `Category "${category.name}" added` });
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to add category",
        variant: "destructive",
      });
    }
  };

  useEffect(() => {
    if (expense) {
      setAmount(expense.amount.toString());
      setCategoryId(expense.category.id);
      setNote(expense.note || "");
      setExpenseDate(expense.expense_date);
    } else if (preselectedCategory) {
      setAmount("");
      setCategoryId(preselectedCategory.id);
      setNote("");
      setExpenseDate(todayISO());
    } else {
      setAmount("");
      setCategoryId("");
      setNote("");
      setExpenseDate(todayISO());
    }
  }, [expense, preselectedCategory, open]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!amount || !categoryId) {
      toast({
        title: "Error",
        description: "Amount and category are required",
        variant: "destructive",
      });
      return;
    }

    try {
      if (isEditing && expense) {
        const updateData: ExpenseUpdate = {
          amount: parseFloat(amount),
          category_id: categoryId,
          note: note.trim() || null,
          expense_date: expenseDate || undefined,
        };
        await updateExpense.mutateAsync({ id: expense.id, data: updateData });
        toast({
          title: "Success",
          description: "Expense updated successfully",
        });
      } else {
        const createData: ExpenseCreate = {
          amount: parseFloat(amount),
          category_id: categoryId,
          note: note || undefined,
          expense_date: expenseDate || undefined,
        };
        await createExpense.mutateAsync(createData);
        toast({
          title: "Success",
          description: "Expense added successfully",
        });
      }
      
      onClose();
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to save expense",
        variant: "destructive",
      });
    }
  };

  // A just-created category may not be in `categories` until the refetch lands
  const selectedCategory =
    categories.find((c) => c.id === categoryId) ??
    (createdCategory?.id === categoryId ? createdCategory : undefined);

  return (
    <Dialog open={open} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>
            {preselectedCategory && !isEditing ? (
              <span className="flex items-center gap-2">
                <span>{preselectedCategory.icon}</span>
                {preselectedCategory.name}
              </span>
            ) : isEditing ? (
              "Edit Expense"
            ) : (
              "Add Expense"
            )}
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="amount">Amount (৳) *</Label>
            <Input
              id="amount"
              type="number"
              step="0.01"
              min="0"
              placeholder="0.00"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              required
            />
          </div>

          {!preselectedCategory && (
            <div className="space-y-2">
              <Label htmlFor="category">Category *</Label>
              <Select value={categoryId} onValueChange={handleCategoryChange}>
                <SelectTrigger id="category">
                  <SelectValue placeholder="Select a category">
                    {selectedCategory && (
                      <span className="flex items-center gap-2">
                        <span>{selectedCategory.icon}</span>
                        {selectedCategory.name}
                      </span>
                    )}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {categories.map((category) => (
                    <SelectItem key={category.id} value={category.id}>
                      <span className="flex items-center gap-2">
                        <span>{category.icon}</span>
                        {category.name}
                      </span>
                    </SelectItem>
                  ))}
                  <SelectItem value={NEW_CATEGORY} className="border-t text-primary">
                    <span className="flex items-center gap-2">
                      <Plus className="h-4 w-4" />
                      Add new category...
                    </span>
                  </SelectItem>
                </SelectContent>
              </Select>

              {addingCategory && (
                <div className="space-y-2 rounded-lg border bg-muted/30 p-3">
                  <div className="flex gap-2">
                    <Input
                      aria-label="New category icon"
                      placeholder="🍔"
                      value={newCategoryIcon}
                      onChange={(e) => setNewCategoryIcon(e.target.value)}
                      maxLength={50}
                      className="w-16"
                    />
                    <Input
                      aria-label="New category name"
                      placeholder="Category name"
                      value={newCategoryName}
                      onChange={(e) => setNewCategoryName(e.target.value)}
                      onKeyDown={(e) => {
                        // Enter adds the category instead of submitting the expense
                        if (e.key === "Enter") {
                          e.preventDefault();
                          handleCreateCategory();
                        }
                      }}
                      maxLength={100}
                      autoFocus
                    />
                  </div>
                  <div className="flex justify-end gap-2">
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setAddingCategory(false)}
                    >
                      Cancel
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      onClick={handleCreateCategory}
                      disabled={createCategory.isPending}
                    >
                      {createCategory.isPending ? "Adding..." : "Add"}
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="note">Note (optional)</Label>
            <Input
              id="note"
              placeholder="Add a note..."
              value={note}
              onChange={(e) => setNote(e.target.value)}
              maxLength={500}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="date">Date</Label>
            <Input
              id="date"
              type="date"
              value={expenseDate}
              onChange={(e) => setExpenseDate(e.target.value)}
              max={todayISO()}
            />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? "Saving..." : isEditing ? "Update" : "Save Expense"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
