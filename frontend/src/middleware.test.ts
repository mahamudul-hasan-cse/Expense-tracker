import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { middleware } from "./middleware";

// NextResponse.next({ request: { headers } }) passes the new request headers on as
// "x-middleware-request-<name>" response headers; read them back from there.
function forwarded(res: Response, name: string) {
  return res.headers.get(`x-middleware-request-${name}`);
}

function request(headers: Record<string, string>) {
  return new NextRequest("https://app.example.com/api/v1/expenses", { headers });
}

afterEach(() => vi.unstubAllEnvs());

describe("API proxy middleware", () => {
  it("adds the visitor's IP and the shared secret when configured", () => {
    vi.stubEnv("PROXY_SHARED_SECRET", "s".repeat(40));
    const res = middleware(request({ "x-real-ip": "203.0.113.7" }));
    expect(forwarded(res, "x-client-ip")).toBe("203.0.113.7");
    expect(forwarded(res, "x-proxy-secret")).toBe("s".repeat(40));
  });

  it("uses the first X-Forwarded-For entry when X-Real-IP is missing", () => {
    vi.stubEnv("PROXY_SHARED_SECRET", "s".repeat(40));
    const res = middleware(request({ "x-forwarded-for": "198.51.100.2, 10.0.0.1" }));
    expect(forwarded(res, "x-client-ip")).toBe("198.51.100.2");
  });

  it("never forwards a client-supplied IP or secret", () => {
    vi.stubEnv("PROXY_SHARED_SECRET", "");
    const res = middleware(request({ "x-client-ip": "1.2.3.4", "x-proxy-secret": "guess" }));
    expect(forwarded(res, "x-client-ip")).toBeNull();
    expect(forwarded(res, "x-proxy-secret")).toBeNull();
  });
});
