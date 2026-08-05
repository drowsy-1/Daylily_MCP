FROM node:22-slim

# Install sqlite3 CLI (needed for FTS5 queries) and curl (to fetch the database)
RUN apt-get update && apt-get install -y sqlite3 curl && rm -rf /var/lib/apt/lists/*

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

# Download the database from GitHub LFS instead of uploading it with the
# build context (343 MB — upload from local machines times out on slow
# connections). Bump DB_VERSION to bust the Docker layer cache after
# pushing an updated database to GitHub.
ARG DB_VERSION=1
RUN mkdir -p data && \
    curl -fL --retry 3 -o data/daylily.db \
      "https://media.githubusercontent.com/media/drowsy-1/Daylily_MCP/main/data/daylily.db" && \
    head -c 16 data/daylily.db | grep -q "SQLite format 3" || \
      (echo "Downloaded file is not a SQLite database (LFS pointer?)" && exit 1)

# Configure for Railway
ENV MCP_TRANSPORT=http
ENV DB_PATH=/app/data/daylily.db
ENV SQLITE3_BIN=/usr/bin/sqlite3
ENV PORT=8080

EXPOSE 8080

CMD ["node", "build/index.js"]
