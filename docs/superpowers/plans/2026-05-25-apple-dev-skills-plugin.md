# apple-dev-skills Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the Metal skill into an `apple-dev-skills` Claude Code plugin: a shared, domain-agnostic indexing toolset plus three skills (umbrella `apple-ecosystem`, `metal-resources`, and a new `swift-resources` with no samples).

**Architecture:** A plugin rooted at the repo. `tools/` holds the canonical, domain-agnostic `search.py` (runtime) and `build_index.py` (build-time) plus tests. Each skill under `skills/` is self-contained: a `SKILL.md`, a **vendored copy** of `search.py` in `scripts/`, and a `data/` dir (`videos.csv`, transcripts, optional `samples.csv`, `search_config.json`). A sync script + drift test keep the vendored copies byte-identical to `tools/search.py`. Skills ground answers in curated WWDC transcripts **and** refresh current API details from context7.

**Tech Stack:** Python 3 standard library only (no pip). Claude Code plugin + skills (`SKILL.md`, `${CLAUDE_SKILL_DIR}`). `unittest` for tests.

---

## File Structure (end state)

```
llm-skills/                              (plugin: apple-dev-skills)
├── .gitignore                           # ignore .DS_Store
├── .claude-plugin/plugin.json           # manifest: name, description, version
├── README.md                            # plugin overview + maintainer build steps
├── tools/                               # canonical source of truth
│   ├── search.py                        #   runtime tool (canonical), domain-agnostic
│   ├── build_index.py                   #   build-time tool, explicit flags
│   ├── sync_vendored.sh                 #   copies search.py into each skill's scripts/
│   ├── test_search.py                   #   tests for search.py
│   ├── test_build_index.py              #   tests for build_index.py
│   └── test_tools_in_sync.py            #   asserts vendored copies match canonical
├── skills/
│   ├── apple-ecosystem/SKILL.md         # umbrella: routes + workflow + extension guide
│   ├── metal-resources/
│   │   ├── SKILL.md
│   │   ├── scripts/search.py            #   vendored copy of tools/search.py
│   │   └── data/{videos.csv, samples.csv, search_config.json, transcipts/ (105)}
│   └── swift-resources/
│       ├── SKILL.md                     #   NO samples section
│       ├── scripts/search.py            #   vendored copy of tools/search.py
│       └── data/{videos.csv, search_config.json, transcipts/ (124)}
├── sources/                             # maintainer-only raw inputs
│   ├── metal/{videos.html, metal_samples.txt}
│   └── swift/{videos.html}
└── docs/superpowers/{specs,plans}/      # this plan + the design spec (+ earlier metal spec)
```

**Responsibilities:**
- `tools/search.py` — rank `videos.csv` (+ optional `samples.csv`) in a `--data` dir against a query; samples optional; domain stopwords from `search_config.json`.
- `tools/build_index.py` — parse a saved Apple videos grid HTML → `videos.csv`, one row per video that has a transcript.
- Each `SKILL.md` — when/how to use that skill; invokes its own `scripts/search.py`.
- `search_config.json` (per skill) — `{"domain_stopwords": [...]}`.

---

## Task 1: Initialize git + baseline commit

**Files:**
- Create: `.gitignore`

- [ ] **Step 1: Init repo**

Run:
```bash
cd /Users/amressam/projects/llm-skills
git init
```
Expected: "Initialized empty Git repository".

- [ ] **Step 2: Create `.gitignore`**

Create `.gitignore`:
```
.DS_Store
**/.DS_Store
__pycache__/
*.pyc
```

- [ ] **Step 3: Remove tracked cruft and baseline-commit the current tree**

Run:
```bash
cd /Users/amressam/projects/llm-skills
find . -name .DS_Store -delete
git add -A
git commit -m "chore: baseline current metal + swift tree before plugin restructure"
```
Expected: a commit containing the existing `metal/` and `swift/` trees.

---

## Task 2: Move build tooling into `tools/` (no code change yet)

**Files:**
- Move: `metal/tools/build_index.py` → `tools/build_index.py`
- Move: `metal/tools/test_build_index.py` → `tools/test_build_index.py`

- [ ] **Step 1: Create `tools/` and move the build tool + its test**

Run:
```bash
cd /Users/amressam/projects/llm-skills
mkdir -p tools
git mv metal/tools/build_index.py tools/build_index.py
git mv metal/tools/test_build_index.py tools/test_build_index.py
```

- [ ] **Step 2: Verify the existing suite still passes from the new location**

