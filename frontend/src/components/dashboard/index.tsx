"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { formatCurrency, formatDate } from "@/lib/utils";
import { format, parseISO } from "date-fns";
import { usePrefersReducedMotion } from "@/lib/use-reduced-motion";
import { Category, Expense } from "@/types";
import { DashboardSkeleton } from "@/components/shared/skeletons";
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
import { Plus, Edit2, ArrowRight, TrendingUp, Wallet, CalendarDays, Target } from "lucide-react";
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

export function Dashboard() {
  const [period, setPeriod] = useState<"weekly" | "monthly">("monthly");
  const reducedMotion = usePrefersReducedMotion();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<Category | null>(null);
  const [editingExpense, setEditingExpense] = useState<Expense | null>(null);

  // React Query hooks
  const { data: stats, isLoading: statsLoading } = useStats(period);
  const { data: categoriesData, isLoading: categoriesLoading } = useCategories();
  const { data: expensesData, isLoading: expensesLoading } = useExpenses({ limit: 5 });
  const { data: upcomingData, isLoading: upcomingLoading } = useUpcoming();

  const categories = categoriesData?.categories ?? [];
  const recentExpenses = expensesData?.expenses ?? [];
  const upcoming = upcomingData?.upcoming ?? [];

  const loading = statsLoading || categoriesLoading || expensesLoading || upcomingLoading;

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

  const handleQuickAdd = (category: Category) => {
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

  if (loading) {
    return <DashboardSkeleton />;
  }

  const pieData =
    stats?.by_category.map((cat) => ({
      name: cat.category_name,
      value: Number(cat.total),
      icon: cat.category_icon,
    })) || [];

  const barData =
    stats?.daily_totals.map((dt) => ({
      // Weekly: "Mon", "Tue"…; monthly: day of month
      date: format(parseISO(dt.date), period === "weekly" ? "EEE" : "d"),
      total: Number(dt.total),
    })) || [];

  const totalSpent = Number(stats?.total_spent || 0);
  // Per day so far this period (the whole period once it's over)
  const avgDaily = stats ? dailyAverage(totalSpent, stats.start_date, stats.end_date) : 0;
  const { bills: upcomingBills, income: upcomingIncome } = splitUpcoming(upcoming);

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">Track your spending and stay on budget</p>
        </div>
        <Tabs value={period} onValueChange={(v) => setPeriod(v as "weekly" | "monthly")}>
          <TabsList className="grid w-full grid-cols-2 md:w-[200px]">
            <TabsTrigger value="weekly">Weekly</TabsTrigger>
            <TabsTrigger value="monthly">Monthly</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="relative overflow-hidden">
          <div className="absolute right-0 top-0 h-24 w-24 translate-x-8 -translate-y-8 rounded-full bg-primary/10" />
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Spent</CardTitle>
            <div className="rounded-full bg-primary/10 p-2">
              <Wallet className="h-4 w-4 text-primary" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{formatCurrency(totalSpent)}</div>
            <p className="mt-1 text-xs text-muted-foreground">
              {period === "weekly" ? "This week" : "This month"}
            </p>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden">
          <div className="absolute right-0 top-0 h-24 w-24 translate-x-8 -translate-y-8 rounded-full bg-teal-500/10" />
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Daily Average
            </CardTitle>
            <div className="rounded-full bg-teal-500/10 p-2">
              <TrendingUp className="h-4 w-4 text-teal-500" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{formatCurrency(avgDaily)}</div>
            <p className="mt-1 text-xs text-muted-foreground">Per day so far</p>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden">
          <div className="absolute right-0 top-0 h-24 w-24 translate-x-8 -translate-y-8 rounded-full bg-amber-500/10" />
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Categories</CardTitle>
            <div className="rounded-full bg-amber-500/10 p-2">
              <Target className="h-4 w-4 text-amber-500" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{pieData.length}</div>
            <p className="mt-1 text-xs text-muted-foreground">
              With spending this {period === "weekly" ? "week" : "month"}
            </p>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden">
          <div className="absolute right-0 top-0 h-24 w-24 translate-x-8 -translate-y-8 rounded-full bg-rose-500/10" />
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Bills Due</CardTitle>
            <div className="rounded-full bg-rose-500/10 p-2">
              <CalendarDays className="h-4 w-4 text-rose-500" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{upcomingBills.length}</div>
            <p className="mt-1 text-xs text-muted-foreground">
              Within 7 days
              {upcomingIncome.length > 0 && ` · ${upcomingIncome.length} income expected`}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Income / Spent / Saved this month */}
      <CashflowRow />

      {/* AI weekly insight (only when the assistant is on) */}
      <InsightCard />

      {/* Charts Row */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Pie Chart */}
        <Card role="region" aria-label="Spending by Category">
          <CardHeader>
            <CardTitle>Spending by Category</CardTitle>
          </CardHeader>
          <CardContent>
            {pieData.length > 0 ? (
              <div className="flex flex-col items-center gap-6 lg:flex-row">
                <ResponsiveContainer width="100%" height={220}>
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
                    >
                      {pieData.map((_, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={CHART_COLORS[index % CHART_COLORS.length]}
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(value: number) => formatCurrency(value)}
                      contentStyle={{
                        borderRadius: "8px",
                        border: "1px solid hsl(var(--border))",
                        backgroundColor: "hsl(var(--card))",
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {pieData.slice(0, 6).map((item, index) => (
                    <div key={item.name} className="flex items-center gap-2">
                      <div
                        className="h-3 w-3 rounded-full"
                        style={{ backgroundColor: CHART_COLORS[index % CHART_COLORS.length] }}
                      />
                      <span className="truncate text-muted-foreground">{item.name}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="flex h-[220px] items-center justify-center text-muted-foreground">
                No spending data yet
              </div>
            )}
          </CardContent>
        </Card>

        {/* Bar Chart */}
        <Card role="region" aria-label="Daily Spending Trend">
          <CardHeader>
            <CardTitle>Daily Spending Trend</CardTitle>
          </CardHeader>
          <CardContent>
            {barData.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={barData}>
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
                    tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                    tickFormatter={(value) => `৳${value}`}
                  />
                  <Tooltip
                    formatter={(value: number) => formatCurrency(value)}
                    contentStyle={{
                      borderRadius: "8px",
                      border: "1px solid hsl(var(--border))",
                      backgroundColor: "hsl(var(--card))",
                    }}
                  />
                  <Bar
                    dataKey="total"
                    fill="hsl(var(--primary))"
                    radius={[6, 6, 0, 0]}
                    // Animating re-layouts (e.g. a resize) slid bars in from stale
                    // positions; users who ask for reduced motion get static charts
                    isAnimationActive={!reducedMotion}
                  />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-[220px] items-center justify-center text-muted-foreground">
                No spending data yet
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Budget Overview */}
      <div className="grid gap-6 lg:grid-cols-2">
        <BudgetOverview />
        <GoalsCard />
      </div>

      {/* Quick Add */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Add Expense</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {categories.map((category) => (
              <Button
                key={category.id}
                variant="outline"
                onClick={() => handleQuickAdd(category)}
                className="gap-2 transition-all hover:border-primary hover:bg-primary/5"
              >
                <span className="text-lg">{category.icon}</span>
                {category.name}
              </Button>
            ))}
            <Button
              onClick={() => {
                setSelectedCategory(null);
                setEditingExpense(null);
                setDialogOpen(true);
              }}
              className="gap-2"
            >
              <Plus className="h-4 w-4" />
              New Expense
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Bottom Row */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Upcoming Reminders */}
        <Card role="region" aria-label="Upcoming bills and income">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Upcoming Bills &amp; Income</CardTitle>
            <Link href="/settings">
              <Button variant="ghost" size="sm" className="gap-1 text-muted-foreground">
                Manage <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent>
            {upcoming.length > 0 ? (
              <div className="space-y-3">
                {upcoming.slice(0, 4).map((reminder) => (
                  <div
                    key={reminder.id}
                    className="flex items-center justify-between rounded-xl border bg-muted/30 p-4 transition-colors hover:bg-muted/50"
                  >
                    <div className="flex items-center gap-4">
                      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-background text-2xl shadow-sm">
                        {reminder.category.icon}
                      </div>
                      <div>
                        <p className="font-semibold">{reminder.name}</p>
                        <p className="text-sm text-muted-foreground">
                          {reminder.days_until === 0 ? (
                            <span className="text-rose-500 font-medium">Due today</span>
                          ) : (
                            `Due in ${reminder.days_until} day${reminder.days_until > 1 ? "s" : ""}`
                          )}
                        </p>
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <p
                        className={`text-lg font-bold ${reminder.kind === "income" ? "text-emerald-600 dark:text-emerald-400" : ""}`}
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
                        {reminder.kind === "income" ? "Mark received" : "Mark paid"}
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex h-[200px] items-center justify-center text-muted-foreground">
                Nothing due in the next 7 days
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Expenses */}
        <Card role="region" aria-label="Recent Expenses">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Recent Expenses</CardTitle>
            <Link href="/expenses">
              <Button variant="ghost" size="sm" className="gap-1 text-muted-foreground">
                View All <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent>
            {recentExpenses.length > 0 ? (
              <div className="space-y-3">
                {recentExpenses.map((expense) => (
                  <div
                    key={expense.id}
                    className="group flex items-center justify-between rounded-xl border bg-muted/30 p-4 transition-colors hover:bg-muted/50"
                  >
                    <div className="flex items-center gap-4">
                      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-background text-2xl shadow-sm">
                        {expense.category.icon}
                      </div>
                      <div>
                        <p className="font-semibold">{expense.category.name}</p>
                        <p className="text-sm text-muted-foreground">
                          {formatDate(expense.expense_date)}
                          {expense.note && ` · ${expense.note}`}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <p className="text-lg font-bold">{formatCurrency(Number(expense.amount))}</p>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleEdit(expense)}
                        aria-label={`Edit ${expense.category.name} expense, ${formatCurrency(Number(expense.amount))}`}
                        className="text-muted-foreground"
                      >
                        <Edit2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex h-[200px] items-center justify-center text-muted-foreground">
                No expenses yet
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
