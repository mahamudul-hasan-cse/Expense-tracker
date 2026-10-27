"""Chat endpoint with a scripted fake LLM (no network): flow, errors, limits, isolation."""

import copy
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional

import pytest

from app.assistant.llm_client import (
    Finished,
    LLMClient,
    LLMOutOfCredits,
    LLMRateLimited,
    TextDelta,
    ToolCall,
    ToolCallsReady,
    Usage,
)
from app.assistant.router import get_llm_client
from app.config import get_settings
from app.database import SessionLocal
from app.main import app
from app.models.assistant import AssistantMessage, AssistantUsage
from tests.conftest import register

API = "/api/v1"


class FakeLLM:
    """Plays back scripted rounds. Each round is a list of TextDelta / ToolCallsReady / Exception."""

    def __init__(self, rounds: list[list[Any]]):
        self.rounds = list(rounds)
        self.calls: list[dict[str, Any]] = []

    async def stream_chat(self, messages, tools, *, max_tokens, allow_tools=True, session_id: Optional[str] = None):
        self.calls.append({"messages": copy.deepcopy(messages), "allow_tools": allow_tools, "tools": tools})
        script = self.rounds.pop(0) if self.rounds else [TextDelta("Done.")]
        for item in script:
            if isinstance(item, Exception):
                raise item
            yield item
        yield Finished(
            "stop", Usage(model="fake/model", prompt_tokens=120, completion_tokens=30, cost_usd=Decimal("0.0002"))
        )


def tool_round(*calls: tuple[str, Any]) -> list[Any]:
    return [
        ToolCallsReady(
            [
                ToolCall(id=f"call_{i}", name=n, arguments=a if isinstance(a, str) else json.dumps(a))
                for i, (n, a) in enumerate(calls)
            ]
        )
    ]


@pytest.fixture
def use_llm():
    """Install a FakeLLM for the request(s); returns a setter."""
    holder: dict[str, FakeLLM] = {}

    def install(fake: FakeLLM) -> FakeLLM:
        holder["fake"] = fake
        app.dependency_overrides[get_llm_client] = lambda: holder["fake"]
        return fake

    yield install
    app.dependency_overrides.pop(get_llm_client, None)


@pytest.fixture
def enabled(client, auth_headers):
    assert client.put(f"{API}/assistant/settings", json={"enabled": True}, headers=auth_headers).status_code == 200
    return auth_headers


def sse(response) -> list[tuple[str, dict]]:
    events = []
    for block in response.text.split("\n\n"):
        lines = [line for line in block.splitlines() if not line.startswith(":")]
        if not lines:
            continue
        event = next(line[7:] for line in lines if line.startswith("event: "))
        data = json.loads(next(line[6:] for line in lines if line.startswith("data: ")))
        events.append((event, data))
    return events


def chat(client, headers, message, conversation_id=None):
    body = {"message": message}
    if conversation_id:
        body["conversation_id"] = conversation_id
    return client.post(f"{API}/assistant/chat", json=body, headers=headers)


# --- Safety: tests can't reach the real API -------------------------------------------------


def test_real_client_refuses_to_run_in_tests():
    assert get_settings().openrouter_api_key.get_secret_value() == ""
    with pytest.raises(RuntimeError, match="must not be used"):
        LLMClient(get_settings())


# --- Availability --------------------------------------------------------------------------------


def test_not_configured_without_key(client, auth_headers):
    status = client.get(f"{API}/assistant/status", headers=auth_headers).json()
    assert (status["configured"], status["available"], status["reason"]) == (False, False, "not_configured")
    res = chat(client, auth_headers, "hi")
    assert res.status_code == 503 and res.json()["error"]["details"][0]["message"] == "not_configured"


def test_off_by_default_until_user_opts_in(client, auth_headers, use_llm):
    use_llm(FakeLLM([]))
    status = client.get(f"{API}/assistant/status", headers=auth_headers).json()
    assert (status["configured"], status["enabled"], status["reason"]) == (True, False, "disabled")
    assert chat(client, auth_headers, "hi").status_code == 403
    on = client.put(f"{API}/assistant/settings", json={"enabled": True}, headers=auth_headers).json()
    assert (on["enabled"], on["available"], on["daily_limit"]) == (True, True, 20)


