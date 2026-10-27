import type { Page, Route } from "@playwright/test";

/**
 * Browser-side fake of the assistant API (/api/v1/assistant/*), so e2e tests and
 * screenshots never call a real model and always look the same. The rest of the app
 * (login, expenses, ...) still talks to the real backend.
 *
 * Replies are real answers the model gave for the seeded demo user
 * (docs/ASSISTANT_EXAMPLES.md), with digits as the server now sends them (0-9).
 */

export const REPLIES = {
  english: `**Short answer:** Spending is up ৳3,985 (9.6%) so far this month, and almost all of the increase comes from one category, "Random."

**Month-over-month (Sep 1–30 vs Oct 1–26)**
- September: ৳41,715 across 90 expenses
- October so far: ৳45,700 across 72 expenses

**What changed by category**
- **Random:** ৳985 → ৳9,180 (+৳8,195). A single ৳8,500 entry on Oct 14 ("Eid shopping, Bashundhara City") accounts for most of it.
- **Groceries:** ৳9,315 → ৳8,175 (−12.2%)
- **Food:** ৳5,845 → ৳4,845 (−17.1%)
- **Transport:** ৳3,670 → ৳3,205 (−12.7%)

**Where you can save**
1. **Plan for one-off big purchases.** Consider a separate "festival" budget or a savings goal for Eid, so it doesn't push Random far over.
2. **Bring Transport back under ৳2,500.** It's already ৳705 over with about five days left.
3. **Split "Random".** It's 20% of your spending; categories like Shopping or Gifts would show where it goes.`,
  bangla: `এই মাসের (1–26 অক্টোবর) বাজেটের অবস্থা ভালো নয়। দুটি খাত ইতিমধ্যে বাজেট ছাড়িয়ে গেছে, আর একটি ঝুঁকিতে আছে।

**বাজেটের অবস্থা**
- **Random (🎲):** বাজেট ৳3,000, খরচ ৳9,180 (306%)। 🔴
- **Transport (🚕):** বাজেট ৳2,500, খরচ ৳3,205 (128%)। 🔴
- **Groceries (🛒):** বাজেট ৳9,000, খরচ ৳8,175 (91%)। বাকি আছে ৳825। 🟠
- **Food (🍛):** বাজেট ৳7,000, খরচ ৳4,845 (69%)। 🟢`,
  quickAdd:
    "দুপুরের খাবারের জন্য ৳250 (Food, আজ) প্রস্তুত করেছি, এখনো সেভ হয়নি। কার্ডটি দেখে **Save expense** চাপুন।",
};

export interface MockState {
  configured: boolean;
  enabled: boolean;
  messagesToday: number;
  dailyLimit: number;
  conversations: { id: string; title: string; created_at: string; updated_at: string }[];
  confirmCalls: number;
  cancelCalls: number;
  /** Optional delay before a chat reply is sent, to show the "thinking" state */
  replyDelayMs: number;
}

const API = "**/api/v1/assistant";

function status(s: MockState) {
  const limited = s.messagesToday >= s.dailyLimit;
  const reason = !s.configured
    ? "not_configured"
    : !s.enabled
      ? "disabled"
      : limited
        ? "daily_limit"
        : null;
  return {
    configured: s.configured,
    enabled: s.enabled,
    available: reason === null,
    reason,
    message: limited
      ? `You've used all ${s.dailyLimit} assistant messages for today. They reset at midnight (Bangladesh time).`
      : null,
    messages_today: s.messagesToday,
    daily_limit: s.dailyLimit,
  };
}

function sse(events: [string, unknown][]) {
  return (
    ": stream open\n\n" +
    events.map(([e, d]) => `event: ${e}\ndata: ${JSON.stringify(d)}\n\n`).join("")
  );
}

/** Split an answer into small token events, like a real stream. */
function tokens(text: string): [string, unknown][] {
  return (text.match(/[\s\S]{1,24}/g) ?? []).map((t) => ["token", { text: t }]);
}

const QUICK_ADD_PROPOSAL = {
  amount: 250,
  category_id: "00000000-0000-0000-0000-00000000f00d",
  category_name: "Food",
  category_icon: "🍛",
  expense_date: new Date().toISOString().slice(0, 10),
  note: "দুপুরের খাবার",
};

