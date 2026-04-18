# Unlocking 80 Years of Daylily History with AI: Building a Searchable Archive from American Daylily Society Records

## A Labor of Love Meets Modern Technology

What if you could ask a question — in plain English — and instantly search across eight decades of daylily knowledge? Every hybridizer profile, every cultivation tip, every regional show report, every letter to the editor from 1946 to 2026?

That's exactly what the **DAYLILY_MCP** project does. It takes the entire digital archive of the American Daylily Society's publications — journals, newsletters, bulletins, and yearbooks — and makes them searchable through an AI assistant. No more thumbing through individual PDFs. No more trying to remember which issue had that article about spider daylilies or which region's newsletter covered a particular garden tour. Just ask, and the AI finds it.

## What's in the Archive?

The American Daylily Society maintains a members-only digital archive of its publications stretching back to the very first bulletin published in 1946. This project processed **2,259 PDF files** downloaded manually from that archive:

- **338 journals** — the flagship publication of the AHS, including *The Hemerocallis Journal*, *The Daylily Journal*, yearbooks, and early bulletins
- **1,921 regional newsletters** — from all 15 AHS regions across the United States, capturing the grassroots heart of the daylily community

These publications span from **1946 through 2026** — eighty years of uninterrupted daylily history, hybridizing records, garden photography, show results, and community storytelling.

### By the Numbers

| Metric | Value |
|---|---|
| Total PDF files | 2,259 |
| Unique documents (after deduplication) | 2,148 |
| Total pages extracted | 82,517 |
| Total characters of text | 201 million |
| Raw PDF size (journals) | 7.6 GB |
| Raw PDF size (newsletters) | 46 GB |
| **Total raw PDF archive** | **53.6 GB** |
| Extracted text (markdown) | 197 MB |
| Search database | 352 MB |

That's over fifty gigabytes of scanned and digital PDFs distilled into a fast, searchable database — a compression of raw material into pure, queryable knowledge.

### A Few Gaps

Out of 2,259 files, only **3 PDFs were corrupted or empty** and could not be meaningfully extracted:

- `1994-R08-Spring` (Region 8 Spring 1994)
- `1994-R13-Fall-Winter` (Region 13 Fall/Winter 1994)
- `1994-R13-Summer` (Region 13 Summer 1994)

Additionally, **8 duplicate journal files** were identified (same content published under slightly different filenames) and automatically flagged to avoid double-counting in search results. That means 99.9% of the archive is fully searchable — a remarkably complete dataset.

## What Can You Do With It?

The project creates an **MCP server** (more on the technology below) that gives an AI assistant like Claude four powerful tools:

1. **Search** — Full-text search across all 82,517 pages. Search for a cultivar name, a hybridizer, a growing technique, a region, a year range — anything. The search engine ranks results by relevance and shows you highlighted snippets so you can quickly find what matters.

2. **Read Pages** — Pull up the complete text of any page from any publication. Found a promising search result? Read the full article right there in your conversation.

3. **Browse Publications** — List and filter publications by type (journal, newsletter, yearbook), by year range, or by AHS region number. Great for exploring what's available.

4. **Get Publication Details** — View metadata and a page-by-page overview of any publication — see what's on each page before diving in.

### Real-World Uses

Imagine the possibilities:

- **"What hybridizers were featured in the 1970s journals?"** — Search across a decade of publications in seconds.
- **"Find all mentions of 'Stella de Oro' in regional newsletters"** — Track the rise of the world's most popular daylily across community publications.
- **"What did Region 6 report about their 2015 summer garden tours?"** — Go directly to a specific region's newsletter.
- **"Show me articles about daylily rust from 2002 to 2010"** — Research how the community responded to a major disease challenge.
- **"What cultivation advice was given for northern climates in the 1990s?"** — Mine decades of regional growing wisdom.

This isn't just a search engine — it's a **research assistant** with access to the entire institutional memory of the American Daylily Society. For historians, hybridizers, garden writers, judges, and anyone passionate about *Hemerocallis*, this is an unprecedented resource.

## How It Was Built

Building this project involved two major phases: extracting the knowledge from thousands of PDFs, and then making it accessible through AI.

### Phase 1: The Extraction Pipeline

