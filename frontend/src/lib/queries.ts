import { useQuery, useMutation, useQueryClient, QueryClient } from "@tanstack/react-query";
import { api } from "./api";
import {
  ExpenseCreate,
  ExpenseUpdate,
  CategoryCreate,
  CategoryUpdate,
  RecurringExpenseCreate,
  RecurringExpenseUpdate,
  BudgetCreate,
  BudgetUpdate,
  ContributionCreate,
  GoalCreate,
  GoalUpdate,
  IncomeCreate,
  IncomeUpdate,
} from "@/types";

// Query Keys
export const queryKeys = {
  categories: ["categories"] as const,
  expenses: (params?: {
    page?: number;
    limit?: number;
    category_id?: string;
    start_date?: string;
    end_date?: string;
    search?: string;
  }) => ["expenses", params] as const,
  recurring: ["recurring"] as const,
  stats: (period: "weekly" | "monthly", date?: string) => ["stats", period, date] as const,
  upcoming: ["upcoming"] as const,
  budgets: (month?: number, year?: number) => ["budgets", month, year] as const,
  budgetSummary: (month?: number, year?: number) => ["budgetSummary", month, year] as const,
};

// Everything derived from expenses: lists, stats, and budget spending
function invalidateExpenseData(queryClient: QueryClient) {
  queryClient.invalidateQueries({ queryKey: ["expenses"] });
  queryClient.invalidateQueries({ queryKey: ["stats"] });
  queryClient.invalidateQueries({ queryKey: ["budgets"] });
  queryClient.invalidateQueries({ queryKey: ["budgetSummary"] });
  // Spending changes Saved
  queryClient.invalidateQueries({ queryKey: ["cashflow"] });
}

// Categories
export function useCategories() {
  return useQuery({
    queryKey: queryKeys.categories,
    queryFn: () => api.getCategories(),
    staleTime: 5 * 60 * 1000, // Categories change rarely, cache 5 min
  });
}

export function useCreateCategory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CategoryCreate) => api.createCategory(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.categories });
    },
  });
}

export function useUpdateCategory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: CategoryUpdate }) =>
      api.updateCategory(id, data),
    onSuccess: () => {
      // Category names/icons are embedded in expenses, stats, budgets and recurring items
      queryClient.invalidateQueries({ queryKey: queryKeys.categories });
      queryClient.invalidateQueries({ queryKey: queryKeys.recurring });
      queryClient.invalidateQueries({ queryKey: queryKeys.upcoming });
      invalidateExpenseData(queryClient);
    },
  });
}

export function useDeleteCategory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteCategory(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.categories });
    },
  });
}

// Expenses
export function useExpenses(params?: {
  page?: number;
  limit?: number;
  category_id?: string;
  start_date?: string;
  end_date?: string;
  search?: string;
}) {
  return useQuery({
    queryKey: queryKeys.expenses(params),
    queryFn: () => api.getExpenses(params),
  });
}

export function useCreateExpense() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ExpenseCreate) => api.createExpense(data),
    onSuccess: () => {
      invalidateExpenseData(queryClient);
    },
  });
}

export function useUpdateExpense() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ExpenseUpdate }) => api.updateExpense(id, data),
    onSuccess: () => {
      invalidateExpenseData(queryClient);
    },
  });
}

export function useDeleteExpense() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteExpense(id),
    onSuccess: () => {
      invalidateExpenseData(queryClient);
    },
  });
}

// Recurring
export function useRecurring() {
  return useQuery({
    queryKey: queryKeys.recurring,
    queryFn: () => api.getRecurring(),
  });
}

export function useCreateRecurring() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: RecurringExpenseCreate) => api.createRecurring(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.recurring });
      queryClient.invalidateQueries({ queryKey: queryKeys.upcoming });
    },
  });
}

export function useUpdateRecurring() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: RecurringExpenseUpdate }) =>
      api.updateRecurring(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.recurring });
      queryClient.invalidateQueries({ queryKey: queryKeys.upcoming });
    },
  });
}

export function useDeleteRecurring() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteRecurring(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.recurring });
      queryClient.invalidateQueries({ queryKey: queryKeys.upcoming });
    },
  });
}

// Stats
export function useStats(period: "weekly" | "monthly", date?: string) {
  return useQuery({
    queryKey: queryKeys.stats(period, date),
    queryFn: () => api.getStats(period, date),
  });
}

export function useUpcoming() {
  return useQuery({
    queryKey: queryKeys.upcoming,
    queryFn: () => api.getUpcoming(),
  });
}