Run:
```bash
cd /Users/amressam/projects/llm-skills/tools && python3 -m unittest test_build_index -v
```
Expected: all tests OK (the suite always passes explicit flags, so location doesn't matter).

- [ ] **Step 3: Commit**

```bash
cd /Users/amressam/projects/llm-skills
git add -A && git commit -m "refactor: move build_index tool + tests to shared tools/"
```

---

## Task 3: Generalize `build_index.py` (require explicit flags)

**Files:**
- Modify: `tools/build_index.py`

- [ ] **Step 1: Replace the magic default paths with required flags**

In `tools/build_index.py`, delete the `_SCRIPT_DIR`/`_REPO_ROOT`/`DEFAULT_HTML`/`DEFAULT_TRANSCRIPTS`/`DEFAULT_OUT` block (the lines defining those constants, just below `DOMAIN = ...`). Replace the `main()` argument parser so the three paths are required:

```python
def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", required=True,
                        help="Saved Apple videos grid HTML file to parse")
    parser.add_argument("--transcripts", required=True,
                        help="Folder of <collection>-<id>.txt transcripts")
    parser.add_argument("--out", required=True,
                        help="Output CSV path")
    args = parser.parse_args(argv)
```

Leave the rest of `main()` (the body after `args = ...`) unchanged.

- [ ] **Step 2: Update the usage docstring**

In the module docstring at the top of `tools/build_index.py`, replace the `Usage (...)` block with:

```
Usage (all paths explicit; this is a shared, domain-agnostic tool):
    python3 build_index.py --html <grid.html> --transcripts <dir> --out <videos.csv>
```

- [ ] **Step 3: Run the suite (must stay green)**

Run:
```bash
cd /Users/amressam/projects/llm-skills/tools && python3 -m unittest test_build_index -v
```
Expected: all tests OK (they already pass `--html/--transcripts/--out`).

- [ ] **Step 4: Commit**

```bash
cd /Users/amressam/projects/llm-skills
git add -A && git commit -m "refactor: make build_index.py domain-agnostic with required flags"
```

---

## Task 4: Create canonical `tools/search.py` (generalized) — TDD

This moves the Metal `search.py` to `tools/`, then generalizes it: `--data <dir>`, optional samples, domain stopwords from config, standard `samples.csv` name. Tests come first.

**Files:**
- Move: `metal/metal-resources/scripts/search.py` → `tools/search.py`
- Create: `tools/test_search.py`
- Modify: `tools/search.py`

- [ ] **Step 1: Move the existing search tool to `tools/`**

Run:
```bash
cd /Users/amressam/projects/llm-skills
git mv metal/metal-resources/scripts/search.py tools/search.py
```

- [ ] **Step 2: Write the failing tests**

Create `tools/test_search.py`:
```python
"""Tests for the generalized search.py (domain-agnostic, samples optional).

Run: python3 -m unittest test_search
"""

import csv
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

import search


VIDEO_COLS = ["id", "title", "description", "keywords", "topics", "platforms",
              "event", "collection", "duration", "video_url", "thumbnail_url",
              "transcript_path"]
SAMPLE_COLS = ["id", "topic", "title", "description", "language", "tags",
               "source_available", "source_code_path"]


def make_data(dir_path, videos, transcripts=None, samples=None, config=None):
    """Build a fixture data dir: videos.csv, transcipts/, optional samples.csv/config."""
    d = Path(dir_path)
    (d / "transcipts").mkdir(parents=True, exist_ok=True)
    with (d / "videos.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=VIDEO_COLS)
        w.writeheader()
        for v in videos:
            row = {c: "" for c in VIDEO_COLS}
            row.update(v)
            w.writerow(row)
    for name, text in (transcripts or {}).items():
        (d / "transcipts" / name).write_text(text, encoding="utf-8")
    if samples is not None:
        with (d / "samples.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=SAMPLE_COLS)
            w.writeheader()
            for s in samples:
                row = {c: "" for c in SAMPLE_COLS}
                row.update(s)
                w.writerow(row)
    if config is not None:
        (d / "search_config.json").write_text(json.dumps(config), encoding="utf-8")
    return d


def run_main(args):
    """Run search.main(args), capturing (exit_code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = search.main(args)
    return code, out.getvalue(), err.getvalue()


class StopwordTests(unittest.TestCase):
    def test_base_stopwords_drop_generic_words(self):
        self.assertEqual(search.query_tokens("how to use lighting"), ["lighting"])

    def test_domain_stopwords_loaded_from_config(self):
        with tempfile.TemporaryDirectory() as d:
            make_data(d, [], config={"domain_stopwords": ["metal", "apple"]})
            stop = search.load_stopwords(d)
            self.assertEqual(search.query_tokens("metal lighting apple", stop),
                             ["lighting"])

    def test_missing_config_is_base_only(self):
        with tempfile.TemporaryDirectory() as d:
            make_data(d, [])
            stop = search.load_stopwords(d)
            self.assertIn("the", stop)
            self.assertNotIn("metal", stop)


class VideoSearchTests(unittest.TestCase):
    def test_finds_video_by_keyword(self):
        with tempfile.TemporaryDirectory() as d:
            make_data(
                d,
                videos=[{"id": "1", "collection": "wwdc2020", "title": "Deferred Lighting",
                         "keywords": "lighting", "video_url": "u1"}],
                transcripts={"wwdc2020-1.txt": "deferred lighting on apple gpus"},
            )
            code, out, _ = run_main(["lighting", "--data", d])
            self.assertEqual(code, 0)
            self.assertIn("Deferred Lighting", out)

    def test_transcript_frequency_breaks_ties(self):
        with tempfile.TemporaryDirectory() as d:
            make_data(
                d,
                videos=[
                    {"id": "1", "collection": "wwdc2020", "title": "Talk One",
                     "keywords": "lighting", "video_url": "u1"},
                    {"id": "2", "collection": "wwdc2020", "title": "Talk Two",
                     "keywords": "lighting", "video_url": "u2"},
                ],
                transcripts={
                    "wwdc2020-1.txt": "lighting " * 1,
                    "wwdc2020-2.txt": "lighting " * 20,
                },
            )
            code, out, _ = run_main(["lighting", "--data", d])
            self.assertEqual(code, 0)
            self.assertLess(out.index("Talk Two"), out.index("Talk One"))

    def test_missing_videos_csv_errors(self):
        with tempfile.TemporaryDirectory() as d:
            code, _, err = run_main(["lighting", "--data", d])
            self.assertEqual(code, 1)
            self.assertIn("videos index not found", err)

    def test_query_with_only_stopwords_errors(self):
        with tempfile.TemporaryDirectory() as d:
            make_data(d, [])
            code, _, err = run_main(["how to use", "--data", d])
            self.assertEqual(code, 1)
            self.assertIn("no searchable terms", err)


class SamplesOptionalTests(unittest.TestCase):
    def test_type_all_without_samples_returns_videos_only(self):
        with tempfile.TemporaryDirectory() as d:
            make_data(
                d,
                videos=[{"id": "1", "collection": "wwdc2020", "title": "Concurrency",
                         "keywords": "actors", "video_url": "u1"}],
                transcripts={"wwdc2020-1.txt": "actors and tasks"},
            )
            code, out, _ = run_main(["actors", "--type", "all", "--data", d])
            self.assertEqual(code, 0)
            self.assertIn("Concurrency", out)
            self.assertNotIn("[SAMPLE]", out)

    def test_type_sample_without_samples_is_clean(self):
        with tempfile.TemporaryDirectory() as d:
            make_data(d, [{"id": "1", "collection": "wwdc2020", "title": "X",
                           "keywords": "actors", "video_url": "u1"}])
            code, out, _ = run_main(["actors", "--type", "sample", "--data", d])
            self.assertEqual(code, 0)
            self.assertIn("No samples in this index", out + _)

    def test_samples_searched_when_present(self):
        with tempfile.TemporaryDirectory() as d:
            make_data(
                d,
                videos=[],
                samples=[{"id": "s1", "topic": "Lighting", "title": "Deferred sample",
                          "tags": "deferred,lighting", "source_available": "false"}],
            )
            code, out, _ = run_main(["deferred", "--type", "sample", "--data", d])
            self.assertEqual(code, 0)
            self.assertIn("Deferred sample", out)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run the tests to confirm they fail**

Run:
```bash
cd /Users/amressam/projects/llm-skills/tools && python3 -m unittest test_search -v
```
Expected: failures/errors — `load_stopwords` doesn't exist, `query_tokens` has no stopwords arg, `main` has no `--data`, etc.

- [ ] **Step 4: Rewrite `tools/search.py` with the generalized implementation**

Replace the entire contents of `tools/search.py` with:
```python
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
```

- [ ] **Step 5: Run the tests to confirm they pass**

Run:
```bash
cd /Users/amressam/projects/llm-skills/tools && python3 -m unittest test_search -v
```
Expected: all tests OK.

- [ ] **Step 6: Commit**

```bash
cd /Users/amressam/projects/llm-skills
git add -A && git commit -m "feat: generalize search.py (--data, optional samples, config stopwords) + tests"
```

---

## Task 5: Move + finalize the `metal-resources` skill data

**Files:**
- Move: `metal/metal-resources/SKILL.md` → `skills/metal-resources/SKILL.md`
- Move: `metal/metal-resources/data/` → `skills/metal-resources/data/`
- Rename: `skills/metal-resources/data/metal_samples.csv` → `samples.csv`
- Create: `skills/metal-resources/data/search_config.json`

- [ ] **Step 1: Move the metal skill bundle to `skills/`**

Run:
```bash
cd /Users/amressam/projects/llm-skills
mkdir -p skills
git mv metal/metal-resources skills/metal-resources
```

- [ ] **Step 2: Standardize the samples filename**

Run:
```bash
cd /Users/amressam/projects/llm-skills
git mv skills/metal-resources/data/metal_samples.csv skills/metal-resources/data/samples.csv
```

- [ ] **Step 3: Add the metal search config**

Create `skills/metal-resources/data/search_config.json`:
```json
{
  "domain_stopwords": ["metal", "apple"]
}
```

- [ ] **Step 4: Sanity-check search against the real metal data**

Run:
```bash
cd /Users/amressam/projects/llm-skills
python3 tools/search.py "deferred lighting tile shaders" --data skills/metal-resources/data --limit 3
```
Expected: 2-3 `[VIDEO]` results with `url:` and `transcript:` lines; transcript paths under `skills/metal-resources/data/transcipts/`. Confirm a `[SAMPLE]` appears for `python3 tools/search.py "deferred lighting" --type sample --data skills/metal-resources/data`.

- [ ] **Step 5: Commit**

```bash
cd /Users/amressam/projects/llm-skills
git add -A && git commit -m "refactor: move metal-resources into skills/, standardize samples.csv + config"
```

---

## Task 6: Vendor `search.py` into `metal-resources` + update its SKILL.md

**Files:**
- Create: `skills/metal-resources/scripts/search.py` (copy of `tools/search.py`)
- Modify: `skills/metal-resources/SKILL.md`

- [ ] **Step 1: Vendor the canonical tool into the skill**

Run:
```bash
cd /Users/amressam/projects/llm-skills
mkdir -p skills/metal-resources/scripts
cp tools/search.py skills/metal-resources/scripts/search.py
```

- [ ] **Step 2: Repoint the search command in `SKILL.md`**

In `skills/metal-resources/SKILL.md`, in the "1. Search the index" section, replace the code block:
```
python3 scripts/search.py "<concept terms>" [--type video|sample|all] [--limit N] [--json]
```
with:
```
python3 "${CLAUDE_SKILL_DIR}/scripts/search.py" "<concept terms>" \
    --data "${CLAUDE_SKILL_DIR}/data" [--type video|sample|all] [--limit N] [--json]
```
and replace the sentence "Run it from this skill's directory, or give the full path to `scripts/search.py`." with "`${CLAUDE_SKILL_DIR}` resolves to this skill's own directory, so the command works regardless of the current working directory."

- [ ] **Step 3: Add the context7 refresh step to the workflow**

In `skills/metal-resources/SKILL.md`, immediately after the "### 3. Deep-dive mode" section (before "### Samples"), insert:
```markdown
### 4. Refresh current API details from context7

Transcripts explain concepts and Apple's reasoning but are pinned to their WWDC
year; Metal's exact API shapes change across OS versions. **Before writing or
finalizing any Metal implementation code, refresh the current API from
context7**: resolve the relevant framework (Metal, MetalKit, MetalFX, etc.) and
query its docs to confirm exact signatures, parameters, and availability. Don't
ship API shapes from memory or a dated transcript.

When sources conflict: for API specifics prefer context7 (most current); for
concepts/patterns prefer the transcripts (most recent `event` year). This step
applies to implementation/debug/review work — pure "what should I watch?" asks
can skip it.
```

- [ ] **Step 4: Fix the samples filename + tools path references**

In `skills/metal-resources/SKILL.md`:
- In "What's bundled (`data/`)", change `**`metal_samples.csv`**` to `**`samples.csv`**`.
- In "Limitations", change "regenerate `videos.csv` with the repo's `tools/build_index.py` and re-copy the data into `data/`." to "regenerate `videos.csv` with the plugin's `tools/build_index.py` (maintainer-only)."

- [ ] **Step 5: Verify the vendored copy matches the canonical**

Run:
```bash
cd /Users/amressam/projects/llm-skills
diff tools/search.py skills/metal-resources/scripts/search.py && echo "IN SYNC"
```
Expected: "IN SYNC" (no diff output).

- [ ] **Step 6: Commit**

```bash
cd /Users/amressam/projects/llm-skills
git add -A && git commit -m "feat: vendor search.py into metal-resources + repoint SKILL.md, add context7 step"
```

---

## Task 7: Build the Swift video index

**Files:**
- Move: `swift/transcipts/` → `skills/swift-resources/data/transcipts/`
- Move: `swift/videos.html` → `sources/swift/videos.html`
- Create: `skills/swift-resources/data/videos.csv` (built)

- [ ] **Step 1: Place the Swift transcripts under the new skill's data dir**

Run:
```bash
cd /Users/amressam/projects/llm-skills
mkdir -p skills/swift-resources/data
git mv swift/transcipts skills/swift-resources/data/transcipts
find skills/swift-resources/data/transcipts -name .DS_Store -delete
```

- [ ] **Step 2: Move the Swift raw HTML into `sources/`**

Run:
```bash
cd /Users/amressam/projects/llm-skills
mkdir -p sources/swift
git mv swift/videos.html sources/swift/videos.html
```

- [ ] **Step 3: Build `videos.csv` from the Swift grid + transcripts**

Run:
```bash
cd /Users/amressam/projects/llm-skills
python3 tools/build_index.py \
  --html sources/swift/videos.html \
  --transcripts skills/swift-resources/data/transcipts \
  --out skills/swift-resources/data/videos.csv
```
Expected (stderr): `parsed 1424 cards -> wrote N rows ...` where N is the number of Swift transcripts that matched a card (up to 124).

- [ ] **Step 4: Spot-check the built index**

Run:
```bash
cd /Users/amressam/projects/llm-skills
head -1 skills/swift-resources/data/videos.csv
wc -l skills/swift-resources/data/videos.csv
```
Expected: header `id,title,description,...,transcript_path`; line count = N rows + 1. If N is 0 or far below ~100, the grid markup differs — STOP and inspect `sources/swift/videos.html` for `vc-card` structure before continuing.

- [ ] **Step 5: Commit**

```bash
cd /Users/amressam/projects/llm-skills
git add -A && git commit -m "feat: build swift-resources video index from saved grid + transcripts"
```

---

## Task 8: Create the `swift-resources` skill (SKILL.md, config, vendored tool)

**Files:**
- Create: `skills/swift-resources/data/search_config.json`
- Create: `skills/swift-resources/scripts/search.py` (copy of `tools/search.py`)
- Create: `skills/swift-resources/SKILL.md`

- [ ] **Step 1: Add the Swift search config**

Create `skills/swift-resources/data/search_config.json`:
```json
{
  "domain_stopwords": ["swift", "apple"]
}
```

- [ ] **Step 2: Vendor the canonical tool**

Run:
```bash
cd /Users/amressam/projects/llm-skills
mkdir -p skills/swift-resources/scripts
cp tools/search.py skills/swift-resources/scripts/search.py
```

- [ ] **Step 3: Write `SKILL.md` (no samples section)**

Create `skills/swift-resources/SKILL.md`:
```markdown
---
name: swift-resources
description: >-
  Curated offline index of Apple's official Swift guidance — WWDC and Tech Talk
  videos with full searchable transcripts — plus a ranked search tool that finds
  the most relevant authoritative material for any Swift topic and grounds
  answers in the actual transcripts. Use this skill whenever you write,
  implement, debug, optimize, explain, answer questions about, or review Swift
  code: the Swift language and standard library, Swift Concurrency (async/await,
  actors, tasks, Sendable, structured concurrency), generics, macros, value vs
  reference semantics, error handling, protocols, result builders, Swift testing,
  interoperability, performance, and related topics — even when the user does not
  mention videos, docs, WWDC, or this skill by name. Prefer grounding Swift work
  in these sources over memory, because Swift evolves every release. Before
  writing code, refresh exact current API details from context7.
---

# Swift Resources

A curated, offline knowledge base of Apple's **own** Swift guidance, plus a
search tool to mine it. Swift evolves every year (concurrency, macros, ownership,
testing), so grounding work in Apple's actual talks — and confirming current API
shapes against live docs — keeps it correct and current.

Consult this skill for any non-trivial Swift task — implementing, reviewing,
debugging, optimizing, or answering a question. Don't wait to be asked for "a
video"; the point is to ground the work itself.

## What's bundled (`data/`)

- **`videos.csv`** — Apple Developer videos (WWDC sessions + Tech Talks) that
  have a full transcript on disk. Columns include `title`, `description`,
  `topics`, `event`, `duration`, `video_url`, and `transcript_path`.
- **`transcipts/`** — the plain-text transcript for every video above, named
  `<collection>-<id>.txt`. This is the real substance — Apple engineers
  explaining the language and the reasoning behind it.

There are **no samples** in this skill.

## Workflow

### 1. Search the index

Turn the task into a few concept terms (not a full sentence) and run the search
tool. Think about the Swift concepts involved — e.g. "make this code safe to call
from multiple tasks" becomes `actors sendable data races`.

```
python3 "${CLAUDE_SKILL_DIR}/scripts/search.py" "<concept terms>" \
    --data "${CLAUDE_SKILL_DIR}/data" [--limit N] [--json]
```

`${CLAUDE_SKILL_DIR}` resolves to this skill's own directory, so the command
works regardless of the current working directory. The tool ranks by curated
tags/keywords, title, and how much each transcript actually discusses your terms,
and prints each video's `video_url` and absolute `transcript:` path.

### 2. Quick mode — surface what's relevant

For a navigational ask ("what should I watch to learn X?"), the ranked output is
the answer. Present the top few with a one-line reason and the citation format
below. Don't read transcripts unless the work needs it.

### 3. Deep-dive mode — ground the answer in the transcript

For substantive work — implementing, reviewing, debugging, or any non-trivial
question — **read the transcript of the top one or two videos** (`Read` the
`transcript:` path from the search output) before you answer or write code. The
transcript is where Apple's concrete guidance, gotchas, and recommended patterns
live. If transcripts conflict, prefer the most recent `event` year. The
transcripts have no timestamps, so quote or paraphrase rather than pointing at a
time.

### 4. Refresh current API details from context7

Transcripts explain concepts and Apple's reasoning but are pinned to their WWDC
year; Swift's APIs and standard library evolve every release. **Before writing or
finalizing any Swift implementation code, refresh the current API from
context7**: resolve the relevant library/framework (the Swift standard library,
Swift Concurrency, Foundation, etc.) and query its docs to confirm exact
signatures, availability, and current best practice. Don't ship API shapes from
memory or a dated transcript.

When sources conflict: for API specifics prefer context7 (most current); for
concepts/patterns prefer the transcripts (most recent `event` year). This step
applies to implementation/debug/review work — pure "what should I watch?" asks
can skip it.

## Citation format

Make recommendations skimmable and clickable:

> **Meet async/await in Swift** (WWDC21, 31:55) — introduces structured
> concurrency, `async`/`await`, and how it replaces completion handlers.
> https://developer.apple.com/videos/play/wwdc2021/10132/

When you ground an answer in a transcript, say which video it came from so the
developer can go deeper.

## Good search terms

- Use distinctive Swift nouns: `actors`, `sendable`, `structured concurrency`,
  `macros`, `result builders`, `existentials`, `ownership`, `typed throws`.
- The tool drops generic words (and `swift`, `apple`); a query of only generic
  words returns nothing. If a search is thin, retry with a synonym or broader
  concept.

## Limitations

- The corpus is curated, not exhaustive — only videos with a transcript on disk
  are indexed. A miss means "not in this index," not "doesn't exist."
- To refresh the index, regenerate `videos.csv` with the plugin's
  `tools/build_index.py` (maintainer-only).
```

- [ ] **Step 4: Verify search works against the Swift skill**

Run:
```bash
cd /Users/amressam/projects/llm-skills
python3 tools/search.py "actors sendable concurrency" --data skills/swift-resources/data --limit 3
python3 tools/search.py "anything" --type sample --data skills/swift-resources/data
```
Expected: first prints `[VIDEO]` results; second prints "No samples in this index." and exits 0.

- [ ] **Step 5: Commit**

```bash
cd /Users/amressam/projects/llm-skills
git add -A && git commit -m "feat: add swift-resources skill (no samples) with vendored search tool"
```

---

## Task 9: Create the `apple-ecosystem` umbrella skill

**Files:**
- Create: `skills/apple-ecosystem/SKILL.md`

- [ ] **Step 1: Write the umbrella SKILL.md**

Create `skills/apple-ecosystem/SKILL.md`:
```markdown
---
name: apple-ecosystem
description: >-
  Umbrella for grounding Apple-platform development in Apple's own authoritative
  material (WWDC and Tech Talk transcripts, plus official samples). Use when a
  task involves Apple developer technologies and you want correct, current
  guidance rather than memory. Routes to a domain skill: Metal graphics/compute →
  metal-resources; the Swift language & concurrency → swift-resources. Establishes
  the shared workflow — search the curated index, read the transcript, then
  refresh exact current API details from context7 before writing code.
---

# Apple Ecosystem Resources (umbrella)

This is the entry point for the `apple-dev-skills` family: a set of skills that
ground Apple-platform development in Apple's **own** guidance (WWDC / Tech Talk
transcripts and official samples), instead of relying on memory that drifts as
APIs change.

