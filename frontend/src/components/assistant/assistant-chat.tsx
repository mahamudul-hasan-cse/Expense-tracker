"use client";

import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  History,
  Loader2,
  MessageSquarePlus,
  RotateCcw,
  Send,
  Sparkles,
  Square,
  Trash2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { api } from "@/lib/api";
import { AssistantUnavailableError, ChatEvent, streamChat } from "@/lib/assistant-stream";
import {
  useAssistantStatus,
  useConversations,
  useDeleteConversation,
  useSetAssistantEnabled,
} from "@/lib/queries";
import { cn } from "@/lib/utils";
import { AssistantMessage, ExpenseProposal, ProposalStatus } from "@/types";
import { Markdown } from "./markdown";
import { OptInCard } from "./opt-in-card";
import { ProposalCard } from "./proposal-card";

export interface ChatItem {
  key: string;
  /** Server message id (assistant replies get it when the stream finishes) */
  id: string | null;
  role: "user" | "assistant";
  content: string;
  proposal: ExpenseProposal | null;
  proposalStatus: ProposalStatus | null;
  state: "streaming" | "ok" | "error" | "interrupted";
  statusText?: string;
  error?: string;
}

export const EXAMPLE_PROMPTS = [
  "How much did I spend this month?",
  "Where can I save money?",
  "Am I on track with my budgets?",
  "এই মাসে কত খরচ হলো?",
  "কোন খাতে বেশি খরচ হচ্ছে?",
  "rickshaw 80 taka today",
];

let keyCounter = 0;
const newKey = () => `m${++keyCounter}`;

function fromServer(m: AssistantMessage): ChatItem {
  return {
    key: m.id,
    id: m.id,
    role: m.role,
    content: m.content,
    proposal: m.proposal,
    proposalStatus: m.proposal_status,
    state: m.status === "ok" ? "ok" : m.status,
    error: m.status === "error" ? "This answer didn't finish." : undefined,
  };
}

