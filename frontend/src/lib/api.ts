import {
  Category,
  CategoryCreate,
  CategoryUpdate,
  CategoriesResponse,
  Expense,
  ExpenseCreate,
  ExpenseUpdate,
  ExpenseListResponse,
  RecurringExpense,
  RecurringExpenseCreate,
  RecurringExpenseUpdate,
  RecurringListResponse,
  StatsSummary,
  UpcomingResponse,
  Budget,
  BudgetCreate,
  BudgetUpdate,
  BudgetListResponse,
  BudgetSummary,
} from "@/types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "API request failed");
  }

  // Handle 204 No Content
  if (res.status === 204) {
    return undefined as T;
  }

  return res.json();
}

export const api = {
  // Categories
  getCategories: () => request<CategoriesResponse>("/categories"),

  createCategory: (data: CategoryCreate) =>
    request<Category>("/categories", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateCategory: (id: string, data: CategoryUpdate) =>
    request<Category>(`/categories/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deleteCategory: (id: string) =>
    request<void>(`/categories/${id}`, { method: "DELETE" }),

  // Expenses
  getExpenses: (params?: {
    page?: number;
    limit?: number;
    category_id?: string;
    start_date?: string;
    end_date?: string;
    search?: string;
    sort?: string;
  }) => {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== "") {
          searchParams.set(key, String(value));
        }
      });
    }
    const query = searchParams.toString();
    return request<ExpenseListResponse>(`/expenses${query ? `?${query}` : ""}`);
  },

  createExpense: (data: ExpenseCreate) =>
    request<Expense>("/expenses", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateExpense: (id: string, data: ExpenseUpdate) =>
    request<Expense>(`/expenses/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deleteExpense: (id: string) =>
    request<void>(`/expenses/${id}`, { method: "DELETE" }),

  // Recurring
  getRecurring: () => request<RecurringListResponse>("/recurring"),

  createRecurring: (data: RecurringExpenseCreate) =>
    request<RecurringExpense>("/recurring", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateRecurring: (id: string, data: RecurringExpenseUpdate) =>
    request<RecurringExpense>(`/recurring/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deleteRecurring: (id: string) =>
    request<void>(`/recurring/${id}`, { method: "DELETE" }),

  // Stats
  getStats: (period: "weekly" | "monthly", date?: string) => {
    const params = new URLSearchParams({ period });
    if (date) params.set("date", date);
    return request<StatsSummary>(`/stats/summary?${params.toString()}`);
  },

  getUpcoming: () => request<UpcomingResponse>("/stats/upcoming-recurring"),

  // Export
  exportCSV: (start_date: string, end_date: string) => {
    window.open(
      `${API_BASE}/export/csv?start_date=${start_date}&end_date=${end_date}`,
      "_blank"
    );
  },

  // Budgets
  getBudgets: (month?: number, year?: number) => {
    const params = new URLSearchParams();
    if (month) params.set("month", month.toString());
    if (year) params.set("year", year.toString());
    const query = params.toString();
    return request<BudgetListResponse>(`/budgets${query ? `?${query}` : ""}`);
  },

  getBudgetSummary: (month?: number, year?: number) => {
    const params = new URLSearchParams();
    if (month) params.set("month", month.toString());
    if (year) params.set("year", year.toString());
    const query = params.toString();
    return request<BudgetSummary>(`/budgets/summary${query ? `?${query}` : ""}`);
  },

  createBudget: (data: BudgetCreate) =>
    request<Budget>("/budgets", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateBudget: (id: string, data: BudgetUpdate) =>
    request<Budget>(`/budgets/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deleteBudget: (id: string) =>
    request<void>(`/budgets/${id}`, { method: "DELETE" }),
};
