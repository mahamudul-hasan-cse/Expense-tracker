import { AssistantUnavailableReason, ExpenseProposal } from "@/types";
import { ApiError, authedFetch, errorMessage } from "./api";

/** Server-sent events from POST /assistant/chat, in the order they can arrive. */
export type ChatEvent =
  | { event: "conversation"; data: { id: string; title: string } }
  | { event: "status"; data: { text: string; tool: string } }
  | { event: "token"; data: { text: string } }
  | { event: "proposal"; data: ExpenseProposal }
  | {
      event: "done";
      data: { message_id: string; model: string | null; proposal: ExpenseProposal | null };
    }
  | { event: "error"; data: { code: string; message: string; retry_after?: number } };

/** The chat request was refused before streaming (assistant off, daily limit, ...). */
export class AssistantUnavailableError extends ApiError {
  constructor(
    message: string,
    status: number,
    public reason: AssistantUnavailableReason | null
  ) {
    super(message, status);
  }
}

/**
 * Incremental SSE parser: feed it decoded text as it arrives, it calls `onEvent`
 * for every complete event. Comment lines (": ...") are ignored.
 */
export function createSSEParser(onEvent: (event: ChatEvent) => void) {
  let buffer = "";
  return (text: string) => {
    buffer += text.replace(/\r\n/g, "\n");
    let end: number;
    while ((end = buffer.indexOf("\n\n")) !== -1) {
      const block = buffer.slice(0, end);
      buffer = buffer.slice(end + 2);
      let name = "message";
      const data: string[] = [];
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) name = line.slice(6).trim();
        else if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
      }
      if (data.length === 0) continue;
      try {
        onEvent({ event: name, data: JSON.parse(data.join("\n")) } as ChatEvent);
      } catch {
        // A malformed event is skipped rather than breaking the whole answer
      }
    }
  };
}

/**
 * Send a message and stream the reply. Resolves when the stream ends; rejects with
 * AssistantUnavailableError when the server refuses, or an AbortError when stopped.
 */
export async function streamChat(
  message: string,
  conversationId: string | null,
  onEvent: (event: ChatEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const res = await authedFetch("/assistant/chat", {
    method: "POST",
    body: JSON.stringify({ message, conversation_id: conversationId ?? undefined }),
    headers: { Accept: "text/event-stream" },
    signal,
  });
  if (!res.ok || !res.body) {
    const body = await res.json().catch(() => ({}));
    const reason = body?.error?.details?.find?.(
      (d: { field?: string }) => d.field === "reason"
    )?.message;
    throw new AssistantUnavailableError(errorMessage(body), res.status, reason ?? null);
  }
  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  const push = createSSEParser(onEvent);
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    push(value);
  }
}
