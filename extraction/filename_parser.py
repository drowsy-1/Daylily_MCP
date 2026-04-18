"""Parse journal and newsletter PDF filenames into structured metadata."""

import re
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SEASON_NORMALIZE = {
    'spring': 'Spring', 'spg': 'Spring', 'spr': 'Spring',
    'summer': 'Summer', 'sum': 'Summer',
    'fall': 'Fall', 'autumn': 'Fall',
    'winter': 'Winter', 'win': 'Winter',
}

MONTH_TO_SEASON = {
    'january': 'Winter', 'february': 'Winter', 'march': 'Spring',
    'april': 'Spring', 'may': 'Spring', 'june': 'Summer',
    'july': 'Summer', 'august': 'Summer', 'september': 'Fall',
    'october': 'Fall', 'november': 'Fall', 'december': 'Winter',
}

MONTHS = set(MONTH_TO_SEASON.keys())

ISSUE_TO_SEASON = {1: 'Spring', 2: 'Summer', 3: 'Fall', 4: 'Winter'}


@dataclass
class DocumentMetadata:
    doc_type: str  # journal, newsletter, yearbook, bulletin, enews
    filename: str
    source_path: str  # relative to project root
    year: int
    volume: Optional[int] = None
    issue_number: Optional[int] = None
    season: Optional[str] = None
    region: Optional[int] = None
    newsletter_name: Optional[str] = None


def _normalize_season(s: str) -> Optional[str]:
    """Normalize a season or month string to standard season name."""
    low = s.lower().strip()
    if low in SEASON_NORMALIZE:
        return SEASON_NORMALIZE[low]
    if low in MONTH_TO_SEASON:
        return MONTH_TO_SEASON[low]
    return None


def _is_month(s: str) -> bool:
    return s.lower().strip() in MONTHS


