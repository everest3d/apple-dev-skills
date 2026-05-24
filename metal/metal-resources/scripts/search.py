#!/usr/bin/env python3
"""Search the bundled Metal resource index (videos + samples) by relevance.

Ranks Apple Developer videos (which have a full transcript on disk) and Metal
sample-code entries against a free-text query, scoring on tags/keywords, title,
and description. Use it to find the most relevant authoritative Apple material
for any Metal task, then read a video's transcript to ground your answer.

Zero dependencies — standard library only.

Examples:
    python3 scripts/search.py "deferred lighting tile shaders"
    python3 scripts/search.py "argument buffers" --type sample
    python3 scripts/search.py "ray tracing reflections" --limit 3 --json
"""

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
VIDEOS_CSV = DATA_DIR / "videos.csv"
SAMPLES_CSV = DATA_DIR / "metal_samples.csv"

# Words too generic to discriminate between Metal resources (every row is about
# Metal), or that carry no topical signal. Dropped from the query before scoring.
STOPWORDS = {
    "a", "an", "the", "to", "of", "for", "in", "on", "and", "or", "with", "how",
    "do", "i", "me", "my", "you", "your", "is", "are", "can", "what", "best",
    "way", "ways", "using", "use", "used", "want", "need", "should", "app",
    "apps", "code", "metal", "apple", "it", "this", "that", "implement", "create",
    "build", "make", "show", "find", "help", "about", "into", "from", "as", "at",
}

WORD_RE = re.compile(r"[a-z0-9]+")


def tokenize(text):
    """Lowercase word tokens from a string."""
    return WORD_RE.findall(text.lower())


def query_tokens(query):
    """Meaningful tokens from a user query (stopwords and 1-char tokens removed)."""
    return [t for t in tokenize(query) if t not in STOPWORDS and len(t) > 1]


def _score(tokens, title, title_tokens, meta_blob, meta_tokens, tag_tokens,
           transcript_counts):
    """Score one row against the query tokens.

    Curated tag/keyword hits weigh most (the human-meaningful signal), then a
    title hit, then a hit anywhere in the metadata. For videos we also add the
    transcript term frequency (capped) so a talk that actually *discusses* a
    topic outranks one that merely name-drops it in its blurb — the metadata
    alone is too thin to rank videos well.

    Longer tokens use substring matching so 'render' also matches 'rendering';
    short tokens (2-3 chars, e.g. 'ml', '3d') require a whole-word hit to avoid
    spurious substring matches.
    """
    score = 0
    matched = []
    for t in tokens:
        s = 0
        long = len(t) >= 4
        if t in tag_tokens:
            s += 5
        in_title = (t in title) if long else (t in title_tokens)
        if in_title:
            s += 4
        elif ((t in meta_blob) if long else (t in meta_tokens)):
            s += 2
        tf = transcript_counts.get(t, 0)
        if tf:
            s += min(tf, 8)
        if s > 0:
            score += s
            matched.append(t)
    return score, matched


def search_videos(tokens):
    results = []
    with VIDEOS_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            title = row["title"].lower()
            title_tokens = set(tokenize(row["title"]))
            tag_tokens = set(tokenize(row["keywords"]) + tokenize(row["topics"]))
            meta_blob = " ".join([row["title"], row["description"], row["keywords"],
                                  row["topics"], row["event"], row["collection"]]).lower()
            meta_tokens = set(tokenize(meta_blob))
            # Locate the transcript within this skill's bundled data by
            # reconstructing the filename from collection+id, rather than trusting
            # the CSV's transcript_path column. This keeps the skill self-contained
            # and portable even if that column holds an absolute path from an older
            # build, and it's where the term-frequency signal comes from too.
            transcript = DATA_DIR / "transcipts" / f"{row['collection']}-{row['id']}.txt"
            try:
                tcounts = Counter(tokenize(transcript.read_text(encoding="utf-8")))
            except OSError:
                tcounts = Counter()
            score, matched = _score(tokens, title, title_tokens, meta_blob,
                                    meta_tokens, tag_tokens, tcounts)
            if score <= 0:
                continue
            results.append({
                "kind": "video",
                "score": score,
                "matched": matched,
                "id": row["id"],
                "title": row["title"],
                "event": row["event"],
                "duration": row["duration"],
                "topics": row["topics"],
                "video_url": row["video_url"],
                "transcript_path": str(transcript),
            })
    return results


def search_samples(tokens):
    results = []
    with SAMPLES_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            title = row["title"].lower()
            title_tokens = set(tokenize(row["title"]))
            tag_tokens = set(tokenize(row["tags"]))
            meta_blob = " ".join([row["title"], row["description"], row["tags"],
                                  row["topic"], row["language"]]).lower()
            meta_tokens = set(tokenize(meta_blob))
            score, matched = _score(tokens, title, title_tokens, meta_blob,
                                    meta_tokens, tag_tokens, {})
            if score <= 0:
                continue
            results.append({
                "kind": "sample",
                "score": score,
                "matched": matched,
                "id": row["id"],
                "title": row["title"],
                "topic": row["topic"],
                "language": row["language"],
                "tags": row["tags"],
                "source_available": row["source_available"],
                "source_code_path": row["source_code_path"],
            })
    return results


def rank(results, limit):
    results.sort(key=lambda r: (-r["score"], -len(r["matched"]), r["title"]))
    return results[:limit]


def format_text(results):
    if not results:
        return "No matching Metal resources found. Try broader or different terms."
    lines = []
    for r in results:
        why = ", ".join(r["matched"])
        if r["kind"] == "video":
            lines.append(f"[VIDEO]  (score {r['score']}) {r['title']}")
            lines.append(f"  {r['event']} · {r['duration']} · {r['topics']}")
            lines.append(f"  why: matched {why}")
            lines.append(f"  url: {r['video_url']}")
            lines.append(f"  transcript: {r['transcript_path']}")
        else:
            lines.append(f"[SAMPLE] (score {r['score']}) {r['title']}")
            lang = f" · {r['language']}" if r["language"] else ""
            lines.append(f"  topic: {r['topic']}{lang}")
            lines.append(f"  tags: {r['tags']}")
            lines.append(f"  why: matched {why}")
            if r["source_available"].lower() == "true" and r["source_code_path"]:
                lines.append(f"  source: {r['source_code_path']}")
            else:
                lines.append(f"  source: NOT bundled — ask the developer for the "
                             f"source of sample id '{r['id']}'")
        lines.append("")
    return "\n".join(lines).rstrip()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("query", help="Free-text query, e.g. 'deferred lighting'")
    parser.add_argument("--type", choices=["video", "sample", "all"], default="all",
                        help="Restrict to videos, samples, or both (default: all)")
    parser.add_argument("--limit", type=int, default=5,
                        help="Max results per type (default: 5)")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    args = parser.parse_args(argv)

    tokens = query_tokens(args.query)
    if not tokens:
        print("error: query had no searchable terms after removing stopwords.",
              file=sys.stderr)
        return 1

    out = []
    if args.type in ("video", "all"):
        out += rank(search_videos(tokens), args.limit)
    if args.type in ("sample", "all"):
        out += rank(search_samples(tokens), args.limit)
    # When mixing, keep each type's internal ranking but show videos first.
    out.sort(key=lambda r: (0 if r["kind"] == "video" else 1, -r["score"]))

    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print(format_text(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
