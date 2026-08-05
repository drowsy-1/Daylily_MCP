"""SQLite database creation and loading for the daylily corpus."""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timezone

from .config import DB_PATH
from .filename_parser import DocumentMetadata

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_type TEXT NOT NULL,
    filename TEXT NOT NULL UNIQUE,
    source_path TEXT NOT NULL,
    year INTEGER NOT NULL,
    volume INTEGER,
    issue_number INTEGER,
    season TEXT,
    region INTEGER,
    newsletter_name TEXT,
    page_count INTEGER NOT NULL,
    total_text_length INTEGER NOT NULL,
    extracted_at TEXT NOT NULL,
    markdown_path TEXT,
    is_duplicate INTEGER DEFAULT 0,
    duplicate_of INTEGER REFERENCES documents(id)
);

CREATE INDEX IF NOT EXISTS idx_documents_year ON documents(year);
CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(doc_type);
CREATE INDEX IF NOT EXISTS idx_documents_region ON documents(region);
CREATE INDEX IF NOT EXISTS idx_documents_volume ON documents(volume, issue_number);

CREATE TABLE IF NOT EXISTS pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id),
    page_number INTEGER NOT NULL,
    text_content TEXT NOT NULL,
    text_length INTEGER NOT NULL,
    UNIQUE(document_id, page_number)
);

CREATE INDEX IF NOT EXISTS idx_pages_document ON pages(document_id);
"""

FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts USING fts5(
    text_content,
    content='pages',
    content_rowid='id',
    tokenize='porter unicode61'
);

CREATE TRIGGER IF NOT EXISTS pages_ai AFTER INSERT ON pages BEGIN
    INSERT INTO pages_fts(rowid, text_content)
    VALUES (new.id, new.text_content);
END;

CREATE TRIGGER IF NOT EXISTS pages_ad AFTER DELETE ON pages BEGIN
    INSERT INTO pages_fts(pages_fts, rowid, text_content)
    VALUES ('delete', old.id, old.text_content);
END;

CREATE TRIGGER IF NOT EXISTS pages_au AFTER UPDATE ON pages BEGIN
    INSERT INTO pages_fts(pages_fts, rowid, text_content)
    VALUES ('delete', old.id, old.text_content);
    INSERT INTO pages_fts(rowid, text_content)
    VALUES (new.id, new.text_content);
END;
"""


class DatabaseLoader:
    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript(SCHEMA_SQL)
        self.conn.executescript(FTS_SQL)
        self.conn.commit()

    def document_exists(self, filename: str) -> bool:
        """Check if a document has already been loaded."""
        row = self.conn.execute(
            "SELECT 1 FROM documents WHERE filename = ?", (filename,)
        ).fetchone()
        return row is not None

    def insert_document(
        self,
        metadata: DocumentMetadata,
        pages: list[tuple[int, str]],
        markdown_path: str | None = None,
        is_duplicate: bool = False,
    ) -> int:
        """Insert a document and its pages into the database.

        Returns the document ID.
        """
        total_text = sum(len(text) for _, text in pages)
        now = datetime.now(timezone.utc).isoformat()

        cursor = self.conn.execute(
            """INSERT INTO documents
            (doc_type, filename, source_path, year, volume, issue_number,
             season, region, newsletter_name, page_count, total_text_length,
             extracted_at, markdown_path, is_duplicate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                metadata.doc_type,
                metadata.filename,
                metadata.source_path,
                metadata.year,
                metadata.volume,
                metadata.issue_number,
                metadata.season,
                metadata.region,
                metadata.newsletter_name,
                len(pages),
                total_text,
                now,
                markdown_path,
                1 if is_duplicate else 0,
            ),
        )
        doc_id = cursor.lastrowid

        if not is_duplicate:
            self.conn.executemany(
                """INSERT INTO pages (document_id, page_number, text_content, text_length)
                VALUES (?, ?, ?, ?)""",
                [(doc_id, pn, text, len(text)) for pn, text in pages],
            )

        return doc_id

    def commit(self):
        self.conn.commit()

    def rebuild_fts(self):
        """Rebuild the FTS index from scratch."""
        logger.info("Rebuilding FTS index...")
        self.conn.execute("INSERT INTO pages_fts(pages_fts) VALUES('rebuild')")
        self.conn.commit()
        logger.info("FTS index rebuilt.")

    def get_stats(self) -> dict:
        """Get corpus statistics."""
        stats = {}
        row = self.conn.execute(
            "SELECT COUNT(*), SUM(page_count), SUM(total_text_length) "
            "FROM documents WHERE is_duplicate = 0"
        ).fetchone()
        stats['documents'] = row[0]
        stats['pages'] = row[1] or 0
        stats['total_chars'] = row[2] or 0

        rows = self.conn.execute(
            "SELECT doc_type, COUNT(*) FROM documents WHERE is_duplicate = 0 GROUP BY doc_type"
        ).fetchall()
        stats['by_type'] = {r[0]: r[1] for r in rows}

        return stats

    def close(self):
        self.conn.close()
