"""LLMClient parsing and error mapping, without any network (the SDK client is faked)."""

import asyncio
from decimal import Decimal
from types import SimpleNamespace as NS

import httpx
import openai
import pytest

from app.assistant.llm_client import (
    Finished,
    LLMClient,
    LLMMisconfigured,
    LLMOutOfCredits,
    LLMRateLimited,
    LLMTimeout,
    LLMUnavailable,
    TextDelta,
    ToolCallsReady,
    _map_status,
)
from app.config import Settings


def chunk(content=None, tool_calls=None, finish=None, usage=None, model="anthropic/claude-haiku-5.5"):
    delta = NS(content=content, tool_calls=tool_calls)
    return NS(model=model, usage=usage, choices=[NS(delta=delta, finish_reason=finish)])


def tc(index, id=None, name=None, args=None):
    return NS(index=index, id=id, function=NS(name=name, arguments=args))


class FakeStream:
    def __init__(self, chunks, error=None):
        self.chunks, self.error = chunks, error

    def __aiter__(self):
        return self._gen()

    async def _gen(self):
        for c in self.chunks:
            yield c
        if self.error:
            raise self.error


def make_client(create, **settings):
    """An LLMClient with a fake SDK underneath (bypasses the APP_ENV=test guard on purpose)."""
    client = object.__new__(LLMClient)
    client.settings = Settings(_env_file=None, **settings)
    client.models = client.settings.assistant_models
    client._client = NS(chat=NS(completions=NS(create=create)))
    return client


def collect(client, **kw):
    async def run():
        return [e async for e in client.stream_chat([{"role": "user", "content": "hi"}], [], max_tokens=50, **kw)]

    return asyncio.run(run())


def test_text_tool_fragments_and_usage_are_assembled():
    usage = NS(prompt_tokens=1200, completion_tokens=80, prompt_tokens_details=NS(cached_tokens=1000), cost=0.000325)
    chunks = [
        chunk(content="Let me "),
        chunk(content="check."),
        chunk(tool_calls=[tc(0, id="call_a", name="get_spending", args='{"start_')]),
        chunk(tool_calls=[tc(0, name="_summary", args='date": "2026-03-01",')]),
        chunk(tool_calls=[tc(1, id="call_b", name="list_categories", args="{}")]),
        chunk(tool_calls=[tc(0, args=' "end_date": "2026-03-20"}')], finish="tool_calls"),
        chunk(usage=usage),
    ]
    seen = {}

    async def create(**kwargs):
        seen.update(kwargs)
        return FakeStream(chunks)

    events = collect(make_client(create, assistant_fallback_models="openai/gpt-6-luna"), session_id="s1")
    assert [e.text for e in events if isinstance(e, TextDelta)] == ["Let me ", "check."]
    calls = next(e for e in events if isinstance(e, ToolCallsReady)).calls
    assert [(c.id, c.name, c.arguments) for c in calls] == [
        ("call_a", "get_spending_summary", '{"start_date": "2026-03-01", "end_date": "2026-03-20"}'),
        ("call_b", "list_categories", "{}"),
    ]
    done = events[-1]
    assert isinstance(done, Finished) and done.finish_reason == "tool_calls"
    assert (done.usage.prompt_tokens, done.usage.cached_tokens, done.usage.cost_usd) == (
        1200,
        1000,
        Decimal("0.000325"),
    )
    assert done.usage.model == "anthropic/claude-haiku-5.5"

    # Request shape: fallbacks, privacy routing, session, tools on
    body = seen["extra_body"]
    assert body["models"] == ["anthropic/claude-haiku-5.5", "openai/gpt-6-luna"]
    assert body["provider"] == {"data_collection": "deny", "require_parameters": True, "zdr": True}
    assert body["session_id"] == "s1"
    assert seen["tool_choice"] == "auto" and seen["stream"] is True and seen["max_tokens"] == 50


def test_zdr_can_be_turned_off_and_tools_disabled():
    seen = {}

    async def create(**kwargs):
        seen.update(kwargs)
        return FakeStream([chunk(content="ok", finish="stop")])

    collect(make_client(create, assistant_require_zdr=False), allow_tools=False)
    assert "zdr" not in seen["extra_body"]["provider"] and "models" not in seen["extra_body"]
    assert seen["tool_choice"] == "none"


def test_reasoning_effort_is_sent_only_when_set():
    seen = {}

    async def create(**kwargs):
        seen.update(kwargs)
        return FakeStream([chunk(content="ok", finish="stop")])

    collect(make_client(create))
    assert "reasoning" not in seen["extra_body"]  # the model's own default
    collect(make_client(create, assistant_reasoning_effort="low"))
    assert seen["extra_body"]["reasoning"] == {"effort": "low", "exclude": True}


def test_parallel_tool_calls_flag_is_opt_in():
    """Off by default: with zdr + require_parameters no Haiku endpoint accepts it (measured)."""
    seen = {}

    async def create(**kwargs):
        seen.clear()
        seen.update(kwargs)
        return FakeStream([chunk(content="ok", finish="stop")])

    collect(make_client(create))
    assert "parallel_tool_calls" not in seen
    collect(make_client(create, assistant_parallel_tool_calls=True))
    assert seen["parallel_tool_calls"] is True
    collect(make_client(create, assistant_parallel_tool_calls=True), allow_tools=False)
    assert "parallel_tool_calls" not in seen


def test_mid_stream_error_finish_reason():
    async def create(**kwargs):
        return FakeStream([chunk(content="par"), chunk(finish="error")])

    with pytest.raises(LLMUnavailable):
        collect(make_client(create))


def _status_error(code, headers=None):
    response = httpx.Response(
        code, headers=headers or {}, request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
    )
    return openai.APIStatusError("err", response=response, body={"error": {"message": f"provider says {code}"}})


@pytest.mark.parametrize(
    "code, expected",
    [
        (402, LLMOutOfCredits),
        (429, LLMRateLimited),
        (408, LLMTimeout),
        (401, LLMMisconfigured),
        (403, LLMMisconfigured),
        (502, LLMUnavailable),
        (503, LLMUnavailable),
        (404, LLMUnavailable),
    ],
)
def test_http_errors_are_mapped(code, expected):
    async def create(**kwargs):
        raise _status_error(code, {"retry-after": "12"} if code == 429 else None)

    with pytest.raises(expected) as info:
        collect(make_client(create))
    if code == 429:
        assert info.value.retry_after == 12
    assert "provider says" in str(info.value)  # detail kept for logs; user_message is separate
    assert "provider says" not in info.value.user_message


def test_timeouts_and_connection_errors():
    request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")

    async def timeout(**kwargs):
        raise openai.APITimeoutError(request=request)

    async def conn(**kwargs):
        raise openai.APIConnectionError(request=request)

    with pytest.raises(LLMTimeout):
        collect(make_client(timeout))
    with pytest.raises(LLMUnavailable):
        collect(make_client(conn))


def test_map_status_direct():
    assert isinstance(_map_status(402, "", None), LLMOutOfCredits)
    assert _map_status(429, "", 3).retry_after == 3


def test_missing_key_is_misconfigured_outside_tests():
    settings = Settings(_env_file=None, app_env="development", openrouter_api_key="")
    with pytest.raises(LLMMisconfigured):
        LLMClient(settings)


def test_key_never_appears_in_settings_repr():
    settings = Settings(_env_file=None, openrouter_api_key="sk-or-v1-supersecretvalue")
    assert "supersecretvalue" not in repr(settings) and "supersecretvalue" not in str(settings.model_dump())
