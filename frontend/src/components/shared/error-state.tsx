import { AlertCircle, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";

/** Shown when data couldn't be loaded, with a way to try again. */
export function ErrorState({
  message = "Something went wrong while loading this.",
  onRetry,
  className = "",
}: {
  message?: string;
  onRetry: () => void;
  className?: string;
}) {
  return (
    <div
      role="alert"
      className={`flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed p-8 text-center ${className}`}
    >
      <AlertCircle className="h-8 w-8 text-destructive" aria-hidden />
      <p className="text-sm text-muted-foreground">{message}</p>
      <Button variant="outline" size="sm" onClick={onRetry} className="gap-2">
        <RotateCcw className="h-4 w-4" />
        Try again
      </Button>
    </div>
  );
}
