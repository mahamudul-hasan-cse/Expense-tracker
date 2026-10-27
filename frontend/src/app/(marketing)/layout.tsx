import type { Metadata } from "next";

export const metadata: Metadata = {
  title: { absolute: "Wallet Agent: expense tracker for Bangladesh" },
  description:
    "Track expenses and income in Taka, set monthly budgets and savings goals, and get bill reminders. Free and open source.",
};

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  // Marketing pages render without the app navbar/container
  return <>{children}</>;
}
