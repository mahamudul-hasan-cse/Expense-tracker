import { goalStatus, GoalTone } from "@/lib/cashflow";
import { cn } from "@/lib/utils";
import { Goal } from "@/types";

const TONES: Record<GoalTone, string> = {
  success: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
  warning: "bg-amber-500/10 text-amber-700 dark:text-amber-400",
  danger: "bg-destructive/10 text-destructive",
  // muted-foreground on bg-muted is 4.4:1, just under WCAG AA for small text
  neutral: "bg-muted text-foreground/75",
};

export function GoalStatusBadge({ goal }: { goal: Pick<Goal, "state" | "remaining"> }) {
  const { text, tone } = goalStatus(goal);
  return <span className={cn("rounded px-2 py-0.5 text-xs font-medium", TONES[tone])}>{text}</span>;
}