def test_daily_message_cap(client, enabled, use_llm, monkeypatch):
    monkeypatch.setattr(get_settings(), "assistant_daily_message_limit", 2)
    use_llm(FakeLLM([[TextDelta("one")], [TextDelta("two")]]))
    assert chat(client, enabled, "1").status_code == 200
    assert chat(client, enabled, "2").status_code == 200
    third = chat(client, enabled, "3")
    assert third.status_code == 429
    assert "all 2 assistant messages" in third.json()["error"]["message"]
    assert client.get(f"{API}/assistant/status", headers=enabled).json()["messages_today"] == 2


def test_global_daily_budget(client, enabled, use_llm, monkeypatch):
    monkeypatch.setattr(get_settings(), "assistant_global_daily_budget_usd", 0.0005)
    use_llm(FakeLLM([[TextDelta("a")], [TextDelta("b")], [TextDelta("c")]]))
    assert chat(client, enabled, "1").status_code == 200  # costs 0.0002
    assert chat(client, enabled, "2").status_code == 200  # 0.0004
    assert chat(client, enabled, "3").status_code == 200  # 0.0006 -> now over
    res = chat(client, enabled, "4")
    assert res.status_code == 503 and "today's usage limit" in res.json()["error"]["message"]


# --- Streaming and history -----------------------------------------------------------------------


def test_text_reply_streams_and_is_saved(client, enabled, use_llm):
    use_llm(FakeLLM([[TextDelta("Hello "), TextDelta("there!")]]))
    res = chat(client, enabled, "  hi  ")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/event-stream")
    assert "no-transform" in res.headers["cache-control"] and res.headers["x-accel-buffering"] == "no"
    events = sse(res)
    assert [e for e, _ in events] == ["conversation", "token", "token", "done"]
    convo_id = events[0][1]["id"]
    assert events[-1][1]["model"] == "fake/model"

    detail = client.get(f"{API}/assistant/conversations/{convo_id}", headers=enabled).json()
    assert detail["title"] == "hi"
    assert [(m["role"], m["content"]) for m in detail["messages"]] == [("user", "hi"), ("assistant", "Hello there!")]
    listed = client.get(f"{API}/assistant/conversations", headers=enabled).json()
    assert [c["id"] for c in listed["conversations"]] == [convo_id]


def test_bangla_digits_are_always_sent_as_english_digits(client, enabled, use_llm):
    """Real Bangla answers slipped into ০-৯ despite the prompt; the server enforces 0-9."""
    use_llm(FakeLLM([[TextDelta("এই মাসে ৳১২,"), TextDelta("৪৫০ খরচ (৩৮%), ২৭ অক্টোবর পর্যন্ত")]]))
    events = sse(chat(client, enabled, "এই মাসে কত খরচ?"))
    text = "".join(d["text"] for e, d in events if e == "token")
    assert text == "এই মাসে ৳12,450 খরচ (38%), 27 অক্টোবর পর্যন্ত"
    saved = client.get(f"{API}/assistant/conversations/{events[0][1]['id']}", headers=enabled).json()
    assert saved["messages"][-1]["content"] == text


def test_text_before_and_after_a_tool_call_stays_in_separate_paragraphs(client, enabled, use_llm):
    use_llm(FakeLLM([[TextDelta("Let me check."), *tool_round(("list_categories", {}))], [TextDelta("Food is top.")]]))
    events = sse(chat(client, enabled, "top category?"))
    assert "".join(d["text"] for e, d in events if e == "token") == "Let me check.\n\nFood is top."


