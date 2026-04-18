#!/usr/bin/env python3
"""Main extraction pipeline orchestrator.

Usage:
    python -m extraction.run_extract [OPTIONS]

Options:
    --journals-only     Only process journal PDFs
    --newsletters-only  Only process newsletter PDFs
    --dry-run           Parse filenames only, don't extract text
    --rebuild-fts       Rebuild the FTS index without re-extracting
    --limit N           Process only the first N documents
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from extraction.config import (
    JOURNALS_DIR, NEWSLETTERS_DIR, JOURNALS_MD_DIR, NEWSLETTERS_MD_DIR,
)
from extraction.filename_parser import (
    parse_journal_filename, parse_newsletter_filename, find_duplicates,
)
from extraction.text_extractor import extract_pages
from extraction.markdown_writer import write_markdown, get_markdown_filename
from extraction.db_loader import DatabaseLoader

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)


def collect_pdfs(journals: bool = True, newsletters: bool = True):
    """Collect all PDF paths and parse their filenames."""
    documents = []

    if journals:
        for pdf in sorted(JOURNALS_DIR.glob("*.pdf")):
            rel = str(pdf.relative_to(JOURNALS_DIR.parent))
            md = parse_journal_filename(pdf.name, rel)
            documents.append((pdf, md))
        logger.info(f"Found {sum(1 for _, m in documents if m.doc_type != 'newsletter')} journal PDFs")

    if newsletters:
        nl_count = 0
        for subfolder in sorted(NEWSLETTERS_DIR.iterdir()):
            if subfolder.is_dir() and subfolder.name.startswith('download_'):
                for pdf in sorted(subfolder.glob("*.pdf")):
                    rel = str(pdf.relative_to(NEWSLETTERS_DIR.parent))
                    md = parse_newsletter_filename(pdf.name, rel)
                    documents.append((pdf, md))
                    nl_count += 1
        logger.info(f"Found {nl_count} newsletter PDFs")

    return documents


def main():
    parser = argparse.ArgumentParser(description='Extract text from daylily PDFs')
    parser.add_argument('--journals-only', action='store_true')
    parser.add_argument('--newsletters-only', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--rebuild-fts', action='store_true')
    parser.add_argument('--limit', type=int, default=0)
    args = parser.parse_args()

    do_journals = not args.newsletters_only
    do_newsletters = not args.journals_only

    db = DatabaseLoader()

    if args.rebuild_fts:
        db.rebuild_fts()
        stats = db.get_stats()
        logger.info(f"Stats: {stats}")
        db.close()
        return

    # Collect and parse
    logger.info("Scanning PDFs...")
    documents = collect_pdfs(journals=do_journals, newsletters=do_newsletters)
    logger.info(f"Total: {len(documents)} PDFs found")

    # Find duplicates (journals only)
    journal_mds = [md for _, md in documents]
    skip_filenames = find_duplicates(journal_mds)
    logger.info(f"Duplicates to skip: {len(skip_filenames)}")

    if args.dry_run:
        logger.info("Dry run — no extraction performed.")
        for pdf, md in documents:
            dup = "DUPLICATE" if md.filename in skip_filenames else ""
            logger.info(f"  {md.filename} -> {md.doc_type} {md.year} {dup}")
        db.close()
        return

    # Process documents
    total = len(documents)
    if args.limit > 0:
        documents = documents[:args.limit]
        total = len(documents)

    processed = 0
    skipped_existing = 0
    skipped_dup = 0
    errors = 0
    start_time = time.time()

    for i, (pdf_path, metadata) in enumerate(documents):
        is_dup = metadata.filename in skip_filenames

        # Skip already extracted
        if db.document_exists(metadata.filename):
            skipped_existing += 1
            continue

        if is_dup:
            # Insert duplicate marker but don't extract text
            db.insert_document(metadata, [], is_duplicate=True)
            skipped_dup += 1
            continue

        # Extract text
        try:
            pages = extract_pages(pdf_path)
            if not pages:
                logger.warning(f"No pages extracted from {metadata.filename}")
                errors += 1
                continue
        except Exception as e:
            logger.error(f"Error extracting {metadata.filename}: {e}")
            errors += 1
            continue

        # Write markdown
        try:
            md_filename = get_markdown_filename(metadata)
            if metadata.doc_type in ('journal', 'yearbook', 'bulletin'):
                md_path = JOURNALS_MD_DIR / md_filename
            else:
                md_path = NEWSLETTERS_MD_DIR / md_filename
            write_markdown(metadata, pages, md_path)
            rel_md_path = str(md_path.relative_to(md_path.parent.parent.parent))
        except Exception as e:
            logger.error(f"Error writing markdown for {metadata.filename}: {e}")
            rel_md_path = None

        # Insert into database
        try:
            db.insert_document(metadata, pages, markdown_path=rel_md_path)
            processed += 1
        except Exception as e:
            logger.error(f"Error inserting {metadata.filename} into DB: {e}")
            errors += 1
            continue

        # Commit every 50 documents
        if processed % 50 == 0:
            db.commit()

        # Progress
        elapsed = time.time() - start_time
        rate = (processed + skipped_existing + skipped_dup + errors) / elapsed if elapsed > 0 else 0
        remaining = (total - i - 1) / rate if rate > 0 else 0
        logger.info(
            f"[{i+1}/{total}] {metadata.filename} "
            f"({len(pages)} pages) "
            f"[{rate:.1f} docs/s, ~{remaining:.0f}s remaining]"
        )

    # Final commit
    db.commit()

    elapsed = time.time() - start_time
    logger.info(f"\nExtraction complete in {elapsed:.1f}s")
    logger.info(f"  Processed: {processed}")
    logger.info(f"  Skipped (existing): {skipped_existing}")
    logger.info(f"  Skipped (duplicate): {skipped_dup}")
    logger.info(f"  Errors: {errors}")

    # Stats
    stats = db.get_stats()
    logger.info(f"  Database: {stats['documents']} docs, {stats['pages']} pages, "
                f"{stats['total_chars']:,} chars")
    logger.info(f"  By type: {stats['by_type']}")

    db.close()


if __name__ == '__main__':
    main()
