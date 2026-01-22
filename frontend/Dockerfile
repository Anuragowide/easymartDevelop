# Multi-stage build for Next.js frontend
# Production-ready for DigitalOcean deployment
FROM node:20-alpine AS base

LABEL maintainer="EasyMart Team"
LABEL description="EasyMart Frontend - Next.js"

# Install security updates
RUN apk upgrade --no-cache

# Enable Corepack for pnpm
RUN corepack enable && corepack prepare pnpm@9.14.0 --activate

# Install dependencies stage
FROM base AS deps
WORKDIR /app

# Install libc6-compat for Alpine compatibility
RUN apk add --no-cache libc6-compat

# Copy package files
COPY package.json pnpm-lock.yaml* ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Build stage
FROM base AS builder
WORKDIR /app

# Build-time environment variables (can be overridden in docker-compose)
ARG NEXT_PUBLIC_API_URL=http://node.gowideai.com
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

ARG NEXT_PUBLIC_ENABLE_FOLLOWUP_CHIPS=true
ENV NEXT_PUBLIC_ENABLE_FOLLOWUP_CHIPS=$NEXT_PUBLIC_ENABLE_FOLLOWUP_CHIPS

# Copy dependencies
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Ensure public directory exists
RUN mkdir -p public

# Disable telemetry during build
ENV NEXT_TELEMETRY_DISABLED=1

# Build Next.js application
RUN pnpm build

# Production stage
FROM base AS production
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Install runtime dependencies
RUN apk add --no-cache curl dumb-init

# Create non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy built application
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000 \
    HOSTNAME="0.0.0.0"

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:3000/ || exit 1

# Use dumb-init for proper signal handling
ENTRYPOINT ["/usr/bin/dumb-init", "--"]
CMD ["node", "server.js"]
