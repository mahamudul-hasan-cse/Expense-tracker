"use client";

import { FormEvent, useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { useCreateIncome, useCreateIncomeCategory, useUpdateIncome } from "@/lib/queries";
import { todayISO } from "@/lib/utils";
import { Category, Income } from "@/types";

// Sentinel Select value for the "+ Add new category" option
const NEW_CATEGORY = "__new__";

interface IncomeFormDialogProps {
  open: boolean;
  onClose: () => void;
  categories: Category[];
  income?: Income | null;
}

export function IncomeFormDialog({ open, onClose, categories, income }: IncomeFormDialogProps) {
  const { toast } = useToast();
  const createIncome = useCreateIncome();
  const updateIncome = useUpdateIncome();
  const createCategory = useCreateIncomeCategory();
  const saving = createIncome.isPending || updateIncome.isPending;

  const [amount, setAmount] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [incomeDate, setIncomeDate] = useState("");
  const [note, setNote] = useState("");
  const [addingCategory, setAddingCategory] = useState(false);
  const [newCategoryName, setNewCategoryName] = useState("");
  const [createdCategory, setCreatedCategory] = useState<Category | null>(null);

  const isEditing = !!income;

  useEffect(() => {
    setAmount(income ? String(income.amount) : "");
    setCategoryId(income?.category.id ?? "");
    setIncomeDate(income?.income_date ?? todayISO());
    setNote(income?.note ?? "");
    setAddingCategory(false);
    setNewCategoryName("");
  }, [income, open]);

  const selectedCategory =
    categories.find((c) => c.id === categoryId) ??
    (createdCategory?.id === categoryId ? createdCategory : undefined);

  const handleCreateCategory = async () => {
    const name = newCategoryName.trim();
    if (!name) return;
    try {
      const category = await createCategory.mutateAsync({ name });
      setCreatedCategory(category);
      setCategoryId(category.id);
      setAddingCategory(false);
      setNewCategoryName("");
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to add category",
        variant: "destructive",
      });
    }
  };

  const handleSubmit = async (e: FormEvent) => {
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
      if (isEditing && income) {
        await updateIncome.mutateAsync({
          id: income.id,
          data: {
            amount: parseFloat(amount),
            income_category_id: categoryId,
            note: note.trim() || null,
            income_date: incomeDate || undefined,
          },
        });
        toast({ title: "Success", description: "Income updated" });
      } else {
        await createIncome.mutateAsync({
          amount: parseFloat(amount),
          income_category_id: categoryId,
          note: note.trim() || undefined,
          income_date: incomeDate || undefined,
        });
        toast({ title: "Success", description: "Income added" });
      }
      onClose();
    } catch (error) {
      // Keep the dialog open with the user's input
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to save income",
        variant: "destructive",
      });
    }
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{isEditing ? "Edit Income" : "Add Income"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="income-amount">Amount (৳) *</Label>
            <Input
              id="income-amount"
              type="number"
              step="0.01"
              min="0"
              placeholder="0.00"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="income-category">Category *</Label>
            <Select
              value={categoryId}
              onValueChange={(v) =>
                v === NEW_CATEGORY ? setAddingCategory(true) : setCategoryId(v)
              }
            >
              <SelectTrigger id="income-category">
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
              <div className="flex gap-2 rounded-lg border bg-muted/30 p-3">
                <Input
                  aria-label="New income category name"
                  placeholder="Category name"
                  value={newCategoryName}
                  onChange={(e) => setNewCategoryName(e.target.value)}
                  onKeyDown={(e) => {
                    // Enter adds the category instead of submitting the income
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleCreateCategory();
                    }
                  }}
                  maxLength={100}
                  autoFocus
                />
                <Button type="button" size="sm" onClick={handleCreateCategory}>
                  Add
                </Button>
              </div>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="income-date">Date</Label>
            <Input
              id="income-date"
              type="date"
              value={incomeDate}
              max={todayISO()}
              onChange={(e) => setIncomeDate(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="income-note">Note (optional)</Label>
            <Input
              id="income-note"
              placeholder="e.g., October salary"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              maxLength={500}
            />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? "Saving..." : isEditing ? "Update" : "Save Income"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
