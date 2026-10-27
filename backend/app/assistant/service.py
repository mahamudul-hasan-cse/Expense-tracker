"""Assistant orchestration: availability checks, the tool-calling loop, persistence and usage."""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, AsyncIterator, Optional, Protocol
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.assistant.llm_client import Finished, LLMError, LLMEvent, TextDelta, ToolCallsReady, Usage
from app.assistant.tools import TOOLS, ToolContext, run_tool, tool_definitions
from app.config import Settings
from app.database import SessionLocal
from app.models.assistant import AssistantConversation, AssistantMessage, AssistantUsage
from app.models.user import User
from app.timeutil import app_timezone
from app.timeutil import today as app_today

logger = logging.getLogger("app.assistant")

SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "system.md").read_text(encoding="utf-8")
TITLE_LENGTH = 60


class ChatModel(Protocol):
    """What the service needs from an LLM client (the real LLMClient or a test fake)."""

    def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        *,
        max_tokens: int,
        allow_tools: bool = True,
        session_id: Optional[str] = None,
    ) -> AsyncIterator[LLMEvent]: ...


# --- Availability and limits ------------------------------------------------------------


@dataclass(frozen=True)
class Availability:
    available: bool
    code: Optional[str] = None
    message: Optional[str] = None
    status_code: int = 200


def _today_bounds() -> tuple[datetime, datetime]:
    """Start and end of today in Asia/Dhaka, as aware datetimes (limits reset at Dhaka midnight)."""
    start = datetime.combine(app_today(), time.min, tzinfo=app_timezone())
    return start, start + timedelta(days=1)


def messages_today(db: Session, user_id: UUID) -> int:
    start, end = _today_bounds()
    return (
        db.query(func.count(AssistantMessage.id))
        .filter(
            AssistantMessage.user_id == user_id,
            AssistantMessage.role == "user",
            AssistantMessage.created_at >= start,
            AssistantMessage.created_at < end,
        )
        .scalar()
        or 0
    )


def spend_today(db: Session) -> Decimal:
    """Total assistant cost today across all users (for the global daily budget)."""
    start, end = _today_bounds()
    total = (
        db.query(func.coalesce(func.sum(AssistantUsage.cost_usd), 0))
        .filter(AssistantUsage.created_at >= start, AssistantUsage.created_at < end)
        .scalar()
    )
    return Decimal(total)


def check_availability(db: Session, user: User, settings: Settings, configured: bool) -> Availability:
    if not configured:
        return Availability(False, "not_configured", "The assistant isn't set up on this server yet.", 503)
    if not user.assistant_enabled:
        return Availability(False, "disabled", "Turn on the assistant to start chatting.", 403)
    if spend_today(db) >= Decimal(str(settings.assistant_global_daily_budget_usd)):
        return Availability(
            False,
            "daily_budget_reached",
            "The assistant has reached today's usage limit. It will be back tomorrow.",
            503,
        )
    if messages_today(db, user.id) >= settings.assistant_daily_message_limit:
        return Availability(
            False,
            "daily_limit",
            f"You've used all {settings.assistant_daily_message_limit} assistant messages for today. "
            "They reset at midnight (Bangladesh time).",
            429,
        )
    return Availability(True)


# --- Persistence helpers (sync; run in a thread) ------------------------------------------


