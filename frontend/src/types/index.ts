// Category types
export interface Category {
  id: string;
  name: string;
  icon: string | null;
  is_default: boolean;
}

export interface CategoryCreate {
  name: string;
  icon?: string;
}

// Expense types
export interface Expense {
  id: string;
  amount: number;
  category: Category;
  note: string | null;
  expense_date: string; // "YYYY-MM-DD"
  created_at: string;
}

export interface ExpenseCreate {
  amount: number;
  category_id: string;
  note?: string;
  expense_date?: string;
}

export interface ExpenseUpdate {
  amount?: number;
  category_id?: string;
  note?: string | null;
  expense_date?: string;
}

// Recurring expense types
export interface RecurringExpense {
  id: string;
  name: string;
  amount: number;
  category: Category;
  frequency: "weekly" | "monthly";
  due_day: number;
  is_active: boolean;
  next_due: string;
}

export interface RecurringExpenseCreate {
  name: string;
  amount: number;
  category_id: string;
  frequency: "weekly" | "monthly";
  due_day: number;
}

export interface RecurringExpenseUpdate {
  name?: string;
  amount?: number;
  category_id?: string;
  frequency?: "weekly" | "monthly";
  due_day?: number;
  is_active?: boolean;
}

// Statistics types
export interface CategoryBreakdown {
  category_id: string;
  category_name: string;
  category_icon: string | null;
  total: number;
  percentage: number;
  count: number;
}

export interface DailyTotal {
  date: string;
  total: number;
}

export interface StatsSummary {
  period: "weekly" | "monthly";
  start_date: string;
  end_date: string;
  total_spent: number;
  by_category: CategoryBreakdown[];
  daily_totals: DailyTotal[];
}

export interface UpcomingReminder {
  id: string;
  name: string;
  amount: number;
  due_date: string;
  days_until: number;
  category: { name: string; icon: string | null };
}

// Pagination types
export interface PaginationInfo {
  page: number;
  limit: number;
  total_items: number;
  total_pages: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: PaginationInfo;
}

// API Response types
export interface CategoriesResponse {
  categories: Category[];
}

export interface ExpenseListResponse {
  expenses: Expense[];
  pagination: PaginationInfo;
}

export interface RecurringListResponse {
  recurring_expenses: RecurringExpense[];
}

export interface UpcomingResponse {
  upcoming: UpcomingReminder[];
}

// Budget types
export interface Budget {
  id: string;
  category: { id: string; name: string; icon: string | null };
  amount: number;
  month: number;
  year: number;
  spent: number;
  percentage: number;
  created_at: string;
}

export interface BudgetCreate {
  category_id: string;
  amount: number;
  month: number;
  year: number;
}

export interface BudgetUpdate {
  amount?: number;
}

export interface BudgetListResponse {
  budgets: Budget[];
}

export interface BudgetSummary {
  total_budget: number;
  total_spent: number;
  percentage: number;
  budgets: Budget[];
}
