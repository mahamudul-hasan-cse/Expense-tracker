import {
  AssistantMessage,
  AssistantStatus,
  ConversationDetail,
  ConversationListResponse,
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
  Cashflow,
  ContributionCreate,
  Goal,
  GoalCreate,
  GoalListResponse,
  GoalUpdate,
  Income,
  IncomeCategoriesResponse,
  IncomeCreate,
  IncomeListResponse,
  IncomeUpdate,
  MarkPaidResponse,
  User,
  WeeklyInsight,
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
export async function authedFetch(endpoint: string, options?: RequestInit): Promise<Response> {
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

  // Recurring: record this cycle as paid / received
  markRecurringPaid: (id: string, data?: { paid_on?: string; amount?: number }) =>
    request<MarkPaidResponse>(`/recurring/${id}/mark-paid`, {
      method: "POST",
      body: JSON.stringify(data ?? {}),
    }),

  // Income categories
  getIncomeCategories: () => request<IncomeCategoriesResponse>("/income-categories"),
  createIncomeCategory: (data: CategoryCreate) =>
    request<Category>("/income-categories", { method: "POST", body: JSON.stringify(data) }),
  updateIncomeCategory: (id: string, data: CategoryUpdate) =>
    request<Category>(`/income-categories/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteIncomeCategory: (id: string) =>
    request<void>(`/income-categories/${id}`, { method: "DELETE" }),

  // Income
  getIncomes: (params?: {
    page?: number;
    limit?: number;
    start_date?: string;
    end_date?: string;
  }) => {
    const searchParams = new URLSearchParams();
    Object.entries(params ?? {}).forEach(([key, value]) => {
      if (value !== undefined && value !== "") searchParams.set(key, String(value));
    });
    const query = searchParams.toString();
    return request<IncomeListResponse>(`/incomes${query ? `?${query}` : ""}`);
  },
  createIncome: (data: IncomeCreate) =>
    request<Income>("/incomes", { method: "POST", body: JSON.stringify(data) }),
  updateIncome: (id: string, data: IncomeUpdate) =>
    request<Income>(`/incomes/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteIncome: (id: string) => request<void>(`/incomes/${id}`, { method: "DELETE" }),

  // Cashflow
  getCashflow: (month?: string) =>
    request<Cashflow>(`/stats/cashflow${month ? `?month=${month}` : ""}`),

  // Savings goals
  getGoals: () => request<GoalListResponse>("/goals"),
  createGoal: (data: GoalCreate) =>
    request<Goal>("/goals", { method: "POST", body: JSON.stringify(data) }),
  updateGoal: (id: string, data: GoalUpdate) =>
    request<Goal>(`/goals/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteGoal: (id: string) => request<void>(`/goals/${id}`, { method: "DELETE" }),
  addContribution: (goalId: string, data: ContributionCreate) =>
    request<Goal>(`/goals/${goalId}/contributions`, { method: "POST", body: JSON.stringify(data) }),

  // Assistant (chat itself streams: see lib/assistant-stream.ts)
  getAssistantStatus: () => request<AssistantStatus>("/assistant/status"),
  setAssistantEnabled: (enabled: boolean) =>
    request<AssistantStatus>("/assistant/settings", {
      method: "PUT",
      body: JSON.stringify({ enabled }),
    }),
  getWeeklyInsight: () => request<WeeklyInsight>("/assistant/insights/weekly"),
  getConversations: () => request<ConversationListResponse>("/assistant/conversations"),
  getConversation: (id: string) => request<ConversationDetail>(`/assistant/conversations/${id}`),
  deleteConversation: (id: string) =>
    request<void>(`/assistant/conversations/${id}`, { method: "DELETE" }),
  deleteAllConversations: () => request<void>("/assistant/conversations", { method: "DELETE" }),
  // Idempotent on the server: retrying returns the same saved expense
  confirmProposal: (messageId: string, edits?: ExpenseUpdate) =>
    request<AssistantMessage>(`/assistant/messages/${messageId}/proposal/confirm`, {
      method: "POST",
      body: edits ? JSON.stringify(edits) : undefined,
    }),
  cancelProposal: (messageId: string) =>
    request<AssistantMessage>(`/assistant/messages/${messageId}/proposal/cancel`, {
      method: "POST",
    }),
};
