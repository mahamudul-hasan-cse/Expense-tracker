"use client";

import { useEffect } from "react";
import { reportError } from "@/lib/sentry";

/** Last-resort error page if the root layout itself fails (it replaces <html>). */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => reportError(error), [error]);

  return (
    <html lang="en">
      <body
        style={{
          fontFamily: "system-ui, sans-serif",
          display: "grid",
          placeItems: "center",
          minHeight: "100vh",
          margin: 0,
          textAlign: "center",
          padding: "1rem",
        }}
      >
        <main>
          <h1 style={{ fontSize: "1.25rem" }}>Wallet Agent ran into a problem</h1>
          <p style={{ color: "#555" }}>Your data is safe. Please try again.</p>
          <button
            onClick={reset}
            style={{
              marginTop: "1rem",
              padding: "0.6rem 1.2rem",
              borderRadius: "0.5rem",
              border: "none",
              background: "#7c3aed",
              color: "#fff",
              fontSize: "1rem",
              cursor: "pointer",
            }}
          >
            Try again
          </button>
        </main>
      </body>
    </html>
  );
}
