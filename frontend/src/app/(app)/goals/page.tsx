import type { Metadata } from "next";
import { GoalsPage } from "@/components/goals/goals-page";

export const metadata: Metadata = { title: "Savings Goals" };

export default function Goals() {
  return <GoalsPage />;
}
