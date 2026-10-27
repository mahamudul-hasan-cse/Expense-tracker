import { describe, expect, it } from "vitest";
import type { ErrorEvent } from "@sentry/nextjs";
import { reportError, scrubEvent, startSentry } from "./sentry";

describe("Sentry (browser)", () => {
  it("does nothing without NEXT_PUBLIC_SENTRY_DSN", async () => {
    expect(await startSentry()).toBeNull();
    expect(() => reportError(new Error("x"))).not.toThrow();
  });

  it("strips bodies, cookies, headers, query strings and user details", () => {
    const event = {
      type: undefined,
      request: {
        url: "https://app.example.com/expenses",
        data: { note: "private" },
        cookies: { refresh_token: "secret" },
        headers: { Authorization: "Bearer abc" },
        query_string: "search=salary",
      },
      user: { id: "u1", email: "alice@example.com", ip_address: "203.0.113.7" },
    } as unknown as ErrorEvent;
    const scrubbed = scrubEvent(event)!;
    expect(scrubbed.request).toEqual({ url: "https://app.example.com/expenses" });
    expect(scrubbed.user).toEqual({ id: "u1" });
  });
});
