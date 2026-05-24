# apple-dev-skills plugin: reusable indexing tools + Apple-ecosystem skill family

**Date:** 2026-05-25
**Status:** Approved

## Purpose

Turn the existing single Metal skill into a **family** of Apple-ecosystem
developer skills that share one set of tools. Concretely:

1. Make the indexing tools (`build_index.py`, `search.py`) reusable and
   domain-agnostic, hosted in one shared place instead of inside the Metal skill.
2. Reuse those tools to add a **`swift-resources`** skill (Swift / SwiftUI /
   concurrency), grounded in its own WWDC/Tech-Talk transcripts. Swift has
   **no samples**.
3. Group everything as a Claude Code **plugin** (`apple-dev-skills`) with an umbrella
   skill that routes to the domain skills, so adding more domains later is a
   drop-in folder.
4. Add a family-wide rule: **refresh exact implementation details from
   context7** before writing or finalizing code.

## Background / current state

- The Metal work lives under `metal/`: a deployable skill bundle
  (`metal/metal-resources/` = `SKILL.md` + `scripts/search.py` + `data/`), plus
  maintainer inputs (`metal/tools/build_index.py` + tests + `videos.html`,
  `metal/metal_samples.txt`, README, an earlier design doc).
- `metal-resources/data/` holds `videos.csv`, `metal_samples.csv`, and 105
  transcripts under `transcipts/` (folder spelled without the second "r").
- `swift/` already contains the raw inputs for a Swift skill: `videos.html`
  (~3.3 MB Apple videos grid) and 124 transcripts under `transcipts/`. No
  samples file.
- **Tooling reality (verified against Claude Code):** there is **no native
  nested/sub-skill** support — only the top-level `SKILL.md` of each skill
  directory is discovered. The supported way to ship a related *family* is a
  **plugin**, which bundles and namespaces member skills
  (`apple-dev-skills:metal-resources`). Cross-skill links are prose + good
  `description` fields, not a built-in mechanism.

## Decisions (resolved during brainstorming)

