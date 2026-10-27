import { defineConfig } from "@playwright/test";
import base from "./playwright.config";

/**
 * Captures UI screenshots into ../docs/screenshots (not a test suite):
 *   npm run screenshots
 * Seeds the demo user (backend/scripts/seed_demo.py) into E2E_DATABASE_URL first.
 */
export default defineConfig({
  ...base,
  testDir: "./screenshots",
  retries: 0,
  reporter: "list",
  timeout: 180_000,
  use: {
    ...base.use,
    // Full-page captures resize the viewport; with animations on, charts are caught
    // mid-re-animation (bars bunched at the left). The app honours reduced motion.
    reducedMotion: "reduce",
  },
  projects: [
    {
      name: "desktop",
      use: { viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 },
    },
    {
      name: "mobile",
      use: {
        viewport: { width: 375, height: 812 },
        deviceScaleFactor: 2,
        isMobile: true,
        hasTouch: true,
      },
    },
  ],
});
