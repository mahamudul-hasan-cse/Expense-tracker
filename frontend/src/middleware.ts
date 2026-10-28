import { NextRequest, NextResponse } from "next/server";

/**
 * Tells the backend who the visitor is, for per-IP rate limits and logs.
 *
 * /api/* is proxied to the backend (next.config.mjs), so the backend only sees this
 * server's address. With PROXY_SHARED_SECRET set (the same value on the backend),
 * each proxied request carries X-Client-IP (the visitor's IP) and X-Proxy-Secret,
 * which the backend checks before trusting X-Client-IP (backend/app/client_ip.py).
 *
 * Only set the secret where the platform overwrites X-Real-IP / X-Forwarded-For with
 * the real client IP (Vercel does); a plain `next start` would pass a spoofed value on.
 */
export function middleware(request: NextRequest) {
  const headers = new Headers(request.headers);
  // Never forward these from the browser
  headers.delete("x-client-ip");
  headers.delete("x-proxy-secret");

  const secret = process.env.PROXY_SHARED_SECRET;
  if (secret) {
    const ip =
      request.headers.get("x-real-ip") ??
      request.headers.get("x-forwarded-for")?.split(",")[0]?.trim();
    if (ip) {
      headers.set("x-client-ip", ip);
      headers.set("x-proxy-secret", secret);
    }
  }
  return NextResponse.next({ request: { headers } });
}

export const config = { matcher: "/api/:path*" };
