# syntax=docker/dockerfile:1.7
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-alpine AS builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Relies on output:"standalone" in next.config.mjs. NEXT_PUBLIC_API_BASE_URL is
# deliberately left unset: .dockerignore keeps .env.local out of the context so
# the bundle falls back to the same-origin "/api/v1".
RUN npm run build

FROM node:22-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0
RUN addgroup -g 10001 -S nodejs && adduser -S -u 10001 -G nodejs nextjs

# standalone bundles its own minimal server and node_modules; static assets are
# not included in it and must be copied alongside. There is no public/ directory
# in this project, so it is intentionally not copied — that would fail the build.
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD wget -q --spider http://127.0.0.1:3000/login || exit 1

# server.js reads PORT and HOSTNAME. HOSTNAME=0.0.0.0 is required: the default
# binds loopback only and Caddy would get connection refused.
CMD ["node", "server.js"]
