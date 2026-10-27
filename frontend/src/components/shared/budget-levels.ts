// Colours for budgetLevel() (lib/utils): red only when over budget, amber when close
// (80%+), matching the warning icon. Lives under components/ so Tailwind sees the classes.
export const LEVEL_BAR = {
  ok: "",
  close: "[&>div]:bg-amber-500",
  over: "[&>div]:bg-destructive",
} as const;

export const LEVEL_TEXT = {
  ok: "text-muted-foreground",
  close: "text-amber-700 dark:text-amber-400", // amber-600 fails contrast on white
  over: "text-destructive",
} as const;
