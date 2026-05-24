---
name: apple-ecosystem
description: >-
  Entry point for grounding Apple-platform development in Apple's own
  authoritative material — WWDC and Tech Talk transcripts plus official samples —
  instead of relying on memory that drifts as APIs change yearly. Use this skill
  when an Apple developer task spans or doesn't cleanly fit one domain, when you
  need to know which domain skill applies, or to recall the shared working method
  for this family. It routes to the right domain skill — Metal graphics/compute →
  metal-resources; the Swift language, standard library, and concurrency →
  swift-resources — and establishes the shared workflow every domain skill
  follows: search the curated transcript index, read the transcript, then refresh
  exact current API details from context7 before writing code. Prefer the
  specific domain skill when the task is clearly Metal-only or Swift-only.
---

# Apple Ecosystem Resources (umbrella)

This is the entry point for the **`apple-dev-skills`** family: a set of skills
that ground Apple-platform development in Apple's **own** guidance (WWDC / Tech
Talk transcripts and official samples) rather than memory that goes stale as APIs
change each year.

Its job is to point you at the right domain skill and to hold the working method
the whole family shares. When a task is clearly Metal-only or Swift-only, go
straight to that domain skill; come here when the task spans domains, when you're
unsure which applies, or to recall the shared workflow.

## Pick the domain skill

- **Metal — graphics & compute.** MSL shaders, render/compute pipelines, command
  buffers, argument buffers, heaps, ray tracing, mesh/tile shaders, MetalFX, GPU
  profiling and performance: use **`metal-resources`** (it also indexes official
  Metal code samples).
- **Swift — the language & concurrency.** The Swift language and standard
  library, Swift Concurrency (async/await, actors, Sendable), generics, macros,
  result builders, ownership, typed throws, Swift testing: use
  **`swift-resources`** (videos only, no samples).

If a task touches both — e.g. a Swift app driving a Metal renderer — use both:
`swift-resources` for the app/language concerns and `metal-resources` for the GPU
concerns.

## Shared workflow (every domain skill follows this)

1. **Search** the curated index with a few concept terms (not a sentence), using
   the skill's own `scripts/search.py` against its `data/` directory.
2. **Read** the top one or two transcripts for concepts, recommended patterns,
   and gotchas before writing or reviewing code.
3. **Refresh from context7.** Before writing or finalizing implementation code,
   resolve the relevant Apple framework/library in context7 and query its docs to
   confirm current API signatures, parameters, and availability. Apple's APIs
   change across OS versions — don't ship shapes from memory or a dated
   transcript.
4. **Write / review & cite.** Ground the answer in both sources; cite the talk,
   and note where context7 confirmed or corrected an API.

When sources conflict: prefer context7 for API specifics (most current) and the
transcripts for concepts and reasoning (most recent event year). The context7
step is for implementation/debug/review work; a pure "what should I watch?" ask
can skip it.

## Adding a new domain skill

The family is designed so a new domain (SwiftUI, ARKit, Core ML, …) is a drop-in:

1. Create `skills/<domain>-resources/` with a `SKILL.md`, a `scripts/` dir, and a
   `data/` dir.
2. Put transcripts in `data/transcipts/` named `<collection>-<id>.txt` (mirroring
   the video URL path `/videos/play/<collection>/<id>/`), save the Apple videos
   grid page to `sources/<domain>/videos.html`, and build the index:
   ```
   python3 tools/build_index.py --html sources/<domain>/videos.html \
     --transcripts skills/<domain>-resources/data/transcipts \
     --out skills/<domain>-resources/data/videos.csv
   ```
3. Add `data/search_config.json` with the domain's `domain_stopwords` (the domain
   name plus `apple`, so they don't pollute ranking).
4. Vendor the search tool: `cp tools/search.py
   skills/<domain>-resources/scripts/search.py` (or run `tools/sync_vendored.sh`).
5. List the new domain under "Pick the domain skill" above.
