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
import { api } from "@/lib/api";
import { Category, Expense, ExpenseCreate, ExpenseUpdate } from "@/types";
import { useToast } from "@/hooks/use-toast";

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
  const [loading, setLoading] = useState(false);
  const [amount, setAmount] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [note, setNote] = useState("");
  const [expenseDate, setExpenseDate] = useState("");

  const isEditing = !!expense;

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
      setExpenseDate(new Date().toISOString().split("T")[0]);
    } else {
      setAmount("");
      setCategoryId("");
      setNote("");
      setExpenseDate(new Date().toISOString().split("T")[0]);
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
      setLoading(true);
      
      if (isEditing && expense) {
        const updateData: ExpenseUpdate = {
          amount: parseFloat(amount),
          category_id: categoryId,
          note: note || undefined,
          expense_date: expenseDate || undefined,
        };
        await api.updateExpense(expense.id, updateData);
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
        await api.createExpense(createData);
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
    } finally {
      setLoading(false);
    }
  };

  const selectedCategory = categories.find((c) => c.id === categoryId);

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
              <Select value={categoryId} onValueChange={setCategoryId}>
                <SelectTrigger>
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
                </SelectContent>
              </Select>
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
              max={new Date().toISOString().split("T")[0]}
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
