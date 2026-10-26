"""Talk to the assistant with the REAL OpenRouter API and print a full trace.

    uv run python -m scripts.try_assistant "How much did I spend this month?" "এই মাসে কত খরচ হয়েছে?"

Each message starts a new conversation. Prints the tool calls (name, arguments,
result summary), streamed status/proposal events, the final answer, the model
that answered, tokens and cost. Costs real money: development use only.
Requires the demo user (scripts.seed_demo) or --email of an existing account.
"""

import argparse
import asyncio
import json
import sys
from decimal import Decimal
from typing import Any

from app.assistant import service
from app.assistant.llm_client import Finished, LLMClient, ToolCallsReady
from app.config import get_settings
from app.database import SessionLocal
from app.services.users import get_user_by_email


class Recorder:
    """Wraps the real client and records tool calls and usage for the trace."""

    def __init__(self, inner: LLMClient):
        self.inner = inner
        self.tool_calls: list[Any] = []
        self.usages: list[Any] = []
        self.finish_reasons: list[Any] = []

    async def stream_chat(self, messages, tools, **kwargs):
        async for event in self.inner.stream_chat(messages, tools, **kwargs):
            if isinstance(event, ToolCallsReady):
                self.tool_calls.extend(event.calls)
            if isinstance(event, Finished):
                self.usages.append(event.usage)
                self.finish_reasons.append(event.finish_reason)
            yield event


def _summarize(result: dict[str, Any]) -> str:
    text = json.dumps(result, ensure_ascii=False, default=str)
    return text if len(text) <= 400 else text[:400] + " …"


async def run(email: str, messages: list[str]) -> Decimal:
    settings = get_settings()
    if settings.app_env != "development":
        sys.exit("try_assistant runs only with APP_ENV=development")
    with SessionLocal() as db:
        user = get_user_by_email(db, email)
        if user is None:
            sys.exit(f"No user {email}; run: uv run python -m scripts.seed_demo --reset")
        user.assistant_enabled = True
        db.commit()
        user_id = user.id

    tool_results: list[tuple[str, dict[str, Any]]] = []
    original = service._run_tool_isolated

    def recording_tool(uid, today, name, arguments):
        outcome = original(uid, today, name, arguments)
        tool_results.append((name, outcome.result))
        return outcome

    service._run_tool_isolated = recording_tool  # type: ignore[assignment]
    total = Decimal("0")
    try:
        for text in messages:
            recorder = Recorder(LLMClient(settings))
            tool_results.clear()
            answer, events = [], []
            async for event, data in service.run_chat(recorder, settings, user_id, None, text):
                if event == "token":
                    answer.append(data["text"])
                elif event != "conversation":
                    events.append((event, data))

            cost = sum((u.cost_usd for u in recorder.usages), Decimal("0"))
            total += cost
            print("=" * 100)
            print(f"USER: {text}")
            # Not strict: a rejected (malformed) call can leave the lists different lengths
            for call, (_name, result) in zip(recorder.tool_calls, tool_results, strict=False):
                print(f"  TOOL CALL  {call.name}({call.arguments})")
                print(f"  TOOL RESULT {_summarize(result)}")
            for event, data in events:
                if event in ("proposal", "error"):
                    print(f"  EVENT {event}: {json.dumps(data, ensure_ascii=False)}")
            print(f"ASSISTANT:\n{''.join(answer)}")
            models = sorted({u.model for u in recorder.usages if u.model})
            print(
                f"  [model {', '.join(models)} | {len(recorder.usages)} LLM requests | "
                f"prompt {sum(u.prompt_tokens for u in recorder.usages)} tok (cached {sum(u.cached_tokens for u in recorder.usages)}) | "
                f"output {sum(u.completion_tokens for u in recorder.usages)} tok (reasoning {[u.reasoning_tokens for u in recorder.usages]}) | "
                f"latency {sum(u.latency_ms for u in recorder.usages)} ms | finish {recorder.finish_reasons} | cost ${cost:.6f}]"
            )
    finally:
        service._run_tool_isolated = original  # type: ignore[assignment]
    print("=" * 100)
    print(f"TOTAL COST THIS RUN: ${total:.6f}")
    return total


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m scripts.try_assistant")
    parser.add_argument("messages", nargs="+")
    parser.add_argument("--email", default="demo@example.com")
    args = parser.parse_args()
    asyncio.run(run(args.email, args.messages))


if __name__ == "__main__":
    main()
