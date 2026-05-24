#!/usr/bin/env python3
"""Search a bundled resource index (videos + optional samples) by relevance.

Ranks Apple Developer videos (which have a full transcript on disk) and, when a
samples index is present, sample-code entries against a free-text query, scoring
on tags/keywords, title, description, and — for videos — transcript term
frequency (so a talk that actually discusses a topic outranks a name-drop). Point
it at a skill's data directory with --data.

Zero dependencies — standard library only.

Examples:
    python3 search.py "deferred lighting tile shaders" --data ./data
    python3 search.py "argument buffers" --type sample --data ./data
    python3 search.py "actors concurrency" --data ./data --json
"""

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

# Generic stopwords: too common to discriminate, or no topical signal. Domain
# words (e.g. "metal", "swift", "apple") are intentionally NOT hardcoded — each
# skill adds its own via <data>/search_config.json, keeping this script
# domain-agnostic and identical across skills.
STOPWORDS = {
    "a", "an", "the", "to", "of", "for", "in", "on", "and", "or", "with", "how",
    "do", "i", "me", "my", "you", "your", "is", "are", "can", "what", "best",
    "way", "ways", "using", "use", "used", "want", "need", "should", "app",
    "apps", "code", "it", "this", "that", "implement", "create", "build", "make",
    "show", "find", "help", "about", "into", "from", "as", "at",
}

WORD_RE = re.compile(r"[a-z0-9]+")


def tokenize(text):
    """Lowercase word tokens from a string."""
    return WORD_RE.findall(text.lower())


def load_stopwords(data_dir):
    """Base stopwords plus any ``domain_stopwords`` in <data_dir>/search_config.json.

    A missing or malformed config yields the base set (never raises).
    """
    stop = set(STOPWORDS)
    cfg = Path(data_dir) / "search_config.json"
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
        for w in data.get("domain_stopwords", []):
            stop.add(str(w).lower())
    except (OSError, ValueError):
        pass
    return stop


def query_tokens(query, stopwords=STOPWORDS):
    """Meaningful tokens from a query (stopwords and 1-char tokens removed)."""
    return [t for t in tokenize(query) if t not in stopwords and len(t) > 1]


def _score(tokens, title, title_tokens, meta_blob, meta_tokens, tag_tokens,
           transcript_counts):
    """Score one row against the query tokens.

    Curated tag/keyword hits weigh most, then a title hit, then a hit anywhere in
    the metadata. For videos we also add transcript term frequency (capped) so a
    talk that discusses a topic outranks one that merely name-drops it. Longer
    tokens use substring matching ('render' matches 'rendering'); short tokens
    (2-3 chars) require a whole-word hit to avoid spurious matches.
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


def search_videos(tokens, data_dir):
    results = []
    data_dir = Path(data_dir)
    with (data_dir / "videos.csv").open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            title = row["title"].lower()
            title_tokens = set(tokenize(row["title"]))
            tag_tokens = set(tokenize(row["keywords"]) + tokenize(row["topics"]))
            meta_blob = " ".join([row["title"], row["description"], row["keywords"],
                                  row["topics"], row["event"], row["collection"]]).lower()
            meta_tokens = set(tokenize(meta_blob))
            # Reconstruct the transcript path from collection+id under this data
            # dir, rather than trusting the CSV column (keeps the skill portable).
            transcript = data_dir / "transcipts" / f"{row['collection']}-{row['id']}.txt"
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


def search_samples(tokens, data_dir):
    results = []
    data_dir = Path(data_dir)
    with (data_dir / "samples.csv").open(newline="", encoding="utf-8") as f:
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
        return "No matching resources found. Try broader or different terms."
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
    parser.add_argument("--data", default="data",
                        help="Skill data directory holding videos.csv, transcipts/, "
                             "and optionally samples.csv / search_config.json "
                             "(default: ./data)")
    parser.add_argument("--type", choices=["video", "sample", "all"], default="all",
                        help="Restrict to videos, samples, or both (default: all)")
    parser.add_argument("--limit", type=int, default=5,
                        help="Max results per type (default: 5)")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    args = parser.parse_args(argv)

    data_dir = Path(args.data)
    videos_csv = data_dir / "videos.csv"
    samples_csv = data_dir / "samples.csv"
    if not videos_csv.is_file():
        print(f"error: videos index not found: {videos_csv}", file=sys.stderr)
        return 1

    tokens = query_tokens(args.query, load_stopwords(data_dir))
    if not tokens:
        print("error: query had no searchable terms after removing stopwords.",
              file=sys.stderr)
        return 1

    # Samples are optional: a skill (e.g. swift) may ship no samples.csv.
    if args.type == "sample" and not samples_csv.is_file():
        if args.json:
            print("[]")
        else:
            print("No samples in this index.")
        return 0

    out = []
    if args.type in ("video", "all"):
        out += rank(search_videos(tokens, data_dir), args.limit)
    if args.type in ("sample", "all") and samples_csv.is_file():
        out += rank(search_samples(tokens, data_dir), args.limit)
    # When mixing, keep each type's internal ranking but show videos first.
    out.sort(key=lambda r: (0 if r["kind"] == "video" else 1, -r["score"]))

    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print(format_text(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