def _prepare_turn(
    user_id: UUID, conversation_id: Optional[UUID], text: str, history_limit: int
) -> tuple[UUID, str, list[dict[str, str]]]:
    """Create/load the conversation, save the user's message, and return recent history."""
    with SessionLocal() as db:
        convo: Optional[AssistantConversation] = None
        if conversation_id is not None:
            convo = (
                db.query(AssistantConversation)
                .filter(AssistantConversation.id == conversation_id, AssistantConversation.user_id == user_id)
                .first()
            )
            if convo is None:
                raise LookupError("conversation not found")
        if convo is None:
            title = " ".join(text.split())[:TITLE_LENGTH] or "New chat"
            convo = AssistantConversation(user_id=user_id, title=title)
            db.add(convo)
            db.flush()

        previous = (
            db.query(AssistantMessage)
            .filter(AssistantMessage.conversation_id == convo.id)
            .order_by(AssistantMessage.created_at.desc())
            .limit(history_limit)
            .all()
        )
        history = [{"role": m.role, "content": m.content} for m in reversed(previous) if m.content.strip()]

        db.add(AssistantMessage(conversation_id=convo.id, user_id=user_id, role="user", content=text, status="ok"))
        convo.updated_at = func.now()
        db.commit()
        return convo.id, convo.title, history


def _save_reply(
    user_id: UUID,
    conversation_id: UUID,
    content: str,
    proposal: Optional[dict[str, Any]],
    model: Optional[str],
    status: str,
) -> UUID:
    with SessionLocal() as db:
        message = AssistantMessage(
            conversation_id=conversation_id,
            user_id=user_id,
            role="assistant",
            content=content,
            proposal=proposal,
            proposal_status="pending" if proposal else None,
            model=model,
            status=status,
        )
        db.add(message)
        db.query(AssistantConversation).filter(AssistantConversation.id == conversation_id).update(
            {"updated_at": func.now()}
        )
        db.commit()
        return message.id


def record_usage(
    user_id: UUID, conversation_id: Optional[UUID], kind: str, usage: Usage, status: str, tools_used: list[str]
) -> None:
    with SessionLocal() as db:
        db.add(
            AssistantUsage(
                user_id=user_id,
                conversation_id=conversation_id,
                kind=kind,
                model=usage.model,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                cached_tokens=usage.cached_tokens,
                cost_usd=usage.cost_usd,
                latency_ms=usage.latency_ms,
                status=status,
            )
        )
        db.commit()
    # Metadata only: never message content, never the API key
    logger.info(
        "llm request",
        extra={
            "user_id": str(user_id),
            "kind": kind,
            "model": usage.model,
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "cached_tokens": usage.cached_tokens,
            "cost_usd": float(usage.cost_usd),
            "latency_ms": usage.latency_ms,
            "tools": tools_used,
            "status": status,
        },
    )


def _run_tool_isolated(user_id: UUID, today: Any, name: str, arguments: str):
    with SessionLocal() as db:
        return run_tool(ToolContext(db=db, user_id=user_id, today=today), name, arguments)


# --- The tool-calling loop ----------------------------------------------------------------


