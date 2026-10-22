# -*- coding: ascii -*-
"""DOC_REGISTER_2026_10_22: scripts/doc_register.py reads the ENTERPRISE_PATH's tables as one register: a label
reused for another item stays apart, each item keeps its last state and the date that last recorded it, "open" is
read from the state's first words, and the CSV says which labels are reused. A made-up file in a temp folder."""
import csv, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOOL = REPO / "scripts" / "doc_register.py"
MARK = "DOC_REGISTER_2026_10_22"
EP = """# path

## Addendum 2026-10-07 (3)

| # | Item | State |
|---|---|---|
| S1 | Srangam: inspect the migration | Ready to run |
| T1 | The Ganita translate | Open: resume |

## Addendum 2026-10-08 (4)

| # | Item | State |
|---|---|---|
| S1 | Srangam: inspect the migration | Done 2026-10-08 |

## Addendum 2026-10-22 (77) (DOCS87_2026_10_22)

| # | Item | State |
|---|---|---|
| S1 | Srangam's SEO Phase AN, uncommitted | Yours: add by name |
| T1 | The top bar's menus | Done: UI_CLARITY |

## Addendum 2026-10-22 (78) (DOCS88_2026_10_22)

| Key | Item | State |
|---|---|---|
| nirukta-text | The Nirukta's text | Yours |
"""


class TheRegister(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        t = self.t = Path(self.td.name)
        (t / "docs").mkdir()
        (t / "docs" / "ENTERPRISE_PATH_2026-10-04.md").write_text(EP, encoding="utf-8")
        (t / "docs" / "ENTERPRISE_PATH_2026-10-04.md.bak_docs87_20261022").write_text("| X9 | old | Open |\n",
                                                                                      encoding="utf-8")

    def tearDown(self):
        self.td.cleanup()

    def run_tool(self, *a):
        r = subprocess.run([sys.executable, str(TOOL), "--root", str(self.t)] + list(a), capture_output=True,
                           text=True, timeout=60)
        return r.returncode, r.stdout + r.stderr

    def test_reused_labels_stay_apart(self):
        rc, out = self.run_tool()
        self.assertEqual(rc, 0, out)
        self.assertIn("6 rows", out)
        self.assertIn("5 items under 3 labels; 2 labels name more than one item", out)
        with open(self.t / "exports" / "ep_register.csv", encoding="utf-8-sig") as f:
            rows = {(r["label"], r["item"]): r for r in csv.DictReader(f)}
        mig = rows[("S1", "Srangam: inspect the migration")]
        self.assertEqual((mig["state"], mig["open"], mig["times"], mig["last"]), ("Done 2026-10-08", "", "2", "2026-10-08"))
        self.assertEqual(rows[("S1", "Srangam's SEO Phase AN, uncommitted")]["open"], "yes")
        self.assertEqual(rows[("T1", "The Ganita translate")]["open"], "yes", "the old item keeps its own state")
        self.assertEqual(mig["label_reused"], "yes")
        self.assertFalse([k for k in rows if k[0] == "X9"], "a backup is not read")
        self.assertEqual(rows[("nirukta-text", "The Nirukta's text")]["label_reused"], "", "a register key is read too")

    def test_open_before(self):
        rc, out = self.run_tool("--open", "--before", "2026-10-15", "--no-write")
        self.assertEqual(rc, 0, out)
        self.assertIn("2026-10-07  T1    The Ganita translate", out)
        self.assertNotIn("Phase AN", out.split("open by their last state")[1].split("VERDICT")[0])
        self.assertFalse((self.t / "exports").exists())

    def test_ascii_and_mark(self):
        for f in (TOOL, Path(__file__)):
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
