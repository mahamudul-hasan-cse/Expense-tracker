"""Measure assistant latency with the REAL OpenRouter API, per reasoning setting.

    uv run python -m scripts.measure_latency --efforts default low none --repeat 1

For each reasoning effort, runs the 3 example conversations (docs/ASSISTANT_EXAMPLES.md)
through the real chat service and prints, per conversation:
time to first token (what the user waits for before text appears), total time,
LLM rounds, reasoning tokens, output tokens, cost, and the answer's first line.
Also flags answers that contain Bangla digits (the prompt requires 0-9).
Costs real money: development use only. Requires the demo user (scripts.seed_demo).
"""

import argparse
import asyncio
import re
import sys
import time
from decimal import Decimal

from app.assistant import service
from app.assistant.llm_client import Finished, LLMClient
from app.config import get_settings
from app.database import SessionLocal
from app.services.users import get_user_by_email

EXAMPLES = [
    "How did my spending this month compare with last month, and where can I save money?",
    "এই মাসে আমার বাজেটের অবস্থা কেমন? কোন খাতে বেশি খরচ হচ্ছে?",
    "আজ দুপুরের খাবার ২৫০ টাকা",
]
BANGLA_DIGITS = re.compile("[০-৯]")


class Recorder:
    def __init__(self, inner: LLMClient):
        self.inner = inner
        self.usages: list = []

    async def stream_chat(self, messages, tools, **kwargs):
        async for event in self.inner.stream_chat(messages, tools, **kwargs):
            if isinstance(event, Finished):
                self.usages.append(event.usage)
            yield event


async def one(settings, user_id, text: str) -> dict:
    recorder = Recorder(LLMClient(settings))
    started = time.monotonic()
    first_token = None
    answer: list[str] = []
    error = None
    async for event, data in service.run_chat(recorder, settings, user_id, None, text):
        if event == "token":
            if first_token is None:
                first_token = time.monotonic() - started
            answer.append(data["text"])
        elif event == "error":
            error = data.get("code")
    total = time.monotonic() - started
    text_out = "".join(answer)
    return {
        "ttft": first_token,
        "total": total,
        "rounds": len(recorder.usages),
        "reasoning": sum(u.reasoning_tokens for u in recorder.usages),
        "output": sum(u.completion_tokens for u in recorder.usages),
        "cost": sum((u.cost_usd for u in recorder.usages), Decimal("0")),
        "models": sorted({u.model for u in recorder.usages if u.model}),
        "bangla_digits": bool(BANGLA_DIGITS.search(text_out)),
        "first_line": text_out.strip().splitlines()[0][:90] if text_out.strip() else "",
        "error": error,
    }


async def run(email: str, efforts: list[str], repeat: int, budget: Decimal) -> None:
    base = get_settings()
    if base.app_env != "development":
        sys.exit("measure_latency runs only with APP_ENV=development")
    with SessionLocal() as db:
        user = get_user_by_email(db, email)
        if user is None:
            sys.exit(f"No user {email}; run: uv run python -m scripts.seed_demo --reset")
        user.assistant_enabled = True
        db.commit()
        user_id = user.id

    spent = Decimal("0")
    for effort in efforts:
        settings = base.model_copy(update={"assistant_reasoning_effort": "" if effort == "default" else effort})
        print("=" * 110)
        print(f"reasoning effort: {effort}   models: {settings.assistant_models}")
        for i, text in enumerate(EXAMPLES, 1):
            for r in range(repeat):
                if spent >= budget:
                    print(f"STOP: spend ${spent:.6f} reached the --budget ${budget}")
                    return
                m = await one(settings, user_id, text)
                spent += m["cost"]
                ttft = f"{m['ttft']:.2f}s" if m["ttft"] is not None else "-"
                print(
                    f"  #{i}.{r + 1} ttft {ttft:>7} | total {m['total']:6.2f}s | rounds {m['rounds']} | "
                    f"reasoning {m['reasoning']:>4} tok | output {m['output']:>4} tok | ${m['cost']:.6f} | "
                    f"bn-digits {'YES' if m['bangla_digits'] else 'no'} | {m['error'] or 'ok'} | {','.join(m['models'])}"
                )
                print(f"         {m['first_line']}")
    print("=" * 110)
    print(f"TOTAL COST THIS RUN: ${spent:.6f}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m scripts.measure_latency")
    parser.add_argument("--efforts", nargs="+", default=["default", "low", "none"])
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--budget", type=Decimal, default=Decimal("0.10"), help="stop once this much USD is spent")
    parser.add_argument("--email", default="demo@example.com")
    args = parser.parse_args()
    asyncio.run(run(args.email, args.efforts, args.repeat, args.budget))


if __name__ == "__main__":
    main()
