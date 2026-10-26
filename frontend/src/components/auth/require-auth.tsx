"use client";

import { ReactNode, useEffect } from "react";
import { useAuth } from "@/lib/auth-provider";
import { redirectToLogin } from "@/lib/auth-token";
import { LoadingSpinner } from "@/components/shared/loading-spinner";

/** Renders children only for signed-in users; otherwise redirects to /login. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { status } = useAuth();

  useEffect(() => {
    if (status === "unauthenticated") redirectToLogin();
  }, [status]);

  if (status !== "authenticated") {
    return (
      <div
        className="flex min-h-[60vh] items-center justify-center"
        role="status"
        aria-label="Loading"
      >
        <LoadingSpinner />
      </div>
    );
  }
  return <>{children}</>;
}