def parse_journal_filename(filename: str, source_path: str) -> DocumentMetadata:
    """Parse a journal PDF filename into structured metadata."""
    stem = Path(filename).stem

    # Bulletin: 1946-Bulletin1.pdf
    m = re.match(r'^(\d{4})-Bulletin(\d+)$', stem, re.IGNORECASE)
    if m:
        return DocumentMetadata(
            doc_type='bulletin', filename=filename, source_path=source_path,
            year=int(m.group(1)), issue_number=int(m.group(2)),
        )

    # Yearbook: 1950-Yearbook.pdf, 1951_-yearbook__1_.pdf, 1952_-_yearbook__1_.pdf
    m = re.match(r'^(\d{4})[_\s-]+(?:yearbook|Yearbook)', stem, re.IGNORECASE)
    if m:
        return DocumentMetadata(
            doc_type='yearbook', filename=filename, source_path=source_path,
            year=int(m.group(1)),
        )

    # AHS 75th Anniversary
    m = re.match(r'^AHS\s+75th\s+Anniversary', stem, re.IGNORECASE)
    if m:
        return DocumentMetadata(
            doc_type='journal', filename=filename, source_path=source_path,
            year=2021,  # 75th anniversary of AHS (founded 1946)
        )

    # Modern DJ with Vol/No: "2024 DJ Spring-Vol 79 No 1-Interactive1"
    # Also: "2023--The-Daylily-Journal-Summer-Vol-78-No-2--Interactive-1"
    # Also: "2020-DJ-Fall-Vol-75-No-3-interactive-1"
    # Also: "2023-DJ-Spring-Vol-78-No-1--interactive-A1"
    # Also: "The-Daylily-Journal-Spring-2020-Vol75-No1-Interactive-pdf (1)"
    m = re.search(r'(\d{4}).*?(?:DJ|Daylily.?Journal)', stem, re.IGNORECASE)
    if not m:
        # Also match when "The-Daylily-Journal" appears before the year
        m = re.search(r'(?:DJ|Daylily.?Journal).*?(\d{4})', stem, re.IGNORECASE)
    if m:
        year = int(m.group(1))
        # Try to extract Vol and No
        vol_m = re.search(r'Vol[\s-]*(\d+)', stem, re.IGNORECASE)
        no_m = re.search(r'No[\s-]*(\d+)', stem, re.IGNORECASE)
        # Try to extract season
        season_m = re.search(
            r'(Spring|Summer|Fall|Winter)', stem, re.IGNORECASE
        )
        volume = int(vol_m.group(1)) if vol_m else None
        issue = int(no_m.group(1)) if no_m else None
        season = season_m.group(1).capitalize() if season_m else None
        if not season and issue:
            season = ISSUE_TO_SEASON.get(issue)
        return DocumentMetadata(
            doc_type='journal', filename=filename, source_path=source_path,
            year=year, volume=volume, issue_number=issue, season=season,
        )

    # Also catch "The Daylily Journal 2019 Fall-interactive-1"
    m = re.match(r'^The[\s-]+Daylily[\s-]+Journal[\s-]+(\d{4})[\s-]+(Spring|Summer|Fall|Winter)', stem, re.IGNORECASE)
    if m:
        year = int(m.group(1))
        season = m.group(2).capitalize()
        issue = {'Spring': 1, 'Summer': 2, 'Fall': 3, 'Winter': 4}.get(season)
        return DocumentMetadata(
            doc_type='journal', filename=filename, source_path=source_path,
            year=year, season=season, issue_number=issue,
        )

    # "DJ Spring 2019a.pdf"
    m = re.match(r'^DJ\s+(Spring|Summer|Fall|Winter)\s+(\d{4})', stem, re.IGNORECASE)
    if m:
        season = m.group(1).capitalize()
        year = int(m.group(2))
        issue = {'Spring': 1, 'Summer': 2, 'Fall': 3, 'Winter': 4}.get(season)
        return DocumentMetadata(
            doc_type='journal', filename=filename, source_path=source_path,
            year=year, season=season, issue_number=issue,
        )

    # "2019 Winter Daylily Journal-interactive"
    m = re.match(r'^(\d{4})\s+(Spring|Summer|Fall|Winter)\s+Daylily\s+Journal', stem, re.IGNORECASE)
    if m:
        year = int(m.group(1))
        season = m.group(2).capitalize()
        issue = {'Spring': 1, 'Summer': 2, 'Fall': 3, 'Winter': 4}.get(season)
        return DocumentMetadata(
            doc_type='journal', filename=filename, source_path=source_path,
            year=year, season=season, issue_number=issue,
        )

    # "Daylily Fall18 (1).pdf", "Daylily Spg18 FINALweb", "Daylily Win17 FINALMedComp"
    # "Daylily Spring 16pdfForPortal", "DaylilyJournalSpring17LowRespdf"
    m = re.match(
        r'^Daylily(?:Journal)?\s*(Spring|Spg|Summer|Sum|Fall|Winter|Win)\s*(\d{2})',
        stem, re.IGNORECASE
    )
    if m:
        season_raw = m.group(1)
        year_short = int(m.group(2))
        year = 2000 + year_short if year_short < 50 else 1900 + year_short
        season = _normalize_season(season_raw)
        issue = {'Spring': 1, 'Summer': 2, 'Fall': 3, 'Winter': 4}.get(season)
        return DocumentMetadata(
            doc_type='journal', filename=filename, source_path=source_path,
            year=year, season=season, issue_number=issue,
        )

    # Season + Year: "Fall 2016.pdf", "Summer 2017a.pdf", "Winter 2016.pdf"
    m = re.match(r'^(Spring|Summer|Fall|Winter)\s+(\d{4})', stem, re.IGNORECASE)
    if m:
        season = m.group(1).capitalize()
        year = int(m.group(2))
        issue = {'Spring': 1, 'Summer': 2, 'Fall': 3, 'Winter': 4}.get(season)
        return DocumentMetadata(
            doc_type='journal', filename=filename, source_path=source_path,
            year=year, season=season, issue_number=issue,
        )

    # "2019 Summer.pdf"
    m = re.match(r'^(\d{4})\s+(Spring|Summer|Fall|Winter)$', stem, re.IGNORECASE)
    if m:
        year = int(m.group(1))
        season = m.group(2).capitalize()
        issue = {'Spring': 1, 'Summer': 2, 'Fall': 3, 'Winter': 4}.get(season)
        return DocumentMetadata(
            doc_type='journal', filename=filename, source_path=source_path,
            year=year, season=season, issue_number=issue,
        )

    # Standard VxxNyy: "1985-V39N01irm.pdf", "2018-V7302.pdf", "1957-v11n03__1_.pdf"
    # "1949-V03N01,_March.pdf", "1960-V14N01a.pdf"
    m = re.match(
        r'^(\d{4})-[Vv](\d{1,3})[Nn]?(\d{2})',
        stem
    )
    if m:
        year = int(m.group(1))
        volume = int(m.group(2))
        issue = int(m.group(3))
        # Check for trailing month/season: ",_March", etc.
        season = ISSUE_TO_SEASON.get(issue)
        month_m = re.search(r'[,_]\s*(January|February|March|April|May|June|July|August|September|October|November|December|Spring|Summer|Fall|Winter|Autumn)', stem, re.IGNORECASE)
        if month_m:
            season = _normalize_season(month_m.group(1)) or season
        return DocumentMetadata(
            doc_type='journal', filename=filename, source_path=source_path,
            year=year, volume=volume, issue_number=issue, season=season,
        )

    # Fallback: try to extract just the year
    m = re.match(r'^(\d{4})', stem)
    if m:
        logger.warning(f"Journal fallback parse (year only): {filename}")
        return DocumentMetadata(
            doc_type='journal', filename=filename, source_path=source_path,
            year=int(m.group(1)),
        )

    logger.error(f"Could not parse journal filename: {filename}")
    return DocumentMetadata(
        doc_type='journal', filename=filename, source_path=source_path,
        year=0,
    )


