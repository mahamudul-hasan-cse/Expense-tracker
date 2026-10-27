"""Compare assistant models on the seeded demo user, with the REAL OpenRouter API.

    uv run python -m scripts.seed_demo --reset          # deterministic data first
    uv run python -m scripts.eval_assistant \\
        --models anthropic/claude-haiku-5.5,openai/gpt-6-luna,anthropic/claude-sonnet-5.5,google/gemini-3.5-flash-lite \\
        --efforts default low --subset-for low --budget 1.20 --json out.json

18 questions (7 English, 6 Bangla, 5 Banglish). Each answer is checked automatically
against ground truth computed directly from the database (the same SQL the tools use):
the key numbers must appear (±1 Taka or ±0.5%), named categories/goals must be
mentioned, quick adds must propose the right amount/category/date, the reply must be in
the question's script, and out-of-scope advice must be declined.

Per model and reasoning setting it reports: accuracy, language match, raw Bangla digits
(before the server's fix-up), time to first status / first text / total, LLM rounds,
cost per message and errors. Costs real money: development use only; stops at --budget.
"""

import argparse
import asyncio
import json
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal
from typing import Any, Callable, Optional

from app.assistant import service
from app.assistant.llm_client import Finished, LLMClient, TextDelta, ToolCallsReady
from app.assistant.tools import ToolContext, run_tool
from app.config import get_settings
from app.database import SessionLocal
from app.services.users import get_user_by_email
from app.timeutil import today as app_today

BANGLA_SCRIPT = re.compile("[ঀ-৿]")
BANGLA_DIGITS = re.compile("[০-৯]")
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


# --- Ground truth ------------------------------------------------------------------------------


def ground_truth(user_id) -> dict[str, Any]:
    today = app_today()
    month_start = today.replace(day=1)
    last_month_end = month_start - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    this_monday = today - timedelta(days=today.weekday())
    last_week = (this_monday - timedelta(days=7), this_monday - timedelta(days=1))

    with SessionLocal() as db:
        ctx = ToolContext(db=db, user_id=user_id, today=today)

        def tool(name: str, **args: Any) -> dict[str, Any]:
            return run_tool(ctx, name, json.dumps(args, default=str)).result

        month = tool("get_spending_summary", start_date=month_start, end_date=today)
        prev = tool("get_spending_summary", start_date=last_month_start, end_date=last_month_end)
        week = tool("get_spending_summary", start_date=last_week[0], end_date=last_week[1])
        budgets = tool("get_budgets_status")
        cashflow = tool("get_cashflow")
        goals = tool("get_savings_goals")
        recurring = tool("get_recurring_items", kind="expense")

    by_cat = {c["category"]: c["total"] for c in month["by_category"]}
    return {
        "today": today,
        "month_total": month["total"],
        "top3": [(c["category"], c["total"]) for c in month["by_category"][:3]],
        "food_month": by_cat.get("Food", 0),
        "last_month_total": prev["total"],
        "last_week_total": week["total"],
        "over_budget": [b["category"] for b in budgets["budgets"] if b["over_budget"]],
        "saved": cashflow["saved"],
        "savings_rate": cashflow["savings_rate_pct"],
        "goals": [(g["name"], g["saved"]) for g in goals["goals"]],
        "next_bills": [i["name"] for i in recurring["items"] if i["active"]][:2],
    }


# --- Checks -------------------------------------------------------------------------------------


def numbers_in(text: str) -> list[float]:
    return [float(n.replace(",", "")) for n in NUMBER.findall(text)]


def has_amount(text: str, value: float) -> bool:
    tolerance = max(1.0, abs(value) * 0.005)
    return any(abs(n - value) <= tolerance for n in numbers_in(text))


def mentions(text: str, name: str) -> bool:
    return name.lower() in text.lower()


Check = Callable[[str, Optional[dict], dict], list[str]]  # returns a list of failures


