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
