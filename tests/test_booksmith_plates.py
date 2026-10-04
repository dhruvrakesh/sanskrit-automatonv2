# -*- coding: ascii -*-
"""BOOKSMITH_PLATES_2026_10_04 - approved generated images -> Booksmith plates (opt-in).
Booksmith itself is not needed: its config read/write is replaced by a fake.
Fails before patch_booksmith_plates.py (no sync_plates), passes after."""
import importlib, shutil, sqlite3, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


class FakeConfig:
    def __init__(self, plates=(), ipv=3):
        self.plates, self.ipv, self.writes = list(plates), ipv, 0

    def __call__(self, new=None, ipv=None):
        if new is not None:
            self.plates, self.ipv = list(new), int(ipv); self.writes += 1
        return {"plate_paths": list(self.plates), "ipv": self.ipv}


class Plates(unittest.TestCase):
    def setUp(self):
        self.bb = importlib.import_module("booksmith_build")
        self.tmp = Path(tempfile.mkdtemp(prefix="plates_"))
        self.db = str(self.tmp / "t.db")
        import db_utils, images
        con = sqlite3.connect(self.db)
        db_utils.ensure_schema(con); images.ensure_schema(con)
        con.execute("INSERT INTO docs(code) VALUES('TestDoc')")
        did = con.execute("SELECT id FROM docs").fetchone()[0]
        rows = [("approved", "generated", 5, 1), ("approved", "generated", 2, 1),
                ("approved", "edition-plate", 3, 1), ("draft", "generated", 4, 1)]
        for i, (st, kind, pg, ix) in enumerate(rows, 1):
            f = self.tmp / ("%d_v1.jpg" % i); f.write_bytes(b"img%d" % i)
            con.execute("INSERT INTO doc_images(doc_id,lineage_id,version,kind,status,anchor_page,anchor_idx,path)"
                        " VALUES(?,?,?,?,?,?,?,?)", (did, i, 1, kind, st, pg, ix, str(f)))
        con.commit(); con.close()
        self.project = self.tmp / "proj"
        (self.project / "work").mkdir(parents=True); (self.project / "build").mkdir()
        (self.project / "book.yaml").write_text("project_id: proj\n", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def sync(self, cfg):
        return self.bb.sync_plates(Path("unused"), self.project, self.db, "TestDoc", config_io=cfg)

    def test_only_approved_generated_in_anchor_order(self):
        cfg = FakeConfig(); rep = self.sync(cfg)
        self.assertEqual(rep["action"], "updated")
        self.assertEqual(cfg.plates, ["assets/plates/imglib_2_v1.jpg", "assets/plates/imglib_1_v1.jpg"])
        self.assertEqual(cfg.ipv, 2)
        self.assertTrue((self.project / "assets/plates/imglib_2_v1.jpg").exists())
        self.assertTrue(list((self.project / "work").glob("book.yaml.bak_plates_*")))

    def test_idempotent(self):
        cfg = FakeConfig(); self.sync(cfg); n = cfg.writes
        rep = self.sync(cfg)
        self.assertEqual(rep["action"], "unchanged"); self.assertEqual(cfg.writes, n)

    def test_keeps_the_projects_own_plates(self):
        cfg = FakeConfig(plates=["assets/plates/frontispiece.png"]); self.sync(cfg)
        self.assertEqual(cfg.plates[0], "assets/plates/frontispiece.png")
        self.assertEqual(len(cfg.plates), 3)

    def test_refuses_when_human_decisions_are_frozen(self):
        (self.project / "work" / "manifest.json").write_text("{}", encoding="utf-8")
        (self.project / "work" / "decisions.jsonl").write_text('{"id": 1}\n', encoding="utf-8")
        cfg = FakeConfig()
        with self.assertRaises(RuntimeError):
            self.sync(cfg)
        self.assertEqual(cfg.writes, 0)
        self.assertFalse((self.project / "assets").exists(), "a refused run must copy nothing")
        self.assertTrue((self.project / "work" / "manifest.json").exists())

    def test_clears_a_stale_manifest_without_decisions(self):
        (self.project / "work" / "manifest.json").write_text("{}", encoding="utf-8")
        (self.project / "build" / "book.pdf").write_bytes(b"%PDF")
        rep = self.sync(FakeConfig())
        self.assertIn("manifest.json", rep["cleared"])
        self.assertFalse((self.project / "work" / "manifest.json").exists())

    def test_cap_of_twelve(self):
        new, copies = self.bb.plan_plates(["own%d.png" % i for i in range(11)],
                                          [{"id": i, "version": 1, "src": Path("x%d.jpg" % i)} for i in range(5)])
        self.assertEqual(len(new), 12); self.assertEqual(len(copies), 1)


if __name__ == "__main__":
    unittest.main()
