#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { createServer } from "http";
import { registerTools } from "./tools.js";

const TRANSPORT = process.env.MCP_TRANSPORT ?? "stdio";
const PORT = parseInt(process.env.PORT ?? "3000", 10);
const BEARER_TOKEN = process.env.BEARER_TOKEN;

function createMcpServer(): McpServer {
  const server = new McpServer({
    name: "daylily-publications",
    version: "1.0.0",
  });
  registerTools(server);
  return server;
}

async function startHttp() {
  const httpServer = createServer(async (req, res) => {
    // CORS headers
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization, Mcp-Session-Id");
    res.setHeader("Access-Control-Expose-Headers", "Mcp-Session-Id");

    if (req.method === "OPTIONS") {
      res.writeHead(204);
      res.end();
      return;
    }

    // Health check
    if (req.url === "/health") {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ status: "ok" }));
      return;
    }

    // Auth check
    if (BEARER_TOKEN) {
      const auth = req.headers.authorization;
      if (!auth || auth !== `Bearer ${BEARER_TOKEN}`) {
        res.writeHead(401, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: "Unauthorized" }));
        return;
      }
    }

    // Only handle /mcp
    if (req.url !== "/mcp") {
      res.writeHead(404, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "Not found" }));
      return;
    }

    // GET and DELETE not supported in stateless mode
    if (req.method === "GET" || req.method === "DELETE") {
      res.writeHead(405, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "Method not allowed in stateless mode" }));
      return;
    }

    if (req.method === "POST") {
      try {
        // Parse the request body
        const body = await new Promise<string>((resolve, reject) => {
          let data = "";
          req.on("data", (chunk) => (data += chunk));
          req.on("end", () => resolve(data));
          req.on("error", reject);
        });
        const parsedBody = JSON.parse(body);

        // Stateless: new transport + server per request
        const transport = new StreamableHTTPServerTransport({
          sessionIdGenerator: undefined,
        });
        const server = createMcpServer();
        await server.connect(transport);
        await transport.handleRequest(req, res, parsedBody);
        await transport.close();
        await server.close();
      } catch (e) {
        if (!res.headersSent) {
          res.writeHead(500, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ error: "Internal server error" }));
        }
      }
      return;
    }

    res.writeHead(405);
    res.end();
  });

  httpServer.listen(PORT, () => {
    console.error(`Daylily MCP Server running on http://0.0.0.0:${PORT}/mcp`);
    if (!BEARER_TOKEN) {
      console.error("WARNING: No BEARER_TOKEN set — server is unauthenticated");
    }
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
