"""Test filename parser against the full corpus."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from extraction.config import JOURNALS_DIR, NEWSLETTERS_DIR
from extraction.filename_parser import (
    parse_journal_filename,
    parse_newsletter_filename,
    find_duplicates,
)


def test_journals():
    print("=" * 80)
    print("JOURNALS")
    print("=" * 80)

    pdfs = sorted(JOURNALS_DIR.glob("*.pdf"))
    print(f"Found {len(pdfs)} journal PDFs\n")

    metadatas = []
    failures = []
    fallbacks = []

    for pdf in pdfs:
        rel = str(pdf.relative_to(JOURNALS_DIR.parent))
        md = parse_journal_filename(pdf.name, rel)
        metadatas.append(md)

        if md.year == 0:
            failures.append(pdf.name)
        elif md.volume is None and md.issue_number is None and md.doc_type == 'journal' and md.season is None:
            fallbacks.append(pdf.name)

    # Print summary table
    print(f"{'Filename':<65} {'Type':<10} {'Year':<6} {'Vol':<5} {'Iss':<5} {'Season':<15}")
    print("-" * 120)
    for md in metadatas:
        vol = str(md.volume) if md.volume is not None else '-'
        iss = str(md.issue_number) if md.issue_number is not None else '-'
        season = md.season or '-'
        print(f"{md.filename:<65} {md.doc_type:<10} {md.year:<6} {vol:<5} {iss:<5} {season:<15}")

    print()
    if failures:
        print(f"FAILURES ({len(failures)}):")
        for f in failures:
            print(f"  {f}")
    else:
        print("No failures!")

    if fallbacks:
        print(f"\nFALLBACKS - parsed but missing key fields ({len(fallbacks)}):")
        for f in fallbacks:
            print(f"  {f}")
    else:
        print("No fallbacks!")

    # Dedup check
    skip = find_duplicates(metadatas)
    if skip:
        print(f"\nDUPLICATES ({len(skip)}):")
        for s in sorted(skip):
            print(f"  {s}")
    else:
        print("\nNo duplicates found.")

    return metadatas


def test_newsletters():
    print("\n" + "=" * 80)
    print("NEWSLETTERS")
    print("=" * 80)

    # Collect all PDFs from subfolders
    pdfs = []
    for subfolder in sorted(NEWSLETTERS_DIR.iterdir()):
        if subfolder.is_dir() and subfolder.name.startswith('download_'):
            for pdf in sorted(subfolder.glob("*.pdf")):
                pdfs.append(pdf)

    print(f"Found {len(pdfs)} newsletter PDFs\n")

    metadatas = []
    failures = []
    fallbacks = []
    no_region = []

    for pdf in pdfs:
        rel = str(pdf.relative_to(NEWSLETTERS_DIR.parent))
        md = parse_newsletter_filename(pdf.name, rel)
        metadatas.append(md)

        if md.year == 0:
            failures.append(pdf.name)
        elif md.region is None and md.doc_type != 'enews':
            no_region.append(pdf.name)

    # Print summary - just first 50 and last 20
    print(f"{'Filename':<70} {'Type':<10} {'Year':<6} {'R':<4} {'Iss':<5} {'Season':<15} {'Name':<20}")
    print("-" * 140)
    show = metadatas[:50] + metadatas[-20:] if len(metadatas) > 70 else metadatas
    for md in show:
        r = str(md.region) if md.region is not None else '-'
        iss = str(md.issue_number) if md.issue_number is not None else '-'
        season = md.season or '-'
        name = (md.newsletter_name or '-')[:20]
        print(f"{md.filename:<70} {md.doc_type:<10} {md.year:<6} {r:<4} {iss:<5} {season:<15} {name:<20}")

    if len(metadatas) > 70:
        print(f"  ... ({len(metadatas) - 70} more rows) ...")

    print()
    if failures:
        print(f"FAILURES ({len(failures)}):")
        for f in failures:
            print(f"  {f}")
    else:
        print("No failures!")

    if no_region:
        print(f"\nNO REGION ({len(no_region)}):")
        for f in no_region:
            print(f"  {f}")

    return metadatas


if __name__ == '__main__':
    j = test_journals()
    n = test_newsletters()

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Journals: {len(j)} parsed")
    print(f"Newsletters: {len(n)} parsed")
    print(f"Total: {len(j) + len(n)} PDFs")
