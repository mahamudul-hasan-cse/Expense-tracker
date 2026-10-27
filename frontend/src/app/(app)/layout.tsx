import { Navbar } from "@/components/shared/navbar";
import { RequireAuth } from "@/components/auth/require-auth";
import { AssistantFab } from "@/components/assistant/assistant-fab";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireAuth>
      <div className="min-h-screen bg-background">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[60] focus:rounded-md focus:bg-background focus:px-4 focus:py-2 focus:shadow"
        >
          Skip to content
        </a>
        <Navbar />
        {/* Bottom padding on phones keeps content clear of the tab bar */}
        <main id="main" className="container mx-auto px-4 pb-24 pt-6 md:pb-6">
          {children}
        </main>
        <AssistantFab />
      </div>
    </RequireAuth>
  );
}
