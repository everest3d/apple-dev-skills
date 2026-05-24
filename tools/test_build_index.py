"""Tests for build_index.py — Apple video grid HTML -> CSV index.

Run: python3 -m unittest test_build_index
"""

import csv
import tempfile
import unittest
from pathlib import Path

import build_index


# The exact card the user provided (id 111433), with a full h5 title.
CARD_111433 = """
<a href="/videos/play/tech-talks/111433/" class="vc-card tile tile-rounded grid-item large-span-4" data-released="true" data-category="0">
  <div class="vc-card__media">
    <div class="vc-card__image-container">
      <img class="vc-card__image" width="250" src="https://devimages-cdn.apple.com/wwdc-services/images/8/10623/10623_wide_250x141_2x.jpg" alt="Prepare your app for Accessibility Nutrition Labels" loading="lazy">
      <span class="vc-card__duration">34:50</span>
    </div>
  </div>
  <div class="vc-card__content">
    <div class="tile-content">
      <h5 class="vc-card__title">Prepare your app for Accessibility Nutrition Labels</h5>
      <div class="vc-card__tags lighter smaller">
        <span class="vc-card__tag vc-card__tag--event">Tech Talks</span>
      </div>
      <span class="vc-card__keywords hidden"
        data-filter-title="prepare your app for accessibility nutrition labels"
        data-filter-description="learn how to prepare your app for accessibility nutrition labels by supporting essential accessibility features."
        data-filter-keywords="accessibility,inclusion,nutrition label"
        data-filter-collectionid="tech-talks"
        data-filter-subtitle="english"
        data-filter-platform="ios|ipados|macos|tvos|visionos|watchos"
        data-filter-topics="Accessibility &amp; Inclusion"></span>
    </div>
  </div>
</a>
"""

# A second card (id 111432) with NO <h5> title, to exercise the img-alt fallback.
CARD_111432 = """
<a href="/videos/play/tech-talks/111432/" class="vc-card tile" data-released="true">
  <div class="vc-card__media">
    <div class="vc-card__image-container">
      <img class="vc-card__image" src="https://example.com/img2.jpg" alt="Second Talk" loading="lazy">
      <span class="vc-card__duration">12:00</span>
    </div>
  </div>
  <div class="vc-card__content">
    <div class="tile-content">
      <div class="vc-card__tags lighter smaller">
        <span class="vc-card__tag vc-card__tag--event">Tech Talks</span>
      </div>
      <span class="vc-card__keywords hidden"
        data-filter-description="second description"
        data-filter-keywords="metal,graphics"
        data-filter-collectionid="tech-talks"
        data-filter-platform="ios|macos"
        data-filter-topics="Graphics &amp; Games"></span>
    </div>
  </div>
</a>
"""


# A WWDC card whose URL path collection ("wwdc2025") differs from its short
# data-filter-collectionid ("wwdc25") and event label ("WWDC25").
CARD_WWDC = """
<a href="/videos/play/wwdc2025/236/" class="vc-card tile" data-released="true">
  <div class="vc-card__media">
    <div class="vc-card__image-container">
      <img class="vc-card__image" src="https://example.com/w.jpg" alt="WWDC Talk" loading="lazy">
      <span class="vc-card__duration">20:00</span>
    </div>
  </div>
  <div class="vc-card__content">
    <div class="tile-content">
      <h5 class="vc-card__title">A WWDC Session</h5>
      <div class="vc-card__tags lighter smaller">
        <span class="vc-card__tag vc-card__tag--event">WWDC25</span>
      </div>
      <span class="vc-card__keywords hidden"
        data-filter-description="a wwdc session description."
        data-filter-keywords="metal"
        data-filter-collectionid="wwdc25"
        data-filter-platform="ios|macos"
        data-filter-topics="Graphics &amp; Games"></span>
    </div>
  </div>
</a>
"""


def grid(*cards):
    return '<div class="vc-collection grid grid-gutterless">' + "".join(cards) + "</div>"