export function AssistantChat() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const status = useAssistantStatus();
  const enable = useSetAssistantEnabled();
  const ready = !!status.data?.enabled && !!status.data?.configured;
  const conversations = useConversations(ready);
  const deleteConversation = useDeleteConversation();

  const [items, setItems] = useState<ChatItem[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [showHistory, setShowHistory] = useState(false);
  const [loadingConversation, setLoadingConversation] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const threadRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const streaming = items.some((i) => i.state === "streaming");

  // Keep the newest text in view while it streams in
  useEffect(() => {
    const el = threadRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [items]);

  // Stop a running answer when leaving the page
  useEffect(() => () => abortRef.current?.abort(), []);

  const update = (key: string, change: (item: ChatItem) => Partial<ChatItem>) =>
    setItems((all) => all.map((i) => (i.key === key ? { ...i, ...change(i) } : i)));

  const send = async (raw: string) => {
    const text = raw.trim();
    if (!text || streaming) return;
    setInput("");
    const replyKey = newKey();
    setItems((all) => [
      ...all,
      {
        key: newKey(),
        id: null,
        role: "user",
        content: text,
        proposal: null,
        proposalStatus: null,
        state: "ok",
      },
      {
        key: replyKey,
        id: null,
        role: "assistant",
        content: "",
        proposal: null,
        proposalStatus: null,
        state: "streaming",
        statusText: "Thinking…",
      },
    ]);

    const controller = new AbortController();
    abortRef.current = controller;
    let finished = false;
    const onEvent = (e: ChatEvent) => {
      switch (e.event) {
        case "conversation":
          setConversationId(e.data.id);
          break;
        case "status":
          update(replyKey, () => ({ statusText: e.data.text }));
          break;
        case "token":
          update(replyKey, (i) => ({ content: i.content + e.data.text, statusText: undefined }));
          break;
        case "proposal":
          update(replyKey, () => ({ proposal: e.data, proposalStatus: "pending" }));
          break;
        case "done":
          finished = true;
          update(replyKey, () => ({ id: e.data.message_id, state: "ok", statusText: undefined }));
          break;
        case "error":
          finished = true;
          update(replyKey, () => ({
            state: "error",
            error: e.data.message,
            statusText: undefined,
          }));
          break;
      }
    };

    try {
      await streamChat(text, conversationId, onEvent, controller.signal);
      if (!finished) {
        update(replyKey, () => ({
          state: "error",
          error: "The connection dropped before the answer finished.",
          statusText: undefined,
        }));
      }
    } catch (e) {
      if (controller.signal.aborted) {
        update(replyKey, () => ({ state: "interrupted", statusText: undefined }));
      } else {
        const message =
          e instanceof AssistantUnavailableError || e instanceof Error
            ? e.message
            : "Something went wrong.";
        update(replyKey, () => ({ state: "error", error: message, statusText: undefined }));
      }
    } finally {
      abortRef.current = null;
      queryClient.invalidateQueries({ queryKey: ["assistantStatus"] });
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
    }
  };

  const retry = (replyKey: string) => {
    const index = items.findIndex((i) => i.key === replyKey);
    const question = items[index - 1];
    if (!question || question.role !== "user") return;
    setItems((all) => all.filter((_, i) => i !== index && i !== index - 1));
    void send(question.content);
  };

  const openConversation = async (id: string) => {
    if (streaming) return;
    setLoadingConversation(true);
    setShowHistory(false);
    try {
      const detail = await api.getConversation(id);
      setConversationId(detail.id);
      setItems(detail.messages.map(fromServer));
    } catch {
      toast({ title: "Error", description: "Couldn't open that chat.", variant: "destructive" });
    } finally {
      setLoadingConversation(false);
    }
  };

  const newChat = () => {
    abortRef.current?.abort();
    setConversationId(null);
    setItems([]);
    setShowHistory(false);
    inputRef.current?.focus();
  };

  const removeConversation = (id: string | null) =>
    deleteConversation.mutate(id, {
      onSuccess: () => {
        if (id === null || id === conversationId) newChat();
        toast({ title: id ? "Chat deleted" : "All chats deleted" });
      },
    });

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    void send(input);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      void send(input);
    }
  };

  if (status.isLoading) {
    return (
      <div className="flex justify-center py-24">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }
  const s = status.data;
  if (!s || !s.configured) {
    return (
      <Card className="mx-auto max-w-xl">
        <CardContent className="py-10 text-center text-muted-foreground">
          The assistant isn&apos;t set up on this server yet.
        </CardContent>
      </Card>
    );
  }
  if (!s.enabled) {
    return (
      <OptInCard
        dailyLimit={s.daily_limit}
        pending={enable.isPending}
        onEnable={() =>
          enable.mutate(true, {
            onError: (e) =>
              toast({ title: "Error", description: e.message, variant: "destructive" }),
          })
        }
      />
    );
  }

  const left = Math.max(0, s.daily_limit - s.messages_today);
  const blocked = s.reason === "daily_limit" || s.reason === "daily_budget_reached";
  const history = conversations.data?.conversations ?? [];

  return (
    <div className="relative grid h-[calc(100dvh-7rem)] min-h-[28rem] gap-4 lg:grid-cols-[16rem_minmax(0,1fr)]">
      {/* History: sidebar on large screens, a toggled panel on phones */}
      <aside
        aria-label="Chat history"
        className={cn(
          "min-h-0 flex-col gap-2 overflow-hidden rounded-xl border bg-card p-3",
          showHistory
            ? "flex max-lg:absolute max-lg:inset-x-2 max-lg:top-14 max-lg:z-20 max-lg:max-h-[70dvh] max-lg:shadow-xl"
            : "hidden lg:flex"
        )}
      >
        <Button variant="outline" size="sm" onClick={newChat} className="justify-start">
          <MessageSquarePlus className="mr-2 h-4 w-4" />
          New chat
        </Button>
        <ul className="min-h-0 flex-1 space-y-1 overflow-y-auto">
          {history.length === 0 && (
            <li className="px-2 py-4 text-center text-sm text-muted-foreground">No chats yet</li>
          )}
          {history.map((c) => (
            <li key={c.id} className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => openConversation(c.id)}
                className={cn(
                  "min-w-0 flex-1 truncate rounded-md px-2 py-2 text-left text-sm hover:bg-muted",
                  c.id === conversationId && "bg-muted font-medium"
                )}
              >
                {c.title}
              </button>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 shrink-0 text-muted-foreground"
                aria-label={`Delete chat: ${c.title}`}
                onClick={() => removeConversation(c.id)}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </li>
          ))}
        </ul>
        {history.length > 0 && (
          <Button
            variant="ghost"
            size="sm"
            className="text-muted-foreground"
            onClick={() => {
              if (window.confirm("Delete all your assistant chats?")) removeConversation(null);
            }}
          >
            Delete all chats
          </Button>
        )}
      </aside>

      <section
        aria-label="Assistant chat"
        className="relative flex min-h-0 flex-col overflow-hidden rounded-xl border bg-card"
      >
        <header className="flex items-center justify-between gap-2 border-b px-4 py-3">
          <div className="flex min-w-0 items-center gap-2">
            <Sparkles className="h-5 w-5 shrink-0 text-primary" />
            <h1 className="truncate font-semibold">Assistant</h1>
          </div>
          <div className="flex items-center gap-1">
            <span className="mr-1 hidden text-xs text-muted-foreground sm:inline">
              {left} of {s.daily_limit} left today
            </span>
            <Button
              variant="ghost"
              size="icon"
              className="h-9 w-9 lg:hidden"
              aria-label="Chat history"
              aria-expanded={showHistory}
              onClick={() => setShowHistory((v) => !v)}
            >
              <History className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-9 w-9 lg:hidden"
              aria-label="New chat"
              onClick={newChat}
            >
              <MessageSquarePlus className="h-4 w-4" />
            </Button>
          </div>
        </header>

        <div ref={threadRef} role="log" className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
          {loadingConversation ? (
            <div className="flex justify-center py-16">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : items.length === 0 ? (
            <EmptyState onPick={(text) => void send(text)} disabled={blocked} />
          ) : (
            <div className="mx-auto max-w-3xl space-y-4">
              {items.map((item) =>
                item.role === "user" ? (
                  <div key={item.key} className="flex justify-end">
                    <p className="max-w-[85%] whitespace-pre-wrap break-words rounded-2xl rounded-br-sm bg-primary px-4 py-2 text-primary-foreground">
                      {item.content}
                    </p>
                  </div>
                ) : (
                  <AssistantBubble
                    key={item.key}
                    item={item}
                    onRetry={() => retry(item.key)}
                    onProposalChange={(m) =>
                      update(item.key, () => ({ proposalStatus: m.proposal_status }))
                    }
                  />
                )
              )}
            </div>
          )}
        </div>

        <div className="border-t p-3">
          {blocked ? (
            <p
              role="status"
              className="mx-auto max-w-3xl rounded-lg bg-muted px-4 py-3 text-sm text-muted-foreground"
            >
              {s.message}
            </p>
          ) : (
            <form onSubmit={onSubmit} className="mx-auto flex max-w-3xl items-end gap-2">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={onKeyDown}
                rows={1}
                maxLength={2000}
                placeholder="Ask about your money, or type an expense…"
                aria-label="Message the assistant"
                className="max-h-40 min-h-10 flex-1 resize-none rounded-md border border-input bg-background px-3 py-2 text-base ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:text-sm"
              />
              {streaming ? (
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  aria-label="Stop"
                  onClick={() => abortRef.current?.abort()}
                >
                  <Square className="h-4 w-4" />
                </Button>
              ) : (
                <Button type="submit" size="icon" aria-label="Send" disabled={!input.trim()}>
                  <Send className="h-4 w-4" />
                </Button>
              )}
            </form>
          )}
          <p className="mx-auto mt-2 max-w-3xl text-center text-xs text-muted-foreground">
            <span className="sm:hidden">
              {left} of {s.daily_limit} left today ·{" "}
            </span>
            AI can make mistakes. Check important numbers.
          </p>
        </div>
      </section>
    </div>
  );
}