def test_continuing_sends_recent_history(client, enabled, use_llm, monkeypatch):
    monkeypatch.setattr(get_settings(), "assistant_history_messages", 2)
    fake = use_llm(FakeLLM([[TextDelta("a1")], [TextDelta("a2")], [TextDelta("a3")]]))
    convo = sse(chat(client, enabled, "q1"))[0][1]["id"]
    chat(client, enabled, "q2", convo)
    chat(client, enabled, "q3", convo)
    sent = fake.calls[-1]["messages"]
    # system + only the 2 most recent stored messages + the new question
    assert [m["role"] for m in sent] == ["system", "user", "assistant", "user"]
    assert [m["content"] for m in sent[1:]] == ["q2", "a2", "q3"]
    assert "Asia/Dhaka" in json.dumps(sent[0]["content"])


def test_tool_call_flow_uses_server_side_user(client, enabled, use_llm):
    cat = client.get(f"{API}/categories", headers=enabled).json()["categories"][0]["id"]
    client.post(f"{API}/expenses", json={"amount": 750, "category_id": cat}, headers=enabled)
    other = register(client, "mallory@example.com")
    ocat = client.get(f"{API}/categories", headers=other).json()["categories"][0]["id"]
    client.post(f"{API}/expenses", json={"amount": 12345, "category_id": ocat, "note": "mallory"}, headers=other)

    fake = use_llm(
        FakeLLM(
            [
                tool_round(("list_expenses", {"limit": 10})),
                [TextDelta("You spent ৳750.")],
            ]
        )
    )
    events = sse(chat(client, enabled, "what did I spend?"))
    assert [e for e, _ in events] == ["conversation", "status", "token", "done"]
    assert events[1][1] == {"text": "Looking through your expenses…", "tool": "list_expenses"}
    tool_msg = fake.calls[1]["messages"][-1]
    assert tool_msg["role"] == "tool" and tool_msg["tool_call_id"] == "call_0"
    payload = json.loads(tool_msg["content"])
    assert [e["amount"] for e in payload["expenses"]] == [750]
    assert "12345" not in tool_msg["content"] and "mallory" not in tool_msg["content"]


def test_status_lines_follow_the_question_language(client, enabled, use_llm):
    use_llm(FakeLLM([tool_round(("get_budgets_status", {})), [TextDelta("ঠিক আছে")]]))
    events = sse(chat(client, enabled, "বাজেটের অবস্থা কেমন?"))
    assert dict(events)["status"] == {"text": "বাজেট দেখছি…", "tool": "get_budgets_status"}
    # Banglish is written in Latin letters: English status
    use_llm(FakeLLM([tool_round(("get_budgets_status", {})), [TextDelta("ok")]]))
    events = sse(chat(client, enabled, "budget er obostha kemon?"))
    assert dict(events)["status"]["text"] == "Checking your budgets…"


def test_category_names_are_in_the_context_as_data(client, enabled, use_llm):
    """Lets quick add call propose_expense directly instead of list_categories first."""
    fake = use_llm(FakeLLM([[TextDelta("ok")]]))
    sse(chat(client, enabled, "rickshaw 80"))
    context = fake.calls[0]["messages"][0]["content"][1]["text"]
    assert "expense categories (data):" in context and '"Rickshaw"' in context


def test_malformed_tool_call_gets_one_retry(client, enabled, use_llm):
    fake = use_llm(
        FakeLLM(
            [
                tool_round(("list_expenses", "{broken json")),
                tool_round(("list_expenses", {"limit": 5})),
                [TextDelta("ok")],
            ]
        )
    )
    events = sse(chat(client, enabled, "list"))
    assert events[-1][0] == "done"
    first_result = json.loads(fake.calls[1]["messages"][-1]["content"])
    assert first_result["error"] == "invalid arguments"


def test_second_malformed_tool_call_fails_gracefully(client, enabled, use_llm):
    use_llm(FakeLLM([tool_round(("list_expenses", "{bad")), tool_round(("get_budgets_status", {"month": "nope"}))]))
    events = sse(chat(client, enabled, "list"))
    assert events[-1] == (
        "error",
        {"code": "tool_call_failed", "message": "I couldn't look that up. Please try rephrasing your question."},
    )


def test_model_supplied_user_id_is_rejected(client, enabled, use_llm):
    fake = use_llm(
        FakeLLM([tool_round(("list_expenses", {"user_id": "00000000-0000-0000-0000-000000000000"})), [TextDelta("ok")]])
    )
    sse(chat(client, enabled, "show me"))
    assert json.loads(fake.calls[1]["messages"][-1]["content"])["error"] == "invalid arguments"


