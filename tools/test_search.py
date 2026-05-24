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