def amounts(*keys: str) -> Check:
    return lambda text, _p, t: [f"missing {k}={t[k]}" for k in keys if not has_amount(text, t[k])]


def top3(text: str, _p: Optional[dict], t: dict) -> list[str]:
    fails = [f"missing category {n}" for n, _ in t["top3"] if not mentions(text, n)]
    return fails + [f"missing {n} amount {v}" for n, v in t["top3"] if not has_amount(text, v)]


def over_budget(text: str, _p: Optional[dict], t: dict) -> list[str]:
    return [f"missing over-budget {n}" for n in t["over_budget"] if not mentions(text, n)]


def savings(text: str, _p: Optional[dict], t: dict) -> list[str]:
    fails = [] if has_amount(text, t["saved"]) else [f"missing saved={t['saved']}"]
    if t["savings_rate"] is not None and not has_amount(text, t["savings_rate"]):
        fails.append(f"missing savings rate={t['savings_rate']}")
    return fails


def goals(text: str, _p: Optional[dict], t: dict) -> list[str]:
    fails = [f"missing goal {n}" for n, _ in t["goals"] if not mentions(text, n)]
    return fails + [f"missing goal saved {v}" for _, v in t["goals"] if not has_amount(text, v)]


def bills(text: str, _p: Optional[dict], t: dict) -> list[str]:
    return [f"missing bill {n}" for n in t["next_bills"] if not mentions(text, n)]


def declines(text: str, _p: Optional[dict], _t: dict) -> list[str]:
    signals = ["can't", "cannot", "can not", "not able", "outside", "professional", "advisor", "adviser", "don't give"]
    return [] if any(s in text.lower() for s in signals) else ["did not decline investment advice"]


def proposes(amount: float, category: str, days_ago: int) -> Check:
    def check(_text: str, proposal: Optional[dict], t: dict) -> list[str]:
        if proposal is None:
            return ["no quick-add proposal"]
        fails = []
        if abs(float(proposal["amount"]) - amount) > 0.001:
            fails.append(f"amount {proposal['amount']} != {amount}")
        if proposal["category_name"].lower() != category.lower():
            fails.append(f"category {proposal['category_name']} != {category}")
        if proposal["expense_date"] != str(t["today"] - timedelta(days=days_ago)):
            fails.append(f"date {proposal['expense_date']}")
        return fails

    return check


@dataclass
class Question:
    id: str
    lang: str  # en | bn | banglish
    text: str
    check: Check
    subset: bool = False  # also run for the extra reasoning settings


QUESTIONS = [
    Question("en-total", "en", "How much did I spend this month?", amounts("month_total"), True),
    Question("en-top3", "en", "What are my top 3 spending categories this month, with amounts?", top3),
    Question(
        "en-compare",
        "en",
        "How did my spending this month compare with last month, and where can I save money?",
        amounts("month_total", "last_month_total"),
        True,
    ),
    Question("en-budgets", "en", "Am I over budget anywhere this month?", over_budget),
    Question("en-savings", "en", "How much have I saved this month and what's my savings rate?", savings),
    Question("en-goals", "en", "How are my savings goals going?", goals),
    Question("en-invest", "en", "Should I put my savings into Bitcoin or stocks?", declines),
    Question("bn-total", "bn", "এই মাসে কত খরচ হয়েছে?", amounts("month_total"), True),
    Question("bn-top", "bn", "কোন কোন খাতে সবচেয়ে বেশি খরচ হচ্ছে? টাকার পরিমাণসহ বলো।", top3),
    Question("bn-budgets", "bn", "এই মাসে আমার বাজেটের অবস্থা কেমন?", over_budget, True),
    Question("bn-lastweek", "bn", "গত সপ্তাহে (সোমবার থেকে রবিবার) কত খরচ করেছি?", amounts("last_week_total")),
    Question("bn-bills", "bn", "আমার সামনের বিলগুলো কী কী আর কবে?", bills),
    Question("bn-quickadd", "bn", "আজ রিকশা ভাড়া ৮০ টাকা", proposes(80, "Rickshaw", 0), True),
    Question("bl-total", "banglish", "ei mash e koto khoroch holo?", amounts("month_total")),
    Question("bl-food", "banglish", "ei mash e food e koto taka gelo?", amounts("food_month")),
    Question("bl-goals", "banglish", "amar savings goal gulor ki obostha?", goals),
    Question("bl-quickadd", "banglish", "kalke grocery 1200 taka", proposes(1200, "Groceries", 1), True),
    Question(
        "bl-compare",
        "banglish",
        "last month er sathe ei mash er khoroch tulona koro",
        amounts("month_total", "last_month_total"),
    ),
]


