import { Navbar } from "@/components/shared/navbar";
import { RequireAuth } from "@/components/auth/require-auth";
import { AssistantFab } from "@/components/assistant/assistant-fab";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireAuth>
      <div className="min-h-screen bg-background">
        <Navbar />
        <main className="container mx-auto px-4 py-6">{children}</main>
        <AssistantFab />
      </div>
    </RequireAuth>
  );
}
