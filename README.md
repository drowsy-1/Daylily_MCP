# Daylily Publications MCP Server

An MCP (Model Context Protocol) server exposing the American Daylily Society publication archive — journals (1946–2025) and regional newsletters (1952–2026) — as searchable tools for Claude. The archive lives in a SQLite database with FTS5 full-text search.

## Tools

| Tool | Description |
|------|-------------|
| `search_daylily_publications` | Full-text search with relevance ranking. Supports quoted phrases and boolean `AND`/`OR`/`NOT`. Returns page snippets with source attribution. |
| `get_publication_page` | Retrieve the full text of a specific page (by document ID and page number). |
| `list_publications` | Browse the archive, filterable by type (journal, newsletter, yearbook, bulletin, enews), year range, or region. |
| `get_publication_info` | Metadata and a page-level overview for a specific publication. |

## Connecting to Claude (web / desktop)

The server is deployed on Railway at:

```
https://compassionate-freedom-production.up.railway.app
```

### Add the connector

1. In Claude, go to **Settings → Connectors** (claude.ai → your profile → Settings → Connectors).
2. Click **Add custom connector**.
3. Enter:
   - **Name:** Daylily Publications (or anything you like)
   - **URL:** `https://compassionate-freedom-production.up.railway.app/mcp`

   Note the `/mcp` path — the MCP endpoint is at `/mcp`, not the root URL (visiting the root in a browser shows `Cannot GET /`, which is expected).
4. Click **Add**. Claude will discover the server's OAuth metadata and walk through the authorization flow automatically. The server auto-approves the authorization request, so no login screen appears.
5. In a chat, open the tools/connectors menu and make sure the connector is enabled. Then just ask questions — e.g. *"Search the daylily archive for Stout Medal winners in the 1970s."*

### After a redeploy

OAuth tokens are held in memory, so every redeploy or restart invalidates them. Claude receives the standard OAuth "stale credentials" responses (`401 invalid_token` / `400 invalid_grant`) and silently re-authorizes on its next connection — no action needed. If a connector was added while the server was returning errors and appears stuck, remove it and re-add it once.

## Deployment (Railway)

The repo root `Dockerfile` builds the TypeScript server and downloads the database from this repo's Git LFS storage on GitHub during the build (rather than shipping it in the upload — a 343 MB context upload times out on slow connections; with the download approach `railway up` uploads under 1 MB). `.railwayignore` keeps the upload small, and `railway.json` configures the `/health` healthcheck.

When the database changes: commit and push it (it's LFS-tracked, so `git push` uploads it to GitHub), then bump the `DB_VERSION` arg in the Dockerfile so the Docker layer cache re-downloads it, and redeploy.

Required service variables:

| Variable | Value | Purpose |
|----------|-------|---------|
| `BASE_URL` | `https://<your-service-domain>` | Public URL advertised in the OAuth metadata. **Must** match the Railway domain or clients will try to authorize against the wrong host. |
| `MCP_TRANSPORT` | `http` | Set in the Dockerfile; selects the Streamable HTTP transport (default is `stdio`). |
| `PORT` | `8080` | Set in the Dockerfile; Railway's injected `PORT` overrides it if configured. |

Deploy by pushing to the linked repo, or with the CLI:

```sh
railway up
```

Sanity checks after deploy:

```sh
curl https://<domain>/health                                  # → {"status":"ok"}
curl https://<domain>/.well-known/oauth-authorization-server  # endpoints should show your domain, not localhost
```

## Running locally

```sh
cd mcp-server
npm install
npx tsc
```

**Stdio mode** (for Claude Desktop / Claude Code local config):

```sh
DB_PATH=../data/daylily.db node build/index.js
```

**HTTP mode:**

```sh
MCP_TRANSPORT=http PORT=8080 DB_PATH=../data/daylily.db node build/index.js
# server listens on http://localhost:8080/mcp
```

Requires the `sqlite3` CLI on the PATH (or set `SQLITE3_BIN`) for FTS5 queries.

## Repo layout

- `mcp-server/` — TypeScript MCP server (Express + `@modelcontextprotocol/sdk`, OAuth 2.1 with dynamic client registration)
- `data/daylily.db` — SQLite archive with FTS5 index
- `extraction/` — Python pipeline that extracted text from the publication PDFs and built the database
- `journals/`, `newsletters/` — source publications