def test_answer_cut_off_by_token_limit_says_so(client, enabled, use_llm):
    class LengthLLM(FakeLLM):
        async def stream_chat(self, messages, tools, *, max_tokens, allow_tools=True, session_id=None):
            yield TextDelta("This answer runs out of")
            yield Finished("length", Usage(model="fake/model"))

    use_llm(LengthLLM([]))
    events = sse(chat(client, enabled, "long question"))
    text = "".join(d["text"] for e, d in events if e == "token")
    assert text.endswith("_(My answer was cut short — ask me to continue.)_")
    assert events[-1][0] == "done"


def test_tool_call_cap_forces_an_answer(client, enabled, use_llm, monkeypatch):
    monkeypatch.setattr(get_settings(), "assistant_max_tool_calls", 2)
    rounds = [tool_round(("list_categories", {}))] * 2 + [[TextDelta("final")]]
    fake = use_llm(FakeLLM(rounds))
    events = sse(chat(client, enabled, "loop"))
    assert [e for e, _ in events].count("status") == 2
    assert [c["allow_tools"] for c in fake.calls] == [True, True, False]
    assert events[-1][0] == "done"


@pytest.mark.parametrize(
    "error, code, retry_after",
    [
        (LLMOutOfCredits("402 from provider"), "out_of_credits", None),
        (LLMRateLimited("429", retry_after=7), "rate_limited", 7),
    ],
)
def test_provider_errors_are_mapped(client, enabled, use_llm, error, code, retry_after):
    use_llm(FakeLLM([[error]]))
    events = sse(chat(client, enabled, "hi"))
    kind, data = events[-1]
    assert kind == "error" and data["code"] == code
    assert data.get("retry_after") == retry_after
    assert "402 from provider" not in json.dumps(data)  # provider detail never reaches the user
    with SessionLocal() as db:
        statuses = [u.status for u in db.query(AssistantUsage).all()]
    assert code in statuses
    # The rest of the app keeps working
    assert client.get(f"{API}/expenses", headers=enabled).status_code == 200


def test_usage_recorded_without_content(client, enabled, use_llm):
    use_llm(FakeLLM([tool_round(("list_categories", {})), [TextDelta("secret words")]]))
    sse(chat(client, enabled, "my private question"))
    with SessionLocal() as db:
        rows = db.query(AssistantUsage).all()
    assert len(rows) == 2 and all(r.model == "fake/model" and r.cost_usd == Decimal("0.0002") for r in rows)
    dump = json.dumps([{c.name: str(getattr(r, c.name)) for c in r.__table__.columns} for r in rows])
    assert "private question" not in dump and "secret words" not in dump


# --- Quick add ------------------------------------------------------------------------------


def test_quick_add_proposal_requires_user_confirmation(client, enabled, use_llm):
    use_llm(
        FakeLLM(
            [
                tool_round(("propose_expense", {"amount": 80, "category": "rickshaw", "note": "office"})),
                [TextDelta("Please confirm the card.")],
            ]
        )
    )
    events = sse(chat(client, enabled, "rickshaw 80 taka today"))
    kinds = [e for e, _ in events]
    assert kinds == ["conversation", "status", "proposal", "token", "done"]
    proposal = dict(events)["proposal"]
    assert (proposal["amount"], proposal["category_name"], proposal["note"]) == (80, "Rickshaw", "office")
    # Nothing saved by the model
    assert client.get(f"{API}/expenses", headers=enabled).json()["pagination"]["total_items"] == 0

    convo = client.get(f"{API}/assistant/conversations/{events[0][1]['id']}", headers=enabled).json()
    reply = convo["messages"][-1]
    assert reply["id"] == dict(events)["done"]["message_id"]
    assert reply["proposal"]["amount"] == 80 and reply["proposal_status"] == "pending"
    assert reply["expense_id"] is None

    confirmed = confirm(client, enabled, reply["id"])
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["proposal_status"] == "confirmed"
    expenses = client.get(f"{API}/expenses", headers=enabled).json()["expenses"]
    assert len(expenses) == 1 and expenses[0]["id"] == confirmed.json()["expense_id"]
    assert (expenses[0]["amount"], expenses[0]["category"]["name"], expenses[0]["note"]) == (80, "Rickshaw", "office")
    # A confirmed card can't be cancelled
    assert cancel(client, enabled, reply["id"]).status_code == 409


