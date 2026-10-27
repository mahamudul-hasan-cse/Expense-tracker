import json
from datetime import date, datetime
from decimal import Decimal
from functools import lru_cache
from typing import Any, AsyncIterator, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.assistant.llm_client import LLMClient, LLMError
from app.assistant.service import (
    ChatModel,
    check_availability,
    generate_weekly_insight,
    messages_today,
    run_chat,
    spend_today,
)
from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user, get_user_category
from app.errors import error_response
from app.models.assistant import AssistantConversation, AssistantInsight, AssistantMessage
from app.models.user import User
from app.pagination import paginate
from app.routers.expenses import add_expense
from app.schemas.expense import ExpenseCreate, ExpenseUpdate
from app.schemas.pagination import PaginationInfo
from app.timeutil import today as app_today

router = APIRouter(prefix="/assistant", tags=["Assistant"])


@lru_cache()
def _client() -> LLMClient:
    return LLMClient(get_settings())


def get_llm_client() -> Optional[ChatModel]:
    """The configured LLM client, or None when no API key is set (assistant disabled)."""
    if not get_settings().openrouter_api_key.get_secret_value():
        return None
    return _client()


# --- Schemas -------------------------------------------------------------------------------


class StatusResponse(BaseModel):
    configured: bool
    enabled: bool  # the user's own opt-in
    available: bool
    reason: Optional[str]
    message: Optional[str]
    messages_today: int
    daily_limit: int


class SettingsUpdate(BaseModel):
    enabled: bool


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    conversation_id: Optional[UUID] = None


class ConversationSummary(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationListResponse(BaseModel):
    conversations: list[ConversationSummary]
    pagination: PaginationInfo


class MessageResponse(BaseModel):
    id: UUID
    role: Literal["user", "assistant"]
    content: str
    proposal: Optional[dict[str, Any]]
    # pending | confirmed | cancelled | expired (pending for longer than 24 hours)
    proposal_status: Optional[str] = Field(None, validation_alias="proposal_state")
    # The expense a confirmed proposal created (null if it was deleted later)
    expense_id: Optional[UUID] = Field(None, validation_alias="proposal_expense_id")
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationDetail(ConversationSummary):
    messages: list[MessageResponse]


# --- Endpoints -------------------------------------------------------------------------------


@router.get("/status", response_model=StatusResponse)
def get_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    llm: Optional[ChatModel] = Depends(get_llm_client),
):
    """Whether the assistant can be used right now, and why not if it can't."""
    settings = get_settings()
    availability = check_availability(db, current_user, settings, configured=llm is not None)
    return StatusResponse(
        configured=llm is not None,
        enabled=current_user.assistant_enabled,
        available=availability.available,
        reason=availability.code,
        message=availability.message,
        messages_today=messages_today(db, current_user.id),
        daily_limit=settings.assistant_daily_message_limit,
    )


@router.put("/settings", response_model=StatusResponse)
def update_settings(
    data: SettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    llm: Optional[ChatModel] = Depends(get_llm_client),
):
    """Turn the assistant on or off for this user (it's off by default)."""
    current_user.assistant_enabled = data.enabled
    db.commit()
    return get_status(db, current_user, llm)


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


@router.post("/chat")
async def chat(
    data: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    llm: Optional[ChatModel] = Depends(get_llm_client),
):
    """Send a message; the reply streams back as server-sent events.

    Events: conversation, status, token, proposal, then done or error.
    If the assistant can't be used, returns a normal JSON error instead of a stream.
    """
    settings = get_settings()
    availability = check_availability(db, current_user, settings, configured=llm is not None)
    if not availability.available or llm is None:
        return error_response(
            availability.status_code,
            availability.message or "Assistant unavailable",
            [{"field": "reason", "message": availability.code}],
        )
    if data.conversation_id is not None:
        owned = (
            db.query(AssistantConversation.id)
            .filter(AssistantConversation.id == data.conversation_id, AssistantConversation.user_id == current_user.id)
            .first()
        )
        if not owned:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    user_id = current_user.id

    async def stream() -> AsyncIterator[str]:
        yield ": stream open\n\n"  # comment line: flushes headers through proxies immediately
        async for event, payload in run_chat(llm, settings, user_id, data.conversation_id, data.message.strip()):
            yield _sse(event, payload)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",  # disable buffering in nginx-style proxies
            "Connection": "keep-alive",
        },
    )


@router.get("/conversations", response_model=ConversationListResponse)
def list_conversations(
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        db.query(AssistantConversation)
        .filter(AssistantConversation.user_id == current_user.id)
        .order_by(AssistantConversation.updated_at.desc(), AssistantConversation.id)
    )
    items, pagination = paginate(query, page, limit)
    return ConversationListResponse(conversations=items, pagination=pagination)


def _owned_conversation(db: Session, conversation_id: UUID, user: User) -> AssistantConversation:
    convo = (
        db.query(AssistantConversation)
        .filter(AssistantConversation.id == conversation_id, AssistantConversation.user_id == user.id)
        .first()
    )
    if not convo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return convo


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return _owned_conversation(db, conversation_id, current_user)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    db.delete(_owned_conversation(db, conversation_id, current_user))
    db.commit()
    return None


