"use client";

import { useState } from "react";
import { Edit2, Plus, Trash2 } from "lucide-react";
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
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import {
  useCreateIncomeCategory,
  useDeleteIncomeCategory,
  useIncomeCategories,
  useUpdateIncomeCategory,
} from "@/lib/queries";
import { Category } from "@/types";

/** Income sources: the 5 defaults plus user-defined ones (Settings card). */
export function IncomeCategories() {
  const { toast } = useToast();
  const { data } = useIncomeCategories();
  const categories = data?.income_categories ?? [];
  const createMutation = useCreateIncomeCategory();
  const updateMutation = useUpdateIncomeCategory();
  const deleteMutation = useDeleteIncomeCategory();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Category | null>(null);
  const [name, setName] = useState("");
  const [icon, setIcon] = useState("");
  const [deleting, setDeleting] = useState<Category | null>(null);

  const openDialog = (category?: Category) => {
    setEditing(category ?? null);
    setName(category?.name ?? "");
    setIcon(category?.icon ?? "");
    setDialogOpen(true);
  };

  const onError = (error: Error) =>
    toast({ title: "Error", description: error.message, variant: "destructive" });

  const handleSave = () => {
    const trimmed = name.trim();
    if (!trimmed) {
      toast({ title: "Error", description: "Name is required", variant: "destructive" });
      return;
    }
    const onSuccess = (message: string) => {
      toast({ title: "Success", description: message });
      setDialogOpen(false);
    };
    if (editing) {
      updateMutation.mutate(
        { id: editing.id, data: { name: trimmed, icon: icon.trim() || null } },
        { onSuccess: () => onSuccess("Income category updated"), onError }
      );
    } else {
      createMutation.mutate(
        { name: trimmed, icon: icon.trim() || undefined },
        { onSuccess: () => onSuccess("Income category added"), onError }
      );
    }
  };

  const handleDelete = () => {
    if (!deleting) return;
    deleteMutation.mutate(deleting.id, {
      onSuccess: () => {
        toast({ title: "Success", description: "Income category deleted" });
        setDeleting(null);
      },
      onError,
    });
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-lg">Income Categories</CardTitle>
        <Button size="sm" onClick={() => openDialog()} className="gap-1">
          <Plus className="h-4 w-4" />
          Add Income Category
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
                  onClick={() => openDialog(category)}
                >
                  <Edit2 className="h-4 w-4" />
                </Button>
                {!category.is_default && (
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label={`Delete ${category.name}`}
                    onClick={() => setDeleting(category)}
                  >
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      </CardContent>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editing ? "Edit Income Category" : "Add Income Category"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="income-category-name">Name *</Label>
              <Input
                id="income-category-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Tuition"
                maxLength={100}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="income-category-icon">Icon (emoji)</Label>
              <Input
                id="income-category-icon"
                value={icon}
                onChange={(e) => setIcon(e.target.value)}
                placeholder="e.g., 📚"
                maxLength={50}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleSave}
              disabled={createMutation.isPending || updateMutation.isPending}
            >
              {editing ? "Save" : "Add"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={!!deleting} onOpenChange={(open) => !open && setDeleting(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete income category?</AlertDialogTitle>
            <AlertDialogDescription>
              &ldquo;{deleting?.name}&rdquo; will be removed. Categories that income entries or
              recurring income still use can&apos;t be deleted.
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
    </Card>
  );
}
