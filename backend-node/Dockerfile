# Multi-stage build for Node.js backend
# Production-ready for DigitalOcean deployment
FROM node:20-alpine AS builder

LABEL maintainer="EasyMart Team"
LABEL description="EasyMart Node Backend - Builder"

# Install security updates
RUN apk upgrade --no-cache

# Enable Corepack for pnpm
RUN corepack enable && corepack prepare pnpm@9.14.0 --activate

# Set working directory
WORKDIR /app

# Copy package files
COPY package.json pnpm-lock.yaml* ./
COPY tsconfig.json ./

# Install dependencies
RUN pnpm install --frozen-lockfile --prod=false

# Copy source code
COPY src ./src

# Build TypeScript
RUN pnpm build

# Copy static UI files (not processed by TypeScript compiler)
RUN mkdir -p dist/modules/web/ui && \
    cp -r src/modules/web/ui/* dist/modules/web/ui/ || true

# Production stage
FROM node:20-alpine AS production

LABEL maintainer="EasyMart Team"
LABEL description="EasyMart Node Backend - Production"

# Install security updates
RUN apk upgrade --no-cache

# Enable Corepack for pnpm
RUN corepack enable && corepack prepare pnpm@9.14.0 --activate

# Set working directory
WORKDIR /app

# Install dumb-init and curl for health checks
RUN apk add --no-cache dumb-init curl

# Copy package files and install production dependencies
COPY package.json pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile --prod

# Copy built application from builder
COPY --from=builder /app/dist ./dist

# Create non-root user and set permissions
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001 -G nodejs && \
    chown -R nodejs:nodejs /app

USER nodejs

# Expose port
EXPOSE 3001

# Set environment
ENV NODE_ENV=production \
    PORT=3001

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3001/health', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})"

# Start application with dumb-init
ENTRYPOINT ["dumb-init", "--"]
CMD ["node", "dist/index.js"]
