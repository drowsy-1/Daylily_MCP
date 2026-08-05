"""Extract text from PDF files page by page using pymupdf."""

import fitz  # pymupdf
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_pages(pdf_path: str | Path) -> list[tuple[int, str]]:
    """Extract text from each page of a PDF.

    Returns list of (page_number, text) tuples. Page numbers are 1-indexed.
    """
    pdf_path = str(pdf_path)
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        logger.error(f"Failed to open {pdf_path}: {e}")
        return []

    pages = []
    for i in range(len(doc)):
        try:
            page = doc[i]
            text = page.get_text("text")
            text = post_process_text(text)
            pages.append((i + 1, text))
        except Exception as e:
            logger.warning(f"Failed to extract page {i+1} from {pdf_path}: {e}")
            pages.append((i + 1, ""))

    doc.close()
    return pages


def post_process_text(text: str) -> str:
    """Clean up common OCR artifacts and formatting issues."""
    # Replace common ligature characters
    text = text.replace('\ufb01', 'fi')
    text = text.replace('\ufb02', 'fl')
    text = text.replace('\ufb00', 'ff')
    text = text.replace('\ufb03', 'ffi')
    text = text.replace('\ufb04', 'ffl')

    # Replace other common problematic characters
    text = text.replace('\u2018', "'")   # left single quote
    text = text.replace('\u2019', "'")   # right single quote
    text = text.replace('\u201c', '"')   # left double quote
    text = text.replace('\u201d', '"')   # right double quote
    text = text.replace('\u2013', '-')   # en dash
    text = text.replace('\u2014', '--')  # em dash
    text = text.replace('\u00b7', '.')   # middle dot (OCR artifact)

    # Normalize whitespace per line
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if line:
            line = ' '.join(line.split())
        cleaned_lines.append(line)

    # Collapse 3+ consecutive blank lines to 2
    result = '\n'.join(cleaned_lines)
    while '\n\n\n' in result:
        result = result.replace('\n\n\n', '\n\n')

    return result.strip()
