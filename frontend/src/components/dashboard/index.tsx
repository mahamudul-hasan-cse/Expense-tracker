"use client";

import { ReactNode, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { formatCurrency, formatCurrencyCompact, formatDate } from "@/lib/utils";
import { format, parseISO } from "date-fns";
import { usePrefersReducedMotion } from "@/lib/use-reduced-motion";
import { Category, Expense } from "@/types";
import { DashboardSkeleton } from "@/components/shared/skeletons";
import { ErrorState } from "@/components/shared/error-state";
import { PageHeader } from "@/components/shared/page-header";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import {
  Plus,
  Edit2,
  ArrowRight,
  TrendingUp,
  Wallet,
  CalendarDays,
  Target,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import Link from "next/link";
import { ExpenseFormDialog } from "@/components/expenses/expense-form-dialog";
import {
  useStats,
  useCategories,
  useExpenses,
  useUpcoming,
  useMarkRecurringPaid,
} from "@/lib/queries";
import { useToast } from "@/hooks/use-toast";
import { UpcomingReminder } from "@/types";
import { dailyAverage, splitUpcoming } from "@/lib/stats";
import { BudgetOverview } from "./budget-overview";
import { CashflowRow } from "./cashflow-row";
import { GoalsCard } from "./goals-card";
import { InsightCard } from "@/components/assistant/insight-card";

const CHART_COLORS = [
  "hsl(262, 83%, 58%)",
  "hsl(173, 80%, 40%)",
  "hsl(38, 92%, 50%)",
  "hsl(0, 84%, 60%)",
  "hsl(220, 70%, 50%)",
  "hsl(280, 65%, 60%)",
  "hsl(142, 76%, 36%)",
  "hsl(340, 75%, 55%)",
];

// Readable in light and dark mode (Recharts' default tooltip text is black)
const TOOLTIP_PROPS = {
  contentStyle: {
    borderRadius: "8px",
    border: "1px solid hsl(var(--border))",
    backgroundColor: "hsl(var(--popover))",
    color: "hsl(var(--popover-foreground))",
  },
  labelStyle: { color: "hsl(var(--popover-foreground))", fontWeight: 600 },
  itemStyle: { color: "hsl(var(--popover-foreground))" },
  cursor: { fill: "hsl(var(--muted))", opacity: 0.6 },
};

const LEGEND_ITEMS = 6;
const QUICK_ADD_SHOWN = 5;

export function Dashboard() {
  const [period, setPeriod] = useState<"weekly" | "monthly">("monthly");
  const reducedMotion = usePrefersReducedMotion();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<Category | null>(null);
  const [editingExpense, setEditingExpense] = useState<Expense | null>(null);
  const [showAllCategories, setShowAllCategories] = useState(false);

  const statsQuery = useStats(period);
  const categoriesQuery = useCategories();
  const expensesQuery = useExpenses({ limit: 5 });
  const upcomingQuery = useUpcoming();
  const queries = [statsQuery, categoriesQuery, expensesQuery, upcomingQuery];

  const stats = statsQuery.data;
  const categories = categoriesQuery.data?.categories ?? [];
  const recentExpenses = expensesQuery.data?.expenses ?? [];
  const upcoming = upcomingQuery.data?.upcoming ?? [];

  const { toast } = useToast();
  const markPaid = useMarkRecurringPaid();
  const handleMarkPaid = (reminder: UpcomingReminder) => {
    markPaid.mutate(reminder.id, {
      onSuccess: () =>
        toast({
          title: "Success",
          description:
            reminder.kind === "income"
              ? `${reminder.name} recorded as income`
              : `${reminder.name} recorded as an expense`,
        }),
      onError: (error) =>
        toast({ title: "Error", description: error.message, variant: "destructive" }),
    });
  };

  const openNewExpense = (category: Category | null = null) => {
    setSelectedCategory(category);
    setEditingExpense(null);
    setDialogOpen(true);
  };

  const handleEdit = (expense: Expense) => {
    setEditingExpense(expense);
    setSelectedCategory(null);
    setDialogOpen(true);
  };

  const handleDialogClose = () => {
    setDialogOpen(false);
    setSelectedCategory(null);
    setEditingExpense(null);
  };

  if (queries.some((q) => q.isError)) {
    return (
      <div className="space-y-6">
        <PageHeader title="Dashboard" description="Track your spending and stay on budget" />
        <ErrorState
          message="Couldn't load your dashboard."
          onRetry={() => queries.filter((q) => q.isError).forEach((q) => q.refetch())}
        />
      </div>
    );
  }

  if (queries.some((q) => q.isLoading)) {
    return <DashboardSkeleton />;
  }

  const totalSpent = Number(stats?.total_spent || 0);
  const pieData =
    stats?.by_category.map((cat) => ({
      name: cat.category_name,
      value: Number(cat.total),
      share: totalSpent > 0 ? (Number(cat.total) / totalSpent) * 100 : 0,
    })) || [];

  const barData =
    stats?.daily_totals.map((dt) => ({
      // Weekly: "Mon", "Tue"…; monthly: day of month
      date: format(parseISO(dt.date), period === "weekly" ? "EEE" : "d"),
      total: Number(dt.total),
    })) || [];
  const hasSpending = barData.some((d) => d.total > 0);
  // Text alternative for the bar chart (screen readers)
  const peak = barData.reduce((max, d) => (d.total > max.total ? d : max), {
    date: "",
    total: 0,
  });
  const dailySummary = `Spending per day this ${period === "weekly" ? "week" : "month"}: ${formatCurrency(
    totalSpent
  )} in total, highest ${formatCurrency(peak.total)} on ${period === "weekly" ? peak.date : `day ${peak.date}`}.`;

  // Per day so far this period (the whole period once it's over)
  const avgDaily = stats ? dailyAverage(totalSpent, stats.start_date, stats.end_date) : 0;
  const { bills: upcomingBills, income: upcomingIncome } = splitUpcoming(upcoming);
  const periodWord = period === "weekly" ? "week" : "month";

  // Quick add: the categories used most this period first, then the rest
  const spentNames = pieData.map((p) => p.name);
  const orderedCategories = [
    ...spentNames
      .map((name) => categories.find((c) => c.name === name))
      .filter((c): c is Category => !!c),
    ...categories.filter((c) => !spentNames.includes(c.name)),
  ];
  const quickCategories = showAllCategories
    ? orderedCategories
    : orderedCategories.slice(0, QUICK_ADD_SHOWN);
  const hiddenCount = orderedCategories.length - QUICK_ADD_SHOWN;

  const emptyChart = (
    <div className="flex h-[220px] flex-col items-center justify-center gap-3 text-center text-muted-foreground">
      <p>No spending this {periodWord} yet.</p>
      <Button size="sm" variant="outline" onClick={() => openNewExpense()}>
        Add an expense
      </Button>
    </div>
  );

  return (
    <div className="space-y-6 sm:space-y-8">
      <PageHeader
        title="Dashboard"
        description="Track your spending and stay on budget"
        actions={
          // A two-button toggle, not tabs: there are no separate tab panels
          <div
            role="group"
            aria-label="Period"
            className="grid w-full grid-cols-2 rounded-lg bg-muted p-1 sm:w-[200px]"
          >
            {(["weekly", "monthly"] as const).map((p) => (
              <button
                key={p}
                type="button"
                aria-pressed={period === p}
                onClick={() => setPeriod(p)}
                className={`rounded-md px-3 py-1.5 text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                  period === p
                    ? "bg-background text-foreground shadow-sm"
                    : "text-foreground/75 hover:text-foreground"
                }`}
              >
                {p === "weekly" ? "Weekly" : "Monthly"}
              </button>
            ))}
          </div>
        }
      />

      {/* 2×2 on phones so "This month" is reachable without a long scroll */}
      <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
        <StatCard
          title="Total Spent"
          value={formatCurrency(totalSpent)}
          hint={period === "weekly" ? "This week" : "This month"}
          icon={<Wallet className="h-4 w-4 text-primary" />}
          tint="bg-primary/10"
        />
        <StatCard
          title="Daily Average"
          value={formatCurrency(avgDaily)}
          hint="Per day so far"
          icon={<TrendingUp className="h-4 w-4 text-teal-600 dark:text-teal-400" />}
          tint="bg-teal-500/10"
        />
        <StatCard
          title="Categories"
          value={String(pieData.length)}
          hint={`With spending this ${periodWord}`}
          icon={<Target className="h-4 w-4 text-amber-700 dark:text-amber-400" />}
          tint="bg-amber-500/10"
        />
        <StatCard
          title="Bills Due"
          value={String(upcomingBills.length)}
          hint={`Within 7 days${upcomingIncome.length > 0 ? ` · ${upcomingIncome.length} income expected` : ""}`}
          icon={<CalendarDays className="h-4 w-4 text-rose-700 dark:text-rose-400" />}
          tint="bg-rose-500/10"
        />
      </div>

      {/* Income / Spent / Saved this month */}
      <CashflowRow />

      {/* AI weekly insight (only when the assistant is on) */}
      <InsightCard />

      {/* Charts Row */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card role="region" aria-label="Spending by Category">
          <CardHeader>
            <CardTitle>Spending by Category</CardTitle>
          </CardHeader>
          <CardContent>
            {pieData.length > 0 ? (
              <div className="flex flex-col items-center gap-6 sm:flex-row">
                {/* The legend next to it carries the same information as text */}
                <div className="h-[220px] w-full min-w-0 sm:flex-1" aria-hidden>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={pieData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={90}
                        paddingAngle={2}
                        dataKey="value"
                        isAnimationActive={!reducedMotion}
                        // Not keyboard-focusable: the chart is hidden from assistive tech
                        // and the legend beside it has the same information as text
                        rootTabIndex={-1}
                      >
                        {pieData.map((_, index) => (
                          <Cell
                            key={`cell-${index}`}
                            fill={CHART_COLORS[index % CHART_COLORS.length]}
                          />
                        ))}
                      </Pie>
                      <Tooltip {...TOOLTIP_PROPS} formatter={(v: number) => formatCurrency(v)} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                {/* Full names (no truncation), the top 6, and how many more */}
                <ul className="w-full space-y-1.5 text-sm sm:w-48 sm:shrink-0">
                  {pieData.slice(0, LEGEND_ITEMS).map((item, index) => (
                    <li key={item.name} className="flex items-center gap-2">
                      <span
                        className="h-3 w-3 shrink-0 rounded-full"
                        style={{ backgroundColor: CHART_COLORS[index % CHART_COLORS.length] }}
                        aria-hidden
                      />
                      <span className="min-w-0 flex-1 break-words">{item.name}</span>
                      <span className="tabular-nums text-muted-foreground">
                        {item.share.toFixed(0)}%
                      </span>
                    </li>
                  ))}
                  {pieData.length > LEGEND_ITEMS && (
                    <li className="pl-5 text-muted-foreground">
                      +{pieData.length - LEGEND_ITEMS} more
                    </li>
                  )}
                </ul>
              </div>
            ) : (
              emptyChart
            )}
          </CardContent>
        </Card>

        <Card role="region" aria-label="Daily Spending Trend">
          <CardHeader>
            <CardTitle>Daily Spending Trend</CardTitle>
          </CardHeader>
          <CardContent>
            {hasSpending ? (
              <>
                <p className="sr-only">{dailySummary}</p>
                <div aria-hidden>
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={barData} margin={{ left: 4, right: 4 }}>
                      <CartesianGrid
                        strokeDasharray="3 3"
                        vertical={false}
                        stroke="hsl(var(--border))"
                      />
                      <XAxis
                        dataKey="date"
                        axisLine={false}
                        tickLine={false}
                        tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                      />
                      <YAxis
                        axisLine={false}
                        tickLine={false}
                        width={48}
                        tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                        tickFormatter={(value: number) => formatCurrencyCompact(value)}
                      />
                      <Tooltip {...TOOLTIP_PROPS} formatter={(v: number) => formatCurrency(v)} />
                      <Bar
                        dataKey="total"
                        name="Spent"
                        fill="hsl(var(--primary))"
                        radius={[6, 6, 0, 0]}
                        // Animating re-layouts (e.g. a resize) slid bars in from stale
                        // positions; users who ask for reduced motion get static charts
                        isAnimationActive={!reducedMotion}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </>
            ) : (
              emptyChart
            )}
          </CardContent>
        </Card>
      </div>

      {/* Budget Overview */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <BudgetOverview />
        <GoalsCard />
      </div>

      {/* Quick Add: the most-used categories, the rest behind "More" */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Add Expense</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2" id="quick-add-categories">
            {quickCategories.map((category) => (
              <Button
                key={category.id}
                variant="outline"
                onClick={() => openNewExpense(category)}
                className="gap-2 transition-all hover:border-primary hover:bg-primary/5"
              >
                <span className="text-lg" aria-hidden>
                  {category.icon}
                </span>
                {category.name}
              </Button>
            ))}
            {hiddenCount > 0 && (
              <Button
                variant="ghost"
                onClick={() => setShowAllCategories((v) => !v)}
                aria-expanded={showAllCategories}
                aria-controls="quick-add-categories"
                className="gap-1 text-muted-foreground"
              >
                {showAllCategories ? (
                  <>
                    Fewer <ChevronUp className="h-4 w-4" />
                  </>
                ) : (
                  <>
                    More ({hiddenCount}) <ChevronDown className="h-4 w-4" />
                  </>
                )}
              </Button>
            )}
            <Button onClick={() => openNewExpense()} className="gap-2">
              <Plus className="h-4 w-4" />
              New Expense
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card role="region" aria-label="Upcoming bills and income">
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <CardTitle>Upcoming Bills &amp; Income</CardTitle>
            <Button asChild variant="ghost" size="sm" className="gap-1 text-muted-foreground">
              <Link href="/settings">
                Manage <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent>
            {upcoming.length > 0 ? (
              <ul className="space-y-3">
                {upcoming.slice(0, 4).map((reminder) => (
                  <li
                    key={reminder.id}
                    className="flex items-center gap-3 rounded-xl border bg-muted/30 p-3 sm:gap-4 sm:p-4"
                  >
                    <span
                      className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-background text-2xl shadow-sm"
                      aria-hidden
                    >
                      {reminder.category.icon}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-semibold">{reminder.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {reminder.days_until === 0 ? (
                          <span className="font-medium text-rose-700 dark:text-rose-400">
                            Due today
                          </span>
                        ) : (
                          `Due in ${reminder.days_until} day${reminder.days_until > 1 ? "s" : ""}`
                        )}
                      </p>
                    </div>
                    <div className="flex shrink-0 flex-col items-end gap-1">
                      <p
                        className={`font-bold tabular-nums sm:text-lg ${reminder.kind === "income" ? "text-emerald-700 dark:text-emerald-400" : ""}`}
                      >
                        {reminder.kind === "income" ? "+" : ""}
                        {formatCurrency(Number(reminder.amount))}
                      </p>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleMarkPaid(reminder)}
                        disabled={markPaid.isPending}
                        aria-label={`${reminder.kind === "income" ? "Mark received" : "Mark paid"}: ${reminder.name}`}
                      >
                        {/* Short on phones so the name keeps room; the full name is the aria-label */}
                        <span className="sm:hidden">
                          {reminder.kind === "income" ? "Received" : "Paid"}
                        </span>
                        <span className="hidden sm:inline">
                          {reminder.kind === "income" ? "Mark received" : "Mark paid"}
                        </span>
                      </Button>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="flex h-[200px] flex-col items-center justify-center gap-3 text-center text-muted-foreground">
                <p>Nothing due in the next 7 days.</p>
                <Button asChild size="sm" variant="outline">
                  <Link href="/settings">Add a recurring bill or income</Link>
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        <Card role="region" aria-label="Recent Expenses">
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <CardTitle>Recent Expenses</CardTitle>
            <Button asChild variant="ghost" size="sm" className="gap-1 text-muted-foreground">
              <Link href="/expenses">
                View All <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent>
            {recentExpenses.length > 0 ? (
              <ul className="space-y-3">
                {recentExpenses.map((expense) => (
                  <li
                    key={expense.id}
                    className="flex items-center gap-3 rounded-xl border bg-muted/30 p-3 sm:gap-4 sm:p-4"
                  >
                    <span
                      className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-background text-2xl shadow-sm"
                      aria-hidden
                    >
                      {expense.category.icon}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-semibold">{expense.category.name}</p>
                      <p className="truncate text-sm text-muted-foreground">
                        {formatDate(expense.expense_date)}
                        {expense.note && ` · ${expense.note}`}
                      </p>
                    </div>
                    {/* Fixed right column: amounts line up on every row */}
                    <p className="shrink-0 text-right font-bold tabular-nums sm:text-lg">
                      {formatCurrency(Number(expense.amount))}
                    </p>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleEdit(expense)}
                      aria-label={`Edit ${expense.category.name} expense, ${formatCurrency(Number(expense.amount))}`}
                      className="shrink-0 text-muted-foreground"
                    >
                      <Edit2 className="h-4 w-4" />
                    </Button>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="flex h-[200px] flex-col items-center justify-center gap-3 text-center text-muted-foreground">
                <p>No expenses yet.</p>
                <Button size="sm" onClick={() => openNewExpense()}>
                  Add your first expense
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <ExpenseFormDialog
        open={dialogOpen}
        onClose={handleDialogClose}
        categories={categories}
        expense={editingExpense}
        preselectedCategory={selectedCategory}
      />
    </div>
  );
}

function StatCard({
  title,
  value,
  hint,
  icon,
  tint,
}: {
  title: string;
  value: string;
  hint: string;
  icon: ReactNode;
  tint: string;
}) {
  return (
    <Card className="relative overflow-hidden">
      <div
        className={`absolute right-0 top-0 hidden h-24 w-24 -translate-y-8 translate-x-8 rounded-full sm:block ${tint}`}
        aria-hidden
      />
      <CardHeader className="flex flex-row items-center justify-between space-y-0 p-4 pb-1 sm:p-6 sm:pb-2">
        <CardTitle className="text-xs font-medium text-muted-foreground sm:text-sm">
          {title}
        </CardTitle>
        <div className={`hidden rounded-full p-2 sm:block ${tint}`} aria-hidden>
          {icon}
        </div>
      </CardHeader>
      <CardContent className="p-4 pt-0 sm:p-6 sm:pt-0">
        <div className="text-xl font-bold tabular-nums sm:text-3xl">{value}</div>
        <p className="mt-1 text-xs text-muted-foreground">{hint}</p>
      </CardContent>
    </Card>
  );
}