// Budgets
export function useBudgets(month?: number, year?: number) {
  return useQuery({
    queryKey: queryKeys.budgets(month, year),
    queryFn: () => api.getBudgets(month, year),
  });
}

export function useBudgetSummary(month?: number, year?: number) {
  return useQuery({
    queryKey: queryKeys.budgetSummary(month, year),
    queryFn: () => api.getBudgetSummary(month, year),
  });
}

export function useCreateBudget() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: BudgetCreate) => api.createBudget(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["budgets"] });
      queryClient.invalidateQueries({ queryKey: ["budgetSummary"] });
    },
  });
}

export function useUpdateBudget() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: BudgetUpdate }) => api.updateBudget(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["budgets"] });
      queryClient.invalidateQueries({ queryKey: ["budgetSummary"] });
    },
  });
}

export function useDeleteBudget() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteBudget(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["budgets"] });
      queryClient.invalidateQueries({ queryKey: ["budgetSummary"] });
    },
  });
}

// Income
export function useIncomeCategories() {
  return useQuery({
    queryKey: ["incomeCategories"],
    queryFn: () => api.getIncomeCategories(),
    staleTime: 5 * 60 * 1000,
  });
}

export function useCreateIncomeCategory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CategoryCreate) => api.createIncomeCategory(data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["incomeCategories"] }),
  });
}

export function useUpdateIncomeCategory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: CategoryUpdate }) =>
      api.updateIncomeCategory(id, data),
    onSuccess: () => {
      // Names/icons are embedded in income entries and recurring income
      queryClient.invalidateQueries({ queryKey: ["incomeCategories"] });
      queryClient.invalidateQueries({ queryKey: ["incomes"] });
      queryClient.invalidateQueries({ queryKey: queryKeys.recurring });
      queryClient.invalidateQueries({ queryKey: queryKeys.upcoming });
    },
  });
}

export function useDeleteIncomeCategory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteIncomeCategory(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["incomeCategories"] }),
  });
}

export function useIncomes(params?: {
  page?: number;
  limit?: number;
  start_date?: string;
  end_date?: string;
}) {
  return useQuery({
    queryKey: ["incomes", params],
    queryFn: () => api.getIncomes(params),
  });
}

function invalidateIncomeData(queryClient: QueryClient) {
  queryClient.invalidateQueries({ queryKey: ["incomes"] });
  queryClient.invalidateQueries({ queryKey: ["cashflow"] });
}

export function useCreateIncome() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: IncomeCreate) => api.createIncome(data),
    onSuccess: () => invalidateIncomeData(queryClient),
  });
}

export function useUpdateIncome() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: IncomeUpdate }) => api.updateIncome(id, data),
    onSuccess: () => invalidateIncomeData(queryClient),
  });
}

export function useDeleteIncome() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteIncome(id),
    onSuccess: () => invalidateIncomeData(queryClient),
  });
}

export function useCashflow(month?: string) {
  return useQuery({
    queryKey: ["cashflow", month],
    queryFn: () => api.getCashflow(month),
  });
}

// Recurring: mark this cycle paid (bill) or received (income)
export function useMarkRecurringPaid() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.markRecurringPaid(id),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.recurring });
      queryClient.invalidateQueries({ queryKey: queryKeys.upcoming });
      if (result.record_type === "expense") invalidateExpenseData(queryClient);
      else invalidateIncomeData(queryClient);
    },
  });
}

// Savings goals (contributions are allocations: they change goals and the
// cashflow's "allocated" figure, never spending)
export function useGoals() {
  return useQuery({ queryKey: ["goals"], queryFn: () => api.getGoals() });
}

function invalidateGoalData(queryClient: QueryClient) {
  queryClient.invalidateQueries({ queryKey: ["goals"] });
  queryClient.invalidateQueries({ queryKey: ["cashflow"] });
}

export function useCreateGoal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: GoalCreate) => api.createGoal(data),
    onSuccess: () => invalidateGoalData(queryClient),
  });
}

export function useUpdateGoal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: GoalUpdate }) => api.updateGoal(id, data),
    onSuccess: () => invalidateGoalData(queryClient),
  });
}

export function useDeleteGoal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteGoal(id),
    onSuccess: () => invalidateGoalData(queryClient),
  });
}

export function useAddContribution() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ goalId, data }: { goalId: string; data: ContributionCreate }) =>
      api.addContribution(goalId, data),
    onSuccess: () => invalidateGoalData(queryClient),
  });
}
