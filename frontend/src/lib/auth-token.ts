import { AuthResponse, User } from "@/types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// The access token lives only in memory; the long-lived refresh token is an
// httpOnly cookie the browser sends to /auth/* (JavaScript can't read it).
let accessToken: string | null = null;
let refreshPromise: Promise<User | null> | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null) {
  accessToken = token;
}

/**
 * Get a new access token from the refresh cookie. Concurrent callers share one
 * request. Resolves to the user, or null if the session is gone.
 */
export function refreshSession(): Promise<User | null> {
  if (!refreshPromise) {
    refreshPromise = fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      credentials: "include",
    })
      .then(async (res) => {
        if (!res.ok) {
          setAccessToken(null);
          return null;
        }
        const data: AuthResponse = await res.json();
        setAccessToken(data.access_token);
        return data.user;
      })
      .catch(() => {
        setAccessToken(null);
        return null;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

/** Send the user to the login page, remembering where they were. */
export function redirectToLogin(reason?: "expired") {
  if (typeof window === "undefined") return;
  const { pathname, search } = window.location;
  if (pathname.startsWith("/login") || pathname.startsWith("/register")) return;
  const params = new URLSearchParams({ next: pathname + search });
  if (reason) params.set("reason", reason);
  window.location.assign(`/login?${params.toString()}`);
}
