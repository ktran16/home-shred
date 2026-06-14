import type { NextConfig } from "next";

// In prod (docker) BACKEND_INTERNAL_URL = "http://backend:8000".
// In dev it defaults to the locally running uvicorn server.
const backendUrl = process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  // Small runtime image for self-hosting (SPEC §14.3).
  output: "standalone",
  // This box often previews through its LAN address; allow HMR for those dev origins.
  allowedDevOrigins: ["192.168.1.128", "192.168.1.194"],
  // Proxy /api/* to the backend so the browser only ever talks to the FE
  // origin — no CORS, no hardcoded backend IP (SPEC §14.4).
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backendUrl}/api/:path*` }];
  },
};

export default nextConfig;
