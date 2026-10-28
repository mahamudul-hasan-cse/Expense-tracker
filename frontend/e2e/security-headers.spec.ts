import { expect, test } from "@playwright/test";

/**
 * Security headers. Pages get them from next.config.mjs; proxied API responses (/api/*)
 * aren't touched by Next's headers() and carry the backend's own (backend/app/middleware.py).
 */
for (const path of ["/", "/login", "/dashboard"]) {
  test(`security headers on the page ${path}`, async ({ request }) => {
    const headers = (await request.get(path, { maxRedirects: 0 })).headers();
    expect(headers["x-content-type-options"]).toBe("nosniff");
    expect(headers["x-frame-options"]).toBe("DENY");
    expect(headers["content-security-policy"]).toContain("frame-ancestors 'none'");
    expect(headers["referrer-policy"]).toBe("strict-origin-when-cross-origin");
    expect(headers["permissions-policy"]).toContain("camera=()");
    expect(headers["x-powered-by"]).toBeUndefined();
  });
}

test("security headers on proxied API responses", async ({ request }) => {
  const headers = (await request.get("/api/v1/auth/me")).headers();
  expect(headers["x-content-type-options"]).toBe("nosniff");
  expect(headers["x-frame-options"]).toBe("DENY");
  expect(headers["referrer-policy"]).toBe("no-referrer");
  expect(headers["x-powered-by"]).toBeUndefined();
});
