# -*- coding: ascii -*-
"""SITE_LINE_2026_10_07: the Srangam status generator stops calling the corpus "loaded, no reading page"
once /texts is live, and carries the 2026-10-07 site measurement. Runs on a fixture with the exact
original text, and also on the real D:\\srangam-42267 file when it exists (skipped otherwise)."""
import importlib.util, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "scripts" / "patch_site_line_2026_10_07.py"
REAL = Path(os.environ.get("SRANGAM_ROOT", r"D:\srangam-42267")) / "scripts" / "emit_project_status.py"

FIXTURE = '''from __future__ import annotations
SITE_CORPUS = {
    "measuredOn": "2026-09-27",
    "texts": 1,
    "passages": 439,
    "published": 1,
    "readerPage": False,
}


def _site_line(c: dict) -> str:
    s = c.get("site") or SITE_CORPUS
    if not s.get("texts"):
        return "The Sanskrit corpus is not yet published to this site. Tables exist; nothing is loaded."
    one = s["texts"] == 1
    line = ("%d Sanskrit text%s (%s passages) %s loaded into this site's corpus tables, and %d "
            "%s marked published (measured %s)."
            % (s["texts"], "" if one else "s", f"{s['passages']:,}", "is" if one else "are",
               s["published"], "is" if s["published"] == 1 else "are", s["measuredOn"]))
    if not s.get("readerPage"):
        line += " There is no reading page for %s yet." % ("it" if one else "them")
    return line
'''


def _load(path):
    spec = importlib.util.spec_from_file_location("eps_%d" % id(path), str(path))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


class SiteLine(unittest.TestCase):
    def _run(self, root, *extra):
        return subprocess.run([sys.executable, str(PATCH), "--root", str(root), *extra],
                              capture_output=True, text=True, timeout=60)

    def _fixture_root(self, text=FIXTURE):
        root = Path(tempfile.mkdtemp(prefix="siteline_"))
        (root / "scripts").mkdir()
        (root / "scripts" / "emit_project_status.py").write_text(text, encoding="utf-8", newline="\r\n")
        self.addCleanup(shutil.rmtree, root, True)
        return root

    def test_fixture_before_and_after(self):
        root = self._fixture_root()
        before = _load(root / "scripts" / "emit_project_status.py")
        self.assertIn("no reading page", before._site_line({"works": 65}))
        self.assertEqual(self._run(root, "--check").returncode, 0)
        r = self._run(root); self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self._run(root).stdout.strip(), "Already patched (SITE_LINE_2026_10_07). Nothing to do.")
        raw = (root / "scripts" / "emit_project_status.py").read_bytes()
        self.assertIn(b"\r\n", raw); self.assertNotIn(b"\r\r\n", raw)          # line endings kept
        after = _load(root / "scripts" / "emit_project_status.py")
        self.assertEqual(after.SITE_CORPUS, {"measuredOn": "2026-10-07", "texts": 2, "passages": 1655,
                                             "published": 2, "readerPage": True})
        line = after._site_line({"works": 65})
        self.assertEqual(line, "Only 2 of the 65 works in the corpus can be read on this site so far "
                               "(1,655 passages at /texts, measured 2026-10-07); the rest exist only in the working corpus.")
        old_style = after._site_line({"works": 65, "site": {"texts": 1, "passages": 439, "published": 1,
                                                            "measuredOn": "2026-09-27", "readerPage": False}})
        self.assertIn("There is no reading page for it yet.", old_style)    # unchanged without a reader page

    def test_refuses_when_the_anchor_moved(self):
        root = self._fixture_root(FIXTURE.replace('"texts": 1,', '"texts": 3,'))
        r = self._run(root)
        self.assertEqual(r.returncode, 1); self.assertIn("REFUSING TO WRITE", r.stdout)
        self.assertFalse(list((root / "scripts").glob("*.bak_siteline_*")))

    @unittest.skipUnless(REAL.exists(), "Srangam repo not on this machine")
    def test_real_file_checks_clean(self):
        r = self._run(REAL.parents[1], "--check")
        self.assertIn(r.returncode, (0,), r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
