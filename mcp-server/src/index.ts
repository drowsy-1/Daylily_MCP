#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { mcpAuthRouter } from "@modelcontextprotocol/sdk/server/auth/router.js";
import { requireBearerAuth } from "@modelcontextprotocol/sdk/server/auth/middleware/bearerAuth.js";
import { getOAuthProtectedResourceMetadataUrl } from "@modelcontextprotocol/sdk/server/auth/router.js";
import express from "express";
import { registerTools } from "./tools.js";
import { oauthProvider } from "./auth.js";

const TRANSPORT = process.env.MCP_TRANSPORT ?? "stdio";
const PORT = parseInt(process.env.PORT ?? "8080", 10);
const BASE_URL = process.env.BASE_URL ?? `http://localhost:${PORT}`;

function createMcpServer(): McpServer {
  const server = new McpServer({
    name: "daylily-publications",
    version: "1.0.0",
  });
  registerTools(server);
  return server;
}

async function startHttp() {
  const app = express();

  const issuerUrl = new URL(BASE_URL);
  const mcpEndpointUrl = new URL("/mcp", BASE_URL);

  // OAuth auth router — handles /.well-known/*, /authorize, /token, /register, /revoke
  app.use(
    mcpAuthRouter({
      provider: oauthProvider,
      issuerUrl,
      baseUrl: issuerUrl,
      resourceServerUrl: mcpEndpointUrl,
      resourceName: "Daylily Publications MCP Server",
    })
  );

  // Health check (unauthenticated)
  app.get("/health", (_req, res) => {
    res.json({ status: "ok" });
  });

  // Bearer auth middleware for the MCP endpoint
  const resourceMetadataUrl = getOAuthProtectedResourceMetadataUrl(mcpEndpointUrl);
  const bearerAuth = requireBearerAuth({
    verifier: oauthProvider,
    resourceMetadataUrl,
  });

  // MCP endpoint — POST only, stateless
  app.post("/mcp", bearerAuth, async (req, res) => {
    try {
      const transport = new StreamableHTTPServerTransport({
        sessionIdGenerator: undefined,
      });
      const server = createMcpServer();
      await server.connect(transport);
      await transport.handleRequest(req, res, req.body);
      await transport.close();
      await server.close();
    } catch {
      if (!res.headersSent) {
        res.status(500).json({ error: "Internal server error" });
      }
    }
  });

  // GET and DELETE on /mcp — not supported in stateless mode
  app.all("/mcp", bearerAuth, (_req, res) => {
    res.status(405).json({ error: "Method not allowed in stateless mode" });
  });

  app.listen(PORT, "0.0.0.0", () => {
    console.error(`Daylily MCP Server running on ${BASE_URL}/mcp`);
  });
}

async function startStdio() {
  const server = createMcpServer();
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Daylily MCP Server running on stdio");
}

const starter = TRANSPORT === "http" ? startHttp : startStdio;
starter().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
