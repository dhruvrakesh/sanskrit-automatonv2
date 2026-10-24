# -*- coding: ascii -*-
"""KIN_LINES_2026_10_24: the lines of descent in kin_lineages.md join only the index's own entries. Two persons of one
name (Janamejaya (I), son of Puru, and Janamejaya (II), son of Pariksit) are one entity in our names, and the old
lineages() ran one line through both; lines() keeps them apart, takes a homonym's number ("(II)", "[2]", "3."), takes
an unnumbered homonym only when exactly one of them names the other person, never crosses from one index to another,
and counts the steps both entries state. Then kin_index.py --check writes the new page. A made-up database and a stub
model in a temp folder; never data/context.db, never the network."""
import contextlib, importlib.util, io, sqlite3, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOOL = REPO / "scripts" / "kin_index.py"
PAT = REPO / "scripts" / "patch_kin_lines_2026_10_24.py"
BASE_TEST = REPO / "tests" / "test_kin_index_2026_10_23.py"
MARK = "KIN_LINES_2026_10_24"
ON = TOOL.exists() and MARK.encode() in TOOL.read_bytes()
JAN = 1    # one entity id for every Janamejaya, as in our names


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def row(src, eid, head, subj, rel, obj, s_ent=None, o_ent=None, kept=True):
    return {"source": src, "entry_id": eid, "head": head, "subject": subj, "relation": rel, "object": obj,
            "kept": kept, "subject_entity": s_ent, "object_entity": o_ent, "subject_name": subj, "object_name": obj}


# The Purana Index: Yayati (one entry) > Puru (I) > Janamejaya (I) > Pracinvat; Abhimanyu > Pariksit (I) >
# Janamejaya (II) > Satanika. Janamejaya (I) and (II) are one entity in our names (id 1).
HEADS = [(10, "pui", "Yay\u0101ti"), (11, "pui", "P\u016bru (I)"), (12, "pui", "P\u016bru (II)"),
         (13, "pui", "Janamejaya (I)"), (14, "pui", "Janamejaya (II)"), (15, "pui", "Pr\u0101cinvat"),
         (16, "pui", "Abhimanyu"), (17, "pui", "Parik\u1e63it (I)"), (18, "pui", "\u015aat\u0101n\u012bka"),
         (30, "vei", "3. \u1e5a\u1e63abha"), (31, "vei", "Vi\u015bv\u0101mitra"), (40, "inm", "Jaratk\u0101ru[2]"),
         (41, "inm", "\u0100st\u012bka")]
ROWS = [
    row("pui", 11, "P\u016bru (I)", "P\u016bru (I)", "son_of", "Yay\u0101ti", 2, 3),
    row("pui", 10, "Yay\u0101ti", "Yay\u0101ti", "father_of", "P\u016bru", 3, 2),     # Puru: two homonyms, (I) names Yayati
    row("pui", 13, "Janamejaya (I)", "Janamejaya (I)", "son_of", "P\u016bru (I)", JAN, 2),
    row("pui", 13, "Janamejaya (I)", "Janamejaya (I)", "father_of", "Pr\u0101cinvat", JAN, 4),
    row("pui", 17, "Parik\u1e63it (I)", "Parik\u1e63it (I)", "son_of", "Abhimanyu", 5, 6),
    row("pui", 14, "Janamejaya (II)", "Janamejaya (II)", "son_of", "Parik\u1e63it (I)", JAN, 5),
    row("pui", 14, "Janamejaya (II)", "Janamejaya (II)", "father_of", "\u015aat\u0101n\u012bka", JAN, 7),
    row("pui", 18, "\u015aat\u0101n\u012bka", "\u015aat\u0101n\u012bka", "son_of", "Janamejaya", 7, JAN),  # no number: (II) names him
    row("pui", 15, "Pr\u0101cinvat", "Pr\u0101cinvat", "son_of", "Janamejaya", 4, JAN, kept=False),       # set aside
    row("vei", 30, "3. \u1e5a\u1e63abha", "\u1e5a\u1e63abha (3)", "son_of", "Vi\u015bv\u0101mitra", 8, 9),
    row("inm", 40, "Jaratk\u0101ru[2]", "Jaratk\u0101ru[2]", "mother_of", "\u0100st\u012bka", 10, 11),
]


