"use client";

import { useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useQueryClient } from "@tanstack/react-query";
import { Check, Clock, Loader2, Pencil, X } from "lucide-react";
import { ExpenseFormDialog } from "@/components/expenses/expense-form-dialog";
import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/lib/api";
import { invalidateExpenseData, useCategories } from "@/lib/queries";
import { cn, formatCurrency, formatDateFull } from "@/lib/utils";
import { AssistantMessage, ExpenseCreate, ExpenseProposal, ProposalStatus } from "@/types";

interface ProposalCardProps {
  proposal: ExpenseProposal;
  status: ProposalStatus;
  /** Server id of the assistant message; null while the answer is still streaming */
  messageId: string | null;
  onChange: (message: AssistantMessage) => void;
}

const STATE_TEXT: Record<Exclude<ProposalStatus, "pending">, string> = {
  confirmed: "Saved to your expenses",
  cancelled: "Not saved",
  expired: "Expired after 24 hours. Ask again to log it.",
};

/**
 * Quick-add confirmation. Nothing is saved until the user presses Save; the server
 * makes Save idempotent, and the button is disabled while a request is in flight.
 */
export function ProposalCard({ proposal, status, messageId, onChange }: ProposalCardProps) {
  const queryClient = useQueryClient();
  const [busy, setBusy] = useState<"confirm" | "cancel" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const categories = useCategories();
  // Stable object: the form resets its fields whenever `initial` changes
  const initial = useMemo<ExpenseCreate>(
    () => ({
      amount: proposal.amount,
      category_id: proposal.category_id,
      note: proposal.note ?? undefined,
      expense_date: proposal.expense_date,
    }),
    [proposal]
  );

  // Edit → the regular expense form, saved through the same idempotent confirm
  const saveEdited = async (data: ExpenseCreate) => {
    if (!messageId) return;
    const updated = await api.confirmProposal(messageId, data);
    invalidateExpenseData(queryClient);
    onChange(updated);
  };

  // A ref, not just state: a second click can arrive before React re-renders
  const inFlight = useRef(false);

  const act = async (action: "confirm" | "cancel") => {
    if (!messageId || inFlight.current) return;
    inFlight.current = true;
    setBusy(action);
    setError(null);
    try {
      const updated =
        action === "confirm"
          ? await api.confirmProposal(messageId)
          : await api.cancelProposal(messageId);
      if (action === "confirm") invalidateExpenseData(queryClient);
      onChange(updated);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong. Please try again.");
    } finally {
      inFlight.current = false;
      setBusy(null);
    }
  };

  const pending = status === "pending";
  return (
    <section
      aria-label="Expense to confirm"
      className={cn(
        "mt-3 rounded-xl border bg-card p-4 text-card-foreground shadow-sm",
        pending ? "border-primary/40" : "opacity-90"
      )}
    >
      <div className="flex items-start gap-3">
        <span className="text-2xl leading-none" aria-hidden>
          {proposal.category_icon || "🧾"}
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {pending ? "Check and save this expense" : "Quick add"}
          </p>
          <p className="mt-1 text-2xl font-bold tabular-nums">{formatCurrency(proposal.amount)}</p>
          <dl className="mt-1 grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-sm">
            <dt className="text-muted-foreground">Category</dt>
            <dd className="truncate">{proposal.category_name}</dd>
            <dt className="text-muted-foreground">Date</dt>
            <dd>{formatDateFull(proposal.expense_date)}</dd>
            {proposal.note && (
              <>
                <dt className="text-muted-foreground">Note</dt>
                <dd className="break-words">{proposal.note}</dd>
              </>
            )}
          </dl>
        </div>
      </div>

      {pending ? (
        <div className="mt-4 flex flex-wrap gap-2">
          <Button
            size="sm"
            onClick={() => act("confirm")}
            disabled={!messageId || busy !== null}
            aria-busy={busy === "confirm"}
          >
            {busy === "confirm" ? (
              <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
            ) : (
              <Check className="mr-1.5 h-4 w-4" />
            )}
            Save expense
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => act("cancel")}
            disabled={!messageId || busy !== null}
          >
            <X className="mr-1.5 h-4 w-4" />
            Don&apos;t save
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setEditing(true)}
            disabled={!messageId || busy !== null}
          >
            <Pencil className="mr-1.5 h-4 w-4" />
            Edit
          </Button>
          <ExpenseFormDialog
            open={editing}
            onClose={() => setEditing(false)}
            categories={categories.data?.categories ?? []}
            initial={initial}
            onSave={saveEdited}
          />
        </div>
      ) : (
        <p
          role="status"
          className={cn(
            "mt-3 flex items-center gap-1.5 text-sm font-medium",
            status === "confirmed"
              ? "text-emerald-600 dark:text-emerald-400"
              : "text-muted-foreground"
          )}
        >
          {status === "confirmed" && <Check className="h-4 w-4" />}
          {status === "cancelled" && <X className="h-4 w-4" />}
          {status === "expired" && <Clock className="h-4 w-4" />}
          {STATE_TEXT[status]}
          {status === "confirmed" && (
            <Link href="/expenses" className="ml-1 underline underline-offset-2">
              View
            </Link>
          )}
        </p>
      )}
      {error && (
        <p role="alert" className="mt-2 text-sm text-destructive">
          {error}
        </p>
      )}
    </section>
  );
}
