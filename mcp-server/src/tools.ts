import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import {
  searchPages,
  getPage,
  listDocuments,
  getDocumentInfo,
  formatSource,
} from "./db.js";

export function registerTools(server: McpServer): void {
  // Tool 1: Full-text search
  server.tool(
    "search_daylily_publications",
    "Search the American Daylily Society publication archive (journals 1946-2025, " +
      "regional newsletters 1952-2026). Uses full-text search with relevance ranking. " +
      "Returns matching page snippets with full source attribution (publication, issue, page number). " +
      "Supports phrases in quotes and boolean AND/OR/NOT operators.",
    {
      query: z
        .string()
        .describe(
          "Search query. Supports phrases in quotes and boolean AND/OR/NOT."
        ),
      year_from: z
        .number()
        .optional()
        .describe("Filter: minimum year (inclusive)"),
      year_to: z
        .number()
        .optional()
        .describe("Filter: maximum year (inclusive)"),
      doc_type: z
        .enum(["journal", "newsletter", "yearbook", "bulletin", "enews"])
        .optional()
        .describe("Filter by publication type"),
      region: z
        .number()
        .min(1)
        .max(15)
        .optional()
        .describe("Filter newsletters by AHS region number (1-15)"),
      limit: z
        .number()
        .min(1)
        .max(50)
        .default(20)
        .optional()
        .describe("Maximum results to return (default 20)"),
      offset: z
        .number()
        .min(0)
        .default(0)
        .optional()
        .describe("Offset for pagination"),
    },
    async ({ query, year_from, year_to, doc_type, region, limit, offset }) => {
      try {
        const results = await searchPages(query, limit ?? 20, offset ?? 0, {
          year_from,
          year_to,
          doc_type,
          region,
        });

        if (results.length === 0) {
          return {
            content: [
              {
                type: "text" as const,
                text: `No results found for "${query}". Try broader search terms or different filters.`,
              },
            ],
          };
        }

        const formatted = results
          .map((r) => {
            const source = formatSource(r);
            return `**${source}, page ${r.page_number}**\n(doc_id: ${r.document_id})\n\n${r.snippet}`;
          })
          .join("\n\n---\n\n");

        return {
          content: [
            {
              type: "text" as const,
              text: `Found ${results.length} results for "${query}":\n\n${formatted}`,
            },
          ],
        };
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        return {
          content: [{ type: "text" as const, text: `Search error: ${msg}` }],
          isError: true,
        };
      }
    }
  );

  // Tool 2: Get full page text
  server.tool(
    "get_publication_page",
    "Retrieve the full text of a specific page from a daylily publication. " +
      "Use after searching to read complete page content with source attribution.",
    {
      document_id: z.number().describe("Document ID from search results"),
      page_number: z.number().min(1).describe("Page number to retrieve"),
    },
    async ({ document_id, page_number }) => {
      const result = await getPage(document_id, page_number);
      if (!result) {
        return {
          content: [
            {
              type: "text" as const,
              text: `Document ${document_id}, page ${page_number} not found.`,
            },
          ],
          isError: true,
        };
      }

      const source = formatSource(result.document);

      return {
        content: [
          {
            type: "text" as const,
            text: `**${source}, page ${page_number}** (of ${result.document.page_count} pages)\nSource file: ${result.document.filename}\n\n---\n\n${result.page_text}`,
          },
        ],
      };
    }
  );

  // Tool 3: List/browse publications
  server.tool(
    "list_publications",
    "List available daylily publications with optional filters. " +
      "Useful for browsing what's in the archive by type, year range, or region.",
    {
      doc_type: z
        .enum(["journal", "newsletter", "yearbook", "bulletin", "enews"])
        .optional()
        .describe("Filter by publication type"),
      year_from: z.number().optional().describe("Minimum year (inclusive)"),
      year_to: z.number().optional().describe("Maximum year (inclusive)"),
      region: z
        .number()
        .min(1)
        .max(15)
        .optional()
        .describe("Filter by AHS region number"),
      limit: z
        .number()
        .min(1)
        .max(100)
        .default(50)
        .optional()
        .describe("Maximum results (default 50)"),
    },
    async ({ doc_type, year_from, year_to, region, limit }) => {
      const docs = await listDocuments({
        doc_type,
        year_from,
        year_to,
        region,
        limit: limit ?? 50,
      });

      if (docs.length === 0) {
        return {
          content: [
            {
              type: "text" as const,
              text: "No publications found matching the filters.",
            },
          ],
        };
      }

      const lines = docs.map((d) => {
        const source = formatSource(d);
        return `- **${source}** (${d.page_count} pages, doc_id: ${d.id})`;
      });

      return {
        content: [
          {
            type: "text" as const,
            text: `Found ${docs.length} publications:\n\n${lines.join("\n")}`,
          },
        ],
      };
    }
  );

  // Tool 4: Get document info (metadata + page TOC)
  server.tool(
    "get_publication_info",
    "Get detailed information about a specific publication, including " +
      "metadata and a page-level overview showing the first ~150 characters of each page.",
    {
      document_id: z.number().describe("Document ID"),
    },
    async ({ document_id }) => {
      const result = await getDocumentInfo(document_id);
      if (!result) {
        return {
          content: [
            {
              type: "text" as const,
              text: `Document ${document_id} not found.`,
            },
          ],
          isError: true,
        };
      }

      const source = formatSource(result.document);
      const meta = [
        `**${source}**`,
        `- Type: ${result.document.doc_type}`,
        `- File: ${result.document.filename}`,
        `- Pages: ${result.document.page_count}`,
        `- Total text: ${result.document.total_text_length.toLocaleString()} characters`,
      ];
      if (result.document.region != null) {
        meta.push(`- Region: ${result.document.region}`);
      }
      if (result.document.newsletter_name) {
        meta.push(`- Newsletter: ${result.document.newsletter_name}`);
      }

      const toc = result.page_previews
        .map(
          (p) =>
            `  Page ${p.page_number}: ${p.preview.replace(/\n/g, " ").trim()}`
        )
        .join("\n");

      return {
        content: [
          {
            type: "text" as const,
            text: `${meta.join("\n")}\n\n**Page overview:**\n${toc}`,
          },
        ],
      };
    }
  );
}
