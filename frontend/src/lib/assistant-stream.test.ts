import { describe, expect, it } from "vitest";
import { ChatEvent, createSSEParser } from "./assistant-stream";

function collect(chunks: string[]) {
  const events: ChatEvent[] = [];
  const push = createSSEParser((e) => events.push(e));
  chunks.forEach(push);
  return events;
}

describe("createSSEParser", () => {
  it("parses events split across arbitrary chunk boundaries", () => {
    const stream =
      ": stream open\n\n" +
      'event: conversation\ndata: {"id": "c1", "title": "Hi"}\n\n' +
      'event: token\ndata: {"text": "আজ ৳250"}\n\n' +
      'event: done\ndata: {"message_id": "m1", "model": "x", "proposal": null}\n\n';
    // Feed it 7 characters at a time, like a slow network
    const chunks = stream.match(/[\s\S]{1,7}/g)!;
    expect(collect(chunks)).toEqual([
      { event: "conversation", data: { id: "c1", title: "Hi" } },
      { event: "token", data: { text: "আজ ৳250" } },
      { event: "done", data: { message_id: "m1", model: "x", proposal: null } },
    ]);
  });

  it("waits for the blank line before emitting, and handles CRLF", () => {
    const events: ChatEvent[] = [];
    const push = createSSEParser((e) => events.push(e));
    push('event: token\r\ndata: {"text": "a"}\r\n');
    expect(events).toHaveLength(0);
    push("\r\n");
    expect(events).toEqual([{ event: "token", data: { text: "a" } }]);
  });

  it("skips comments and malformed data without stopping", () => {
    expect(
      collect([
        ": ping\n\n",
        "event: token\ndata: {broken\n\n",
        'event: token\ndata: {"text": "ok"}\n\n',
      ])
    ).toEqual([{ event: "token", data: { text: "ok" } }]);
  });
});
