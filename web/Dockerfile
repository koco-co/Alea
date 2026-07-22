FROM oven/bun:1.3.10-alpine AS deps
WORKDIR /app
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

FROM oven/bun:1.3.10-alpine AS builder
WORKDIR /app
ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY
ENV NEXT_PUBLIC_SUPABASE_URL=$NEXT_PUBLIC_SUPABASE_URL
ENV NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=$NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN bun run build

FROM deps AS development
COPY . .

FROM oven/bun:1.3.10-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN addgroup -S alea && adduser -S alea -G alea
COPY --from=builder --chown=alea:alea /app/.next/standalone ./
COPY --from=builder --chown=alea:alea /app/.next/static ./.next/static
COPY --from=builder --chown=alea:alea /app/public ./public
USER alea
EXPOSE 3000
CMD HOSTNAME=0.0.0.0 bun server.js
