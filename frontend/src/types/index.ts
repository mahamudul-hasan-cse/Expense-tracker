// Auth types
export interface User {
  id: string;
  email: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: User;
}

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

export interface CategoryUpdate {
  name?: string;
  icon?: string | null;
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

// Recurring items: bills (kind "expense") and income such as a salary (kind "income")
export type RecurringKind = "expense" | "income";

export interface RecurringExpense {
  id: string;
  kind: RecurringKind;
  name: string;
  amount: number;
  /** Set for kind "expense" */
  category: Category | null;
  /** Set for kind "income" */
  income_category: Category | null;
  frequency: "weekly" | "monthly";
  due_day: number;
  is_active: boolean;
  last_paid_on: string | null;
  next_due: string;
}

export interface RecurringExpenseCreate {
  kind?: RecurringKind;
  name: string;
  amount: number;
  category_id?: string;
  income_category_id?: string;
  frequency: "weekly" | "monthly";
  due_day: number;
}

export interface RecurringExpenseUpdate {
  name?: string;
  amount?: number;
  category_id?: string;
  income_category_id?: string;
  frequency?: "weekly" | "monthly";
  due_day?: number;
  is_active?: boolean;
}

export interface MarkPaidResponse {
  recurring: RecurringExpense;
  record_type: RecurringKind;
  record_id: string;
}

// Income types (income categories have the same shape as expense categories)
export interface Income {
  id: string;
  amount: number;
  category: Category;
  note: string | null;
  income_date: string; // "YYYY-MM-DD"
  created_at: string;
}

export interface IncomeCreate {
  amount: number;
  income_category_id: string;
  note?: string;
  income_date?: string;
}

export interface IncomeUpdate {
  amount?: number;
  income_category_id?: string;
  note?: string | null;
  income_date?: string;
}

export interface IncomeListResponse {
  incomes: Income[];
  pagination: PaginationInfo;
}

export interface IncomeCategoriesResponse {
  income_categories: Category[];
  pagination: PaginationInfo;
}

// Cashflow: saved = income - spent; goal contributions never change it
export interface Cashflow {
  month: string; // "YYYY-MM"
  start_date: string;
  end_date: string;
  income: number;
  spent: number;
  saved: number;
  /** null when there was no income */
  savings_rate: number | null;
  allocated_to_goals: number;
  unallocated: number;
}

// Savings goals
export type GoalState = "completed" | "no_deadline" | "overdue" | "on_track" | "behind";

export interface Goal {
  id: string;
  name: string;
  icon: string | null;
  target_amount: number;
  target_date: string | null;
  status: "active" | "archived";
  created_at: string;
  saved: number;
  remaining: number;
  progress_pct: number;
  state: GoalState;
  on_track: boolean | null;
  months_left: number | null;
  required_per_month: number | null;
}

export interface GoalCreate {
  name: string;
  icon?: string;
  target_amount: number;
  target_date?: string;
}

export interface GoalUpdate {
  name?: string;
  icon?: string | null;
  target_amount?: number;
  target_date?: string | null;
  status?: "active" | "archived";
}

export interface GoalListResponse {
  goals: Goal[];
  pagination: PaginationInfo;
}

export interface ContributionCreate {
  /** Negative = withdrawal */
  amount: number;
  contributed_on?: string;
  note?: string;
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
  kind: RecurringKind;
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
  pagination: PaginationInfo;
}

export interface ExpenseListResponse {
  expenses: Expense[];
  pagination: PaginationInfo;
}

export interface RecurringListResponse {
  recurring_expenses: RecurringExpense[];
  pagination: PaginationInfo;
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
  pagination: PaginationInfo;
}

export interface BudgetSummary {
  total_budget: number;
  total_spent: number;
  percentage: number;
  budgets: Budget[];
}

// Assistant
export type AssistantUnavailableReason =
  "not_configured" | "disabled" | "daily_budget_reached" | "daily_limit";

export interface AssistantStatus {
  configured: boolean;
  enabled: boolean;
  available: boolean;
  reason: AssistantUnavailableReason | null;
  message: string | null;
  messages_today: number;
  daily_limit: number;
}

/** A quick-add suggestion from the assistant. Nothing is saved until the user confirms. */
export interface ExpenseProposal {
  amount: number;
  category_id: string;
  category_name: string;
  category_icon: string | null;
  expense_date: string;
  note: string | null;
}

export type ProposalStatus = "pending" | "confirmed" | "cancelled" | "expired";

export interface AssistantMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  proposal: ExpenseProposal | null;
  proposal_status: ProposalStatus | null;
  expense_id: string | null;
  status: "ok" | "interrupted" | "error";
  created_at: string;
}

export interface ConversationSummary {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationListResponse {
  conversations: ConversationSummary[];
  pagination: PaginationInfo;
}

export interface ConversationDetail extends ConversationSummary {
  messages: AssistantMessage[];
}
