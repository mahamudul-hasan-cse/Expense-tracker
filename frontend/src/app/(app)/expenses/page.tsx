import type { Metadata } from "next";
import { ExpenseList } from "@/components/expenses/expense-list";

export const metadata: Metadata = { title: "Expenses" };

export default function ExpensesPage() {
  return <ExpenseList />;
}