## Pick the domain skill

- **Metal** — graphics & compute (MSL shaders, render/compute pipelines,
  argument buffers, ray tracing, MetalFX, GPU profiling): use **`metal-resources`**.
- **Swift** — the language & standard library, Swift Concurrency, generics,
  macros, testing: use **`swift-resources`**.

If a task spans both (e.g. a Swift app driving a Metal renderer), use both: the
Swift skill for app/language concerns and the Metal skill for GPU concerns.

## Shared workflow (every domain skill follows this)

1. **Search** the curated index with a few concept terms (not a sentence) via the
   skill's `scripts/search.py` against its `data/` dir.
2. **Read** the top one or two transcripts for concepts, recommended patterns,
   and gotchas before writing or reviewing code.
3. **Refresh from context7** — before writing or finalizing implementation code,
   resolve the relevant Apple framework/library in context7 and query its docs to
   confirm current API signatures, parameters, and availability. Apple's APIs
   change across OS versions; don't ship shapes from memory or a dated transcript.
4. **Write / review & cite** — ground the answer in both sources; cite the talk,
   and note where context7 confirmed or corrected an API.

Precedence on conflict: API specifics → context7 (most current); concepts and
reasoning → transcripts (most recent event year). The context7 step is for
implementation/debug/review work; pure "what should I watch?" asks can skip it.

