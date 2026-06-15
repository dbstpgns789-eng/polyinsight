# PolyInsight 프론트엔드 (Next.js 16, standalone)
# ── build stage ──
FROM node:20-bookworm-slim AS build
WORKDIR /app

# NEXT_PUBLIC_* 는 빌드 시점에 클라이언트 번들로 인라인된다 → build arg 필수.
ARG NEXT_PUBLIC_POSTHOG_KEY=""
ARG NEXT_PUBLIC_POSTHOG_HOST="https://us.i.posthog.com"
ENV NEXT_PUBLIC_POSTHOG_KEY=$NEXT_PUBLIC_POSTHOG_KEY \
    NEXT_PUBLIC_POSTHOG_HOST=$NEXT_PUBLIC_POSTHOG_HOST

COPY package.json package-lock.json ./
COPY web/package.json ./web/package.json
RUN npm ci
COPY web ./web
RUN npm run build --workspace=web

# ── run stage ──
FROM node:20-bookworm-slim AS run
WORKDIR /app
ENV NODE_ENV=production \
    HOSTNAME=0.0.0.0 \
    PORT=3000

# standalone 번들(server.js + 최소 node_modules) + 정적 자산.
# 모노레포(workspaces)라 standalone 루트 안에 web/ 경로로 들어간다.
COPY --from=build /app/web/.next/standalone ./
COPY --from=build /app/web/.next/static ./web/.next/static
COPY --from=build /app/web/public ./web/public

EXPOSE 3000
CMD ["node", "web/server.js"]
