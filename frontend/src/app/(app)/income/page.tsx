import type { Metadata } from "next";
import { IncomeList } from "@/components/income/income-list";

export const metadata: Metadata = { title: "Income" };

export default function IncomePage() {
  return <IncomeList />;
}
