"""Write extracted document data as markdown files with YAML frontmatter."""

import yaml
import logging
from pathlib import Path
from datetime import datetime, timezone

from .filename_parser import DocumentMetadata

logger = logging.getLogger(__name__)


def write_markdown(
    metadata: DocumentMetadata,
    pages: list[tuple[int, str]],
    output_path: Path,
) -> None:
    """Write a markdown file for a single document.

    Args:
        metadata: Parsed document metadata.
        pages: List of (page_number, text) tuples.
        output_path: Path to write the .md file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    frontmatter = {
        'doc_type': metadata.doc_type,
        'filename': metadata.filename,
        'source_path': metadata.source_path,
        'year': metadata.year,
        'page_count': len(pages),
        'extracted_at': datetime.now(timezone.utc).isoformat(),
    }
    if metadata.volume is not None:
        frontmatter['volume'] = metadata.volume
    if metadata.issue_number is not None:
        frontmatter['issue_number'] = metadata.issue_number
    if metadata.season:
        frontmatter['season'] = metadata.season
    if metadata.region is not None:
        frontmatter['region'] = metadata.region
    if metadata.newsletter_name:
        frontmatter['newsletter_name'] = metadata.newsletter_name

    # Build title
    title = _build_title(metadata)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('---\n')
        f.write(yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True))
        f.write('---\n\n')
        f.write(f'# {title}\n\n')

        for page_num, text in pages:
            f.write(f'## Page {page_num}\n\n')
            if text.strip():
                f.write(text)
            else:
                f.write('*[No text content on this page]*')
            f.write('\n\n')

    logger.debug(f"Wrote {output_path}")


def get_markdown_filename(metadata: DocumentMetadata) -> str:
    """Generate a markdown filename from document metadata."""
    parts = [str(metadata.year)]

    if metadata.doc_type == 'journal':
        parts.append('journal')
        if metadata.volume is not None:
            parts.append(f'v{metadata.volume:02d}')
        if metadata.issue_number is not None:
            parts.append(f'n{metadata.issue_number:02d}')
    elif metadata.doc_type == 'newsletter':
        parts.append('newsletter')
        if metadata.region is not None:
            parts.append(f'r{metadata.region:02d}')
        if metadata.season:
            parts.append(metadata.season.lower().replace('-', '_'))
        if metadata.issue_number is not None:
            parts.append(f'n{metadata.issue_number:02d}')
    elif metadata.doc_type == 'yearbook':
        parts.append('yearbook')
    elif metadata.doc_type == 'bulletin':
        parts.append('bulletin')
        if metadata.issue_number is not None:
            parts.append(str(metadata.issue_number))
    elif metadata.doc_type == 'enews':
        parts.append('enews')
        if metadata.season:
            parts.append(metadata.season.lower())

    return '-'.join(parts) + '.md'


def _build_title(metadata: DocumentMetadata) -> str:
    """Build a human-readable title from metadata."""
    if metadata.doc_type == 'journal':
        title = 'The Daylily Journal'
        if metadata.volume is not None and metadata.issue_number is not None:
            title += f' Vol. {metadata.volume}, No. {metadata.issue_number}'
        if metadata.season:
            title += f' ({metadata.season} {metadata.year})'
        else:
            title += f' ({metadata.year})'
        return title
    elif metadata.doc_type == 'newsletter':
        title = f'Region {metadata.region}' if metadata.region else 'Newsletter'
        if metadata.newsletter_name:
            title += f' - {metadata.newsletter_name}'
        else:
            title += ' Newsletter'
        if metadata.season:
            title += f' ({metadata.season} {metadata.year})'
        else:
            title += f' ({metadata.year})'
        return title
    elif metadata.doc_type == 'yearbook':
        return f'AHS Yearbook ({metadata.year})'
    elif metadata.doc_type == 'bulletin':
        return f'AHS Bulletin {metadata.issue_number} ({metadata.year})'
    elif metadata.doc_type == 'enews':
        title = 'Daylily E-News/Dispatch'
        if metadata.season:
            title += f' ({metadata.season} {metadata.year})'
        else:
            title += f' ({metadata.year})'
        return title
    return f'Daylily Publication ({metadata.year})'
