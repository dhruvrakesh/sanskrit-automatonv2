# -*- coding: ascii -*-
"""DOCS97_2026_10_25: the genealogies of the indexes on the site recorded in STATE (section 32), RUNBOOK.md and
README.md, and the new docs/INDEX_SITE_2026-10-25.md. The patcher replays on copies of the documents as they were
before it, refuses without what it records, and does nothing the second time."""
import shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs97_2026_10_25.py"
MARK = "DOCS97_2026_10_25"
DOCS = ["docs/STATE_2026-10-18.md", "RUNBOOK.md", "README.md"]
NEW = REPO / "docs" / "INDEX_SITE_2026-10-25.md"
REQ = ["docs/INDEX_SITE_2026-10-25.md", "scripts/index_sync.py"]


def before(rel: str) -> bytes:
    p = REPO / rel
    bak = sorted(p.parent.glob(p.name + ".bak_docs97_*"))
    return (bak[0] if bak else p).read_bytes()


class TestDocs97(unittest.TestCase):
    def test_the_record(self):
        t = NEW.read_text(encoding="utf-8")
        for s in ("INDEX_SITE_2026_10_25", "C21_INDEX_SITE_2026_10_25", "53,628", "CC BY-NC-SA 3.0", "CC BY-NC-SA 4.0",
                  "never a verse", "9,940 of 10,008", "B2", "corpus-index", "--if-configured", "Rollback"):
            self.assertIn(s, t)

    def test_patch_ascii(self):
        self.assertTrue(all(b < 128 for b in PAT.read_bytes()))

    def test_replay(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for rel in DOCS:
                (t / rel).parent.mkdir(parents=True, exist_ok=True)
                (t / rel).write_bytes(before(rel))
            if all(MARK.encode() in (t / rel).read_bytes() for rel in DOCS):
                self.skipTest("no copy from before the patch to replay against")
            r = subprocess.run([sys.executable, str(PAT), "--check"], cwd=str(t), capture_output=True, text=True)
            self.assertIn("REFUSE", r.stdout)                     # without what it records
            for rel in REQ:
                (t / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(REPO / rel, t / rel)
            r = subprocess.run([sys.executable, str(PAT), "--check"], cwd=str(t), capture_output=True, text=True)
            self.assertIn("CHECK OK", r.stdout, r.stdout + r.stderr)
            r = subprocess.run([sys.executable, str(PAT)], cwd=str(t), capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for rel in DOCS:
                self.assertIn(MARK.encode(), (t / rel).read_bytes(), rel)
            self.assertIn("## 32. 25 Oct, night", (t / "docs/STATE_2026-10-18.md").read_text(encoding="utf-8"))
            self.assertIn("**/corpus/genealogies**", (t / "README.md").read_text(encoding="utf-8"))
            r2 = subprocess.run([sys.executable, str(PAT)], cwd=str(t), capture_output=True, text=True)
            self.assertIn("Nothing to do", r2.stdout)


if __name__ == "__main__":
    unittest.main()
