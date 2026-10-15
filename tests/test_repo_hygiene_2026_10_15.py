# -*- coding: ascii -*-
"""REPO_HYGIENE_2026_10_15: .gitignore keeps an e-text's import (data/raw_<book>_ce) and the heal logs out of the repo;
release.ps1 refuses them as it refuses the other working dirs, and never refuses a path being taken out (a D in the
status). Temp files only; nothing is committed."""
import re, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
GI = REPO / ".gitignore"
PS = SCRIPTS / "release.ps1"
APPLIED = GI.exists() and b"REPO_HYGIENE_2026_10_15" in GI.read_bytes()


@unittest.skipUnless(APPLIED, "REPO_HYGIENE_2026_10_15 is not applied here")
class TheIgnore(unittest.TestCase):
    @unittest.skipUnless(shutil.which("git"), "git is not installed")
    def test_what_git_leaves_out(self):
        with tempfile.TemporaryDirectory() as d:
            shutil.copy2(GI, Path(d) / ".gitignore")
            subprocess.run(["git", "init", "-q", d], check=True)
            ign = lambda p: subprocess.run(["git", "-C", d, "check-ignore", "-q", p]).returncode == 0
            self.assertTrue(ign("data/raw_mbh01_ce/MBh01_0001.jsonl"))
            self.assertTrue(ign("data/raw_mbh02_ce/MBh02_0001.jsonl"))
            self.assertTrue(ign("data/heal/etext_meta_MBh01_20261014_210000.jsonl"))
            self.assertFalse(ign("scripts/heal_etext_meta.py"))
            self.assertFalse(ign("docs/SCHOLAR_V21_2026-10-14.md"))

    def test_the_release_check(self):
        src = PS.read_text(encoding="ascii")
        self.assertIn("if ($line.Substring(0, 2) -match 'D') { continue }", src)
        pat = re.search(r"if \(\$p -match '(\(\^\|/\|\\\\\)data[^']+)'\)", src).group(1)
        rx = re.compile(pat)
        self.assertTrue(rx.search("data/raw_mbh01_ce/MBh01_0001.jsonl"))
        self.assertTrue(rx.search("data/heal/x.jsonl"))
        self.assertFalse(rx.search("data/raw_mbh01/x.jsonl"))
        self.assertFalse(rx.search("scripts/heal_etext_meta.py"))
        self.assertTrue(all(x < 128 for x in PS.read_bytes()), "PowerShell 5.1: ASCII")


class ThePatcher(unittest.TestCase):
    def test_it_applies_once_to_what_it_found(self):
        baks = {".gitignore": sorted(REPO.glob(".gitignore.bak_hygiene_*")),
                "scripts/release.ps1": sorted(SCRIPTS.glob("release.ps1.bak_hygiene_*"))}
        if not all(baks.values()):
            self.skipTest("no pre-patch copies")
        pat = [sys.executable, str(SCRIPTS / "patch_repo_hygiene_2026_10_15.py")]
        with tempfile.TemporaryDirectory() as td:
            t = Path(td); (t / "scripts").mkdir()
            for rel, b in baks.items():
                shutil.copy2(b[0], t / rel)
            r = subprocess.run(pat + ["--check"], cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual((t / ".gitignore").read_bytes(), GI.read_bytes())
            self.assertEqual((t / "scripts" / "release.ps1").read_bytes(), PS.read_bytes())
            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)
            shutil.copy2(baks[".gitignore"][0], t / ".gitignore")
            shutil.copy2(baks["scripts/release.ps1"][0], t / "scripts" / "release.ps1")
            p = t / "scripts" / "release.ps1"
            p.write_bytes(p.read_bytes().replace(b"raw_vision|raw_merged|probe", b"raw_vision|probe"))
            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("anchor 1 found 0 times", r.stdout)
            self.assertNotIn(b"REPO_HYGIENE", (t / ".gitignore").read_bytes(), "all or nothing")

    def test_files(self):
        for p in (SCRIPTS / "patch_repo_hygiene_2026_10_15.py", Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(all(x < 128 for x in b), p); self.assertIn(b"REPO_HYGIENE_2026_10_15", b)


if __name__ == "__main__":
    unittest.main()
