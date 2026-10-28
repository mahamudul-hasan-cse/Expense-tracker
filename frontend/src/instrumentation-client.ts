// Runs in the browser before the app starts. Sentry (if NEXT_PUBLIC_SENTRY_DSN is set)
// then catches uncaught errors and unhandled promise rejections on every page.
import { startSentry } from "@/lib/sentry";

void startSentry();
