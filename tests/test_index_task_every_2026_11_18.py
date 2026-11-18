# -*- coding: ascii -*-
"""VAMSA_EVERY_2026_11_18: the scheduled task sends the dynasties of every work read, once applied; it needs
index_sync.py's option (VAMSA_SITE_2026_11_18); line endings kept; the patch replays on the copy from before it, once."""
import shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
S = REPO / "scripts"
PAT = S / "patch_index_task_every_2026_11_18.py"
MARK = "VAMSA_EVERY_2026_11_18"


@unittest.skipUnless(PAT.exists(), "the patch is not here")
class TheTask(unittest.TestCase):
    def setUp(self):
        task = S / "corpus_mirror_task.ps1"
        bak = sorted(S.glob("corpus_mirror_task.ps1.bak_indexevery_*"))
        self.src = bak[0] if bak else task
        if MARK.encode() in self.src.read_bytes():
            self.skipTest("only a patched task to replay against")
        self.td = tempfile.TemporaryDirectory()
        self.t = Path(self.td.name)
        (self.t / "scripts").mkdir()
        shutil.copy2(self.src, self.t / "scripts" / "corpus_mirror_task.ps1")

    def tearDown(self):
        self.td.cleanup()

    def run_pat(self, *a):
        return subprocess.run([sys.executable, str(PAT)] + list(a), cwd=str(self.t), capture_output=True, text=True)

    def test_refused_without_the_option(self):
        (self.t / "scripts" / "index_sync.py").write_text("# no option here\n", encoding="ascii")
        r = self.run_pat()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("REFUSE", r.stdout)

    def test_replays_once(self):
        shutil.copy2(S / "index_sync.py", self.t / "scripts" / "index_sync.py")
        if b"VAMSA_SITE_2026_11_18" not in (S / "index_sync.py").read_bytes():
            self.skipTest("index_sync.py has no VAMSA_SITE_2026_11_18 here")
        self.assertIn("CHECK OK: 1 file(s)", self.run_pat("--check").stdout)
        r = self.run_pat()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        raw = (self.t / "scripts" / "corpus_mirror_task.ps1").read_bytes()
        self.assertTrue(raw.isascii())
        self.assertIn(b"& $py scripts\\index_sync.py --apply --if-configured --dynasty-works every 2>&1", raw)
        self.assertEqual(raw.count(b"index_sync.py --apply"), 1)
        self.assertEqual(raw.count(b"\r\n") > 0, self.src.read_bytes().count(b"\r\n") > 0, "line endings kept")
        self.assertIn("Nothing to do", self.run_pat().stdout)

    def test_ascii(self):
        for f in (PAT, Path(__file__)):
            self.assertTrue(f.read_bytes().isascii(), f.name)


if __name__ == "__main__":
    unittest.main()
