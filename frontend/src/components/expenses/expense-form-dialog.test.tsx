import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Category, Expense } from "@/types";
import { ExpenseFormDialog } from "./expense-form-dialog";

const createExpense = vi.fn();
const updateExpense = vi.fn();
const createCategory = vi.fn();
const toast = vi.fn();

vi.mock("@/lib/queries", () => ({
  useCreateExpense: () => ({ mutateAsync: createExpense, isPending: false }),
  useUpdateExpense: () => ({ mutateAsync: updateExpense, isPending: false }),
  useCreateCategory: () => ({ mutateAsync: createCategory, isPending: false }),
}));
vi.mock("@/hooks/use-toast", () => ({ useToast: () => ({ toast }) }));

const categories: Category[] = [
  { id: "c1", name: "Rickshaw", icon: "🛺", is_default: true },
  { id: "c2", name: "Random", icon: "🎲", is_default: true },
];

const expense: Expense = {
  id: "e1",
  amount: 350,
  category: categories[1],
  note: "Lunch at Chillox",
  expense_date: "2026-01-17",
  created_at: "2026-01-17T10:30:00Z",
};

function renderDialog(props: Partial<React.ComponentProps<typeof ExpenseFormDialog>> = {}) {
  const onClose = vi.fn();
  render(<ExpenseFormDialog open onClose={onClose} categories={categories} {...props} />);
  return { onClose, user: userEvent.setup() };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("ExpenseFormDialog", () => {
  it("requires a category before saving", async () => {
    const { user } = renderDialog();
    await user.type(screen.getByLabelText(/Amount/), "80");
    await user.click(screen.getByRole("button", { name: "Save Expense" }));
    expect(createExpense).not.toHaveBeenCalled();
    expect(toast).toHaveBeenCalledWith(expect.objectContaining({ variant: "destructive", description: "Amount and category are required" }));
  });

  it("creates an expense with the preselected category and today's Dhaka date", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date("2026-10-25T23:30:00Z")); // 05:30 Oct 26 in Dhaka
    createExpense.mockResolvedValue({});
    const { user, onClose } = renderDialog({ preselectedCategory: categories[0] });

    const dateInput = screen.getByLabelText("Date");
    expect(dateInput).toHaveValue("2026-10-26");
    expect(dateInput).toHaveAttribute("max", "2026-10-26"); // no future dates

    await user.type(screen.getByLabelText(/Amount/), "80");
    await user.type(screen.getByLabelText(/Note/), "campus");
    await user.click(screen.getByRole("button", { name: "Save Expense" }));

    expect(createExpense).toHaveBeenCalledWith({
      amount: 80,
      category_id: "c1",
      note: "campus",
      expense_date: "2026-10-26",
    });
    expect(onClose).toHaveBeenCalled();
  });

  it("sends note: null when the note is cleared while editing (regression)", async () => {
    updateExpense.mockResolvedValue({});
    const { user } = renderDialog({ expense });
    expect(screen.getByLabelText(/Note/)).toHaveValue("Lunch at Chillox");

    await user.clear(screen.getByLabelText(/Note/));
    await user.click(screen.getByRole("button", { name: "Update" }));

    expect(updateExpense).toHaveBeenCalledWith({
      id: "e1",
      data: expect.objectContaining({ amount: 350, category_id: "c2", note: null, expense_date: "2026-01-17" }),
    });
  });

  it("keeps the dialog open and the input when saving fails", async () => {
    createExpense.mockRejectedValue(new Error("Category not found"));
    const { user, onClose } = renderDialog({ preselectedCategory: categories[0] });
    await user.type(screen.getByLabelText(/Amount/), "80");
    await user.click(screen.getByRole("button", { name: "Save Expense" }));

    expect(toast).toHaveBeenCalledWith(expect.objectContaining({ variant: "destructive", description: "Category not found" }));
    expect(onClose).not.toHaveBeenCalled();
    expect(screen.getByLabelText(/Amount/)).toHaveValue(80);
  });

  it("adds a new category inline and selects it, without submitting the expense", async () => {
    createCategory.mockResolvedValue({ id: "c9", name: "Gym", icon: "💪", is_default: false });
    const { user } = renderDialog();

    await user.click(screen.getByRole("combobox"));
    await user.click(await screen.findByRole("option", { name: /Add new category/ }));
    await user.type(screen.getByLabelText("New category icon"), "💪");
    await user.type(screen.getByLabelText("New category name"), "Gym{Enter}");

    expect(createCategory).toHaveBeenCalledWith({ name: "Gym", icon: "💪" });
    expect(createExpense).not.toHaveBeenCalled();
    expect(screen.getByRole("combobox")).toHaveTextContent("Gym");
    expect(screen.queryByLabelText("New category name")).not.toBeInTheDocument();
  });
});