| Decision | Choice |
|---|---|
| Packaging | Claude Code **plugin** `apple-dev-skills` with member skills under `skills/` |
| "Sub-skills" | Realized as: one **umbrella** skill that routes + N domain skills (plugin namespacing makes them a family) |
| Shared tool model | **Vendored copies from a single source of truth**: canonical `tools/search.py`; each skill bundles `scripts/search.py`; a sync command + drift test keep them byte-identical. (Docs don't support reaching a sibling `tools/` from inside a skill, so each skill references its own `${CLAUDE_SKILL_DIR}/scripts/search.py`.) |
| Tool location | `tools/` at the plugin root, sibling to `skills/` |
| Swift samples | None — search must work with videos only |
| Grounding | **Two-source loop**: curated transcripts (concepts) + context7 (current API) |

## Target layout

```
llm-skills/                              (plugin: apple-dev-skills)
├── .claude-plugin/plugin.json           # manifest: name, version, description
├── tools/                               # canonical source of truth + maintainer build
│   ├── search.py                        #   runtime: --data <dir>, samples optional (canonical)
│   ├── build_index.py                   #   build-time: --html/--transcripts/--out
│   ├── test_search.py                   #   NEW
│   ├── test_tools_in_sync.py            #   NEW: fails if a vendored copy drifts
│   └── test_build_index.py
├── skills/
│   ├── apple-ecosystem/                 # umbrella skill (routes + extension guide)
│   │   └── SKILL.md
│   ├── metal-resources/
│   │   ├── SKILL.md
│   │   ├── scripts/search.py            #   vendored copy of tools/search.py
│   │   └── data/{videos.csv, samples.csv, search_config.json, transcipts/}
│   └── swift-resources/                 # NO samples
│       ├── SKILL.md
│       ├── scripts/search.py            #   vendored copy of tools/search.py
│       └── data/{videos.csv, search_config.json, transcipts/}
├── sources/                             # maintainer-only raw inputs (not runtime logic)
│   ├── metal/{videos.html, metal_samples.txt}
│   └── swift/{videos.html}
├── docs/superpowers/specs/              # design docs (this file + earlier metal spec)
└── README.md                            # plugin overview + maintainer build steps
```

This relocates `metal/metal-resources/` → `skills/metal-resources/`, hoists the
tools to `tools/`, parks big raw inputs under `sources/`, and moves the earlier
`metal/docs/...` spec to root `docs/`.

## Runtime invocation (vendored tool)

Each member SKILL.md instructs the agent to run the skill's **own** copy of the
tool:

```
python3 "${CLAUDE_SKILL_DIR}/scripts/search.py" --data "${CLAUDE_SKILL_DIR}/data" "<terms>"
```

`${CLAUDE_SKILL_DIR}` is the documented variable for a skill's own directory, so
both `scripts/search.py` and `data/` are referenced inside the skill — the
robust, supported pattern. No cross-skill or plugin-root path assumptions.

**Why vendored, not a shared reference:** Claude Code documents no
`${CLAUDE_PLUGIN_ROOT}` for skills, and reaching a sibling `tools/` via `../../`
is undocumented/fragile (skills are designed self-contained). So the single
source of truth lives in `tools/search.py` and is **copied** into each skill's
`scripts/`; a sync command plus a drift test keep them identical.

### Sync mechanism

- Source of truth: `tools/search.py`.
- Propagate: `cp tools/search.py skills/metal-resources/scripts/search.py &&
  cp tools/search.py skills/swift-resources/scripts/search.py`
  (a `tools/sync_vendored.sh` helper wraps this for all skills under `skills/`).
- `tools/test_tools_in_sync.py` reads `tools/search.py` and each
  `skills/*/scripts/search.py` and asserts byte-for-byte equality, failing CI/
  the test run if any copy drifted.

## tools/search.py — generalization

Behavior changes from the current Metal-coupled version:

- **`--data <dir>` argument** (the skill's data dir). Replaces the hardcoded
  `__file__/../data`. Default `./data` for convenience. The tool reads
  `<data>/videos.csv` and (optionally) `<data>/samples.csv`, and reconstructs
  transcript paths as `<data>/transcipts/<collection>-<id>.txt` (it already
  recomputes these rather than trusting the CSV column).
- **Samples optional.** If `<data>/samples.csv` is absent: search videos only;
  `--type sample` prints a clear "no samples in this index" and exits 0;
  `--type all` searches videos only. If present: behaves as today.
- **Domain-agnostic stopwords.** Remove `"metal"`/`"apple"` from the hardcoded
  set. Load extra stopwords from optional `<data>/search_config.json`:
  `{"domain_stopwords": ["metal", "apple"]}`. Missing/invalid file → no extras,
  no crash.
- **Standard samples filename.** Use `samples.csv` (rename Metal's
  `metal_samples.csv` → `skills/metal-resources/data/samples.csv`; update all
  references). The raw `metal_samples.txt` source moves to `sources/metal/`.
- Ranking logic (tag/title/meta weights + transcript term-frequency for videos)
  is unchanged.

## tools/build_index.py — generalization

- Already domain-neutral in its columns and parsing. Remove the
  `metal/tools`-relative "magic" defaults; require explicit
  `--html`, `--transcripts`, `--out` (it now lives in a shared `tools/` with no
  meaningful sibling defaults). Keep argument names and behavior otherwise.
- The existing `unittest` suite stays valid (it always passed explicit flags).

## Skills

### apple-ecosystem (umbrella)
- Broad trigger: Apple-platform development grounded in Apple's own WWDC /
  Tech-Talk material.
- Routes: *Metal graphics/compute → metal-resources; Swift language &
  concurrency / SwiftUI → swift-resources.*
- States the **two-source workflow** once and the family-wide **context7** rule.
- Includes a short "how to add a new domain skill" note (new `skills/<x>/` with
  `data/`, build its `videos.csv`, add a `search_config.json`, list it here).
- Description tuned to be umbrella-like (not competing with member skills).

### metal-resources
- Existing SKILL.md content, repointed to the shared tool via
  `${CLAUDE_SKILL_DIR}`. Keep Metal framing, the samples section, and citation
  format.
- `data/`: `videos.csv` (moved), `samples.csv` (renamed), `transcipts/` (105),
  `search_config.json` = `{"domain_stopwords": ["metal", "apple"]}`.
- Add the context7 refresh step to its workflow.

### swift-resources
- New SKILL.md adapted from Metal's: Swift / SwiftUI / Swift Concurrency
  framing. **Samples section removed** (no samples).
- `data/`: `videos.csv` (built), `transcipts/` (124),
  `search_config.json` = `{"domain_stopwords": ["swift", "apple"]}`.
- Workflow = search → read transcript → **context7 refresh** → write/cite.

## Two-source grounding workflow (family-wide)

1. **Search** the curated index → identify the authoritative talk/sample.
2. **Read** the top transcript(s) for concepts, recommended patterns, gotchas.
3. **Refresh from context7** — before writing/finalizing implementation code,
   resolve the relevant Apple framework in context7 and query its docs to
   confirm current API signatures/parameters/availability. Do not ship API
   shapes from memory or a dated transcript.
4. **Write / review & cite** — ground in both; cite the talk; note where
   context7 confirmed or corrected an API.

**Precedence on conflict:** API specifics → prefer context7 (most current);
concepts/patterns/reasoning → prefer transcripts (most recent WWDC year among
them). **Scope:** the context7 step applies to implementation/debug/review/code
tasks; pure navigational asks ("what should I watch?") skip it.

## Building the Swift index

```
python3 tools/build_index.py \
  --html sources/swift/videos.html \
  --transcripts skills/swift-resources/data/transcipts \
  --out skills/swift-resources/data/videos.csv
```

Assumption: `sources/swift/videos.html` uses the same `vc-card` grid markup as
Metal's page (same Apple videos site). Verify during implementation; if the
markup differs, adjust the parser. Each row is emitted only when its transcript
exists, so the row count is the number of usable Swift transcripts.

## Testing

- Keep `tools/test_build_index.py` (domain-neutral; must stay green after the
  default-paths change).
- Add `tools/test_search.py` (TDD for the new behavior):
  - ranking order against a fixture data dir;
  - `--type sample`/`all` with **no** `samples.csv` present (videos-only, clean
    message, exit 0);
  - samples present behaves as before;
  - `domain_stopwords` from `search_config.json` are dropped from the query;
  - `--data` points the tool at the right dir and transcript paths resolve.
- Add `tools/test_tools_in_sync.py`: asserts every `skills/*/scripts/search.py`
  is byte-identical to `tools/search.py` (catches vendored drift).
- Manual verification: run the real `search.py` against both skills' data and
  confirm sensible top results; build the Swift `videos.csv` and spot-check.

## Error handling

- search.py: missing `videos.csv` → clear error, non-zero exit. Missing
  `samples.csv` → videos-only, no crash. Query of only stopwords → existing
  "no searchable terms" error. Missing/invalid `search_config.json` → ignored.
- build_index.py: unchanged (missing HTML → error; empty transcripts → header
  only + warning; missing card fields → blank cells).

## Migration / file moves

- `metal/metal-resources/` → `skills/metal-resources/` (keep `scripts/`; its
  `search.py` is replaced by a vendored copy of the new canonical
  `tools/search.py`).
- `metal/tools/{build_index.py,test_build_index.py}` → `tools/`.
- `metal/tools/videos.html` → `sources/metal/videos.html`;
  `metal/metal_samples.txt` → `sources/metal/`.
- `metal/docs/superpowers/specs/2026-05-23-...` → `docs/superpowers/specs/`.
- Redundant root copies in `metal/` (`videos.csv`, `metal_samples.csv`, empty
  `transcipts/`, README) are reconciled into the new structure; the old `metal/`
  wrapper folder is removed once its contents are relocated.
- `swift/videos.html` → `sources/swift/`; `swift/transcipts/` →
  `skills/swift-resources/data/transcipts/`.

## Out of scope

- Fetching/enriching new transcripts or new videos.html pages.
- Detail-page enrichment (`related_links`) for the video index.
- Any change to the ranking algorithm itself.
- Bundling sample source code (still metadata-only / request-on-demand for
  Metal).

## Files created/changed

- `.claude-plugin/plugin.json` (new)
- `tools/search.py` (moved + generalized; canonical), `tools/build_index.py`
  (moved + defaults change), `tools/test_search.py` (new),
  `tools/test_tools_in_sync.py` (new), `tools/sync_vendored.sh` (new),
  `tools/test_build_index.py` (moved)
- `skills/apple-ecosystem/SKILL.md` (new)
- `skills/metal-resources/SKILL.md` (moved + repointed to own `scripts/` +
  context7 step); `scripts/search.py` (vendored copy); `data/` moved,
  `samples.csv` renamed, `search_config.json` new
- `skills/swift-resources/SKILL.md` (new); `scripts/search.py` (vendored copy);
  `data/videos.csv` built; `transcipts/` moved; `search_config.json` new
- `sources/**`, `docs/**`, `README.md` (repo overview)
