"use client";

import { FormEvent, useEffect, useState } from "react";
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
import { FieldError } from "@/components/ui/field-error";
import { amountError } from "@/lib/validation";
import { useToast } from "@/hooks/use-toast";
import { useCreateGoal, useUpdateGoal } from "@/lib/queries";
import { formatDateForInput } from "@/lib/utils";
import { Goal } from "@/types";

function tomorrowISO(): string {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  return formatDateForInput(d);
}

export function GoalFormDialog({
  open,
  onClose,
  goal,
}: {
  open: boolean;
  onClose: () => void;
  goal?: Goal | null;
}) {
  const { toast } = useToast();
  const createGoal = useCreateGoal();
  const updateGoal = useUpdateGoal();
  const saving = createGoal.isPending || updateGoal.isPending;

  const [name, setName] = useState("");
  const [icon, setIcon] = useState("");
  const [target, setTarget] = useState("");
  const [deadline, setDeadline] = useState("");
  // Server/unexpected errors at the top; field problems under each field
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<
    Record<"name" | "target" | "deadline", string | null>
  >({ name: null, target: null, deadline: null });

  useEffect(() => {
    setName(goal?.name ?? "");
    setIcon(goal?.icon ?? "");
    setTarget(goal ? String(goal.target_amount) : "");
    setDeadline(goal?.target_date ?? "");
    setError(null);
    setFieldErrors({ name: null, target: null, deadline: null });
  }, [goal, open]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const errors = {
      name: name.trim() ? null : "Give the goal a name",
      target: amountError(target),
      // An unchanged past deadline on an existing goal is fine; new ones must be in the future
      deadline:
        deadline && deadline < tomorrowISO() && deadline !== goal?.target_date
          ? "The deadline must be in the future"
          : null,
    };
    setFieldErrors(errors);
    if (errors.name || errors.target || errors.deadline) return;
    const amount = parseFloat(target);
    setError(null);
    try {
      if (goal) {
        await updateGoal.mutateAsync({
          id: goal.id,
          data: {
            name: name.trim(),
            icon: icon.trim() || null,
            target_amount: amount,
            ...(deadline !== (goal.target_date ?? "") && { target_date: deadline || null }),
          },
        });
        toast({ title: "Success", description: "Goal updated" });
      } else {
        await createGoal.mutateAsync({
          name: name.trim(),
          icon: icon.trim() || undefined,
          target_amount: amount,
          target_date: deadline || undefined,
        });
        toast({ title: "Success", description: "Goal created" });
      }
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save goal");
    }
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{goal ? "Edit Goal" : "New Savings Goal"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          {error && (
            <p className="rounded-md bg-destructive/10 p-3 text-sm text-destructive" role="alert">
              {error}
            </p>
          )}
          <div className="space-y-2">
            <Label htmlFor="goal-name">Name *</Label>
            <Input
              id="goal-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., New laptop"
              maxLength={100}
              aria-invalid={!!fieldErrors.name}
              aria-describedby="goal-name-error"
            />
            <FieldError id="goal-name-error" message={fieldErrors.name} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="goal-icon">Icon (optional)</Label>
            <Input
              id="goal-icon"
              value={icon}
              onChange={(e) => setIcon(e.target.value)}
              maxLength={50}
              className="w-24"
              aria-describedby="goal-icon-hint"
            />
            <p id="goal-icon-hint" className="text-xs text-muted-foreground">
              An emoji, e.g. a laptop or a plane. Leave empty for 🎯.
            </p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="goal-target">Target amount (৳) *</Label>
            <Input
              id="goal-target"
              type="number"
              min="0"
              step="0.01"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              placeholder="0.00"
              aria-invalid={!!fieldErrors.target}
              aria-describedby="goal-target-error"
            />
            <FieldError id="goal-target-error" message={fieldErrors.target} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="goal-deadline">Deadline (optional)</Label>
            <div className="flex gap-2">
              <Input
                id="goal-deadline"
                type="date"
                min={tomorrowISO()}
                value={deadline}
                onChange={(e) => setDeadline(e.target.value)}
                aria-invalid={!!fieldErrors.deadline}
                aria-describedby="goal-deadline-error goal-deadline-hint"
              />
              {deadline && (
                <Button type="button" variant="ghost" onClick={() => setDeadline("")}>
                  Clear
                </Button>
              )}
            </div>
            <FieldError id="goal-deadline-error" message={fieldErrors.deadline} />
            <p id="goal-deadline-hint" className="text-xs text-muted-foreground">
              With a deadline you&apos;ll see how much to save each month.
            </p>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? "Saving..." : goal ? "Save" : "Create Goal"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