## Adding a new domain skill

1. Create `skills/<domain>-resources/` with `SKILL.md`, `scripts/`, and `data/`.
2. Put transcripts in `data/transcipts/` named `<collection>-<id>.txt`, save the
   Apple videos grid to `sources/<domain>/videos.html`, and build the index:
   `python3 tools/build_index.py --html sources/<domain>/videos.html
   --transcripts skills/<domain>-resources/data/transcipts --out
   skills/<domain>-resources/data/videos.csv`.
3. Add `data/search_config.json` with the domain's `domain_stopwords`.
4. Vendor the tool: `cp tools/search.py skills/<domain>-resources/scripts/search.py`
   (or run `tools/sync_vendored.sh`).
5. List the new domain in the "Pick the domain skill" section above.
```

- [ ] **Step 2: Commit**

```bash
cd /Users/amressam/projects/llm-skills
git add -A && git commit -m "feat: add apple-ecosystem umbrella skill (routing + shared workflow)"
```

---

## Task 10: Sync helper + drift test

**Files:**
- Create: `tools/sync_vendored.sh`
- Create: `tools/test_tools_in_sync.py`

- [ ] **Step 1: Write the sync helper**

Create `tools/sync_vendored.sh`:
```bash
#!/usr/bin/env bash
# Copy the canonical tools/search.py into every skill's scripts/search.py.
# Run from anywhere; paths are resolved relative to this script.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(dirname "$here")"
src="$here/search.py"
count=0
for skill_scripts in "$root"/skills/*/scripts; do
  [ -d "$skill_scripts" ] || continue
  cp "$src" "$skill_scripts/search.py"
  echo "synced -> ${skill_scripts#"$root"/}/search.py"
  count=$((count + 1))
done
echo "synced $count vendored copy/copies from tools/search.py"
```
Then: `chmod +x tools/sync_vendored.sh`.

- [ ] **Step 2: Write the drift test**

Create `tools/test_tools_in_sync.py`:
```python
"""Each skill's vendored scripts/search.py must match the canonical tools/search.py.

Run: python3 -m unittest test_tools_in_sync
"""

import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
ROOT = TOOLS_DIR.parent
CANONICAL = TOOLS_DIR / "search.py"


class VendoredCopiesInSyncTests(unittest.TestCase):
    def test_every_skill_copy_matches_canonical(self):
        canonical = CANONICAL.read_bytes()
        copies = sorted((ROOT / "skills").glob("*/scripts/search.py"))
        self.assertTrue(copies, "no vendored search.py copies found under skills/*/scripts/")
        for copy in copies:
            with self.subTest(copy=str(copy.relative_to(ROOT))):
                self.assertEqual(copy.read_bytes(), canonical,
                                 f"{copy.relative_to(ROOT)} drifted from tools/search.py; "
                                 f"run tools/sync_vendored.sh")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run the sync helper, then the full tool test suite**