def parse_newsletter_filename(filename: str, source_path: str) -> DocumentMetadata:
    """Parse a newsletter PDF filename into structured metadata."""
    stem = Path(filename).stem

    # Region-6 special format: "Region-6-newsletter-1986-1.pdf"
    m = re.match(r'^Region-(\d+)-newsletter-(\d{4})-(\d+(?:-\d+)?)$', stem, re.IGNORECASE)
    if m:
        region = int(m.group(1))
        year = int(m.group(2))
        issue_str = m.group(3)
        # Handle "2006-2-3" as combined issue
        issue = int(issue_str.split('-')[0])
        return DocumentMetadata(
            doc_type='newsletter', filename=filename, source_path=source_path,
            year=year, region=region, issue_number=issue,
        )

    # E-News / Dispatch: broad match for national daylily email newsletters
    # "2009-March-Daylily-E-News-from-AHS--2-.pdf"
    # "2025-October-Daylily-Dispatch.pdf"
    # "2015-1-April-Daylily-E-News-from-the-AHS.pdf"
    # "2018-June-July-Daylily-Dispatch---Summer-is-in-Full-Swing.pdf"
    # "2018-December-Reminder_-NEW-From-the-Daylily-Dispatch..."
    # "2019-March-A-dose-of-sunshine-for-daylily-lovers-.pdf"
    # "2020-March-An-interview--a-database--daylily-books-and-much-more-.pdf"
    if re.search(r'Daylily[-\s]+(E-News|Dispatch|eNews)', stem, re.IGNORECASE) or \
       re.search(r'dose.of.sunshine.for.daylily|All.about.daylilies|An.interview.*daylily', stem, re.IGNORECASE):
        m = re.match(r'^(\d{4})', stem)
        if m:
            year = int(m.group(1))
            # Try to extract a month
            month_m = re.search(
                r'(January|February|March|April|May|June|July|August|'
                r'September|October|November|December)',
                stem, re.IGNORECASE
            )
            season = _normalize_season(month_m.group(1)) if month_m else None
            return DocumentMetadata(
                doc_type='enews', filename=filename, source_path=source_path,
                year=year, season=season,
            )

    # Dual-year newsletters: "1984-1985-R03-Winter.pdf", "1996-1997-R04-Fall-Winter-Daylilies-in-the-Great-Northeast.pdf"
    m = re.match(
        r'^(\d{4})-(\d{4})-R(\d{1,2})(?:-(.+))?$',
        stem, re.IGNORECASE
    )
    if m:
        year = int(m.group(1))  # use the first year
        region = int(m.group(3))
        rest = m.group(4) or ''
        season = None
        newsletter_name = None
        if rest:
            parts = rest.split('-')
            first = parts[0].strip()
            first_season = _normalize_season(first)
            if first_season:
                season = first_season
                remaining = parts[1:]
                if remaining and _normalize_season(remaining[0]):
                    season = f"{first_season}-{_normalize_season(remaining[0])}"
                    remaining = remaining[1:]
                name_parts = [p for p in remaining if p.lower() not in ('newsletter',)]
                if name_parts:
                    newsletter_name = ' '.join(name_parts)
        return DocumentMetadata(
            doc_type='newsletter', filename=filename, source_path=source_path,
            year=year, region=region, season=season, newsletter_name=newsletter_name,
        )

    # Triple-dash modern: "2020---R11---N02----Summer---MoKanOk.pdf"
    # Also "2020---R12---N01---Spring---Florida-Daylily-News.pdf"
    # Also "2018---R15---N03---Fall-Winter-Hemalina.pdf" (single dash in season-name)
    # Also "2020---R06---N02---Daylilies-of-the-Southwest.pdf" (no season, just name)
    m = re.match(
        r'^(\d{4})-{2,}R(\d{1,2})-{2,}N(\d{2})-{2,}(.+)$',
        stem, re.IGNORECASE
    )
    if m:
        year = int(m.group(1))
        region = int(m.group(2))
        issue = int(m.group(3))
        rest = m.group(4)

        # Split on triple-dash first (separates season from name)
        triple_parts = re.split(r'-{2,}', rest)
        if len(triple_parts) >= 2:
            season_raw = triple_parts[0]
            name_raw = triple_parts[-1]
        else:
            # Single chunk: "Fall-Winter-Hemalina" or "Daylilies-of-the-Southwest"
            # Try to extract season from front
            season_raw = None
            name_raw = None
            single_parts = triple_parts[0].split('-')
            first_s = _normalize_season(single_parts[0]) if single_parts else None
            if first_s:
                season_raw = single_parts[0]
                # Check for compound season
                if len(single_parts) > 1 and _normalize_season(single_parts[1]):
                    season_raw = single_parts[0] + '-' + single_parts[1]
                    name_raw = '-'.join(single_parts[2:]) if len(single_parts) > 2 else None
                else:
                    name_raw = '-'.join(single_parts[1:]) if len(single_parts) > 1 else None
            else:
                # No season, entire thing is a name
                name_raw = triple_parts[0]

        season = None
        if season_raw:
            s_parts = season_raw.split('-')
            season = _normalize_season(s_parts[0])
            if len(s_parts) > 1 and _normalize_season(s_parts[1]):
                season = f"{season}-{_normalize_season(s_parts[1])}"

        name = name_raw.replace('-', ' ') if name_raw else None
        return DocumentMetadata(
            doc_type='newsletter', filename=filename, source_path=source_path,
            year=year, region=region, issue_number=issue,
            season=season, newsletter_name=name,
        )

    # Modern with issue number: "2024-R02-N01-Winter-Great-Lakes-Daylily.pdf"
    # "2021-R11-N01-Spring-MoKanOK.pdf"
    # "2021-R15-NO3-Fall-Winter-Hemalina.pdf" (NO instead of N0)
    # "2022-R15-N03-Fall-Winter-Hemalina.pdf"
    m = re.match(
        r'^(\d{4})-R(\d{1,2})-N[Oo]?(\d{1,2})-(.+)$',
        stem, re.IGNORECASE
    )
    if m:
        year = int(m.group(1))
        region = int(m.group(2))
        issue = int(m.group(3))
        rest = m.group(4)

        # Parse rest into season + name
        parts = rest.split('-')
        season = None
        name = None

        first_s = _normalize_season(parts[0]) if parts else None
        if first_s:
            season = first_s
            remaining = parts[1:]
            # Check for compound season
            if remaining and _normalize_season(remaining[0]):
                season = f"{first_s}-{_normalize_season(remaining[0])}"
                remaining = remaining[1:]
            if remaining:
                name = ' '.join(remaining)
        else:
            # No season recognized, entire rest is name
            name = ' '.join(parts)

        return DocumentMetadata(
            doc_type='newsletter', filename=filename, source_path=source_path,
            year=year, region=region, issue_number=issue,
            season=season, newsletter_name=name,
        )

    # Classic: "2006-R15-Spring.pdf", "1986-R08-Fall-Winter.pdf"
    # Also: "1975-R10-Fall_00001.pdf", "1973-R13-Spring--1-.pdf"
    # Also: "1968-R12-No-2_00001.pdf"
    # Also: "1960-R05-July.pdf" (month)
    # Also: "1960-R11-Spring-Newsletter.pdf"
    # Also: "1963-R05-Spring-Georgia-Newsletter.pdf"
    # Also: "1953-R02-Summer-Activities-Hemerocallis-Society.pdf"
    # Also: "1952-R4-The-Hemerocallis-Society-Newsletter.pdf"
    m = re.match(
        r'^(\d{4})-R(\d{1,2})(?:-(.+))?$',
        stem, re.IGNORECASE
    )
    if m:
        year = int(m.group(1))
        region = int(m.group(2))
        rest = m.group(3) or ''

        # Clean trailing suffixes like _00001, --1-, (1)
        rest = re.sub(r'[_-]+\d+[_-]*$', '', rest)
        rest = re.sub(r'--\d+--?$', '', rest)
        rest = re.sub(r'\s*\(\d+\)\s*$', '', rest)

        # Try to extract season or month from the rest
        season = None
        newsletter_name = None
        issue_number = None

        if not rest:
            # Just "1959-R05.pdf" - no additional info
            pass
        else:
            # Check for "No-2" pattern (issue number only)
            no_m = re.match(r'^No-(\d+)', rest, re.IGNORECASE)
            if no_m:
                issue_number = int(no_m.group(1))
            else:
                # Split on hyphens and analyze parts
                parts = rest.split('-')
                # First part is usually a season or month
                first = parts[0].strip()
                first_season = _normalize_season(first)

                if first_season:
                    season = first_season
                    remaining = parts[1:]

                    # Check if second part is also a season (compound: Fall-Winter)
                    if remaining and _normalize_season(remaining[0]):
                        season = f"{first_season}-{_normalize_season(remaining[0])}"
                        remaining = remaining[1:]

                    # Filter out generic words like "Newsletter", "Region", "Activities"
                    name_parts = [p for p in remaining
                                  if p.lower() not in ('newsletter', 'region', str(region), 'activities')]
                    if name_parts:
                        newsletter_name = ' '.join(name_parts)
                elif _is_month(first):
                    season = _normalize_season(first)
                    remaining = parts[1:]
                    name_parts = [p for p in remaining if p.lower() not in ('newsletter',)]
                    if name_parts:
                        newsletter_name = ' '.join(name_parts)
                else:
                    # First part is a name or description, not a season
                    name_parts = [p for p in parts if p.lower() not in ('newsletter',)]
                    newsletter_name = ' '.join(name_parts) if name_parts else None

        return DocumentMetadata(
            doc_type='newsletter', filename=filename, source_path=source_path,
            year=year, region=region, issue_number=issue_number,
            season=season, newsletter_name=newsletter_name,
        )

    # Fallback: try to get year
    m = re.match(r'^(\d{4})', stem)
    if m:
        logger.warning(f"Newsletter fallback parse (year only): {filename}")
        return DocumentMetadata(
            doc_type='newsletter', filename=filename, source_path=source_path,
            year=int(m.group(1)),
        )

    logger.error(f"Could not parse newsletter filename: {filename}")
    return DocumentMetadata(
        doc_type='newsletter', filename=filename, source_path=source_path,
        year=0,
    )


