import type { Metadata } from "next";
import { IncomeList } from "@/components/income/income-list";

export const metadata: Metadata = { title: "Income · Wallet Agent" };

export default function IncomePage() {
  return <IncomeList />;
}
