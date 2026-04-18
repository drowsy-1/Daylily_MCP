FROM node:22-slim

# Install sqlite3 CLI (needed for FTS5 queries)
RUN apt-get update && apt-get install -y sqlite3 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install all dependencies (including dev for build)
COPY mcp-server/package.json mcp-server/package-lock.json ./
RUN npm ci

# Copy source and build
COPY mcp-server/src ./src
COPY mcp-server/tsconfig.json ./
RUN npx tsc

# Remove dev dependencies after build
RUN npm prune --omit=dev

# Copy the database
COPY data/daylily.db ./data/daylily.db

# Configure for Railway
ENV MCP_TRANSPORT=http
ENV DB_PATH=/app/data/daylily.db
ENV SQLITE3_BIN=/usr/bin/sqlite3
ENV PORT=3000

EXPOSE 3000

CMD ["node", "build/index.js"]
