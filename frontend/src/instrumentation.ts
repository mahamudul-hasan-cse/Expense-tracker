// Server-side error reporting (pages rendered on the server, middleware), only when
// SENTRY_DSN is set. Loaded lazily so nothing runs without a DSN.

export async function register() {
  if (!process.env.SENTRY_DSN) return;
  const Sentry = await import("@sentry/nextjs");
  Sentry.init({
    dsn: process.env.SENTRY_DSN,
    environment: process.env.SENTRY_ENVIRONMENT || process.env.NODE_ENV,
    tracesSampleRate: 0,
    // No personal data by default in this SDK version; also drop request details
    beforeSend(event) {
      if (event.request) {
        delete event.request.data;
        delete event.request.cookies;
        delete event.request.headers;
        delete event.request.query_string;
      }
      return event;
    },
  });
}

type CaptureArgs = Parameters<typeof import("@sentry/nextjs").captureRequestError>;

export async function onRequestError(...args: CaptureArgs) {
  if (!process.env.SENTRY_DSN) return;
  const Sentry = await import("@sentry/nextjs");
  Sentry.captureRequestError(...args);
}
