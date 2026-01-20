import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Wallet Agent - Simple Expense Tracking",
  description: "A clean, fast expense tracker with beautiful charts, budget goals, and recurring reminders. No signup required.",
};

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Marketing pages render without the app navbar/container
  return <>{children}</>;
}
