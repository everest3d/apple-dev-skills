---
name: metal-resources
description: >-
  Curated offline index of Apple's official Metal guidance — 100+ WWDC and Tech
  Talk videos with full searchable transcripts, plus Apple's Metal sample-code
  library — with a ranked search tool that finds the most relevant authoritative
  material for any Metal topic and grounds answers in the actual transcripts. Use
  this skill whenever you write, implement, debug, optimize, explain, answer
  questions about, or review code that touches Apple's Metal graphics or compute
  API: Metal Shading Language (MSL) shaders, render and compute pipelines,
  command buffers and queues, MetalKit, argument buffers, resource heaps,
  fences/events, ray tracing, mesh/object shaders, tile shaders, image blocks,
  MetalFX, sparse textures, deferred and forward(+) lighting, GPU performance and
  profiling, and related topics — even when the user does not mention videos,
  docs, WWDC, or this skill by name. Prefer grounding Metal work in these sources
  over relying on memory, because Metal's APIs and recommended practices change
  across OS versions.
---

# Metal Resources

This skill is a curated, offline knowledge base of Apple's **own** Metal
guidance, plus a search tool to mine it. It exists because Metal is large,
evolves every year, and is easy to get subtly wrong from memory — wrong API
shape, outdated best practice, or advice that doesn't fit Apple-silicon's
tile-based GPU. Grounding your work in Apple's actual talks and samples makes it
correct and current.

You are working on a large Metal graphics codebase, so this applies constantly:
**consult this skill for any non-trivial Metal task — implementing, reviewing,
debugging, optimizing, or answering a question.** Don't wait to be asked for "a
video"; the point is to ground the work itself.

## What's bundled (`data/`)

- **`videos.csv`** — ~100 Apple Developer videos (WWDC sessions + Tech Talks)
  that have a full transcript on disk. Columns include `title`, `description`,
  `topics`, `event`, `duration`, `video_url`, and `transcript_path`.
- **`transcipts/`** — the plain-text transcript for every video above, named
  `<collection>-<id>.txt`. This is the real substance — Apple engineers
  explaining the API and the reasoning behind it.
- **`metal_samples.csv`** — Apple's Metal sample-code library (48 official
  samples), with `topic`, `tags`, `language`, and a `source_available` flag.
  The sample **source code is not bundled** (see "Samples" below).

## Workflow

### 1. Search the index

Turn the task into a few concept terms (not a full sentence) and run the search
tool. Think about the Metal concepts involved — e.g. a task about "smooth
shadow edges on Apple GPUs" becomes `msaa antialiasing tile`.

```
python3 scripts/search.py "<concept terms>" [--type video|sample|all] [--limit N] [--json]
```

The tool ranks results by curated tags/keywords, title, and — for videos — how
much each transcript actually discusses your terms (so a talk *about* the topic
beats one that merely name-drops it). Each video result prints its
`video_url` and the absolute `transcript:` path.

Run it from this skill's directory, or give the full path to `scripts/search.py`.

### 2. Quick mode — surface what's relevant

For a navigational ask ("what should I watch to learn X?", "is there a sample
for Y?"), the ranked output is the answer. Present the top few with a one-line
reason, using the citation format below. Don't read transcripts unless the work
needs it.

### 3. Deep-dive mode — ground the answer in the transcript

For substantive work — implementing, reviewing, debugging, or any non-trivial
question — **read the transcript of the top one or two videos** (`Read` the
`transcript:` path from the search output) before you answer or write code. The
transcript is where Apple's concrete guidance, gotchas, and recommended
patterns live. Base your implementation or review on what it actually says, and
cite it. If transcripts conflict, prefer the most recent `event` year, since
Metal's guidance evolves.

This is the default for real Metal work. The transcripts have no timestamps, so
quote or paraphrase the relevant passage rather than pointing at a time.

### Samples — and requesting source code

`metal_samples.csv` tells you a sample *exists* and what it covers, but its
source code is **not** in this skill (`source_available=false`). When a sample
is the right reference for the task:

1. Name it and where it lives (Apple's Metal sample-code library), using its
   `id`/`title`.
2. **Ask the developer to provide that sample's source** (they have it, or can
   download it) so you can read the real code. Reference it by `id`.
3. If/when the source is supplied, it can be recorded in the CSV's
   `source_code_path` for next time.

Don't invent the contents of a sample you can't see — recommend it and request
the code.

## Citation format

Make recommendations skimmable and clickable:

**Video**
> **Modern Rendering with Metal** (WWDC19, 55:28) — covers deferred shading and
> tile-based lighting on Apple GPUs.
> https://developer.apple.com/videos/play/wwdc2019/601/

**Sample**
> **Rendering a scene with deferred lighting in Swift** (Lighting techniques) —
> official Apple sample; source not bundled, ask me to provide it (id:
> `rendering-a-scene-with-deferred-lighting-in-swift`).

When you ground an answer in a transcript, say which video it came from so the
developer can go deeper.

## Good search terms

- Use distinctive Metal nouns: `argument buffers`, `mesh shaders`, `sparse
  textures`, `ray tracing`, `tile shaders`, `MetalFX`, `heaps fences`.
- The tool drops generic words (`metal`, `how`, `code`, `implement`…), so don't
  worry about phrasing — but a query of only generic words returns nothing.
- If a search is thin, retry with a synonym or a broader concept (`lighting`
  instead of `forward plus`).

## Limitations

- The corpus is curated, not exhaustive — only videos that have a transcript on
  disk are indexed. A miss means "not in this index," not "doesn't exist."
- Sample source code is metadata-only until provided (see Samples).
- To refresh the index, regenerate `videos.csv` with the repo's
  `tools/build_index.py` and re-copy the data into `data/`.
