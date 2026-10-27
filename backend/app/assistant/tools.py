"""Read-only tools the assistant can call. Every number comes from SQL/Python here.

Security model:
- user_id is bound on the server (ToolContext) and is never a tool argument.
  Argument models forbid unknown fields, so a model can't even pass one.
- Arguments are validated and clamped (dates, ranges, limits, string lengths).
- Free text written by users (notes, names) is truncated and returned as data;
  the system prompt tells the model never to follow instructions found in it.
- propose_expense never writes: it validates and returns a proposal that the
  user must confirm in the UI (saved through the normal expense endpoint).
"""

import calendar
import json
import statistics
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Callable, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.budget import Budget
from app.models.category import Category
from app.models.expense import Expense
from app.models.goal import SavingsGoal
from app.models.income import IncomeCategory
from app.models.recurring import RecurringExpense
from app.routers.budgets import spent_by_category
from app.routers.recurring import next_unpaid_due
from app.services.cashflow import get_cashflow, month_bounds
from app.services.goals import compute_progress, saved_by_goal

MIN_DATE = date(2015, 1, 1)
MAX_RANGE_DAYS = 366
MAX_DAY_GROUPING = 62
MAX_LIST_LIMIT = 50
MAX_TEXT = 100
MAX_AMOUNT = Decimal("99999999.99")


@dataclass(frozen=True)
class ToolContext:
    db: Session
    user_id: UUID
    today: date


class ToolArgError(Exception):
    """A valid call with unusable values (e.g. a range too long). Reported to the model."""


