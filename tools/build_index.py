#!/usr/bin/env python3
"""Build a CSV index of Apple Developer videos from a saved grid HTML page.

Reads a locally-saved HTML page containing a grid of ``vc-card`` video tiles,
and for every card whose transcript exists on disk
(``<transcripts>/<collection>-<id>.txt``) writes one CSV row. Cards without a
transcript are skipped, so every row in the output is immediately actionable:
the transcript is guaranteed readable.

Zero dependencies — standard library only.

Usage (from the repo root, no flags needed):
    python3 tools/build_index.py
"""

import argparse
import csv
import os
import sys
from html.parser import HTMLParser
from pathlib import Path

DOMAIN = "https://developer.apple.com"

# Default locations. This script lives in tools/; the input HTML sits next to it,
# while the transcripts folder and output CSV live at the repo root (the parent
# directory). Anchoring to __file__ makes `python3 tools/build_index.py` work with
# no flags regardless of the current working directory.
_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
DEFAULT_HTML = _SCRIPT_DIR / "videos.html"
DEFAULT_TRANSCRIPTS = _REPO_ROOT / "transcipts"
DEFAULT_OUT = _REPO_ROOT / "videos.csv"

# CSV column order. Everything here is sourced from the grid card itself.
COLUMNS = [
    "id",
    "title",
    "description",
    "keywords",
    "topics",
    "platforms",
    "event",
    "collection",
    "duration",
    "video_url",
    "thumbnail_url",
    "transcript_path",
]


class _CardParser(HTMLParser):
    """Collect one dict per ``<a class="vc-card ...">`` tile in the grid."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.cards = []
        self._cur = None        # the card currently being built, or None
        self._capture = None     # field name we're accumulating text into

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        classes = a.get("class", "")

        if tag == "a" and "vc-card" in classes:
            self._cur = {key: "" for key in (
                "href", "title", "img_alt", "img_src", "duration",
                "event", "description", "keywords", "topics",
                "platforms", "collection",
            )}
            self._cur["href"] = a.get("href", "")
            return

        if self._cur is None:
            return

        if tag == "img" and "vc-card__image" in classes:
            self._cur["img_src"] = a.get("src", "")
            self._cur["img_alt"] = a.get("alt", "")
        elif tag == "h5" and "vc-card__title" in classes:
            self._capture = "title"
        elif tag == "span" and "vc-card__duration" in classes:
            self._capture = "duration"
        elif tag == "span" and "vc-card__tag--event" in classes:
            self._capture = "event"
        elif tag == "span" and "vc-card__keywords" in classes:
            # The hidden keywords span carries the rich matching metadata.
            self._cur["description"] = a.get("data-filter-description", "")
            self._cur["keywords"] = a.get("data-filter-keywords", "")
            self._cur["topics"] = a.get("data-filter-topics", "")
            self._cur["platforms"] = a.get("data-filter-platform", "")
            self._cur["collection"] = a.get("data-filter-collectionid", "")

    def handle_data(self, data):
        if self._cur is not None and self._capture is not None:
            self._cur[self._capture] += data

    def handle_endtag(self, tag):
        if self._cur is None:
            return
        if tag in ("h5", "span") and self._capture is not None:
            self._capture = None
        if tag == "a":
            for field in ("title", "duration", "event"):
                self._cur[field] = self._cur[field].strip()
            self.cards.append(self._cur)
            self._cur = None


def parse_cards(html):
    """Parse grid HTML into a list of raw card dicts."""
    parser = _CardParser()
    parser.feed(html)
    return parser.cards


def extract_id(href):
    """Return the trailing path segment of an href, e.g. '111433'."""
    parts = [p for p in href.split("/") if p]
    return parts[-1] if parts else ""


def build_video_url(href):
    """Return the canonical https://developer.apple.com video URL for an href."""
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if not href.startswith("/"):
        href = "/" + href
    return DOMAIN + href


def find_transcript(collection, video_id, transcripts_dir):
    """Return the Path to <transcripts_dir>/<collection>-<id>.txt if it exists.

    Transcript filenames mirror the video's URL path (/videos/play/<collection>/<id>/
    -> <collection>-<id>.txt). Matching on the full collection+id pair is required:
    the same numeric id is reused across collections (e.g. tech-talks-602,
    wwdc2014-602, wwdc2015-602 are three different videos).
    """
    path = Path(transcripts_dir) / f"{collection}-{video_id}.txt"
    return path if path.is_file() else None


def build_rows(cards, transcripts_dir, out_dir=None):
    """Build CSV rows, keeping only cards with a transcript and no duplicates.

    A video is identified by (collection, id); a repeated card is inserted once.
    When ``out_dir`` is given, ``transcript_path`` is stored relative to it so the
    CSV stays portable (it resolves wherever the CSV and its sibling transcripts
    folder are copied — repo root, skill bundle, another machine). Without it the
    absolute path is kept.
    """
    transcripts_dir = Path(transcripts_dir)
    rows = []
    seen = set()
    for card in cards:
        video_id = extract_id(card["href"])
        collection = _collection_from_href(card["href"])
        if not video_id or not collection:
            continue
        key = (collection, video_id)
        if key in seen:
            continue
        transcript = find_transcript(collection, video_id, transcripts_dir)
        if transcript is None:
            continue
        seen.add(key)
        transcript_path = (os.path.relpath(transcript, out_dir)
                           if out_dir else str(transcript))
        rows.append({
            "id": video_id,
            "title": card["title"] or card["img_alt"],
            "description": card["description"],
            "keywords": card["keywords"],
            "topics": card["topics"],
            "platforms": card["platforms"],
            "event": card["event"],
            # Use the URL-path collection so it agrees with video_url and
            # transcript_path (the card's data-filter-collectionid uses a short
            # form like "wwdc25"; the human label is in the event column).
            "collection": collection,
            "duration": card["duration"],
            "video_url": build_video_url(card["href"]),
            "thumbnail_url": card["img_src"],
            "transcript_path": transcript_path,
        })
    return rows


def _collection_from_href(href):
    """Derive the collection segment from an href, e.g. 'tech-talks'."""
    parts = [p for p in href.split("/") if p]
    return parts[-2] if len(parts) >= 2 else ""


def write_csv(rows, out_path):
    """Write rows to CSV (header always written)."""
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", default=str(DEFAULT_HTML),
                        help="Saved grid HTML file (default: <tool dir>/videos.html)")
    parser.add_argument("--transcripts", default=str(DEFAULT_TRANSCRIPTS),
                        help="Folder of <collection>-<id>.txt transcripts "
                             "(default: <repo>/transcipts)")
    parser.add_argument("--out", default=str(DEFAULT_OUT),
                        help="Output CSV path (default: <repo>/videos.csv)")
    args = parser.parse_args(argv)

    html_path = Path(args.html)
    if not html_path.is_file():
        print(f"error: HTML file not found: {html_path}", file=sys.stderr)
        return 1

    transcripts_dir = Path(args.transcripts)
    if not transcripts_dir.is_dir():
        print(f"warning: transcripts folder not found: {transcripts_dir} "
              f"(no rows will be written)", file=sys.stderr)

    cards = parse_cards(html_path.read_text(encoding="utf-8"))
    rows = build_rows(cards, transcripts_dir, out_dir=Path(args.out).resolve().parent)
    write_csv(rows, args.out)

    print(f"parsed {len(cards)} cards -> wrote {len(rows)} rows "
          f"(skipped duplicates and cards without a transcript) -> {args.out}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
