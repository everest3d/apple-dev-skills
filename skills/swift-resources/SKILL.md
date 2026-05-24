---
name: swift-resources
description: >-
  Curated offline index of Apple's own Swift guidance — WWDC and Tech Talk
  videos with full searchable transcripts — plus a ranked search tool that finds
  the most relevant authoritative material for any Swift topic and grounds the
  answer in what Apple's engineers actually said. Use this skill whenever you
  write, implement, debug, optimize, review, or explain Swift code: the Swift
  language and standard library, Swift Concurrency (async/await, actors, tasks,
  Sendable, structured concurrency, data races), generics and existentials,
  macros, result builders, value vs reference semantics, ownership, typed throws,
  error handling, protocols, and Swift testing — even when the user never
  mentions WWDC, videos, transcripts, or this skill by name, and even if they
  only paste Swift code and ask "why is this slow / is this safe / is this
  idiomatic". Prefer grounding Swift work in these sources over memory, because
  Swift changes every release; then confirm exact current API details against
  context7 before writing code.
---

# Swift Resources

A curated, offline knowledge base of Apple's **own** Swift guidance, plus a tool
to search it. Swift moves fast — concurrency, macros, ownership, typed throws,
and the testing story have all shifted in recent releases — so answering from
memory is risky. Grounding the work in Apple's actual talks, and confirming the
current API shape against live docs, is what keeps it correct.

Reach for this on any non-trivial Swift task — implementing, reviewing,
debugging, optimizing, or answering a "why does this behave this way?" question.
Don't wait to be asked for "a video": the point is to ground the work itself, not
to recommend watching.

## What's bundled (`data/`)

- **`videos.csv`** — Apple Developer videos (WWDC sessions + Tech Talks) that
  have a full transcript on disk. Columns include `title`, `description`,
  `topics`, `event`, `duration`, `video_url`, and `transcript_path`.
- **`transcipts/`** — the plain-text transcript for every video above, named
  `<collection>-<id>.txt`. This is the real substance: Apple engineers
  explaining the language and the reasoning behind it.

There are **no code samples** in this skill — the index is videos only.

## Workflow

### 1. Search the index

Turn the task into a few concept terms (not a full sentence) and run the search
tool. Think about the Swift concepts involved — e.g. "make this code safe to call
from several tasks at once" becomes `actors sendable data races`.

```
python3 "${CLAUDE_SKILL_DIR}/scripts/search.py" "<concept terms>" \
    --data "${CLAUDE_SKILL_DIR}/data" [--limit N] [--json]
```

`${CLAUDE_SKILL_DIR}` resolves to this skill's own directory, so the command
works regardless of the current working directory. The tool ranks by curated
tags/keywords, by title, and by how much each transcript actually discusses your
terms — so a talk that is *about* your topic beats one that merely name-drops it.
Each result prints its `video_url` and the absolute `transcript:` path.

### 2. Quick mode — surface what's relevant

For a navigational ask ("what should I watch to learn X?"), the ranked list *is*
the answer. Present the top few with a one-line reason each, using the citation
format below. Don't open transcripts unless the work needs it.

### 3. Deep-dive mode — ground the answer in the transcript

For substantive work — implementing, reviewing, debugging, or any non-trivial
question — **read the transcript of the top one or two videos** (`Read` the
`transcript:` path from the search output) before you answer or write code. The
transcript is where Apple's concrete guidance, gotchas, and recommended patterns
live; base your work on what it actually says, and cite it. If two transcripts
disagree, prefer the most recent `event` year, since Swift's guidance evolves.
Transcripts have no timestamps, so quote or paraphrase the passage rather than
pointing at a time.

### 4. Refresh current API details from context7

Transcripts explain concepts and Apple's reasoning, but each is pinned to its
WWDC year, and Swift's standard library and concurrency APIs keep changing.
**Before writing or finalizing any Swift implementation code, refresh the current
API from context7**: resolve the relevant library (the Swift standard library,
Swift Concurrency, Foundation, Swift Testing, etc.) and query its docs to confirm
exact signatures, availability, and current best practice. Don't ship API shapes
from memory or a dated transcript.

When sources conflict: for API specifics prefer context7 (most current); for
concepts and reasoning prefer the transcripts (most recent year). This step is
for implementation/debug/review work — a pure "what should I watch?" ask can skip
it.

## Citation format

Make recommendations skimmable and clickable:

> **Meet async/await in Swift** (WWDC21, 31:55) — introduces structured
> concurrency, `async`/`await`, and how it replaces completion handlers.
> https://developer.apple.com/videos/play/wwdc2021/10132/

When you ground an answer in a transcript, name the video it came from so the
developer can go deeper.

## Good search terms

- Use distinctive Swift nouns: `actors`, `sendable`, `structured concurrency`,
  `macros`, `result builders`, `existentials`, `ownership`, `typed throws`,
  `swift testing`.
- The tool drops generic words (and the domain words `swift`/`apple`), so don't
  fuss over phrasing — but a query made only of generic words returns nothing.
- If a search comes back thin, retry with a synonym or a broader concept
  (`concurrency` instead of `cooperative thread pool`).

## Limitations

- The corpus is curated, not exhaustive — only videos with a transcript on disk
  are indexed. A miss means "not in this index," not "doesn't exist."
- To refresh the index, regenerate `videos.csv` with the plugin's
  `tools/build_index.py` (maintainer-only).
