import json
from datetime import datetime
from functools import lru_cache
from typing import Any, AsyncIterator, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.assistant.llm_client import LLMClient
from app.assistant.service import ChatModel, check_availability, messages_today, run_chat
from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user
from app.errors import error_response
from app.models.assistant import AssistantConversation, AssistantMessage
from app.models.user import User
from app.pagination import paginate
from app.schemas.pagination import PaginationInfo

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

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    conversations: list[ConversationSummary]
    pagination: PaginationInfo


class MessageResponse(BaseModel):
    id: UUID
    role: Literal["user", "assistant"]
    content: str
    proposal: Optional[dict[str, Any]]
    proposal_status: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationDetail(ConversationSummary):
    messages: list[MessageResponse]


class ProposalUpdate(BaseModel):
    status: Literal["confirmed", "cancelled"]


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
    """Clear all chat history for this user (usage records without content are kept for cost accounting)."""
    db.query(AssistantConversation).filter(AssistantConversation.user_id == current_user.id).delete()
    db.commit()
    return None


@router.patch("/messages/{message_id}/proposal", response_model=MessageResponse)
def update_proposal(
    message_id: UUID,
    data: ProposalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record what the user did with a quick-add proposal.

    Confirming here only records the choice; the expense itself is created by the
    client through the normal POST /expenses endpoint and its validation.
    """
    message = (
        db.query(AssistantMessage)
        .filter(AssistantMessage.id == message_id, AssistantMessage.user_id == current_user.id)
        .first()
    )
    if not message or message.proposal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")
    if message.proposal_status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Proposal already {message.proposal_status}"
        )
    message.proposal_status = data.status
    db.commit()
    db.refresh(message)
    return message