def propose(client, headers, use_llm, amount=80, **extra) -> str:
    """Chat once with a scripted propose_expense call; return the proposal's message id."""
    args = {"amount": amount, "category": "rickshaw", **extra}
    use_llm(FakeLLM([tool_round(("propose_expense", args)), [TextDelta("Confirm the card.")]]))
    return dict(sse(chat(client, headers, f"rickshaw {amount}")))["done"]["message_id"]


def confirm(client, headers, message_id, edits=None):
    return client.post(f"{API}/assistant/messages/{message_id}/proposal/confirm", json=edits, headers=headers)


def cancel(client, headers, message_id):
    return client.post(f"{API}/assistant/messages/{message_id}/proposal/cancel", headers=headers)


def expense_count(client, headers) -> int:
    return client.get(f"{API}/expenses", headers=headers).json()["pagination"]["total_items"]


def test_confirm_is_idempotent(client, enabled, use_llm):
    """A double click or a retry after a lost response must not add a second expense."""
    message_id = propose(client, enabled, use_llm)
    first = confirm(client, enabled, message_id).json()
    second = confirm(client, enabled, message_id).json()
    assert second["expense_id"] == first["expense_id"] is not None
    assert expense_count(client, enabled) == 1


def test_concurrent_confirms_create_one_expense(client, enabled, use_llm):
    """Parallel confirms are serialized by the row lock: one expense, same id for everyone."""
    message_id = propose(client, enabled, use_llm)
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(lambda _: confirm(client, enabled, message_id), range(5)))
    assert [r.status_code for r in results] == [200] * 5
    assert len({r.json()["expense_id"] for r in results}) == 1
    assert expense_count(client, enabled) == 1


def test_confirm_with_edits_uses_manual_entry_validation(client, enabled, use_llm):
    message_id = propose(client, enabled, use_llm)
    # Same rules as POST /expenses: no future dates, no third decimal
    assert confirm(client, enabled, message_id, {"expense_date": "2999-01-01"}).status_code == 422
    assert confirm(client, enabled, message_id, {"amount": 1.234}).status_code == 422
    # Someone else's category is rejected like on the expense form
    bob = register(client, "bob@example.com")
    bob_category = client.get(f"{API}/categories", headers=bob).json()["categories"][0]["id"]
    foreign = confirm(client, enabled, message_id, {"category_id": bob_category})
    manual = client.post(f"{API}/expenses", json={"amount": 95, "category_id": bob_category}, headers=enabled)
    assert foreign.status_code == manual.status_code == 400
    assert expense_count(client, enabled) == 0

    saved = confirm(client, enabled, message_id, {"amount": 95, "note": "office, with tip"})
    assert saved.status_code == 200
    expense = client.get(f"{API}/expenses", headers=enabled).json()["expenses"][0]
    assert (expense["amount"], expense["note"]) == (95, "office, with tip")


def test_cancel_then_confirm_is_refused(client, enabled, use_llm):
    message_id = propose(client, enabled, use_llm)
    assert cancel(client, enabled, message_id).json()["proposal_status"] == "cancelled"
    assert cancel(client, enabled, message_id).status_code == 200  # cancelling twice is fine
    assert confirm(client, enabled, message_id).status_code == 409
    assert expense_count(client, enabled) == 0