class ExtractIdTests(unittest.TestCase):
    def test_extracts_trailing_id_from_relative_href(self):
        self.assertEqual(build_index.extract_id("/videos/play/tech-talks/111433/"), "111433")

    def test_extracts_id_without_trailing_slash(self):
        self.assertEqual(build_index.extract_id("/videos/play/wwdc2024/10123"), "10123")

    def test_extracts_id_from_full_url(self):
        self.assertEqual(
            build_index.extract_id("https://developer.apple.com/videos/play/tech-talks/111432/"),
            "111432",
        )


class BuildVideoUrlTests(unittest.TestCase):
    def test_prefixes_domain_to_relative_href(self):
        self.assertEqual(
            build_index.build_video_url("/videos/play/tech-talks/111433/"),
            "https://developer.apple.com/videos/play/tech-talks/111433/",
        )

    def test_leaves_absolute_url_untouched(self):
        url = "https://developer.apple.com/videos/play/tech-talks/111433/"
        self.assertEqual(build_index.build_video_url(url), url)


class ParseCardsTests(unittest.TestCase):
    def test_extracts_all_fields_from_a_card(self):
        cards = build_index.parse_cards(grid(CARD_111433))
        self.assertEqual(len(cards), 1)
        c = cards[0]
        self.assertEqual(c["href"], "/videos/play/tech-talks/111433/")
        self.assertEqual(c["title"], "Prepare your app for Accessibility Nutrition Labels")
        self.assertEqual(c["img_alt"], "Prepare your app for Accessibility Nutrition Labels")
        self.assertEqual(
            c["img_src"],
            "https://devimages-cdn.apple.com/wwdc-services/images/8/10623/10623_wide_250x141_2x.jpg",
        )
        self.assertEqual(c["duration"], "34:50")
        self.assertEqual(c["event"], "Tech Talks")
        self.assertEqual(c["keywords"], "accessibility,inclusion,nutrition label")
        self.assertEqual(c["topics"], "Accessibility & Inclusion")  # entity decoded
        self.assertEqual(c["platforms"], "ios|ipados|macos|tvos|visionos|watchos")
        self.assertEqual(c["collection"], "tech-talks")
        self.assertTrue(c["description"].startswith("learn how to prepare your app"))

    def test_parses_multiple_cards(self):
        cards = build_index.parse_cards(grid(CARD_111433, CARD_111432))
        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[1]["href"], "/videos/play/tech-talks/111432/")
        self.assertEqual(cards[1]["title"], "")  # no h5 in this card
        self.assertEqual(cards[1]["img_alt"], "Second Talk")


class FindTranscriptTests(unittest.TestCase):
    def test_returns_path_for_collection_and_id(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "tech-talks-111433.txt").write_text("hello")
            result = build_index.find_transcript("tech-talks", "111433", Path(d))
            self.assertIsNotNone(result)
            self.assertEqual(result.name, "tech-talks-111433.txt")

    def test_returns_none_when_file_missing(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(build_index.find_transcript("tech-talks", "999999", Path(d)))

    def test_id_alone_does_not_match_across_collections(self):
        # The id 602 exists under several collections; matching must be exact.
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "wwdc2014-602.txt").write_text("hello")
            self.assertIsNone(build_index.find_transcript("tech-talks", "602", Path(d)))
            self.assertIsNotNone(build_index.find_transcript("wwdc2014", "602", Path(d)))


