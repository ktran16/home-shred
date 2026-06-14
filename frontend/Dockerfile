# syntax=docker/dockerfile:1

# --- Stage 1: deps ---
FROM node:22-slim AS deps
RUN corepack enable && corepack prepare pnpm@11.5.2 --activate
WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

# --- Stage 2: build (Next.js standalone, SPEC §14.3) ---
FROM node:22-slim AS builder
RUN corepack enable && corepack prepare pnpm@11.5.2 --activate
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
# Rewrites read BACKEND_INTERNAL_URL at runtime; arg kept for parity (SPEC §14.5).
ARG BACKEND_INTERNAL_URL=http://backend:8000
RUN pnpm build

# --- Stage 3: runtime ---
FROM node:22-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000
# node:22-slim already ships a uid-1000 "node" user.
COPY --from=builder /app/public ./public
COPY --from=builder --chown=node:node /app/.next/standalone ./
COPY --from=builder --chown=node:node /app/.next/static ./.next/static
USER node
EXPOSE 3000
CMD ["node", "server.js"]
