# Apple video → CSV index builder

**Date:** 2026-05-23
**Status:** Approved

## Purpose

Turn a locally-saved Apple Developer videos grid (HTML) into a CSV index that a
coding agent (and a Metal developer) can search to quickly find the right video
**and its transcript**. Each CSV row is guaranteed actionable: a row exists only
when a matching transcript file is on disk.

## Approach

A single zero-dependency Python 3 script. Parses HTML with the stdlib
`html.parser`, matches video IDs against the `transcipts/` folder, writes a CSV.
No `pip install` — portable, ideal for a skills repo.

Rejected alternatives: a Node/TS script (adds a toolchain for no benefit);
regex-only HTML parsing (more fragile than `html.parser`).

## Inputs

- `--html videos.html` — the saved grid HTML (user provides this file).
- `--transcripts transcipts` — folder of `<collection>-<id>.txt` files
  (e.g. `tech-talks-111432.txt`, `wwdc2024-10089.txt`). The filename mirrors the
  video URL path `/videos/play/<collection>/<id>/`. Note the folder is spelled
  `transcipts` (no second `r`); that is the default.
- `--out videos.csv` — output path.

## Core rule

**Only emit a row when `<transcripts>/<collection>-<id>.txt` exists.** Matching
uses the full `collection+id` pair because the same numeric id is reused across
collections (`tech-talks-602`, `wwdc2014-602`, `wwdc2015-602` are distinct
videos). Cards without a transcript are skipped. A video (`collection`, `id`) is
emitted at most once even if its card repeats in the HTML. Running against an
empty transcripts folder correctly yields an empty CSV (header only).

## CSV columns

| Column | Source in the card | Purpose |
|---|---|---|
| `id` | last path segment of `href` | join key to transcripts |
| `title` | `<h5 class="vc-card__title">` (fallback `img alt`) | human-readable name |
| `description` | `data-filter-description` | full-text search |
| `keywords` | `data-filter-keywords` | tag search |
| `topics` | `data-filter-topics` | category search |
| `platforms` | `data-filter-platform` | platform filter |
| `event` | `vc-card__tag--event` text | e.g. "Tech Talks" |
| `collection` | `data-filter-collectionid` (fallback: from `href`) | e.g. tech-talks, wwdc2024 |
| `duration` | `vc-card__duration` | e.g. 34:50 |
| `video_url` | `https://developer.apple.com` + `href` | link to the talk |
| `thumbnail_url` | `img src` | preview |
| `transcript_path` | path to the matched `.txt` | where the agent reads the transcript |

`related_links` is intentionally **not** included in v1 — it lives on each
video's detail page, not the grid card. The code is structured so a future
detail-page enrichment pass can add it without reworking the parser.

## Data flow

read HTML → `parse_cards()` → for each card derive `collection` + `id` +
`video_url` → skip if `(collection, id)` already seen → `find_transcript(collection, id)`;
if missing, skip → assemble row → `write_csv()`. Print a summary to stderr:
parsed N, wrote M.

## Error handling

- Missing HTML file → clear error, exit non-zero.
- Missing/empty transcripts folder → all cards skipped + a warning, not a crash.
- Card missing a field → blank cell, never crash.
- Duplicate `(collection, id)` → keep first occurrence.

## Testing

Test-first with stdlib `unittest` (no pytest dependency). A fixture using a real
card verifies field extraction, ID parsing, URL building, transcript hit/miss
filtering, and end-to-end CSV output (including the empty-folder case).

## Files

- `build_index.py` — functions + `main()` CLI.
- `test_build_index.py` — unittest suite.
