"use client";

import { useEffect } from "react";
import { AlertCircle, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { reportError } from "@/lib/sentry";

/** Shown instead of a page that crashed; the navigation stays usable. */
export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => reportError(error), [error]);

  return (
    <div
      role="alert"
      className="mx-auto flex max-w-md flex-col items-center gap-4 py-16 text-center"
    >
      <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-destructive/10">
        <AlertCircle className="h-7 w-7 text-destructive" aria-hidden />
      </span>
      <h1 className="text-xl font-semibold">Something went wrong on this page</h1>
      <p className="text-muted-foreground">
        Your data is safe. Try again, or go to another page using the menu.
      </p>
      <Button onClick={reset} className="gap-2">
        <RotateCcw className="h-4 w-4" />
        Try again
      </Button>
    </div>
  );
}