function replyFor(message: string, conversationId: string, n: number): [string, unknown][] {
  const messageId = `00000000-0000-0000-0000-${String(n).padStart(12, "0")}`;
  const convo: [string, unknown] = [
    "conversation",
    { id: conversationId, title: message.slice(0, 60) },
  ];
  if (/২৫০|250|taka|টাকা/.test(message)) {
    return [
      convo,
      ["status", { text: "খরচটি প্রস্তুত করছি…", tool: "propose_expense" }],
      ["proposal", QUICK_ADD_PROPOSAL],
      ...tokens(REPLIES.quickAdd),
      ["done", { message_id: messageId, model: "mock/model", proposal: QUICK_ADD_PROPOSAL }],
    ];
  }
  const bangla = /[ঀ-৿]/.test(message);
  const text = bangla ? REPLIES.bangla : REPLIES.english;
  return [
    convo,
    [
      "status",
      {
        text: bangla ? "বাজেট দেখছি…" : "Checking your budgets…",
        tool: "get_budgets_status",
      },
    ],
    ...tokens(text),
    ["done", { message_id: messageId, model: "mock/model", proposal: null }],
  ];
}

export async function mockAssistant(page: Page, initial: Partial<MockState> = {}) {
  const state: MockState = {
    configured: true,
    enabled: true,
    messagesToday: 3,
    dailyLimit: 20,
    conversations: [],
    confirmCalls: 0,
    cancelCalls: 0,
    replyDelayMs: 0,
    ...initial,
  };
  let counter = 0;
  const json = (route: Route, body: unknown, code = 200) =>
    route.fulfill({ status: code, contentType: "application/json", body: JSON.stringify(body) });

  await page.route(`${API}/status`, (route) => json(route, status(state)));
  await page.route(`${API}/settings`, async (route) => {
    state.enabled = route.request().postDataJSON().enabled;
    return json(route, status(state));
  });
  await page.route(`${API}/conversations`, (route) =>
    json(route, {
      conversations: state.conversations,
      pagination: {
        page: 1,
        limit: 30,
        total_items: state.conversations.length,
        total_pages: 1,
      },
    })
  );
  await page.route(`${API}/chat`, async (route) => {
    const { message, conversation_id } = route.request().postDataJSON();
    const s = status(state);
    if (!s.available) {
      return json(
        route,
        {
          error: {
            code: s.reason,
            message: s.message,
            details: [{ field: "reason", message: s.reason }],
          },
        },
        429
      );
    }
    state.messagesToday += 1;
    counter += 1;
    const id = conversation_id ?? `00000000-0000-0000-0000-c0000000000${counter}`;
    if (!state.conversations.some((c) => c.id === id)) {
      const now = new Date().toISOString();
      state.conversations.unshift({
        id,
        title: message.slice(0, 60),
        created_at: now,
        updated_at: now,
      });
    }
    if (state.replyDelayMs) await new Promise((r) => setTimeout(r, state.replyDelayMs));
    return route
      .fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: sse(replyFor(message, id, counter)),
      })
      .catch(() => undefined); // the page may have pressed Stop (request aborted) meanwhile
  });
  await page.route(`${API}/messages/*/proposal/confirm`, (route) => {
    state.confirmCalls += 1;
    return json(route, {
      id: route.request().url().split("/messages/")[1].split("/")[0],
      role: "assistant",
      content: REPLIES.quickAdd,
      proposal: QUICK_ADD_PROPOSAL,
      proposal_status: "confirmed",
      expense_id: "00000000-0000-0000-0000-0000000000e1",
      status: "ok",
      created_at: new Date().toISOString(),
    });
  });
  await page.route(`${API}/messages/*/proposal/cancel`, (route) => {
    state.cancelCalls += 1;
    return json(route, {
      id: route.request().url().split("/messages/")[1].split("/")[0],
      role: "assistant",
      content: REPLIES.quickAdd,
      proposal: QUICK_ADD_PROPOSAL,
      proposal_status: "cancelled",
      expense_id: null,
      status: "ok",
      created_at: new Date().toISOString(),
    });
  });
  return state;
}