Run:
```bash
cd /Users/amressam/projects/llm-skills
bash tools/sync_vendored.sh
cd tools && python3 -m unittest discover -p 'test_*.py' -v
```
Expected: sync reports 2 copies; all tests (build_index, search, tools_in_sync) OK.

- [ ] **Step 4: Commit**

```bash
cd /Users/amressam/projects/llm-skills
git add -A && git commit -m "feat: add vendored-copy sync helper + drift test"
```

---

## Task 11: Plugin manifest, sources, docs, README, and cleanup

**Files:**
- Create: `.claude-plugin/plugin.json`
- Move: `metal/tools/videos.html` → `sources/metal/videos.html`
- Move: `metal/metal_samples.txt` → `sources/metal/metal_samples.txt`
- Move: `metal/docs/superpowers/specs/2026-05-23-apple-video-csv-index-design.md` → `docs/superpowers/specs/`
- Create: `README.md`
- Delete: leftover `metal/` and `swift/` wrapper dirs

- [ ] **Step 1: Write the plugin manifest**

Create `.claude-plugin/plugin.json`:
```json
{
  "name": "apple-dev-skills",
  "description": "Grounded Apple-platform development: curated WWDC/Tech-Talk transcript indexes and a ranked search tool for Metal and Swift, refreshed against current docs via context7.",
  "version": "0.1.0"
}
```

