// The browser only ever talks to this app's own origin; /api/* is proxied to the
// FastAPI backend, so the refresh-token cookie is first-party (same-site).
// BACKEND_URL is read at build time (rewrites are baked into the build output).
const backendUrl = (process.env.BACKEND_URL || "http://localhost:8000").replace(/\/+$/, "");

// Sent with every page and API response. The CSP only restricts framing, <base>, form
// targets and plugins, so it can't break Next.js's own scripts.
const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "X-Frame-Options", value: "DENY" },
  {
    key: "Content-Security-Policy",
    value: "frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'",
  },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=()" },
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains" },
];

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  poweredByHeader: false,
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
  // E2E runs build into their own folder so they don't clobber a running `next dev`
  distDir: process.env.NEXT_DIST_DIR || ".next",
  // Image Optimization API off (several advisories have targeted it); the only images are
  // pre-sized WebP files in public/, served as-is
  images: { unoptimized: true },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