@unittest.skipUnless(ON, "KIN_LINES_2026_10_24 is not applied here")
class TheLines(unittest.TestCase):
    def setUp(self):
        self.m = load(TOOL, "kin_lines_t")
        con = sqlite3.connect(":memory:")
        con.execute("CREATE TABLE shelf_entries (id INTEGER PRIMARY KEY, source TEXT, head TEXT)")
        con.executemany("INSERT INTO shelf_entries VALUES (?,?,?)", HEADS)
        self.heads = self.m.heads_index(con)
        con.close()

    def test_marks(self):
        sm = self.m.split_mark
        self.assertEqual(sm("Janamejaya (II)"), ("janamejaya", 2))
        self.assertEqual(sm("Jaratk\u0101ru[2]"), ("jaratkaru", 2))
        self.assertEqual(sm("3. \u1e5a\u1e63abha"), sm("\u1e5a\u1e63abha (3)"))
        self.assertEqual(sm("\u015araddh\u0101(dev\u012b) (IV)"), ("sraddha", 4))
        self.assertEqual(sm("P\u016bru"), ("puru", 0))

    def test_homonyms_kept_apart(self):
        got = self.m.lines(ROWS, self.heads, min_len=3)
        pui = [chain for chain, _, _ in got["pui"]]
        self.assertIn(["Yay\u0101ti", "P\u016bru (I)", "Janamejaya (I)", "Pr\u0101cinvat"], pui)
        self.assertIn(["Abhimanyu", "Parik\u1e63it (I)", "Janamejaya (II)", "\u015aat\u0101n\u012bka"], pui)
        self.assertEqual(len(pui), 2, "the two Janamejayas never join: %r" % pui)
        both = dict((tuple(c), b) for c, b, _ in got["pui"])
        self.assertEqual(both[("Yay\u0101ti", "P\u016bru (I)", "Janamejaya (I)", "Pr\u0101cinvat")], 1,
                         "Yayati > Puru (I) is stated by both entries; Prachinvat's own was set aside")
        self.assertEqual(both[("Abhimanyu", "Parik\u1e63it (I)", "Janamejaya (II)", "\u015aat\u0101n\u012bka")], 1)
        self.assertNotIn("vei", [k for k, v in got.items() if v], "a line of two is not a line")

    def test_the_old_function_crosses(self):
        old = self.m.lineages(ROWS, min_len=4)   # kept for the record; no longer exported
        crossed = [chain for chain, _ in old if ("Yay\u0101ti" in chain and "\u015aat\u0101n\u012bka" in chain)
                   or ("Abhimanyu" in chain and "Pr\u0101cinvat" in chain)]
        self.assertTrue(crossed, "by our ids one Janamejaya joins Puru's line to Pariksit's: %r" % old)

    def test_an_unnumbered_homonym_needs_the_other_to_name_him(self):
        rows = [row("pui", 11, "P\u016bru (I)", "P\u016bru (I)", "son_of", "Yay\u0101ti"),
                row("pui", 13, "Janamejaya (I)", "Janamejaya (I)", "son_of", "P\u016bru"),        # two Purus
                row("pui", 99, "Ka\u1e47va", "Ka\u1e47va", "son_of", "Janamejaya")]              # two Janamejayas
        got = self.m.lines(rows, self.heads, min_len=3)
        self.assertEqual(got["pui"], [], "neither Puru names Janamejaya, neither Janamejaya names Kanva: no line")
        rows.append(row("pui", 11, "P\u016bru (I)", "P\u016bru (I)", "father_of", "Janamejaya"))
        got = self.m.lines(rows, self.heads, min_len=3)
        self.assertEqual(got["pui"], [(["Yay\u0101ti", "P\u016bru (I)", "Janamejaya (I)"], 1, 0)],
                         "Puru (I) names Janamejaya and Janamejaya (I) names Puru: one step in both entries")

    def test_a_name_spelt_otherwise_is_one_line(self):
        heads = {"by": {"pui": {}}, "shown": {}}
        names = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "Dd"]
        for i, n in enumerate(names, 100):
            heads["by"]["pui"][self.m.split_mark(n)[0]] = [(i, 0)]
            heads["shown"][("pui", i)] = n
        chain = ["A", "B", "C", "D", "E", "F", "G", "H"]
        rows = [row("pui", 100 + names.index(c), c, c, "son_of", p) for p, c in zip(chain, chain[1:])]
        rows += [row("pui", 110, "Dd", "Dd", "son_of", "C"), row("pui", 104, "E", "E", "son_of", "Dd")]   # D spelt Dd
        got = self.m.lines(rows, heads, min_len=4)["pui"]
        self.assertEqual(len(got), 1, got)
        self.assertEqual(got[0][2], 1, "the variant through Dd is counted, not listed")

    def test_check_writes_the_page(self):
        B = load(BASE_TEST, "kin_base_lines_t")
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "data" / "shelf").mkdir(parents=True)
            B.make_db(t / "data" / "context.db")
            B.make_claims(t / "data" / "shelf" / "claims.db")
            calls = []
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = self.m.main(["--root", str(t), "--yes"], caller=B.stub(calls))
            self.assertEqual(rc, 0, buf.getvalue())
            page = (t / "exports" / "kin_lineages.md").read_text(encoding="utf-8")
            self.assertTrue(page.startswith("# Lines of descent in the indexes (KIN_LINES_2026_10_24)"))
            self.assertIn("never jumps from one person to another of the same name", page)


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f in (TOOL, PAT, Path(__file__)):
            if not f.exists():
                self.skipTest("%s is not here" % f.name)
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            if f != TOOL or ON:
                self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
