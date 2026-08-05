import { execFileSync } from "child_process";
import initSqlJs, { type Database } from "sql.js";
import { readFileSync } from "fs";
import { dirname, resolve } from "path";
import { fileURLToPath } from "url";
import type { DocumentRow, SearchResult } from "./types.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const DB_PATH = process.env.DB_PATH ?? resolve(__dirname, "../../data/daylily.db");
const SQLITE3_BIN = process.env.SQLITE3_BIN ?? "/usr/bin/sqlite3";

// sql.js for non-FTS queries (get_page, list, info)
let db: Database | null = null;

async function getDb(): Promise<Database> {
  if (db) return db;
  const SQL = await initSqlJs();
  const buffer = readFileSync(DB_PATH);
  db = new SQL.Database(buffer);
  return db;
}

/**
 * Run a query using the system sqlite3 CLI (has FTS5 support).
 * Returns results as JSON array of objects.
 */
function queryWithSystemSqlite(sql: string): Record<string, unknown>[] {
  const result = execFileSync(SQLITE3_BIN, [DB_PATH, "-json", sql], {
    encoding: "utf-8",
    maxBuffer: 10 * 1024 * 1024, // 10MB
    timeout: 30000,
  });
  if (!result.trim()) return [];
  return JSON.parse(result);
}

export function formatSource(r: {
  doc_type: string;
  year: number;
  volume: number | null;
  issue_number: number | null;
  season: string | null;
  region: number | null;
  newsletter_name: string | null;
}): string {
  if (r.doc_type === "journal") {
    let s = "The Daylily Journal";
    if (r.volume != null && r.issue_number != null) {
      s += ` Vol. ${r.volume}, No. ${r.issue_number}`;
    }
    s += r.season ? ` (${r.season} ${r.year})` : ` (${r.year})`;
    return s;
  }
  if (r.doc_type === "newsletter") {
    let s = r.region != null ? `Region ${r.region}` : "Newsletter";
    if (r.newsletter_name) s += ` '${r.newsletter_name}'`;
    else s += " Newsletter";
    if (r.issue_number != null) s += `, Issue ${r.issue_number}`;
    s += r.season ? ` (${r.season} ${r.year})` : ` (${r.year})`;
    return s;
  }
  if (r.doc_type === "yearbook") return `AHS Yearbook (${r.year})`;
  if (r.doc_type === "bulletin")
    return `AHS Bulletin ${r.issue_number ?? ""} (${r.year})`;
  if (r.doc_type === "enews") {
    return r.season
      ? `Daylily E-News/Dispatch (${r.season} ${r.year})`
      : `Daylily E-News/Dispatch (${r.year})`;
  }
  return `Daylily Publication (${r.year})`;
}

export async function searchPages(
  query: string,
  limit: number = 20,
  offset: number = 0,
  filters?: {
    year_from?: number;
    year_to?: number;
    doc_type?: string;
    region?: number;
  }
): Promise<SearchResult[]> {
  const conditions: string[] = ["d.is_duplicate = 0"];

  if (filters?.year_from) {
    conditions.push(`d.year >= ${Number(filters.year_from)}`);
  }
  if (filters?.year_to) {
    conditions.push(`d.year <= ${Number(filters.year_to)}`);
  }
  if (filters?.doc_type) {
    conditions.push(`d.doc_type = '${escapeSql(filters.doc_type)}'`);
  }
  if (filters?.region) {
    conditions.push(`d.region = ${Number(filters.region)}`);
  }

  const safeQuery = sanitizeFtsQuery(query);
  const whereClause = conditions.join(" AND ");

  const sql = `
    SELECT
      p.id AS page_id,
      d.id AS document_id,
      d.doc_type,
      d.year,
      d.volume,
      d.issue_number,
      d.season,
      d.region,
      d.newsletter_name,
      d.filename,
      p.page_number,
      snippet(pages_fts, 0, '**', '**', '...', 40) AS snippet,
      pages_fts.rank AS rank
    FROM pages_fts
    JOIN pages p ON p.id = pages_fts.rowid
    JOIN documents d ON p.document_id = d.id
    WHERE ${whereClause}
      AND pages_fts MATCH '${escapeSql(safeQuery)}'
    ORDER BY pages_fts.rank
    LIMIT ${Number(limit)} OFFSET ${Number(offset)};
  `;

  try {
    const rows = queryWithSystemSqlite(sql);
    return rows as unknown as SearchResult[];
  } catch (e) {
    const message = e instanceof Error ? e.message : String(e);
    throw new Error(`Search failed: ${message}`);
  }
}