function EmptyState({ onPick, disabled }: { onPick: (text: string) => void; disabled: boolean }) {
  return (
    <div className="mx-auto flex max-w-xl flex-col items-center py-8 text-center">
      <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10">
        <Sparkles className="h-6 w-6 text-primary" />
      </div>
      <h2 className="text-lg font-semibold">Ask about your money</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        English, বাংলা or Banglish. Answers use your own expenses, income, budgets and goals.
      </p>
      <div className="mt-6 flex flex-wrap justify-center gap-2">
        {EXAMPLE_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            type="button"
            disabled={disabled}
            onClick={() => onPick(prompt)}
            className="rounded-full border bg-background px-3 py-1.5 text-sm transition-colors hover:bg-muted disabled:opacity-50"
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
}

function AssistantBubble({
  item,
  onRetry,
  onProposalChange,
}: {
  item: ChatItem;
  onRetry: () => void;
  onProposalChange: (m: AssistantMessage) => void;
}) {
  const failed = item.state === "error" || item.state === "interrupted";
  return (
    <div className="flex gap-3" aria-busy={item.state === "streaming"}>
      <div className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10">
        <Sparkles className="h-3.5 w-3.5 text-primary" />
      </div>
      <div className="min-w-0 flex-1">
        {item.content && <Markdown text={item.content} />}
        {item.state === "streaming" && item.statusText && (
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            {item.statusText}
          </p>
        )}
        {item.proposal && item.proposalStatus && (
          <ProposalCard
            proposal={item.proposal}
            status={item.proposalStatus}
            messageId={item.state === "streaming" ? null : item.id}
            onChange={onProposalChange}
          />
        )}
        {failed && (
          <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
            <span className={item.state === "error" ? "text-destructive" : "text-muted-foreground"}>
              {item.state === "interrupted" ? "Stopped." : item.error}
            </span>
            <Button variant="outline" size="sm" className="h-8" onClick={onRetry}>
              <RotateCcw className="mr-1.5 h-3.5 w-3.5" />
              Retry
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
