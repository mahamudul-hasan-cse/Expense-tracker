"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Sparkles } from "lucide-react";
import { useAssistantStatus } from "@/lib/queries";

/** Floating shortcut to the assistant on every app page (hidden when the server has no AI key). */
export function AssistantFab() {
  const pathname = usePathname();
  const { data } = useAssistantStatus();
  if (!data?.configured || pathname.startsWith("/assistant")) return null;
  return (
    <>
      {/* Room at the end of the page so the button never covers the last row's actions */}
      <div aria-hidden className="h-16" />
      <Link
        href="/assistant"
        aria-label="Open assistant"
        title="Ask the assistant"
        className="fixed bottom-5 right-5 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg shadow-primary/30 transition-transform hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
      >
        <Sparkles className="h-6 w-6" />
      </Link>
    </>
  );
}