class _Args(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- Helpers -------------------------------------------------------------------------


def _num(value: Decimal | float | int) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _pct(part: Decimal, whole: Decimal) -> Optional[float]:
    if whole == 0:
        return None
    return round(float(part / whole * 100), 1)


def _text(value: Optional[str]) -> Optional[str]:
    """User-written text as plain data: single line, truncated."""
    if value is None:
        return None
    flat = " ".join(value.split())
    return flat[:MAX_TEXT] + ("…" if len(flat) > MAX_TEXT else "")


def _range(start: date, end: date, ctx: ToolContext) -> tuple[date, date, list[str]]:
    notes: list[str] = []
    if end > ctx.today:
        end = ctx.today
        notes.append(f"end_date clamped to today ({ctx.today})")
    if start < MIN_DATE:
        start = MIN_DATE
        notes.append(f"start_date clamped to {MIN_DATE}")
    if start > end:
        raise ToolArgError("start_date must be on or before end_date (and not in the future)")
    if (end - start).days + 1 > MAX_RANGE_DAYS:
        raise ToolArgError(f"date ranges are limited to {MAX_RANGE_DAYS} days; split the question into smaller periods")
    return start, end, notes


def _resolve_category(ctx: ToolContext, name: str) -> Category:
    """Find one of the user's expense categories by name (case-insensitive, then unique prefix/substring)."""
    cats = ctx.db.query(Category).filter(Category.user_id == ctx.user_id).all()
    wanted = name.strip().lower()
    exact = [c for c in cats if c.name.lower() == wanted]
    if exact:
        return exact[0]
    partial = [c for c in cats if wanted and (wanted in c.name.lower() or c.name.lower() in wanted)]
    if len(partial) == 1:
        return partial[0]
    raise ToolArgError(
        f"no single category matches {name!r}; the user's categories are: " + ", ".join(sorted(c.name for c in cats))
    )


def _expense_totals(ctx: ToolContext, start: date, end: date) -> tuple[Decimal, int]:
    total, count = (
        ctx.db.query(func.coalesce(func.sum(Expense.amount), 0), func.count(Expense.id))
        .filter(Expense.user_id == ctx.user_id, Expense.expense_date >= start, Expense.expense_date <= end)
        .one()
    )
    return Decimal(total), int(count)


def _by_category(ctx: ToolContext, start: date, end: date) -> dict[str, dict[str, Any]]:
    rows = (
        ctx.db.query(Category.name, Category.icon, func.sum(Expense.amount), func.count(Expense.id))
        .join(Category, Category.id == Expense.category_id)
        .filter(Expense.user_id == ctx.user_id, Expense.expense_date >= start, Expense.expense_date <= end)
        .group_by(Category.name, Category.icon)
        .all()
    )
    return {name: {"icon": icon, "total": Decimal(total), "count": int(count)} for name, icon, total, count in rows}


CATCH_ALL_CATEGORIES = {"random", "other", "others", "misc", "miscellaneous", "general"}
CATCH_ALL_ENTRIES = 6


def _largest_entries(ctx: ToolContext, category: str, start: date, end: date) -> list[dict[str, Any]]:
    rows = (
        ctx.db.query(Expense.amount, Expense.note, Expense.expense_date)
        .join(Category, Category.id == Expense.category_id)
        .filter(
            Expense.user_id == ctx.user_id,
            Category.name == category,
            Expense.expense_date >= start,
            Expense.expense_date <= end,
        )
        .order_by(Expense.amount.desc(), Expense.expense_date.desc())
        .limit(CATCH_ALL_ENTRIES)
        .all()
    )
    return [{"amount": _num(a), "note": _text(n), "date": str(d)} for a, n, d in rows]


# --- Tools -----------------------------------------------------------------------------


class SpendingSummaryArgs(_Args):
    start_date: date
    end_date: date
    group_by: Literal["category", "day", "week", "month"] = "category"


def get_spending_summary(ctx: ToolContext, args: SpendingSummaryArgs) -> dict[str, Any]:
    start, end, notes = _range(args.start_date, args.end_date, ctx)
    total, count = _expense_totals(ctx, start, end)
    days = (end - start).days + 1
    result: dict[str, Any] = {
        "start_date": str(start),
        "end_date": str(end),
        "days": days,
        "total": _num(total),
        "expense_count": count,
        "daily_average": _num(total / days),
    }
    if args.group_by == "category":
        groups = sorted(_by_category(ctx, start, end).items(), key=lambda kv: kv[1]["total"], reverse=True)
        result["by_category"] = [
            {
                "category": n,
                "icon": g["icon"],
                "total": _num(g["total"]),
                "share_pct": _pct(g["total"], total),
                "count": g["count"],
            }
            for n, g in groups
        ]
        # Catch-all categories hide where money goes; include their largest entries now so
        # the model can suggest a split without a second round of tool calls.
        for item in result["by_category"]:
            if item["category"].strip().lower() in CATCH_ALL_CATEGORIES:
                item["largest_entries"] = _largest_entries(ctx, item["category"], start, end)
    else:
        if args.group_by == "day" and days > MAX_DAY_GROUPING:
            raise ToolArgError(f"group_by=day is limited to {MAX_DAY_GROUPING} days; use week or month")
        bucket = func.date_trunc(args.group_by, Expense.expense_date)
        rows = (
            ctx.db.query(bucket, func.sum(Expense.amount), func.count(Expense.id))
            .filter(Expense.user_id == ctx.user_id, Expense.expense_date >= start, Expense.expense_date <= end)
            .group_by(bucket)
            .order_by(bucket)
            .all()
        )
        result[f"by_{args.group_by}"] = [
            {"period_start": str(b.date()), "total": _num(t), "count": int(c)} for b, t, c in rows
        ]
    if notes:
        result["notes"] = notes
    return result


class Period(_Args):
    start_date: date
    end_date: date


class ComparePeriodsArgs(_Args):
    period_a: Period = Field(description="Baseline period, usually the earlier one")
    period_b: Period = Field(description="Period compared against the baseline")


def compare_periods(ctx: ToolContext, args: ComparePeriodsArgs) -> dict[str, Any]:
    a_start, a_end, notes_a = _range(args.period_a.start_date, args.period_a.end_date, ctx)
    b_start, b_end, notes_b = _range(args.period_b.start_date, args.period_b.end_date, ctx)
    a_total, a_count = _expense_totals(ctx, a_start, a_end)
    b_total, b_count = _expense_totals(ctx, b_start, b_end)
    a_cats, b_cats = _by_category(ctx, a_start, a_end), _by_category(ctx, b_start, b_end)
    deltas: list[dict[str, Any]] = []
    for name in set(a_cats) | set(b_cats):
        a = a_cats.get(name, {}).get("total", Decimal("0"))
        b = b_cats.get(name, {}).get("total", Decimal("0"))
        deltas.append(
            {
                "category": name,
                "period_a": _num(a),
                "period_b": _num(b),
                "change": _num(b - a),
                "change_pct": _pct(b - a, a),
            }
        )
    deltas.sort(key=lambda d: abs(d["change"]), reverse=True)
    result: dict[str, Any] = {
        "period_a": {
            "start_date": str(a_start),
            "end_date": str(a_end),
            "total": _num(a_total),
            "expense_count": a_count,
            "days": (a_end - a_start).days + 1,
        },
        "period_b": {
            "start_date": str(b_start),
            "end_date": str(b_end),
            "total": _num(b_total),
            "expense_count": b_count,
            "days": (b_end - b_start).days + 1,
        },
        "change": _num(b_total - a_total),
        "change_pct": _pct(b_total - a_total, a_total),
        "biggest_category_changes": deltas[:8],
    }
    if notes_a or notes_b:
        result["notes"] = notes_a + notes_b
    return result


class ListExpensesArgs(_Args):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    category: Optional[str] = Field(None, max_length=100)
    min_amount: Optional[Decimal] = Field(None, ge=0)
    max_amount: Optional[Decimal] = Field(None, ge=0)
    search: Optional[str] = Field(None, max_length=100, description="Text to find in expense notes")
    sort: Literal["date_desc", "amount_desc"] = "date_desc"
    limit: int = Field(20, ge=1)


def list_expenses(ctx: ToolContext, args: ListExpensesArgs) -> dict[str, Any]:
    start, end, notes = _range(args.start_date or ctx.today - timedelta(days=89), args.end_date or ctx.today, ctx)
    limit = min(args.limit, MAX_LIST_LIMIT)
    if args.limit > MAX_LIST_LIMIT:
        notes.append(f"limit clamped to {MAX_LIST_LIMIT}")
    query = (
        ctx.db.query(Expense, Category)
        .join(Category, Category.id == Expense.category_id)
        .filter(Expense.user_id == ctx.user_id, Expense.expense_date >= start, Expense.expense_date <= end)
    )
    if args.category:
        query = query.filter(Expense.category_id == _resolve_category(ctx, args.category).id)
    if args.min_amount is not None:
        query = query.filter(Expense.amount >= args.min_amount)
    if args.max_amount is not None:
        query = query.filter(Expense.amount <= args.max_amount)
    if args.search:
        escaped = args.search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.filter(Expense.note.ilike(f"%{escaped}%", escape="\\"))
    matching = query.count()
    order = Expense.amount.desc() if args.sort == "amount_desc" else Expense.expense_date.desc()
    rows = query.order_by(order, Expense.created_at.desc()).limit(limit).all()
    result: dict[str, Any] = {
        "start_date": str(start),
        "end_date": str(end),
        "matching_count": matching,
        "returned": len(rows),
        "expenses": [
            {"date": str(e.expense_date), "amount": _num(e.amount), "category": c.name, "note": _text(e.note)}
            for e, c in rows
        ],
    }
    if notes:
        result["notes"] = notes
    return result


class BudgetsStatusArgs(_Args):
    month: Optional[str] = Field(None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="YYYY-MM; default current month")


def get_budgets_status(ctx: ToolContext, args: BudgetsStatusArgs) -> dict[str, Any]:
    label, start, end = month_bounds(args.month or f"{ctx.today:%Y-%m}")
    if start > ctx.today:
        raise ToolArgError("that month hasn't started yet")
    current = start <= ctx.today <= end
    days_in_month = calendar.monthrange(start.year, start.month)[1]
    days_elapsed = (ctx.today - start).days + 1 if current else days_in_month
    budgets = (
        ctx.db.query(Budget, Category)
        .join(Category, Category.id == Budget.category_id)
        .filter(Budget.user_id == ctx.user_id, Budget.month == start.month, Budget.year == start.year)
        .all()
    )
    spent = spent_by_category(ctx.db, ctx.user_id, start.month, start.year)
    items = []
    for budget, category in budgets:
        s = spent.get(budget.category_id, Decimal("0"))
        projected = s / days_elapsed * days_in_month if current else s
        items.append(
            {
                "category": category.name,
                "limit": _num(budget.amount),
                "spent": _num(s),
                "used_pct": _pct(s, budget.amount),
                "remaining": _num(budget.amount - s),
                "projected_month_end": _num(projected),
                "over_budget": s > budget.amount,
                "at_risk": s > budget.amount or projected > budget.amount,
            }
        )
    items.sort(key=lambda i: i["used_pct"] or 0, reverse=True)
    total_limit = sum((b.amount for b, _ in budgets), Decimal("0"))
    total_spent = sum((spent.get(b.category_id, Decimal("0")) for b, _ in budgets), Decimal("0"))
    return {
        "month": label,
        "days_elapsed": days_elapsed,
        "days_in_month": days_in_month,
        "budgets": items,
        "total_limit": _num(total_limit),
        "total_spent_in_budgeted_categories": _num(total_spent),
        "note": None if items else "No budgets are set for this month.",
    }


class RecurringArgs(_Args):
    status: Literal["active", "paused", "all"] = "active"
    kind: Literal["expense", "income", "all"] = "all"


def get_recurring_items(ctx: ToolContext, args: RecurringArgs) -> dict[str, Any]:
    query = ctx.db.query(RecurringExpense).filter(RecurringExpense.user_id == ctx.user_id)
    if args.status != "all":
        query = query.filter(RecurringExpense.is_active.is_(args.status == "active"))
    if args.kind != "all":
        query = query.filter(RecurringExpense.kind == args.kind)
    items: list[dict[str, Any]] = []
    monthly = {"expense": Decimal("0"), "income": Decimal("0")}
    for rec in query.all():
        category = rec.category if rec.kind == "expense" else rec.income_category
        per_month = rec.amount * Decimal(52) / Decimal(12) if rec.frequency == "weekly" else rec.amount
        if rec.is_active:
            monthly[rec.kind] += per_month
        items.append(
            {
                "name": _text(rec.name),
                "kind": rec.kind,
                "amount": _num(rec.amount),
                "frequency": rec.frequency,
                "due_day": rec.due_day,
                "category": category.name if category else None,
                "active": rec.is_active,
                "next_due": str(next_unpaid_due(rec.frequency, rec.due_day, rec.last_paid_on, ctx.today)),
                "monthly_equivalent": _num(per_month),
            }
        )
    items.sort(key=lambda i: i["next_due"])
    return {
        "items": items,
        "monthly_recurring_expenses": _num(monthly["expense"]),
        "monthly_recurring_income": _num(monthly["income"]),
    }


class UnusualArgs(_Args):
    start_date: date
    end_date: date


def detect_unusual_spending(ctx: ToolContext, args: UnusualArgs) -> dict[str, Any]:
    """Categories well above their usual daily rate, and single expenses far above the category median."""
    start, end, notes = _range(args.start_date, args.end_date, ctx)
    days = (end - start).days + 1
    base_start, base_end = start - timedelta(days=90), start - timedelta(days=1)
    period, baseline = _by_category(ctx, start, end), _by_category(ctx, base_start, base_end)

    categories: list[dict[str, Any]] = []
    for name, cur in period.items():
        cur_daily = cur["total"] / days
        base_daily = baseline.get(name, {}).get("total", Decimal("0")) / 90
        if cur["total"] < 300:
            continue
        # Once-a-month bills (rent, electricity) look "high" over a short window; need a pattern, not 1-2 payments
        if cur["count"] < 3 and base_daily > 0:
            continue
        if (base_daily == 0 and cur["total"] >= 1000) or (base_daily > 0 and cur_daily > base_daily * Decimal("1.5")):
            categories.append(
                {
                    "category": name,
                    "period_total": _num(cur["total"]),
                    "period_daily_average": _num(cur_daily),
                    "usual_daily_average": _num(base_daily),
                    "times_usual": round(float(cur_daily / base_daily), 1) if base_daily > 0 else None,
                }
            )
    categories.sort(key=lambda c: c["period_total"], reverse=True)

    history = (
        ctx.db.query(Expense, Category)
        .join(Category, Category.id == Expense.category_id)
        .filter(Expense.user_id == ctx.user_id, Expense.expense_date >= base_start, Expense.expense_date <= end)
        .all()
    )
    amounts: dict[str, list[Decimal]] = {}
    for e, c in history:
        amounts.setdefault(c.name, []).append(e.amount)
    large: list[dict[str, Any]] = []
    for e, c in history:
        values = amounts[c.name]
        if e.expense_date < start or len(values) < 5 or e.amount < 500:
            continue
        median = Decimal(str(statistics.median(values)))
        if e.amount > median * 3:
            large.append(
                {
                    "date": str(e.expense_date),
                    "amount": _num(e.amount),
                    "category": c.name,
                    "note": _text(e.note),
                    "category_median": _num(median),
                }
            )
    large.sort(key=lambda x: x["amount"], reverse=True)

    result: dict[str, Any] = {
        "start_date": str(start),
        "end_date": str(end),
        "baseline": f"{base_start} to {base_end}",
        "categories_above_usual": categories[:6],
        "unusually_large_expenses": large[:5],
    }
    if notes:
        result["notes"] = notes
    return result


class NoArgs(_Args):
    pass


def list_categories(ctx: ToolContext, args: NoArgs) -> dict[str, Any]:
    expense = ctx.db.query(Category).filter(Category.user_id == ctx.user_id).order_by(Category.name).all()
    income = (
        ctx.db.query(IncomeCategory).filter(IncomeCategory.user_id == ctx.user_id).order_by(IncomeCategory.name).all()
    )
    return {
        "expense_categories": [{"name": c.name, "icon": c.icon} for c in expense],
        "income_categories": [{"name": c.name, "icon": c.icon} for c in income],
    }


class CashflowArgs(_Args):
    month: Optional[str] = Field(None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="YYYY-MM; default current month")


def get_cashflow_tool(ctx: ToolContext, args: CashflowArgs) -> dict[str, Any]:
    label, start, end = month_bounds(args.month or f"{ctx.today:%Y-%m}")
    flow = get_cashflow(ctx.db, ctx.user_id, start, min(end, ctx.today))
    return {
        "month": label,
        "income": _num(flow.income),
        "spent": _num(flow.spent),
        "saved": _num(flow.saved),
        "savings_rate_pct": flow.savings_rate,
        "allocated_to_goals": _num(flow.allocated_to_goals),
        "note": "saved = income - spent; negative means overspent. savings_rate_pct is null when there was no income.",
    }


class GoalsArgs(_Args):
    status: Literal["active", "archived", "all"] = "active"


def get_savings_goals(ctx: ToolContext, args: GoalsArgs) -> dict[str, Any]:
    query = ctx.db.query(SavingsGoal).filter(SavingsGoal.user_id == ctx.user_id)
    if args.status != "all":
        query = query.filter(SavingsGoal.status == args.status)
    goals = query.all()
    saved = saved_by_goal(ctx.db, [g.id for g in goals])
    items = []
    for g in goals:
        p = compute_progress(g, saved.get(g.id, Decimal("0")), ctx.today)
        items.append(
            {
                "name": _text(g.name),
                "target": _num(g.target_amount),
                "saved": _num(p.saved),
                "remaining": _num(p.remaining),
                "progress_pct": p.progress_pct,
                "deadline": str(g.target_date) if g.target_date else None,
                "state": p.state,
                "months_left": p.months_left,
                "required_per_month": _num(p.required_per_month) if p.required_per_month is not None else None,
            }
        )
    return {"goals": items}


class ProposeExpenseArgs(_Args):
    amount: Decimal = Field(gt=0, le=99_999_999.99)
    category: str = Field(min_length=1, max_length=100)
    expense_date: Optional[date] = Field(None, description="YYYY-MM-DD; default today")
    note: Optional[str] = Field(None, max_length=500)


def propose_expense(ctx: ToolContext, args: ProposeExpenseArgs) -> dict[str, Any]:
    """Validate a quick-add request and return a proposal. Never writes to the database."""
    if args.amount != args.amount.quantize(Decimal("0.01")):
        raise ToolArgError("amount can have at most 2 decimal places")
    day = args.expense_date or ctx.today
    if day > ctx.today:
        raise ToolArgError(f"expense date can't be in the future (today is {ctx.today})")
    if day < MIN_DATE:
        raise ToolArgError(f"expense date can't be before {MIN_DATE}")
    category = _resolve_category(ctx, args.category)
    return {
        "proposal": {
            "amount": _num(args.amount),
            "category_id": str(category.id),
            "category_name": category.name,
            "category_icon": category.icon,
            "expense_date": str(day),
            "note": (args.note or "").strip() or None,
        },
        "status": "proposed, NOT saved",
        "next_step": "The user sees a confirmation card and must click Confirm. Tell them to check and confirm it.",
    }


# --- Registry ----------------------------------------------------------------------------


def expense_category_names(db: Session, user_id: UUID, limit: int = 60) -> list[str]:
    """The user's expense category names (as plain data), for the per-request context."""
    rows = db.query(Category.name).filter(Category.user_id == user_id).order_by(Category.name).limit(limit).all()
    return [_text(name) or "" for (name,) in rows]


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    args_model: type[_Args]
    fn: Callable[[ToolContext, Any], dict[str, Any]]
    status_text: str  # shown in the UI while the tool runs (English / Banglish questions)
    status_text_bn: str  # the same, for questions written in Bangla script

    def status(self, language: str) -> str:
        return self.status_text_bn if language == "bn" else self.status_text


TOOLS: dict[str, Tool] = {
    t.name: t
    for t in [
        Tool(
            "get_spending_summary",
            "Total spending for a date range, grouped by category, day, week or month.",
            SpendingSummaryArgs,
            get_spending_summary,
            "Adding up your spending…",
            "আপনার খরচ হিসাব করছি…",
        ),
        Tool(
            "compare_periods",
            "Compare total and per-category spending between two date ranges.",
            ComparePeriodsArgs,
            compare_periods,
            "Comparing with the other period…",
            "আগের সময়ের সাথে তুলনা করছি…",
        ),
        Tool(
            "list_expenses",
            "List individual expenses with optional filters. sort=amount_desc gives the largest expenses.",
            ListExpensesArgs,
            list_expenses,
            "Looking through your expenses…",
            "আপনার খরচগুলো দেখছি…",
        ),
        Tool(
            "get_budgets_status",
            "Budget limits, spending, remaining and projected month-end spending for a month.",
            BudgetsStatusArgs,
            get_budgets_status,
            "Checking your budgets…",
            "বাজেট দেখছি…",
        ),
        Tool(
            "get_recurring_items",
            "Recurring bills and recurring income with next due dates and monthly totals.",
            RecurringArgs,
            get_recurring_items,
            "Checking recurring bills…",
            "নিয়মিত বিল দেখছি…",
        ),
        Tool(
            "detect_unusual_spending",
            "Categories spending well above their usual rate and unusually large single expenses in a date range.",
            UnusualArgs,
            detect_unusual_spending,
            "Looking for unusual spending…",
            "অস্বাভাবিক খরচ খুঁজছি…",
        ),
        Tool(
            "list_categories",
            "The user's expense and income categories.",
            NoArgs,
            list_categories,
            "Checking your categories…",
            "ক্যাটাগরি দেখছি…",
        ),
        Tool(
            "get_cashflow",
            "Income, spending, saved and savings rate for a month.",
            CashflowArgs,
            get_cashflow_tool,
            "Checking income and savings…",
            "আয় আর সঞ্চয় দেখছি…",
        ),
        Tool(
            "get_savings_goals",
            "Savings goals with progress, deadline state and the monthly amount needed.",
            GoalsArgs,
            get_savings_goals,
            "Checking your goals…",
            "সঞ্চয়ের লক্ষ্য দেখছি…",
        ),
        Tool(
            "propose_expense",
            "Prepare an expense for the user to confirm (quick add). Does NOT save anything.",
            ProposeExpenseArgs,
            propose_expense,
            "Preparing the expense…",
            "খরচটি প্রস্তুত করছি…",
        ),
    ]
}


def _schema(model: type[_Args]) -> dict[str, Any]:
    schema = model.model_json_schema()
    schema.pop("title", None)
    for prop in schema.get("properties", {}).values():
        prop.pop("title", None)
    for definition in schema.get("$defs", {}).values():
        definition.pop("title", None)
        for prop in definition.get("properties", {}).values():
            prop.pop("title", None)
    return schema


def tool_definitions() -> list[dict[str, Any]]:
    """OpenAI function-calling definitions for every tool."""
    return [
        {
            "type": "function",
            "function": {"name": t.name, "description": t.description, "parameters": _schema(t.args_model)},
        }
        for t in TOOLS.values()
    ]


@dataclass
class ToolOutcome:
    result: dict[str, Any]
    malformed: bool = False  # bad JSON / schema: counts toward the one-retry limit
    proposal: Optional[dict[str, Any]] = None


def run_tool(ctx: ToolContext, name: str, raw_arguments: str) -> ToolOutcome:
    tool = TOOLS.get(name)
    if tool is None:
        return ToolOutcome({"error": f"unknown tool {name!r}"}, malformed=True)
    try:
        data = json.loads(raw_arguments or "{}")
        if not isinstance(data, dict):
            raise ValueError("arguments must be a JSON object")
        args = tool.args_model.model_validate(data)
    except (ValueError, ValidationError) as exc:
        message = exc.errors(include_url=False, include_context=False) if isinstance(exc, ValidationError) else str(exc)
        return ToolOutcome({"error": "invalid arguments", "details": message}, malformed=True)
    try:
        result = tool.fn(ctx, args)
    except ToolArgError as exc:
        return ToolOutcome({"error": str(exc)})
    proposal = result.get("proposal") if name == "propose_expense" else None
    return ToolOutcome(result, proposal=proposal)
