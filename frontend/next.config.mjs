// The browser only ever talks to this app's own origin; /api/* is proxied to the
// FastAPI backend, so the refresh-token cookie is first-party (same-site).
// BACKEND_URL is read at build time (rewrites are baked into the build output).
const backendUrl = (process.env.BACKEND_URL || "http://localhost:8000").replace(/\/+$/, "");

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  // E2E runs build into their own folder so they don't clobber a running `next dev`
  distDir: process.env.NEXT_DIST_DIR || '.next',
  // No next/image usage: disable the Image Optimization API (several Next 14 advisories target it)
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
