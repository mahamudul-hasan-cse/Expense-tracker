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
  AuthResponse,
  User,
} from "@/types";
import {
  API_BASE,
  getAccessToken,
  redirectToLogin,
  refreshSession,
  setAccessToken,
} from "./auth-token";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number
  ) {
    super(message);
  }
}

// Backend errors look like {"error": {"code", "message", "details", "request_id"}}.
// The legacy FastAPI {"detail": ...} shape is still handled for safety.
export function errorMessage(body: { error?: { message?: unknown }; detail?: unknown }): string {
  if (typeof body.error?.message === "string") return body.error.message;
  if (typeof body.detail === "string") return body.detail;
  if (Array.isArray(body.detail)) {
    return body.detail
      .map((e: { msg?: string }) => e.msg?.replace(/^Value error, /, ""))
      .filter(Boolean)
      .join("; ");
  }
  return "API request failed";
}

function send(endpoint: string, options?: RequestInit): Promise<Response> {
  const token = getAccessToken();
  return fetch(`${API_BASE}${endpoint}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });
}

/** Fetch with auth; on 401 refresh the session once and retry, else go to login. */
async function authedFetch(endpoint: string, options?: RequestInit): Promise<Response> {
  let res = await send(endpoint, options);
  if (res.status === 401 && !endpoint.startsWith("/auth/")) {
    if (await refreshSession()) {
      res = await send(endpoint, options);
    }
    if (res.status === 401) {
      redirectToLogin("expired");
    }
  }
  return res;
}

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await authedFetch(endpoint, options);

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new ApiError(errorMessage(error), res.status);
  }

  // Handle 204 No Content
  if (res.status === 204) {
    return undefined as T;
  }

  return res.json();
}

export const api = {
  // Auth
  register: async (email: string, password: string) => {
    const data = await request<AuthResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setAccessToken(data.access_token);
    return data.user;
  },

  login: async (email: string, password: string) => {
    const data = await request<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setAccessToken(data.access_token);
    return data.user;
  },

  logout: async () => {
    try {
      await request<void>("/auth/logout", { method: "POST" });
    } finally {
      setAccessToken(null);
    }
  },

  me: () => request<User>("/auth/me"),

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

  deleteCategory: (id: string) => request<void>(`/categories/${id}`, { method: "DELETE" }),

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

  deleteExpense: (id: string) => request<void>(`/expenses/${id}`, { method: "DELETE" }),

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

  deleteRecurring: (id: string) => request<void>(`/recurring/${id}`, { method: "DELETE" }),

  // Stats
  getStats: (period: "weekly" | "monthly", date?: string) => {
    const params = new URLSearchParams({ period });
    if (date) params.set("date", date);
    return request<StatsSummary>(`/stats/summary?${params.toString()}`);
  },

  getUpcoming: () => request<UpcomingResponse>("/stats/upcoming-recurring"),

  // Export
  // Fetched with the auth header (a plain link can't send it), then saved via a blob URL
  exportCSV: async (start_date: string, end_date: string) => {
    const params = new URLSearchParams({ start_date, end_date });
    const res = await authedFetch(`/export/csv?${params.toString()}`);
    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      throw new ApiError(errorMessage(error), res.status);
    }
    const url = URL.createObjectURL(await res.blob());
    const link = document.createElement("a");
    link.href = url;
    link.download = `expenses_${start_date}_${end_date}.csv`;
    link.click();
    URL.revokeObjectURL(url);
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

  deleteBudget: (id: string) => request<void>(`/budgets/${id}`, { method: "DELETE" }),
};