def build_messages(history: list[dict[str, str]], user_text: str) -> list[dict[str, Any]]:
    today = app_today()
    system_content = [
        # Static part first so providers that support prompt caching can reuse it
        {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": f"Today is {today:%A, %Y-%m-%d} (Asia/Dhaka). Currency: Bangladeshi Taka (BDT, ৳)."},
    ]
    return [{"role": "system", "content": system_content}, *history, {"role": "user", "content": user_text}]


class ToolCallFailed(Exception):
    pass


_BANGLA_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def english_digits(text: str) -> str:
    """Amounts and dates always use 0-9, even in Bangla replies.

    The prompt asks for this, but models still slip into ০-৯ (seen in real
    Bangla answers), so the server enforces it on every streamed token.
    """
    return text.translate(_BANGLA_DIGITS)


async def run_chat(
    llm: ChatModel, settings: Settings, user_id: UUID, conversation_id: Optional[UUID], user_text: str
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """Yield (event, data) pairs: conversation, status, token, proposal, then done or error."""
    convo_id, title, history = await run_in_threadpool(
        _prepare_turn, user_id, conversation_id, user_text, settings.assistant_history_messages
    )
    yield "conversation", {"id": str(convo_id), "title": title}

    messages = build_messages(history, user_text)
    tools = tool_definitions()
    today = app_today()
    text_parts: list[str] = []
    tools_used: list[str] = []
    proposal: Optional[dict[str, Any]] = None
    model: Optional[str] = None
    status = "ok"
    tool_calls = 0
    malformed = 0
    message_id: Optional[UUID] = None

    try:
        # Bounded: each round either answers or uses tools; once the tool budget is spent,
        # tools are switched off so the model has to answer.
        for _ in range(settings.assistant_max_tool_calls + 2):
            allow_tools = tool_calls < settings.assistant_max_tool_calls
            calls = []
            round_text: list[str] = []
            finish_reason: Optional[str] = None
            async for event in llm.stream_chat(
                messages,
                tools,
                max_tokens=settings.assistant_max_output_tokens,
                allow_tools=allow_tools,
                session_id=str(convo_id),
            ):
                if isinstance(event, TextDelta):
                    piece = english_digits(event.text)
                    if not round_text and "".join(text_parts).strip():
                        # Text before a tool call ("Let me check…") and the answer after it
                        # arrive in separate rounds; keep them as separate paragraphs
                        piece = "\n\n" + piece.lstrip()
                    round_text.append(piece)
                    text_parts.append(piece)
                    yield "token", {"text": piece}
                elif isinstance(event, ToolCallsReady):
                    calls = event.calls
                elif isinstance(event, Finished):
                    model = event.usage.model or model
                    finish_reason = event.finish_reason
                    await run_in_threadpool(
                        record_usage, user_id, convo_id, "chat", event.usage, "ok", list(tools_used)
                    )

            if not calls:
                if finish_reason == "length":
                    # Out of output tokens: say so rather than stopping mid-sentence
                    note = "\n\n_(My answer was cut short — ask me to continue.)_"
                    text_parts.append(note)
                    yield "token", {"text": note}
                break

            messages.append(
                {
                    "role": "assistant",
                    "content": "".join(round_text) or None,
                    "tool_calls": [
                        {"id": c.id, "type": "function", "function": {"name": c.name, "arguments": c.arguments or "{}"}}
                        for c in calls
                    ],
                }
            )
            for call in calls:
                if tool_calls >= settings.assistant_max_tool_calls:
                    result: dict[str, Any] = {"error": "tool call limit reached; answer with what you already have"}
                else:
                    tool_calls += 1
                    tools_used.append(call.name)
                    known = TOOLS.get(call.name)
                    yield "status", {"text": known.status_text if known else "Working…", "tool": call.name}
                    outcome = await run_in_threadpool(_run_tool_isolated, user_id, today, call.name, call.arguments)
                    if outcome.malformed:
                        malformed += 1
                        if malformed > 1:  # one retry, then give up gracefully
                            raise ToolCallFailed(call.name)
                    if outcome.proposal is not None:
                        proposal = outcome.proposal
                        yield "proposal", proposal
                    result = outcome.result
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(result, default=str, ensure_ascii=False),
                    }
                )
    except LLMError as exc:
        status = "error"
        await run_in_threadpool(record_usage, user_id, convo_id, "chat", Usage(model=model), exc.code, list(tools_used))
        logger.warning("assistant provider error", extra={"code": exc.code, "detail": str(exc)})
        payload: dict[str, Any] = {"code": exc.code, "message": exc.user_message}
        if exc.retry_after:
            payload["retry_after"] = exc.retry_after
        yield "error", payload
    except ToolCallFailed:
        status = "error"
        yield (
            "error",
            {"code": "tool_call_failed", "message": "I couldn't look that up. Please try rephrasing your question."},
        )
    except (asyncio.CancelledError, GeneratorExit):
        status = "interrupted"  # client pressed Stop / disconnected
        raise
    finally:
        # Saved synchronously so it still happens while the request is being cancelled
        message_id = _save_reply(user_id, convo_id, "".join(text_parts), proposal, model, status)

    if status == "ok":
        yield "done", {"message_id": str(message_id), "model": model, "proposal": proposal}