def language_ok(lang: str, text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    bangla = sum(1 for c in letters if BANGLA_SCRIPT.match(c)) / len(letters)
    return bangla > 0.5 if lang == "bn" else bangla < 0.2


# --- Running ------------------------------------------------------------------------------------


class Recorder:
    def __init__(self, inner: LLMClient):
        self.inner = inner
        self.usages: list = []
        self.raw: list[str] = []
        self.tools: list[list[str]] = []

    async def stream_chat(self, messages, tools, **kwargs):
        async for event in self.inner.stream_chat(messages, tools, **kwargs):
            if isinstance(event, TextDelta):
                self.raw.append(event.text)
            elif isinstance(event, ToolCallsReady):
                self.tools.append([c.name for c in event.calls])
            elif isinstance(event, Finished):
                self.usages.append(event.usage)
            yield event


@dataclass
class Result:
    question: str
    lang: str
    passed: bool
    failures: list[str]
    language_ok: bool
    raw_bangla_digits: bool
    first_status: Optional[float]
    first_text: Optional[float]
    total: float
    rounds: int
    tools: list[list[str]]
    cost: float
    error: Optional[str]
    answer: str = field(repr=False)


async def ask(settings, user_id, q: Question, truth: dict) -> Result:
    rec = Recorder(LLMClient(settings))
    started = time.monotonic()
    first_status = first_text = None
    parts: list[str] = []
    proposal = None
    error = None
    async for event, data in service.run_chat(rec, settings, user_id, None, q.text):
        now = time.monotonic() - started
        if event == "status" and first_status is None:
            first_status = now
        elif event == "token":
            first_text = first_text if first_text is not None else now
            parts.append(data["text"])
        elif event == "proposal":
            proposal = data
        elif event == "error":
            error = data.get("code")
    answer = "".join(parts)
    failures = ([f"error {error}"] if error else []) + q.check(answer, proposal, truth)
    lang = language_ok(q.lang, answer)
    if not lang:
        failures.append("wrong language")
    return Result(
        question=q.id,
        lang=q.lang,
        passed=not failures,
        failures=failures,
        language_ok=lang,
        raw_bangla_digits=bool(BANGLA_DIGITS.search("".join(rec.raw))),
        first_status=first_status,
        first_text=first_text,
        total=time.monotonic() - started,
        rounds=len(rec.usages),
        tools=rec.tools,
        cost=float(sum((u.cost_usd for u in rec.usages), Decimal("0"))),
        error=error,
        answer=answer,
    )


def avg(values: list[Optional[float]]) -> Optional[float]:
    present = [v for v in values if v is not None]
    return sum(present) / len(present) if present else None


def fmt(value: Optional[float], unit: str = "s") -> str:
    return "-" if value is None else f"{value:.1f}{unit}"


def summarize(model: str, effort: str, results: list[Result]) -> dict[str, Any]:
    n = len(results)
    return {
        "model": model,
        "effort": effort,
        "questions": n,
        "passed": sum(r.passed for r in results),
        "language_ok": sum(r.language_ok for r in results),
        "raw_bangla_digits": sum(r.raw_bangla_digits for r in results if r.lang == "bn"),
        "bn_questions": sum(r.lang == "bn" for r in results),
        "first_status": avg([r.first_status for r in results]),
        "first_text": avg([r.first_text for r in results]),
        "total": avg([r.total for r in results]),
        "rounds": avg([float(r.rounds) for r in results]),
        "cost_per_message": sum(r.cost for r in results) / n if n else 0.0,
        "errors": sum(r.error is not None for r in results),
    }


async def run(args: argparse.Namespace) -> None:
    base = get_settings()
    if base.app_env != "development":
        sys.exit("eval_assistant runs only with APP_ENV=development")
    with SessionLocal() as db:
        user = get_user_by_email(db, args.email)
        if user is None:
            sys.exit(f"No user {args.email}; run: uv run python -m scripts.seed_demo --reset")
        user_id = user.id
    truth = ground_truth(user_id)
    print("Ground truth:", json.dumps(truth, default=str, ensure_ascii=False))

    budget = Decimal(str(args.budget))
    spent = Decimal("0")
    summaries: list[dict[str, Any]] = []
    details: list[dict[str, Any]] = []
    for model in [m.strip() for m in args.models.split(",") if m.strip()]:
        for effort in args.efforts:
            settings = base.model_copy(
                update={
                    "assistant_model": model,
                    "assistant_fallback_models": "",
                    "assistant_reasoning_effort": "" if effort == "default" else effort,
                }
            )
            questions = [q for q in QUESTIONS if q.subset] if effort in args.subset_for else QUESTIONS
            if args.only:
                questions = [q for q in questions if q.id in args.only]
            print("=" * 110)
            print(f"{model} | reasoning {effort} | {len(questions)} questions")
            results: list[Result] = []
            for q in questions:
                if spent >= budget:
                    print(f"STOP: spent ${spent:.4f} reached --budget ${budget}")
                    break
                r = await ask(settings, user_id, q, truth)
                spent += Decimal(str(r.cost))
                results.append(r)
                mark = "PASS" if r.passed else "FAIL"
                print(
                    f"  {mark} {q.id:<12} status {fmt(r.first_status):>5} text {fmt(r.first_text):>5} "
                    f"total {fmt(r.total):>5} rounds {r.rounds} ${r.cost:.5f} "
                    f"{'BN-DIGITS ' if r.raw_bangla_digits else ''}{'; '.join(r.failures)}"
                )
                details.append({"model": model, "effort": effort, **r.__dict__})
            if results:
                summaries.append(summarize(model, effort, results))
            if spent >= budget:
                break
        if spent >= budget:
            break

    print("=" * 110)
    print(
        "| Model | Reasoning | Accuracy | Language | Raw BN digits | First status | First text | Total | Rounds | $/message | Errors |"
    )
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for s in summaries:
        print(
            f"| {s['model']} | {s['effort']} | {s['passed']}/{s['questions']} | {s['language_ok']}/{s['questions']} | "
            f"{s['raw_bangla_digits']}/{s['bn_questions']} | {fmt(s['first_status'])} | {fmt(s['first_text'])} | "
            f"{fmt(s['total'])} | {fmt(s['rounds'], '')} | ${s['cost_per_message']:.5f} | {s['errors']} |"
        )
    print(f"TOTAL COST THIS RUN: ${spent:.6f}")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"truth": truth, "summaries": summaries, "details": details}, fh, default=str, ensure_ascii=False)


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m scripts.eval_assistant")
    parser.add_argument("--models", default="anthropic/claude-haiku-5.5")
    parser.add_argument("--efforts", nargs="+", default=["default"])
    parser.add_argument("--subset-for", nargs="*", default=["low", "none"], help="efforts run on the 6-question subset")
    parser.add_argument("--budget", type=float, default=0.50, help="stop once this much USD is spent")
    parser.add_argument("--email", default="demo@example.com")
    parser.add_argument("--only", nargs="*", help="question ids to run (default: all)")
    parser.add_argument("--json", help="write full results (answers included) to this file")
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
