import { Edit2, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { formatDate } from "@/lib/utils";

/**
 * One expense or income in a list. Fixed columns so amounts and actions line up on
 * every row: the note truncates, the date never wraps (on phones it moves into the
 * second line), and edit/delete always sit in the same place.
 */
export function TransactionRow({
  icon,
  amount,
  category,
  note,
  date,
  label,
  onEdit,
  onDelete,
  amountClassName = "",
}: {
  icon: string | null;
  amount: string;
  category: string;
  note: string | null;
  date: string;
  /** e.g. "Rickshaw expense, ৳80" — used for the buttons' accessible names */
  label: string;
  onEdit: () => void;
  onDelete: () => void;
  amountClassName?: string;
}) {
  return (
    <li className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 p-4 hover:bg-muted/50 sm:gap-4">
      <span className="w-8 text-center text-2xl" aria-hidden>
        {icon || "🧾"}
      </span>
      <div className="min-w-0">
        <p className={`font-medium tabular-nums ${amountClassName}`}>{amount}</p>
        <p className="truncate text-sm text-muted-foreground">
          <span className="sm:hidden">{formatDate(date)} · </span>
          {category}
          {note && ` · ${note}`}
        </p>
      </div>
      <div className="flex items-center gap-1 sm:gap-3">
        <span className="hidden whitespace-nowrap text-sm text-muted-foreground sm:inline">
          {formatDate(date)}
        </span>
        <div className="flex items-center">
          <Button variant="ghost" size="icon" aria-label={`Edit ${label}`} onClick={onEdit}>
            <Edit2 className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" aria-label={`Delete ${label}`} onClick={onDelete}>
            <Trash2 className="h-4 w-4 text-destructive" />
          </Button>
        </div>
      </div>
    </li>
  );
}
