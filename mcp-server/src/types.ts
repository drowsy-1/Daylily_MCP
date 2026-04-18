export interface DocumentRow {
  id: number;
  doc_type: string;
  filename: string;
  source_path: string;
  year: number;
  volume: number | null;
  issue_number: number | null;
  season: string | null;
  region: number | null;
  newsletter_name: string | null;
  page_count: number;
  total_text_length: number;
  markdown_path: string | null;
}

export interface PageRow {
  id: number;
  document_id: number;
  page_number: number;
  text_content: string;
  text_length: number;
}

export interface SearchResult {
  page_id: number;
  document_id: number;
  doc_type: string;
  year: number;
  volume: number | null;
  issue_number: number | null;
  season: string | null;
  region: number | null;
  newsletter_name: string | null;
  filename: string;
  page_number: number;
  snippet: string;
  rank: number;
}
