import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  cacheComponents: true,
  partialPrefetching: true,
  // Project instructions live in CLAUDE.md; skip Next.js's auto-generated AGENTS.md.
  agentRules: false,
  // Every screen has real content pinned to both bottom corners (sidebar status panel on the
  // left, primary action bar on the right), so repositioning the dev-only build indicator just
  // moves which one it covers. Disabling it is the only overlap-free option; it has no effect
  // on production builds.
  devIndicators: false,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
