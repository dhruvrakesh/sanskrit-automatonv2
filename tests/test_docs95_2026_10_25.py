# -*- coding: ascii -*-
"""DOCS95_2026_10_25: 25 Oct recorded in the seven running documents and README.md, and the three new documents
(VAMSA, CONSOLIDATION, EVOLUTION). The patcher replays on copies of the documents as they were before it, refuses
without what it records, and does nothing the second time."""
import shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_docs95_2026_10_25.py"
MARK = "DOCS95_2026_10_25"
DOCS = ["docs/DEBT_2026-10-22.md", "docs/STATE_2026-10-18.md", "RUNBOOK.md", "docs/PLATFORM_2026-10-04.md",
        "docs/ENTERPRISE_PATH_2026-10-04.md", "docs/ASKS_2026-10-22.md", "docs/RELATIONS_AND_ASK_2026-10-22.md",
        "README.md"]
NEW = {"docs/VAMSA_2026-10-25.md": "VAMSA_CHECK_2026_10_25", "docs/CONSOLIDATION_2026-10-25.md": "AUTO_REPAIR_2026_10_25",
       "docs/EVOLUTION_2026-10-25.md": "EVOLUTION_2026_10_25"}
REQ = ["scripts/vamsa_check.py", "scripts/vamsa_view.py", "scripts/vamsa.html", "scripts/patch_vamsa_ui_2026_10_25.py",
       "tests/test_vamsa_2026_10_25.py", "scripts/repair_auto.py", "scripts/patch_auto_repair_2026_10_25.py",
       "tests/test_auto_repair_2026_10_25.py"] + list(NEW)


def before(rel: str) -> bytes:
    p = REPO / rel
    bak = sorted(p.parent.glob(p.name + ".bak_docs95_*"))
    return (bak[0] if bak else p).read_bytes()


class TestDocs95(unittest.TestCase):
    def test_new_documents(self):
        for rel, mark in NEW.items():
            t = (REPO / rel).read_text(encoding="utf-8")
            self.assertIn(mark, t, rel)
        v = (REPO / "docs/VAMSA_2026-10-25.md").read_text(encoding="utf-8")
        for s in ("4,910", "7,098", "reference only", "Vayupurana", "CC BY-NC-SA 4.0", "G4"):
            self.assertIn(s, v)
        c = (REPO / "docs/CONSOLIDATION_2026-10-25.md").read_text(encoding="utf-8")
        for s in ("$0.25 a day", "reserve", "Daivat-Sanhita", "--allow 0"):
            self.assertIn(s, c)

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
            self.assertIn("**/vamsa**", (t / "README.md").read_text(encoding="utf-8"))
            r2 = subprocess.run([sys.executable, str(PAT)], cwd=str(t), capture_output=True, text=True)
            self.assertIn("Nothing to do", r2.stdout)


if __name__ == "__main__":
    unittest.main()
