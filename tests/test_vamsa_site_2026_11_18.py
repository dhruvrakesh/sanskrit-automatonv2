# -*- coding: ascii -*-
"""VAMSA_SITE_2026_11_18 (P2a). The dynasties of every work read can go to the site by G5a's road (vamsa_join,
index_sync, C28's table); by default what is sent is as before (G5a's three). A G6 work's title and source come from
vamsa_read; it has no index text code. The patch replays on the copies from before it, once. Temp folders only."""
import inspect, json, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import vamsa_read as VR                    # noqa: E402
import vamsa_join as VJ                    # noqa: E402
import index_sync as IX                    # noqa: E402
import test_vamsa_join_2026_11_11 as T     # noqa: E402  (its graph and statements)

MARK = "VAMSA_SITE_2026_11_18"
PAT = SCRIPTS / "patch_vamsa_site_2026_11_18.py"


def tree(td, works):
    out = Path(td) / "vamsa_read"
    for w in works:
        d = out / w
        d.mkdir(parents=True)
        rec = {"work": w, "chapter": 1, "part": 0, "statements": [
            T.st("X 1", T.IK, "Manu", 1), T.st("X 2", T.VI, T.IK, 1), T.st("X 3", "Kakutstha", T.VI, 1)]}
        (d / "01.json").write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    return out


class TheWorks(unittest.TestCase):
    def test_works_for(self):
        with tempfile.TemporaryDirectory() as td:
            out = tree(td, ["vip4", "hv", "matsya"])
            self.assertEqual(VJ.works_for("all", out), ["vip4"])
            self.assertEqual(VJ.works_for("g6", out), ["hv", "matsya"])
            self.assertEqual(VJ.works_for("every", out), ["vip4", "hv", "matsya"])
            self.assertEqual(VJ.works_for("hv", out), ["hv"])
            self.assertEqual(VJ.works_for("nowork", out), [])

    def test_a_g6_work(self):
        with tempfile.TemporaryDirectory() as td:
            out = tree(td, ["vip4", "hv"])
            got = VJ.dynasties(str(out), "", "", works=VJ.works_for("every", out), graph=T.graph())
            self.assertEqual(sorted(got), ["hv", "vip4"])
            self.assertEqual(got["hv"]["title"], VR.work_of("hv")["title"])
            self.assertEqual(got["hv"]["source"], VR.source_of("hv"))
            self.assertEqual(got["hv"]["text"], "", "no index text code")
            self.assertEqual(got["vip4"]["text"], "vi")
            self.assertEqual(got["vip4"]["source"], VR.source_of("vip4"), "G5a's source as before")
            self.assertEqual(list(VJ.dynasties(str(out), "", "", graph=T.graph())), ["vip4"], "the default as before")

    def test_index_sync_sends_as_before_by_default(self):
        self.assertEqual(inspect.signature(IX.build).parameters["dynasty_works"].default, "all")
        self.assertEqual(inspect.signature(IX.dynasty_rows).parameters["dynasty_works"].default, "all")
        with tempfile.TemporaryDirectory() as td:
            out = tree(td, ["vip4", "hv"])
            keys = lambda w: sorted(r["key"].split(":")[0] for r in IX.dynasty_rows(str(out), "", "", T.graph(), set(), w))
            self.assertEqual(set(keys("all")), {"vip4"})
            self.assertEqual(set(keys("every")), {"vip4", "hv"})
        src = (SCRIPTS / "index_sync.py").read_text(encoding="ascii")
        self.assertIn('"--dynasty-works", default="all", choices=("all", "every")', src)


@unittest.skipUnless(PAT.exists(), "the patch is not here")
class ThePatch(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f in (PAT, Path(__file__)):
            f.read_bytes().decode("ascii")

    def test_replays_once(self):
        files = ("scripts/vamsa_join.py", "scripts/index_sync.py")
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for rel in files:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_vamsasite_*"))
                srcb = (bak[0] if bak else p).read_bytes()
                if MARK.encode() in srcb:
                    self.skipTest("only patched copies to replay against")
                (t / rel).parent.mkdir(parents=True, exist_ok=True)
                (t / rel).write_bytes(srcb)
            run = lambda *a: subprocess.run([sys.executable, str(PAT)] + list(a), cwd=str(t), capture_output=True, text=True)
            self.assertIn("CHECK OK: 2 file(s)", run("--check").stdout)
            r = run()
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for rel in files:
                if MARK.encode() in (REPO / rel).read_bytes():
                    self.assertEqual((t / rel).read_bytes(), (REPO / rel).read_bytes(), rel)
            self.assertIn("Nothing to do", run().stdout)


if __name__ == "__main__":
    unittest.main()