def test_proposal_expires_after_24_hours(client, enabled, use_llm):
    message_id = propose(client, enabled, use_llm)
    with SessionLocal() as db:
        db.query(AssistantMessage).filter(AssistantMessage.id == message_id).update(
            {AssistantMessage.created_at: datetime.now(timezone.utc) - timedelta(hours=24, minutes=1)}
        )
        db.commit()
    convo_id = client.get(f"{API}/assistant/conversations", headers=enabled).json()["conversations"][0]["id"]
    messages = client.get(f"{API}/assistant/conversations/{convo_id}", headers=enabled).json()["messages"]
    reply = next(m for m in messages if m["id"] == message_id)
    assert reply["proposal_status"] == "expired"
    refused = confirm(client, enabled, message_id)
    assert refused.status_code == 409 and "expired" in refused.text
    assert expense_count(client, enabled) == 0
    # Dismissing an expired card is still allowed
    assert cancel(client, enabled, message_id).json()["proposal_status"] == "cancelled"


def test_deleting_the_expense_keeps_the_card_confirmed(client, enabled, use_llm):
    message_id = propose(client, enabled, use_llm)
    expense_id = confirm(client, enabled, message_id).json()["expense_id"]
    assert client.delete(f"{API}/expenses/{expense_id}", headers=enabled).status_code == 204
    again = confirm(client, enabled, message_id).json()
    assert again["proposal_status"] == "confirmed" and again["expense_id"] is None
    assert expense_count(client, enabled) == 0


def test_bangla_digits_proposal_via_tool(client, enabled, use_llm):
    """The model converts ২৫০ -> 250 before calling the tool; the server validates the result."""
    use_llm(
        FakeLLM(
            [
                tool_round(("propose_expense", {"amount": 250, "category": "Random", "note": "দুপুরের খাবার"})),
                [TextDelta("ঠিক আছে")],
            ]
        )
    )
    proposal = dict(sse(chat(client, enabled, "আজ দুপুরের খাবার ২৫০ টাকা")))["proposal"]
    assert proposal["amount"] == 250 and proposal["note"] == "দুপুরের খাবার"


# --- Isolation & deletion ------------------------------------------------------------------------


def test_conversations_are_private(client, enabled, use_llm):
    use_llm(FakeLLM([tool_round(("propose_expense", {"amount": 5, "category": "Random"})), [TextDelta("x")]]))
    events = sse(chat(client, enabled, "alice's private chat"))
    convo_id = events[0][1]["id"]
    message_id = client.get(f"{API}/assistant/conversations/{convo_id}", headers=enabled).json()["messages"][-1]["id"]

    bob = register(client, "bob@example.com")
    client.put(f"{API}/assistant/settings", json={"enabled": True}, headers=bob)
    assert client.get(f"{API}/assistant/conversations", headers=bob).json()["conversations"] == []
    assert client.get(f"{API}/assistant/conversations/{convo_id}", headers=bob).status_code == 404
    assert client.delete(f"{API}/assistant/conversations/{convo_id}", headers=bob).status_code == 404
    assert chat(client, bob, "continue alice's chat", convo_id).status_code == 404
    assert confirm(client, bob, message_id).status_code == 404
    assert cancel(client, bob, message_id).status_code == 404
    assert client.get(f"{API}/assistant/conversations/{convo_id}", headers=enabled).status_code == 200


def test_delete_one_and_clear_all(client, enabled, use_llm):
    use_llm(FakeLLM([[TextDelta("1")], [TextDelta("2")]]))
    first = sse(chat(client, enabled, "one"))[0][1]["id"]
    sse(chat(client, enabled, "two"))
    assert client.delete(f"{API}/assistant/conversations/{first}", headers=enabled).status_code == 204
    assert len(client.get(f"{API}/assistant/conversations", headers=enabled).json()["conversations"]) == 1
    assert client.delete(f"{API}/assistant/conversations", headers=enabled).status_code == 204
    assert client.get(f"{API}/assistant/conversations", headers=enabled).json()["conversations"] == []
    # Usage rows (no content) are kept for cost accounting
    with SessionLocal() as db:
        assert db.query(AssistantUsage).count() == 2


def test_endpoints_require_auth(client):
    for method, path in [
        ("get", "/assistant/status"),
        ("put", "/assistant/settings"),
        ("post", "/assistant/chat"),
        ("get", "/assistant/conversations"),
    ]:
        assert getattr(client, method)(f"{API}{path}").status_code == 401