def find_duplicates(metadatas: list[DocumentMetadata]) -> list[DocumentMetadata]:
    """Mark duplicate journal entries. Prefers VxxNyy filenames as canonical.

    Returns the same list with is_duplicate info logged (but since we use
    a simple dataclass, we'll return a set of filenames to skip).
    """
    # Group journals by (year, volume, issue_number) where all are non-None
    from collections import defaultdict
    groups: dict[tuple, list[DocumentMetadata]] = defaultdict(list)

    for md in metadatas:
        if md.doc_type != 'journal':
            continue
        if md.volume is not None and md.issue_number is not None:
            key = (md.year, md.volume, md.issue_number)
            groups[key].append(md)

    skip_filenames: set[str] = set()
    for key, group in groups.items():
        if len(group) <= 1:
            continue

        # Prefer VxxNyy format (shorter, canonical)
        def sort_key(md: DocumentMetadata) -> tuple:
            fn = md.filename.lower()
            # Prefer VxxNyy format
            is_vnn = bool(re.match(r'^\d{4}-v\d+n\d+', fn, re.IGNORECASE))
            # Avoid "(1)" copies
            has_copy_suffix = '(1)' in fn
            # Prefer shorter filenames
            return (not is_vnn, has_copy_suffix, len(fn))

        group.sort(key=sort_key)
        canonical = group[0]
        for dup in group[1:]:
            skip_filenames.add(dup.filename)
            logger.info(f"Duplicate: {dup.filename} -> canonical: {canonical.filename}")

    return skip_filenames
