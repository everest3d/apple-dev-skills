# Metal video & sample indexes

Searchable CSV datasets that help a coding agent (or a Metal developer) find the
right learning resource:

- **`videos.csv`** — Apple Developer videos that have a transcript on disk.
  Built by `build_index.py` from a saved grid page (see below).
- **`metal_samples.csv`** — Apple's Metal sample code library (48 samples),
  hand-authored from `metal_samples.txt`. See [Metal samples dataset](#metal-samples-dataset).

## Layout

```
videos.csv          # video index (skill data)
metal_samples.csv   # samples index (skill data)
metal_samples.txt   # raw source for metal_samples.csv
transcipts/         # transcript text files, named <collection>-<id>.txt
tools/              # reusable tooling (maintainer-only)
  build_index.py    #   regenerates videos.csv from a saved page
  test_build_index.py
  videos.html       #   the saved grid page (re-save to refresh)
docs/               # design spec
```

The datasets and transcripts at the root are what the (upcoming) Metal skill
consumes; `tools/` is only needed to regenerate `videos.csv`.

---

# Apple video → CSV index

Turns a saved Apple Developer videos grid page into a searchable CSV index, so a
coding agent (or a Metal developer) can quickly find the right video **and its
transcript**. A row is written only when a matching transcript exists, so every
entry is immediately usable.

## Requirements

Python 3 (standard library only — no `pip install`).

## Usage

1. Open the Apple videos page in a browser, **Save Page As → HTML**, and save it
   over `tools/videos.html` (or point at another file with `--html`).
2. Put transcripts in `transcipts/` named `<collection>-<id>.txt`
   (e.g. `tech-talks-111432.txt`, `wwdc2024-10089.txt`, `meet-with-apple-231.txt`).
   This mirrors a video's URL path `/videos/play/<collection>/<id>/`. Matching uses
   the full `collection+id`, because the same id is reused across collections
   (`tech-talks-602`, `wwdc2014-602`, `wwdc2015-602` are different videos).
3. Run it from the repo root — no flags needed:

   ```
   python3 tools/build_index.py
   ```

   The defaults are location-aware: input `tools/videos.html`, transcripts
   `./transcipts`, output `./videos.csv`. Override any with:

   | Flag | Default | Meaning |
   |---|---|---|
   | `--html` | `tools/videos.html` | Saved grid HTML to parse |
   | `--transcripts` | `./transcipts` | Folder of `<collection>-<id>.txt` files |
   | `--out` | `./videos.csv` | Output CSV path |

Each run prints a summary, e.g. `parsed 1424 cards -> wrote 103 rows (skipped duplicates and cards without a transcript)`.

## Output columns

`id`, `title`, `description`, `keywords`, `topics`, `platforms`, `event`,
`collection`, `duration`, `video_url`, `thumbnail_url`, `transcript_path`.

The `keywords`, `topics`, `platforms`, and `description` columns are the search
signals; `transcript_path` is where to read the transcript.

## Tests

```
cd tools && python3 -m unittest test_build_index
```

## Notes

- Only videos with a transcript on disk are indexed; the rest are skipped.
- Each video (`collection` + `id`) is written at most once, even if its card
  appears multiple times in the HTML.
- `related_links` is not included (it lives on each video's detail page, not the
  grid). The parser is structured so a detail-page enrichment pass can add it later.

---

# Metal samples dataset

`metal_samples.csv` indexes the 48 samples in Apple's [Metal sample code
library](https://developer.apple.com/documentation/metal), grouped by topic and
tagged for search. The raw source text lives in `metal_samples.txt`; the CSV was
written directly (no build script), so to update it edit the CSV.

## Columns

| Column | Example | Purpose |
|---|---|---|
| `id` | `rendering-a-scene-with-deferred-lighting-in-swift` | stable slug to reference a sample |
| `topic` | `Lighting techniques` | one of the 12 library sections |
| `title` | `Rendering a scene with deferred lighting in Swift` | exact sample name |
| `description` | `Avoid expensive lighting calculations…` | full-text search |
| `language` | `Swift` | `Swift` / `Objective-C` / `C++` where a variant exists, else blank |
| `tags` | `lighting-techniques,lighting,deferred-shading,…` | concept keywords for matching |
| `source_available` | `false` | the sample's source code is **not** bundled here |
| `source_code_path` | *(blank)* | where the source lives once provided |

## Requesting source code

The library text has no source code, so every row starts with
`source_available=false` and an empty `source_code_path`. When an agent needs a
sample, it should **ask the developer for that sample's source by `id`/`title`**.
Once you add the source, set `source_available=true` and put the location in
`source_code_path` — the same "is it here, and where?" pattern as the video
index's `transcript_path`.
