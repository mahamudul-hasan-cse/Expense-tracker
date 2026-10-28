import type { ErrorEvent } from "@sentry/nextjs";

/**
 * Browser error reporting to Sentry, only when NEXT_PUBLIC_SENTRY_DSN was set at build
 * time. The SDK is loaded with a dynamic import, so without a DSN the app ships no
 * Sentry code at all. Never sends request bodies, cookies, headers or IP addresses.
 */
const DSN = process.env.NEXT_PUBLIC_SENTRY_DSN;

type SentryModule = typeof import("@sentry/nextjs");
let loading: Promise<SentryModule | null> | null = null;

/** Strip anything that could hold personal or secret data before an event is sent. */
export function scrubEvent(event: ErrorEvent): ErrorEvent | null {
  if (event.request) {
    delete event.request.data;
    delete event.request.cookies;
    delete event.request.headers;
    delete event.request.query_string;
  }
  if (event.user) event.user = event.user.id ? { id: event.user.id } : undefined;
  return event;
}

/** Start Sentry (once). Resolves to null when no DSN is configured. */
export function startSentry(): Promise<SentryModule | null> {
  if (!DSN) return Promise.resolve(null);
  loading ??= import("@sentry/nextjs").then((Sentry) => {
    Sentry.init({
      dsn: DSN,
      environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT || process.env.NODE_ENV,
      // No personal data by default in this SDK version; scrubEvent removes the rest
      tracesSampleRate: 0,
      beforeSend: scrubEvent,
    });
    return Sentry;
  });
  return loading;
}

/** Report an error caught by an error boundary. A no-op without a DSN. */
export function reportError(error: unknown): void {
  void startSentry().then((Sentry) => Sentry?.captureException(error));
}