- [ ] **Step 2: Move maintainer raw inputs into `sources/metal/`**

Run:
```bash
cd /Users/amressam/projects/llm-skills
mkdir -p sources/metal
git mv metal/tools/videos.html sources/metal/videos.html
git mv metal/metal_samples.txt sources/metal/metal_samples.txt
```

- [ ] **Step 3: Move the earlier metal design doc into root docs**

Run:
```bash
cd /Users/amressam/projects/llm-skills
mkdir -p docs/superpowers/specs
git mv metal/docs/superpowers/specs/2026-05-23-apple-video-csv-index-design.md docs/superpowers/specs/
```

- [ ] **Step 4: Inspect and remove the now-empty/leftover wrapper dirs**

Run:
```bash
cd /Users/amressam/projects/llm-skills
find metal swift -type f -not -name .DS_Store
```
Expected leftovers in `metal/`: `README.md`, `videos.csv`, `metal_samples.csv`, and an empty `transcipts/` (root copies the new structure supersedes). `swift/` should have no files left. Then remove them:
```bash
cd /Users/amressam/projects/llm-skills
git rm -r --ignore-unmatch metal/README.md metal/videos.csv metal/metal_samples.csv
rm -rf metal swift
```
(The `rm -rf` clears any remaining empty dirs / `.DS_Store`. Confirm `metal/` and `swift/` are gone with `ls`.)