@router.delete("/conversations", status_code=status.HTTP_204_NO_CONTENT)
def delete_all_conversations(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Clear all chat history and cached insights for this user.

    Usage records (no content) are kept for cost accounting.
    """
    db.query(AssistantConversation).filter(AssistantConversation.user_id == current_user.id).delete()
    db.query(AssistantInsight).filter(AssistantInsight.user_id == current_user.id).delete()
    db.commit()
    return None


class InsightResponse(BaseModel):
    content: str
    generated_for: date
    cached: bool


@router.get("/insights/weekly", response_model=InsightResponse)
async def weekly_insight(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    llm: Optional[ChatModel] = Depends(get_llm_client),
):
    """This week's short insight, generated at most once per Asia/Dhaka day and cached.

    Counts toward the global daily budget, not the user's message limit.
    """
    settings = get_settings()
    if llm is None or not current_user.assistant_enabled:
        availability = check_availability(db, current_user, settings, configured=llm is not None)
        return error_response(
            availability.status_code,
            availability.message or "Assistant unavailable",
            [{"field": "reason", "message": availability.code}],
        )
    today = app_today()
    cached = _todays_insight(db, current_user.id, today)
    if cached:
        return InsightResponse(content=cached.content, generated_for=today, cached=True)
    if spend_today(db) >= Decimal(str(settings.assistant_global_daily_budget_usd)):
        return error_response(
            503,
            "The assistant has reached today's usage limit. It will be back tomorrow.",
            [{"field": "reason", "message": "daily_budget_reached"}],
        )
    user_id = current_user.id
    try:
        content = await generate_weekly_insight(llm, settings, user_id)
    except LLMError as exc:
        return error_response(503, exc.user_message, [{"field": "reason", "message": exc.code}])
    if not content:
        return error_response(503, "Couldn't write this week's insight. Try again later.", [])
    db.add(AssistantInsight(user_id=user_id, kind="weekly", generated_for=today, content=content))
    try:
        db.commit()
    except IntegrityError:  # another tab generated it at the same time: keep the first one
        db.rollback()
        existing = _todays_insight(db, user_id, today)
        if existing:
            return InsightResponse(content=existing.content, generated_for=today, cached=True)
    return InsightResponse(content=content, generated_for=today, cached=False)


def _todays_insight(db: Session, user_id: UUID, today: date) -> Optional[AssistantInsight]:
    return (
        db.query(AssistantInsight)
        .filter(
            AssistantInsight.user_id == user_id,
            AssistantInsight.kind == "weekly",
            AssistantInsight.generated_for == today,
        )
        .first()
    )


def _locked_proposal(db: Session, message_id: UUID, user: User) -> AssistantMessage:
    """The user's proposal message, row-locked until commit so concurrent confirms serialize."""
    message = (
        db.query(AssistantMessage)
        .filter(AssistantMessage.id == message_id, AssistantMessage.user_id == user.id)
        .with_for_update()
        .first()
    )
    if not message or message.proposal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")
    return message


@router.post("/messages/{message_id}/proposal/confirm", response_model=MessageResponse)
def confirm_proposal(
    message_id: UUID,
    edits: Optional[ExpenseUpdate] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Save a quick-add proposal as an expense (optionally with the user's edits from the card).

    Idempotent: a double click or a retry after a lost response returns the same
    message and expense_id instead of adding a second expense. Uses the same
    validation and category check as POST /expenses.
    """
    message = _locked_proposal(db, message_id, current_user)
    if message.proposal_status == "confirmed":
        db.rollback()  # release the lock; nothing to change
        return message
    if message.proposal_status == "cancelled":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Proposal was cancelled")
    if message.proposal_expired:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Proposal expired; ask again to log it")

    proposal = message.proposal or {}  # never None here: _locked_proposal checked it
    proposed = {k: proposal.get(k) for k in ("amount", "category_id", "expense_date", "note")}
    changes = edits.model_dump(exclude_unset=True) if edits else {}
    try:
        expense_data = ExpenseCreate.model_validate({**proposed, **changes})
    except ValidationError as exc:
        raise RequestValidationError(exc.errors(), body=changes) from exc

    expense = add_expense(db, current_user, expense_data)
    category = get_user_category(db, expense.category_id, current_user)
    # The card shows what was actually saved, including the user's edits
    message.proposal = {
        **proposal,
        "amount": float(expense.amount),
        "category_id": str(category.id),
        "category_name": category.name,
        "category_icon": category.icon,
        "expense_date": str(expense.expense_date),
        "note": expense.note,
    }
    message.proposal_status = "confirmed"
    message.proposal_expense_id = expense.id
    db.commit()
    db.refresh(message)
    return message


@router.post("/messages/{message_id}/proposal/cancel", response_model=MessageResponse)
def cancel_proposal(
    message_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Dismiss a quick-add proposal. Cancelling twice is fine; a confirmed one can't be cancelled."""
    message = _locked_proposal(db, message_id, current_user)
    if message.proposal_status == "confirmed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Proposal already saved; delete the expense instead"
        )
    if message.proposal_status != "cancelled":
        message.proposal_status = "cancelled"
    db.commit()
    db.refresh(message)
    return message
