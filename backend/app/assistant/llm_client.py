"""The only module that knows about OpenRouter. Swap providers by replacing it.

Talks to OpenRouter's OpenAI-compatible API through the official `openai` SDK,
with model fallbacks, privacy routing (no data collection, optional ZDR),
attribution headers, usage/cost parsing and typed errors.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, AsyncIterator, Optional, Union

import openai
from openai import AsyncOpenAI

from app.config import Settings

logger = logging.getLogger("app.assistant.llm")

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


# --- Events yielded by stream_chat ---------------------------------------------


@dataclass
class TextDelta:
    text: str


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str  # raw JSON text from the model; parsed and validated by the tools layer


@dataclass
class ToolCallsReady:
    calls: list[ToolCall]


@dataclass
class Usage:
    model: Optional[str]
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0  # hidden "thinking" tokens, billed as output
    cost_usd: Decimal = Decimal("0")
    latency_ms: int = 0


@dataclass
class Finished:
    finish_reason: Optional[str]
    usage: Usage = field(default_factory=lambda: Usage(model=None))


LLMEvent = Union[TextDelta, ToolCallsReady, Finished]


# --- Errors ------------------------------------------------------------------------


class LLMError(Exception):
    """A provider failure, mapped to a stable code and a message safe to show users."""

    code = "unavailable"
    user_message = "The AI service is unavailable right now. Please try again later."

    def __init__(self, detail: str = "", retry_after: Optional[int] = None):
        super().__init__(detail or self.code)
        self.retry_after = retry_after


class LLMOutOfCredits(LLMError):
    code = "out_of_credits"
    user_message = "The assistant is temporarily unavailable."


class LLMRateLimited(LLMError):
    code = "rate_limited"
    user_message = "The assistant is busy right now. Please try again in a moment."


class LLMTimeout(LLMError):
    code = "timeout"
    user_message = "That took too long. Please try again, or ask a simpler question."


class LLMMisconfigured(LLMError):
    code = "misconfigured"
    user_message = "The assistant is not configured correctly."


class LLMUnavailable(LLMError):
    code = "unavailable"


def _map_status(status: int, detail: str, retry_after: Optional[int]) -> LLMError:
    if status == 402:
        return LLMOutOfCredits(detail)
    if status == 429:
        return LLMRateLimited(detail, retry_after)
    if status == 408:
        return LLMTimeout(detail)
    if status in (401, 403):
        return LLMMisconfigured(detail)
    return LLMUnavailable(detail)  # 400 (unsupported params), 404/502/503 (no provider / model down)


def _retry_after(exc: openai.APIStatusError) -> Optional[int]:
    value = exc.response.headers.get("retry-after") if exc.response is not None else None
    try:
        return int(float(value)) if value else None
    except ValueError:
        return None


# --- Client ------------------------------------------------------------------------


class LLMClient:
    """Streaming chat completions with tools via OpenRouter."""

    def __init__(self, settings: Settings):
        if settings.app_env == "test":
            # Tests must use a fake client; this guard makes a real call impossible
            raise RuntimeError("The real LLMClient must not be used when APP_ENV=test")
        api_key = settings.openrouter_api_key.get_secret_value()
        if not api_key:
            raise LLMMisconfigured("OPENROUTER_API_KEY is not set")
        self.settings = settings
        self.models = settings.assistant_models
        self._client = AsyncOpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=api_key,
            timeout=settings.assistant_timeout_seconds,
            max_retries=1,
            default_headers={
                "HTTP-Referer": settings.assistant_app_url,
                "X-OpenRouter-Title": settings.assistant_app_name,
                # Keep this personal app out of OpenRouter's public rankings
                "X-OpenRouter-App-Visibility": "hidden",
            },
        )

    def _provider_routing(self) -> dict[str, Any]:
        routing: dict[str, Any] = {
            "data_collection": "deny",  # only providers that don't store/train on prompts
            "require_parameters": True,  # only providers that support tools
        }
        if self.settings.assistant_require_zdr:
            routing["zdr"] = True  # Zero Data Retention endpoints only
        return routing

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        *,
        max_tokens: int,
        allow_tools: bool = True,
        session_id: Optional[str] = None,
    ) -> AsyncIterator[LLMEvent]:
        """Yield TextDelta events, then ToolCallsReady (if any), then Finished."""
        extra_body: dict[str, Any] = {"provider": self._provider_routing()}
        if len(self.models) > 1:
            extra_body["models"] = self.models  # OpenRouter fallback order
        if session_id:
            extra_body["session_id"] = session_id  # sticky routing keeps the prompt cache warm

        started = time.monotonic()
        partial: dict[int, dict[str, str]] = {}
        usage = Usage(model=None)
        finish_reason: Optional[str] = None
        try:
            # OpenRouter message/tool dicts (e.g. cache_control) are looser than the SDK's TypedDicts
            stream = await self._client.chat.completions.create(  # type: ignore[call-overload]
                model=self.models[0],
                messages=messages,
                tools=tools,
                tool_choice="auto" if allow_tools else "none",
                max_tokens=max_tokens,
                stream=True,
                extra_body=extra_body,
            )
            async for chunk in stream:
                if chunk.model:
                    usage.model = chunk.model
                if chunk.usage is not None:
                    usage = self._parse_usage(chunk.usage, usage.model)
                for choice in chunk.choices:
                    delta = choice.delta
                    if delta and delta.content:
                        yield TextDelta(delta.content)
                    for tc in (delta.tool_calls or []) if delta else []:
                        slot = partial.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
                        if tc.id:
                            slot["id"] = tc.id
                        if tc.function and tc.function.name:
                            slot["name"] += tc.function.name
                        if tc.function and tc.function.arguments:
                            slot["arguments"] += tc.function.arguments
                    if choice.finish_reason:
                        finish_reason = choice.finish_reason
                        if finish_reason == "error":
                            raise LLMUnavailable("provider reported an error mid-stream")
        except openai.APITimeoutError as exc:
            raise LLMTimeout(str(exc)) from None
        except openai.APIStatusError as exc:
            raise _map_status(exc.status_code, _safe_detail(exc), _retry_after(exc)) from None
        except openai.APIConnectionError as exc:
            raise LLMUnavailable(f"connection error: {type(exc).__name__}") from None
        except openai.APIError as exc:  # e.g. an error object inside the SSE stream
            raise LLMUnavailable(_safe_detail(exc)) from None

        usage.latency_ms = int((time.monotonic() - started) * 1000)
        if partial:
            calls = [
                ToolCall(id=s["id"] or f"call_{i}", name=s["name"], arguments=s["arguments"])
                for i, s in sorted(partial.items())
            ]
            yield ToolCallsReady(calls)
        yield Finished(finish_reason=finish_reason, usage=usage)

    @staticmethod
    def _parse_usage(raw: Any, model: Optional[str]) -> Usage:
        details = getattr(raw, "prompt_tokens_details", None)
        cached = getattr(details, "cached_tokens", 0) if details is not None else 0
        out_details = getattr(raw, "completion_tokens_details", None)
        reasoning = getattr(out_details, "reasoning_tokens", 0) if out_details is not None else 0
        cost = getattr(raw, "cost", None)
        if cost is None and getattr(raw, "model_extra", None):
            cost = raw.model_extra.get("cost")
        return Usage(
            model=model,
            prompt_tokens=raw.prompt_tokens or 0,
            completion_tokens=raw.completion_tokens or 0,
            cached_tokens=cached or 0,
            reasoning_tokens=reasoning or 0,
            cost_usd=Decimal(str(cost)) if cost is not None else Decimal("0"),
        )


def _safe_detail(exc: openai.APIError) -> str:
    """Error text for logs: the provider's message only (never request content or headers)."""
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        error = body.get("error", body)
        if isinstance(error, dict):
            return str(error.get("message", ""))[:300]
    try:
        return json.dumps(body)[:300] if body else str(exc)[:300]
    except TypeError:
        return str(exc)[:300]