- [ ] **Step 5: Write the repo/plugin README**

Create `README.md`:
```markdown
# apple-dev-skills

A Claude Code plugin that grounds Apple-platform development in Apple's **own**
guidance. It ships curated, offline indexes of WWDC / Tech-Talk transcripts and a
ranked search tool, exposed as skills.

## Skills

- **apple-ecosystem** — umbrella: routes to a domain skill and defines the shared
  workflow (search → read transcript → refresh API from context7 → cite).
- **metal-resources** — Metal graphics & compute. Includes a samples index.
- **swift-resources** — the Swift language & concurrency. No samples.

## Layout

```
.claude-plugin/plugin.json   # plugin manifest
tools/                       # shared, domain-agnostic tooling (source of truth)
  search.py                  #   runtime ranked search (--data <dir>)
  build_index.py             #   build videos.csv from a saved grid + transcripts
  sync_vendored.sh           #   copy search.py into each skill's scripts/
  test_*.py                  #   unittest suites
skills/<name>/               # self-contained skill: SKILL.md + scripts/ + data/
sources/<domain>/            # maintainer-only raw inputs (videos.html, etc.)
docs/superpowers/            # design specs + implementation plans
```

The runtime `search.py` is **vendored** into each skill's `scripts/` (Claude Code
skills are self-contained and can't reliably reach a sibling `tools/`). Edit the
canonical `tools/search.py`, then run `tools/sync_vendored.sh`;
`tools/test_tools_in_sync.py` fails if a copy drifts.

## Maintainer: refresh / add a video index

1. Save the Apple Developer videos grid page (filtered to the topic) as HTML to
   `sources/<domain>/videos.html`.
2. Put transcripts in `skills/<domain>-resources/data/transcipts/` named
   `<collection>-<id>.txt` (mirrors the URL path `/videos/play/<collection>/<id>/`).
3. Build:
   ```
   python3 tools/build_index.py \
     --html sources/<domain>/videos.html \
     --transcripts skills/<domain>-resources/data/transcipts \
     --out skills/<domain>-resources/data/videos.csv
   ```
   Only videos with a transcript on disk are indexed.

## Tests

```
cd tools && python3 -m unittest discover -p 'test_*.py'
```
```

