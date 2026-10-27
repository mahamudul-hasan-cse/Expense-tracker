"use client";

import { FormEvent, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import { useAddContribution } from "@/lib/queries";
import { formatCurrency, todayISO } from "@/lib/utils";
import { Goal } from "@/types";

export type ContributionMode = "add" | "withdraw";

/** Put money toward a goal, or take some back. Never counted as spending. */
export function ContributionDialog({
  goal,
  mode,
  onClose,
}: {
  goal: Goal | null;
  mode: ContributionMode;
  onClose: () => void;
}) {
  const { toast } = useToast();
  const addContribution = useAddContribution();
  const [amount, setAmount] = useState("");
  const [date, setDate] = useState(todayISO());
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setAmount("");
    setDate(todayISO());
    setNote("");
    setError(null);
  }, [goal, mode]);

  const withdrawing = mode === "withdraw";

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!goal) return;
    const value = parseFloat(amount);
    if (!(value > 0)) return setError("Enter an amount above ৳0");
    if (withdrawing && value > goal.saved) {
      return setError(`You can take back at most ${formatCurrency(goal.saved)}`);
    }
    try {
      await addContribution.mutateAsync({
        goalId: goal.id,
        data: {
          amount: withdrawing ? -value : value,
          contributed_on: date,
          note: note.trim() || undefined,
        },
      });
      toast({
        title: "Success",
        description: withdrawing
          ? `${formatCurrency(value)} taken back from ${goal.name}`
          : `${formatCurrency(value)} added to ${goal.name}`,
      });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save");
    }
  };

  return (
    <Dialog open={!!goal} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="sm:max-w-[400px]">
        <DialogHeader>
          <DialogTitle>
            {withdrawing ? "Take money back" : "Add money"}: {goal?.name}
          </DialogTitle>
          <DialogDescription>
            This only earmarks savings for the goal. It doesn&apos;t count as spending.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          {error && (
            <p className="rounded-md bg-destructive/10 p-3 text-sm text-destructive" role="alert">
              {error}
            </p>
          )}
          <div className="space-y-2">
            <Label htmlFor="contribution-amount">Amount (৳) *</Label>
            <Input
              id="contribution-amount"
              type="number"
              min="0"
              step="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0.00"
              autoFocus
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="contribution-date">Date</Label>
            <Input
              id="contribution-date"
              type="date"
              max={todayISO()}
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="contribution-note">Note (optional)</Label>
            <Input
              id="contribution-note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              maxLength={200}
            />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={addContribution.isPending}>
              {withdrawing ? "Take back" : "Add"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
