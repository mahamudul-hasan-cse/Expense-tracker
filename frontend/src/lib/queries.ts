import { useQuery, useMutation, useQueryClient, QueryClient } from "@tanstack/react-query";
import { api } from "./api";
import {
  ExpenseCreate,
  ExpenseUpdate,
  CategoryCreate,
  RecurringExpenseCreate,
  RecurringExpenseUpdate,
  BudgetCreate,
  BudgetUpdate,
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
  stats: (period: "weekly" | "monthly", date?: string) =>
    ["stats", period, date] as const,
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
    mutationFn: ({ id, data }: { id: string; data: ExpenseUpdate }) =>
      api.updateExpense(id, data),
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
    mutationFn: ({ id, data }: { id: string; data: BudgetUpdate }) =>
      api.updateBudget(id, data),
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