The first challenge was turning 2,259 PDFs — with wildly inconsistent naming conventions spanning eight decades — into structured, searchable data.

A **Python extraction pipeline** was built to handle this:

1. **Filename Parsing** — The archive's filenames follow no single convention. A 1985 journal might be named `1985-V39N01irm.pdf`, while a 2024 journal is `2024-DJ-Spring-Vol-79-No-1-Interactive.pdf`, and a 1960s newsletter is simply `1967-R04-Fall.pdf`. A sophisticated parser was written to recognize dozens of naming patterns and extract structured metadata: publication type, year, volume, issue number, season, region, and newsletter name.

2. **Text Extraction** — Using the **PyMuPDF** library, every page of every PDF was read and its text extracted. Fortunately, all files in the AHS archive contain embedded text (no optical character recognition was needed). The pipeline also normalizes common PDF artifacts like ligature characters, smart quotes, and inconsistent whitespace.

3. **Markdown Output** — Each publication is converted into a clean Markdown file with structured metadata (called "frontmatter") at the top and the full text of every page below. This creates a human-readable archive alongside the database.

4. **Database Loading** — All extracted text is loaded into a **SQLite database** with a full-text search index. The search engine uses a **porter stemmer** (so searching for "hybridizing" also finds "hybridize" and "hybridized") and **Unicode-aware tokenization** for accurate word boundary detection.

The extraction pipeline is incremental — it can be re-run to pick up new publications without reprocessing everything from scratch.

### Phase 2: The MCP Server

The extracted data needs a way to talk to AI. That's where the **Model Context Protocol (MCP)** comes in.

MCP is an open standard developed by Anthropic that lets AI assistants like Claude use external tools — much like how a web browser uses plugins. The DAYLILY_MCP server is a small **TypeScript application** that exposes the four tools described above (search, read, browse, details) so that Claude can query the daylily database during a conversation.

When you ask Claude a question about daylilies, it can call these tools behind the scenes — searching the archive, reading relevant pages, and synthesizing an answer grounded in real AHS publications. The AI doesn't hallucinate daylily facts; it looks them up in the actual historical record.

## Technologies Used

| Technology | Role |
|---|---|
| **Python 3** | Extraction pipeline — PDF parsing, text processing, database loading |
| **PyMuPDF** | PDF text extraction (page-by-page, no OCR needed) |
| **SQLite + FTS5** | Database storage and full-text search with relevance ranking |
| **TypeScript / Node.js** | MCP server application |
| **Model Context Protocol (MCP) SDK** | Standard interface between AI assistants and external tools |
| **sql.js** | Pure JavaScript SQLite engine for metadata queries |
| **Zod** | Runtime type validation for tool inputs |
| **Claude (Anthropic)** | AI assistant that uses the tools to answer questions |

A notable technical challenge: the project uses a **hybrid database approach**. Full-text search queries run through the system's native SQLite (which supports the FTS5 search extension), while simpler metadata queries run through sql.js (a pure JavaScript SQLite implementation that works anywhere without compiled dependencies). This keeps the server lightweight and portable.

## Why This Is Exciting

The American Daylily Society's archive is a treasure — but until now, it's been a treasure locked in thousands of individual PDF files. Finding specific information meant knowing which issue to open, or painstakingly searching file by file.

This project changes that. It transforms a **passive archive into an active knowledge base**. Eighty years of collective wisdom — from the earliest hybridizers to today's cutting-edge introductions — becomes instantly accessible through natural conversation.

For the daylily community, this means:

- **Preserving institutional knowledge** — As longtime members pass on, their contributions to newsletters and journals live on in a searchable format.
- **Accelerating research** — Hybridizers can quickly find historical performance data, parentage discussions, and regional growing reports.
- **Connecting the community** — Regional newsletters are often the most personal and detailed records of daylily culture. Now they're all searchable together, revealing patterns and connections across regions and decades.
- **Making history accessible** — New members can explore the rich history of the society without needing to know where to look.

This is what happens when a passion for daylilies meets modern AI technology — a tool that honors the past while making it useful for the future.

---

*The DAYLILY_MCP project was built using publications from the American Daylily Society's members-only digital archive. All PDFs were downloaded manually by an AHS member. The project processes these files locally and does not redistribute copyrighted content — it simply makes a member's own archive copy searchable through AI.*