export async function getPage(
  documentId: number,
  pageNumber: number
): Promise<{ document: DocumentRow; page_text: string } | null> {
  const database = await getDb();

  const docStmt = database.prepare(
    "SELECT * FROM documents WHERE id = ?"
  );
  docStmt.bind([documentId]);
  if (!docStmt.step()) {
    docStmt.free();
    return null;
  }
  const document = docStmt.getAsObject() as unknown as DocumentRow;
  docStmt.free();

  const pageStmt = database.prepare(
    "SELECT text_content FROM pages WHERE document_id = ? AND page_number = ?"
  );
  pageStmt.bind([documentId, pageNumber]);
  if (!pageStmt.step()) {
    pageStmt.free();
    return null;
  }
  const page_text = pageStmt.getAsObject().text_content as string;
  pageStmt.free();

  return { document, page_text };
}

export async function listDocuments(filters?: {
  doc_type?: string;
  year_from?: number;
  year_to?: number;
  region?: number;
  limit?: number;
}): Promise<DocumentRow[]> {
  const database = await getDb();

  const conditions: string[] = ["is_duplicate = 0"];
  const params: (string | number)[] = [];

  if (filters?.doc_type) {
    conditions.push("doc_type = ?");
    params.push(filters.doc_type);
  }
  if (filters?.year_from) {
    conditions.push("year >= ?");
    params.push(filters.year_from);
  }
  if (filters?.year_to) {
    conditions.push("year <= ?");
    params.push(filters.year_to);
  }
  if (filters?.region) {
    conditions.push("region = ?");
    params.push(filters.region);
  }

  const limit = filters?.limit ?? 50;
  params.push(limit);

  const sql = `
    SELECT id, doc_type, filename, source_path, year, volume, issue_number,
           season, region, newsletter_name, page_count, total_text_length, markdown_path
    FROM documents
    WHERE ${conditions.join(" AND ")}
    ORDER BY year, doc_type, volume, issue_number
    LIMIT ?
  `;

  const stmt = database.prepare(sql);
  stmt.bind(params);

  const results: DocumentRow[] = [];
  while (stmt.step()) {
    results.push(stmt.getAsObject() as unknown as DocumentRow);
  }
  stmt.free();
  return results;
}

export async function getDocumentInfo(
  documentId: number
): Promise<{
  document: DocumentRow;
  page_previews: { page_number: number; preview: string }[];
} | null> {
  const database = await getDb();

  const docStmt = database.prepare(
    "SELECT * FROM documents WHERE id = ?"
  );
  docStmt.bind([documentId]);
  if (!docStmt.step()) {
    docStmt.free();
    return null;
  }
  const document = docStmt.getAsObject() as unknown as DocumentRow;
  docStmt.free();

  const pagesStmt = database.prepare(
    "SELECT page_number, substr(text_content, 1, 150) AS preview FROM pages WHERE document_id = ? ORDER BY page_number"
  );
  pagesStmt.bind([documentId]);

  const page_previews: { page_number: number; preview: string }[] = [];
  while (pagesStmt.step()) {
    const row = pagesStmt.getAsObject() as {
      page_number: number;
      preview: string;
    };
    page_previews.push(row);
  }
  pagesStmt.free();

  return { document, page_previews };
}

function sanitizeFtsQuery(query: string): string {
  // If the query already uses FTS5 operators, pass it through
  if (/\b(AND|OR|NOT)\b/.test(query) || query.includes('"')) {
    return query;
  }
  // Wrap individual terms so special chars don't break FTS5 parsing
  const terms = query
    .split(/\s+/)
    .filter((t) => t.length > 0)
    .map((t) => {
      if (/[^a-zA-Z0-9]/.test(t)) {
        return `"${t.replace(/"/g, '""')}"`;
      }
      return t;
    });
  return terms.join(" ");
}

function escapeSql(s: string): string {
  return s.replace(/'/g, "''");
}