- [ ] **Step 6: Commit**

```bash
cd /Users/amressam/projects/llm-skills
git add -A && git commit -m "feat: add plugin manifest, README, sources/, docs; remove old wrapper dirs"
```

---

## Task 12: Final end-to-end verification

**Files:** none (verification only)

- [ ] **Step 1: Full test suite green**

Run:
```bash
cd /Users/amressam/projects/llm-skills/tools && python3 -m unittest discover -p 'test_*.py' -v
```
Expected: all tests OK (build_index, search, tools_in_sync).

- [ ] **Step 2: Both skills search correctly via their vendored copies**

Run:
```bash
cd /Users/amressam/projects/llm-skills
python3 skills/metal-resources/scripts/search.py "argument buffers heaps" --data skills/metal-resources/data --limit 2
python3 skills/swift-resources/scripts/search.py "structured concurrency tasks" --data skills/swift-resources/data --limit 2
python3 skills/swift-resources/scripts/search.py "x" --type sample --data skills/swift-resources/data
```
Expected: metal + swift each return `[VIDEO]` results with valid `transcript:` paths that exist on disk; the swift `--type sample` call prints "No samples in this index."

- [ ] **Step 3: Verify final tree shape**

Run:
```bash
cd /Users/amressam/projects/llm-skills
test -f .claude-plugin/plugin.json && echo "manifest OK"
ls skills
test ! -d metal && test ! -d swift && echo "old wrappers removed"
git status --short
```
Expected: "manifest OK"; `skills/` lists `apple-ecosystem metal-resources swift-resources`; "old wrappers removed"; clean working tree (or only expected untracked files).

- [ ] **Step 4: Confirm SKILL.md frontmatter validity**

Run:
```bash
cd /Users/amressam/projects/llm-skills
for f in skills/*/SKILL.md; do echo "== $f =="; head -3 "$f"; done
```
Expected: each starts with `---` then a `name:` matching its directory (lowercase/hyphens), then `description:`.

- [ ] **Step 5: Final commit (if anything changed) / done**

```bash
cd /Users/amressam/projects/llm-skills
git add -A && git commit -m "test: end-to-end verification of apple-dev-skills plugin" --allow-empty
```

---

## Self-Review notes (for the implementer)

- **Path variable:** SKILL.md uses `${CLAUDE_SKILL_DIR}` (documented for a skill's
  own dir). If a future Claude Code version doesn't expand it in plain agent Bash,
  the fallback is to `cd` into the skill dir and run `python3 scripts/search.py
  --data data ...` — the vendored copy makes that always available.
- **Row count for swift (Task 7):** N depends on how many of the 124 transcripts
  match a card in the grid; anything near ~100+ is healthy. A near-zero count
  means the grid markup differs — stop and inspect before proceeding.
- **No samples for swift:** enforced by simply not creating `samples.csv`; the
  generalized `search.py` handles its absence (Task 4 tests cover this).
