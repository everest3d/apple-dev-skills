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