class BuildRowsTests(unittest.TestCase):
    def test_only_includes_cards_with_a_transcript(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "tech-talks-111433.txt").write_text("transcript")  # 111432 has none
            cards = build_index.parse_cards(grid(CARD_111433, CARD_111432))
            rows = build_index.build_rows(cards, Path(d))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["id"], "111433")

    def test_row_has_full_video_url_and_transcript_path(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "tech-talks-111433.txt").write_text("transcript")
            cards = build_index.parse_cards(grid(CARD_111433))
            row = build_index.build_rows(cards, Path(d))[0]
            self.assertEqual(
                row["video_url"], "https://developer.apple.com/videos/play/tech-talks/111433/"
            )
            self.assertTrue(row["transcript_path"].endswith("tech-talks-111433.txt"))

    def test_title_falls_back_to_img_alt_when_h5_missing(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "tech-talks-111432.txt").write_text("transcript")
            cards = build_index.parse_cards(grid(CARD_111432))
            row = build_index.build_rows(cards, Path(d))[0]
            self.assertEqual(row["title"], "Second Talk")

    def test_dedupes_repeated_cards_by_collection_and_id(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "tech-talks-111433.txt").write_text("transcript")
            cards = build_index.parse_cards(grid(CARD_111433, CARD_111433))
            rows = build_index.build_rows(cards, Path(d))
            self.assertEqual(len(rows), 1)

    def test_transcript_path_is_relative_to_out_dir(self):
        # A relative path keeps the CSV portable: it resolves wherever the CSV
        # and its sibling transcripts folder are copied (repo root, skill bundle).
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            tdir = d / "transcipts"
            tdir.mkdir()
            (tdir / "tech-talks-111433.txt").write_text("transcript")
            cards = build_index.parse_cards(grid(CARD_111433))
            rows = build_index.build_rows(cards, tdir, out_dir=d)
            self.assertEqual(rows[0]["transcript_path"], "transcipts/tech-talks-111433.txt")


class CollectionConsistencyTests(unittest.TestCase):
    def test_collection_matches_url_path_not_short_event_code(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "wwdc2025-236.txt").write_text("transcript")
            cards = build_index.parse_cards(grid(CARD_WWDC))
            row = build_index.build_rows(cards, Path(d))[0]
            # collection, video_url and transcript_path must all agree on wwdc2025.
            self.assertEqual(row["collection"], "wwdc2025")
            self.assertTrue(row["video_url"].endswith("/wwdc2025/236/"))
            self.assertTrue(row["transcript_path"].endswith("wwdc2025-236.txt"))


class MainEndToEndTests(unittest.TestCase):
    def test_writes_only_rows_with_transcripts(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            html_path = d / "videos.html"
            html_path.write_text(grid(CARD_111433, CARD_111432))
            tdir = d / "transcipts"
            tdir.mkdir()
            (tdir / "tech-talks-111433.txt").write_text("transcript")  # 111432 intentionally missing
            out = d / "videos.csv"

            build_index.main(["--html", str(html_path), "--transcripts", str(tdir), "--out", str(out)])

            with out.open(newline="") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["id"], "111433")
            self.assertEqual(
                rows[0]["video_url"], "https://developer.apple.com/videos/play/tech-talks/111433/"
            )
            self.assertNotIn("111432", [r["id"] for r in rows])

    def test_does_not_insert_the_same_video_twice(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            html_path = d / "videos.html"
            html_path.write_text(grid(CARD_111433, CARD_111433))  # same card twice
            tdir = d / "transcipts"
            tdir.mkdir()
            (tdir / "tech-talks-111433.txt").write_text("transcript")
            out = d / "videos.csv"

            build_index.main(["--html", str(html_path), "--transcripts", str(tdir), "--out", str(out)])

            with out.open(newline="") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 1)

    def test_empty_transcripts_folder_yields_header_only(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            html_path = d / "videos.html"
            html_path.write_text(grid(CARD_111433))
            tdir = d / "transcipts"
            tdir.mkdir()
            out = d / "videos.csv"

            build_index.main(["--html", str(html_path), "--transcripts", str(tdir), "--out", str(out)])

            with out.open(newline="") as f:
                content = list(csv.reader(f))
            self.assertEqual(len(content), 1)  # header only
            self.assertIn("id", content[0])
            self.assertIn("transcript_path", content[0])


if __name__ == "__main__":
    unittest.main()
